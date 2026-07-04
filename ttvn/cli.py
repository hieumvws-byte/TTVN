"""CLI của TTVN - tool việt hóa game Unity trên Android.

    ttvn extract game.apk -o work/         # trích text ra work/
    ttvn csv-export work/ -o dich.csv      # (tuỳ chọn) xuất CSV để dịch
    ttvn csv-import work/ dich.csv         # nhập CSV đã dịch
    ttvn apply game.apk work/ -o game_vi.apk
    ttvn sign game_vi.apk
    ttvn fontcheck work/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__


def cmd_extract(args) -> int:
    from . import textassets

    entries = textassets.extract(
        Path(args.apk),
        Path(args.out),
        name_filter=args.filter,
        include_binary=args.include_binary,
    )
    if not entries:
        print(
            "Không tìm thấy TextAsset nào. Thử --include-binary, hoặc game "
            "này lưu text trong MonoBehaviour/IL2CPP (xem README, mục "
            "'Game không có TextAsset')."
        )
        return 1
    print(f"Đã trích {len(entries)} TextAsset vào {args.out}/")
    print(f"  - Bản gốc      : {args.out}/original/  (đừng sửa)")
    print(f"  - Bản để dịch  : {args.out}/translated/  (sửa file ở đây)")
    for te in entries[:20]:
        tag = " [binary]" if te.binary else ""
        print(f"    {te.file}{tag}  <- {te.entry}")
    if len(entries) > 20:
        print(f"    ... và {len(entries) - 20} file khác (xem index.json)")
    return 0


def cmd_apply(args) -> int:
    from . import textassets

    out = Path(args.out) if args.out else Path(args.apk).with_name(
        Path(args.apk).stem + "-vi.apk"
    )
    n = textassets.apply(Path(args.apk), Path(args.workdir), out)
    if n == 0:
        print(
            "Chưa có file nào trong translated/ khác bản gốc - không có gì "
            "để vá."
        )
        return 1
    print(f"✓ Đã vá {n} TextAsset -> {out}")
    print("  Bước tiếp theo: ký APK để cài được lên máy:")
    print(f"    ttvn sign {out}")
    return 0


def cmd_csv_export(args) -> int:
    from . import csvtool

    n = csvtool.export_csv(Path(args.workdir), Path(args.out), only=args.file)
    print(f"✓ Đã xuất {n} chuỗi -> {args.out}")
    print("  Dịch cột 'text' rồi nhập lại bằng: ttvn csv-import")
    return 0


def cmd_csv_import(args) -> int:
    from . import csvtool

    n = csvtool.import_csv(Path(args.workdir), Path(args.csv))
    print(f"✓ Đã cập nhật {n} chuỗi vào {args.workdir}/translated/")
    return 0


def cmd_fontcheck(args) -> int:
    from . import fontcheck

    fontcheck.check(Path(args.workdir))
    return 0


def cmd_sign(args) -> int:
    from . import signer

    try:
        signer.sign(Path(args.apk), Path(args.out) if args.out else None)
    except Exception as e:  # noqa: BLE001
        print(f"Lỗi: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_status(args) -> int:
    from . import textassets

    changed = textassets.changed_entries(Path(args.workdir))
    total = len(textassets.load_index(Path(args.workdir)))
    print(f"{len(changed)}/{total} file đã chỉnh sửa so với bản gốc:")
    for te in changed:
        print(f"  {te.file}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ttvn",
        description="Tool việt hóa game Unity trên Android (Magic Survival)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--version", action="version", version=f"ttvn {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("extract", help="Trích TextAsset từ APK ra thư mục làm việc")
    sp.add_argument("apk", help="File APK của game")
    sp.add_argument("-o", "--out", default="work", help="Thư mục làm việc (mặc định: work)")
    sp.add_argument("-f", "--filter", help="Chỉ lấy asset có tên khớp regex (vd: lang|locale)")
    sp.add_argument("--include-binary", action="store_true", help="Xuất cả TextAsset nhị phân (.bin)")
    sp.set_defaults(func=cmd_extract)

    sp = sub.add_parser("apply", help="Chèn bản dịch vào APK mới")
    sp.add_argument("apk", help="File APK gốc")
    sp.add_argument("workdir", help="Thư mục làm việc (chứa translated/)")
    sp.add_argument("-o", "--out", help="APK đầu ra (mặc định: <tên>-vi.apk)")
    sp.set_defaults(func=cmd_apply)

    sp = sub.add_parser("csv-export", help="Xuất chuỗi trong file JSON ra CSV để dịch")
    sp.add_argument("workdir", help="Thư mục làm việc")
    sp.add_argument("-o", "--out", default="translate.csv", help="File CSV đầu ra")
    sp.add_argument("--file", action="append", help="Chỉ xuất file JSON này (lặp lại được)")
    sp.set_defaults(func=cmd_csv_export)

    sp = sub.add_parser("csv-import", help="Nhập CSV đã dịch vào translated/")
    sp.add_argument("workdir", help="Thư mục làm việc")
    sp.add_argument("csv", help="File CSV đã dịch")
    sp.set_defaults(func=cmd_csv_import)

    sp = sub.add_parser("status", help="Liệt kê file đã chỉnh so với bản gốc")
    sp.add_argument("workdir", help="Thư mục làm việc")
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("fontcheck", help="Liệt kê ký tự có dấu để kiểm tra font")
    sp.add_argument("workdir", help="Thư mục làm việc")
    sp.set_defaults(func=cmd_fontcheck)

    sp = sub.add_parser("sign", help="Zipalign + ký APK bằng debug key")
    sp.add_argument("apk", help="File APK cần ký")
    sp.add_argument("-o", "--out", help="APK đầu ra (mặc định: <tên>-signed.apk)")
    sp.set_defaults(func=cmd_sign)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
