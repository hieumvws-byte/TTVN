"""Chuyển TextAsset dạng JSON sang CSV để dịch (Google Sheets/Excel) và
nhập ngược bản dịch vào file JSON trong translated/.

CSV có 3 cột: file, key, text. Chỉ các giá trị chuỗi trong JSON được xuất;
cấu trúc (object/array/số/bool) giữ nguyên khi nhập lại.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

from .textassets import TRANSLATED_DIR


def _walk(node: Any, prefix: str = "") -> Iterator[Tuple[str, str]]:
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{prefix}[{i}]")
    elif isinstance(node, str):
        yield prefix, node


def _set_by_key(node: Any, key: str, value: str) -> None:
    """Gán ``value`` vào vị trí ``key`` (định dạng a.b[2].c) trong ``node``."""
    # tách "a.b[3][4].c" -> ["a", "b", 3, 4, "c"]
    tokens: List[Any] = []
    for part in key.split("."):
        base = part
        idxs: List[int] = []
        while base.endswith("]"):
            base, _, tail = base.rpartition("[")
            idxs.insert(0, int(tail[:-1]))
        if base:
            tokens.append(base)
        tokens.extend(idxs)

    cur = node
    for tok in tokens[:-1]:
        cur = cur[tok]
    cur[tokens[-1]] = value


def export_csv(workdir: Path, out_csv: Path, only: List[str] | None = None) -> int:
    """Xuất mọi file JSON trong translated/ ra một file CSV. Trả về số dòng."""
    workdir = Path(workdir)
    trans_dir = workdir / TRANSLATED_DIR
    rows = 0
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["file", "key", "text"])
        for path in sorted(trans_dir.glob("*.json")):
            if only and path.name not in only:
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                continue
            for key, text in _walk(data):
                writer.writerow([path.name, key, text])
                rows += 1
    return rows


def import_csv(workdir: Path, in_csv: Path) -> int:
    """Đọc CSV (cột file,key,text) và ghi đè chuỗi vào file JSON tương ứng
    trong translated/. Trả về số chuỗi đã cập nhật."""
    workdir = Path(workdir)
    trans_dir = workdir / TRANSLATED_DIR

    by_file: Dict[str, List[Tuple[str, str]]] = {}
    with open(in_csv, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fname = (row.get("file") or "").strip()
            key = (row.get("key") or "").strip()
            text = row.get("text")
            if not fname or not key or text is None:
                continue
            by_file.setdefault(fname, []).append((key, text))

    updated = 0
    for fname, pairs in by_file.items():
        path = trans_dir / fname
        if not path.exists():
            print(f"  ! bỏ qua {fname}: không có trong {trans_dir}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for key, text in pairs:
            try:
                _set_by_key(data, key, text)
                updated += 1
            except (KeyError, IndexError, TypeError):
                print(f"  ! {fname}: không tìm thấy key '{key}'")
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return updated
