"""Đọc/ghi file APK ở mức zip: liệt kê các entry chứa Unity assets và
đóng gói lại APK sau khi vá.
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from typing import Dict, Iterator, Tuple

# Các đuôi file bên trong assets/bin/Data/ chắc chắn KHÔNG phải serialized
# asset file (dữ liệu thô đi kèm), bỏ qua để đỡ tốn thời gian thử load.
SKIP_SUFFIXES = (
    ".resS",
    ".resource",
    ".config",
    ".dll",
    ".json",
    ".xml",
    ".txt",
    ".dat",
    ".info",
)

# Ngoài assets/bin/Data/, một số game để asset bundle rời trong assets/.
BUNDLE_SUFFIXES = (".unity3d", ".bundle", ".assets", ".ab")


def is_candidate(name: str) -> bool:
    """Entry trong APK có khả năng là Unity asset file / bundle hay không."""
    if name.startswith("assets/bin/Data/"):
        base = name.rsplit("/", 1)[-1]
        if any(name.endswith(s) for s in SKIP_SUFFIXES):
            return False
        # Machine-code, thư viện...
        if base.endswith(".so"):
            return False
        return True
    if name.startswith("assets/") and any(name.endswith(s) for s in BUNDLE_SUFFIXES):
        return True
    return False


def iter_candidates(zf: zipfile.ZipFile) -> Iterator[str]:
    for name in zf.namelist():
        if is_candidate(name):
            yield name


def repack(
    src_apk: Path,
    dst_apk: Path,
    patched_entries: Dict[str, bytes],
) -> Tuple[int, int]:
    """Tạo APK mới từ ``src_apk``, thay nội dung các entry trong
    ``patched_entries`` (tên entry -> bytes mới), giữ nguyên mọi thứ khác.

    Trả về (số entry đã thay, tổng số entry).

    Lưu ý: APK sau khi sửa sẽ mất chữ ký -> cần zipalign + ký lại
    (xem ttvn/signer.py).
    """
    src_apk = Path(src_apk)
    dst_apk = Path(dst_apk)
    if dst_apk.resolve() == src_apk.resolve():
        raise ValueError("File đích phải khác file nguồn")

    tmp = dst_apk.with_suffix(dst_apk.suffix + ".tmp")
    replaced = 0
    total = 0
    with zipfile.ZipFile(src_apk) as zin, zipfile.ZipFile(
        tmp, "w", allowZip64=True
    ) as zout:
        for info in zin.infolist():
            total += 1
            # Bỏ chữ ký cũ - đằng nào cũng phải ký lại.
            if info.filename.startswith("META-INF/") and info.filename.endswith(
                (".RSA", ".DSA", ".EC", ".SF", ".MF")
            ):
                continue
            data = patched_entries.get(info.filename)
            if data is None:
                data = zin.read(info.filename)
            else:
                replaced += 1
            new_info = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            new_info.compress_type = info.compress_type
            new_info.external_attr = info.external_attr
            new_info.create_system = info.create_system
            zout.writestr(new_info, data)

    shutil.move(str(tmp), str(dst_apk))
    return replaced, total
