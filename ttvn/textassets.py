"""Trích xuất và vá TextAsset trong Unity asset file / bundle bằng UnityPy.

Magic Survival (và đa số game Unity) lưu chuỗi văn bản hiển thị trong các
TextAsset (thường là JSON/CSV ngôn ngữ). Quy trình:

  extract:  APK -> work/original/*  +  work/translated/*  +  work/index.json
  apply:    work/translated/*  (đã sửa)  ->  APK mới
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

import UnityPy

from . import apk as apkmod

INDEX_NAME = "index.json"
ORIGINAL_DIR = "original"
TRANSLATED_DIR = "translated"


@dataclass
class TextEntry:
    """Một TextAsset đã trích xuất."""

    file: str  # tên file trong work/original|translated
    entry: str  # entry trong APK chứa asset này
    path_id: int  # PathID của object trong asset file
    name: str  # m_Name của TextAsset
    binary: bool  # True nếu nội dung không phải văn bản
    sha1: str  # hash nội dung gốc, để phát hiện file đã dịch


def _sanitize(name: str) -> str:
    name = re.sub(r"[^\w\-.]+", "_", name, flags=re.UNICODE)
    return name.strip("._") or "unnamed"


def _guess_ext(name: str, text: str) -> str:
    if "." in name.rsplit("/", 1)[-1]:
        return ""  # tên đã có đuôi
    stripped = text.lstrip()
    if stripped.startswith(("{", "[")):
        try:
            json.loads(text)
            return ".json"
        except (ValueError, RecursionError):
            pass
    return ".txt"


def _script_bytes(data) -> bytes:
    """Lấy nội dung TextAsset dưới dạng bytes (UnityPy decode bằng
    surrogateescape nên encode ngược lại được nguyên vẹn)."""
    script = data.m_Script
    if isinstance(script, bytes):
        return script
    return script.encode("utf-8", "surrogateescape")


def _is_binary(raw: bytes) -> bool:
    if b"\x00" in raw[:4096]:
        return True
    try:
        raw.decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True


def load_index(workdir: Path) -> List[TextEntry]:
    index_path = Path(workdir) / INDEX_NAME
    if not index_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy {index_path} - hãy chạy 'ttvn extract' trước."
        )
    raw = json.loads(index_path.read_text(encoding="utf-8"))
    return [TextEntry(**item) for item in raw["entries"]]


def save_index(workdir: Path, entries: List[TextEntry], apk_name: str) -> None:
    index_path = Path(workdir) / INDEX_NAME
    index_path.write_text(
        json.dumps(
            {"apk": apk_name, "entries": [asdict(e) for e in entries]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def extract(
    apk_path: Path,
    workdir: Path,
    name_filter: Optional[str] = None,
    include_binary: bool = False,
) -> List[TextEntry]:
    """Quét toàn bộ Unity asset trong APK, xuất mọi TextAsset ra workdir."""
    apk_path = Path(apk_path)
    workdir = Path(workdir)
    orig_dir = workdir / ORIGINAL_DIR
    trans_dir = workdir / TRANSLATED_DIR
    orig_dir.mkdir(parents=True, exist_ok=True)
    trans_dir.mkdir(parents=True, exist_ok=True)

    pattern = re.compile(name_filter, re.IGNORECASE) if name_filter else None
    entries: List[TextEntry] = []
    used_names: Dict[str, int] = {}

    with zipfile.ZipFile(apk_path) as zf:
        for entry_name in apkmod.iter_candidates(zf):
            try:
                env = UnityPy.load(zf.read(entry_name))
            except Exception:
                continue  # không phải asset file hợp lệ
            for obj in env.objects:
                if obj.type.name != "TextAsset":
                    continue
                try:
                    data = obj.read()
                except Exception:
                    continue
                asset_name = getattr(data, "m_Name", "") or "unnamed"
                if pattern and not pattern.search(asset_name):
                    continue
                raw = _script_bytes(data)
                binary = _is_binary(raw)
                if binary and not include_binary:
                    continue

                base = _sanitize(asset_name)
                ext = ".bin" if binary else _guess_ext(
                    asset_name, raw.decode("utf-8", "replace")
                )
                fname = f"{base}{ext}"
                # tránh trùng tên giữa các asset khác nhau
                if fname in used_names:
                    used_names[fname] += 1
                    fname = f"{base}__{used_names[fname]}{ext}"
                else:
                    used_names[fname] = 0

                (orig_dir / fname).write_bytes(raw)
                target = trans_dir / fname
                if not target.exists():  # không ghi đè bản dịch dở dang
                    target.write_bytes(raw)

                entries.append(
                    TextEntry(
                        file=fname,
                        entry=entry_name,
                        path_id=obj.path_id,
                        name=asset_name,
                        binary=binary,
                        sha1=hashlib.sha1(raw).hexdigest(),
                    )
                )

    save_index(workdir, entries, apk_path.name)
    return entries


def changed_entries(workdir: Path) -> List[TextEntry]:
    """Các TextAsset có file trong translated/ khác với bản gốc."""
    workdir = Path(workdir)
    changed = []
    for te in load_index(workdir):
        path = workdir / TRANSLATED_DIR / te.file
        if not path.exists():
            continue
        if hashlib.sha1(path.read_bytes()).hexdigest() != te.sha1:
            changed.append(te)
    return changed


def _save_env(env) -> bytes:
    """Serialize lại asset file / bundle sau khi sửa."""
    try:
        return env.file.save(packer="original")
    except TypeError:
        return env.file.save()


def apply(apk_path: Path, workdir: Path, out_apk: Path) -> int:
    """Chèn các bản dịch đã sửa vào APK mới. Trả về số TextAsset đã vá."""
    apk_path = Path(apk_path)
    workdir = Path(workdir)
    todo = changed_entries(workdir)
    if not todo:
        return 0

    # Gom theo entry APK để mỗi asset file chỉ load/save một lần.
    by_entry: Dict[str, List[TextEntry]] = {}
    for te in todo:
        by_entry.setdefault(te.entry, []).append(te)

    patched: Dict[str, bytes] = {}
    count = 0
    with zipfile.ZipFile(apk_path) as zf:
        for entry_name, items in by_entry.items():
            env = UnityPy.load(zf.read(entry_name))
            wanted = {te.path_id: te for te in items}
            hit = 0
            for obj in env.objects:
                te = wanted.get(obj.path_id)
                if te is None or obj.type.name != "TextAsset":
                    continue
                data = obj.read()
                new_raw = (workdir / TRANSLATED_DIR / te.file).read_bytes()
                data.m_Script = new_raw.decode("utf-8", "surrogateescape")
                data.save()
                hit += 1
            if hit:
                patched[entry_name] = _save_env(env)
                count += hit

    if patched:
        apkmod.repack(apk_path, Path(out_apk), patched)
    return count
