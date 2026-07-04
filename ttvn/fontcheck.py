"""Kiểm tra ký tự tiếng Việt trong bản dịch.

Font bitmap / TextMeshPro atlas trong game thường chỉ chứa ký tự ASCII +
bảng chữ gốc (Hàn/Nhật...). Nếu bản dịch dùng ký tự có dấu mà atlas không
có, chữ sẽ hiển thị thành ô vuông. Lệnh này liệt kê toàn bộ ký tự ngoài
ASCII đang dùng để bạn kiểm tra/bổ sung vào font atlas.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Set

from .textassets import TRANSLATED_DIR

# Toàn bộ ký tự tiếng Việt có dấu (thường + hoa)
VIETNAMESE_CHARS: Set[str] = set(
    "àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợ"
    "ùúủũụưừứửữựỳýỷỹỵ"
    "ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢ"
    "ÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ"
)


def check(workdir: Path) -> None:
    trans_dir = Path(workdir) / TRANSLATED_DIR
    counter: Counter[str] = Counter()
    files = 0
    for path in sorted(trans_dir.iterdir()):
        if path.suffix == ".bin" or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        files += 1
        for ch in text:
            if ord(ch) > 127:
                counter[ch] += 1

    if not counter:
        print(f"Đã quét {files} file: không có ký tự ngoài ASCII.")
        return

    vn = sorted(c for c in counter if c in VIETNAMESE_CHARS)
    other = sorted(c for c in counter if c not in VIETNAMESE_CHARS)

    print(f"Đã quét {files} file trong {trans_dir}")
    print(f"\nKý tự tiếng Việt có dấu đang dùng ({len(vn)}):")
    print("  " + "".join(vn))
    if other:
        print(f"\nKý tự ngoài ASCII khác ({len(other)}):")
        print("  " + "".join(other))
    print(
        "\nLưu ý: nếu game dùng TextMeshPro, font atlas trong game phải chứa"
        "\nđủ các ký tự trên. Cách bổ sung:"
        "\n  1. Dùng UABEA / UnityPy tìm asset 'TMP_FontAsset' trong APK."
        "\n  2. Tạo atlas mới bằng Unity (Window > TextMeshPro > Font Asset"
        "\n     Creator) với custom character list gồm chuỗi ký tự ở trên."
        "\n  3. Thay atlas + số liệu glyph vào asset gốc."
        "\nNếu game dùng UI Text (font động .ttf) thì thường không cần làm gì."
    )
