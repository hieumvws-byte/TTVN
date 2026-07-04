"""Unit test cho các phần thuần Python (không cần file Unity thật).

Chạy:  python -m pytest tests/  hoặc  python tests/test_ttvn.py
"""

import csv
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ttvn import apk as apkmod  # noqa: E402
from ttvn import csvtool, textassets  # noqa: E402
from ttvn.textassets import TextEntry, save_index  # noqa: E402

SAMPLE = {
    "menu": {"start": "Start Game", "quit": "Quit"},
    "spells": [{"name": "Fireball", "desc": "Deals {0} damage"}],
    "count": 5,
}


def make_workdir(tmp: Path) -> Path:
    work = tmp / "work"
    (work / "original").mkdir(parents=True)
    (work / "translated").mkdir()
    raw = json.dumps(SAMPLE, ensure_ascii=False, indent=2).encode()
    (work / "original" / "Lang_En.json").write_bytes(raw)
    (work / "translated" / "Lang_En.json").write_bytes(raw)
    save_index(
        work,
        [
            TextEntry(
                file="Lang_En.json",
                entry="assets/bin/Data/sharedassets0.assets",
                path_id=123,
                name="Lang_En",
                binary=False,
                sha1=hashlib.sha1(raw).hexdigest(),
            )
        ],
        "test.apk",
    )
    return work


class CsvRoundTrip(unittest.TestCase):
    def test_export_import(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            work = make_workdir(tmp)
            out_csv = tmp / "out.csv"

            n = csvtool.export_csv(work, out_csv)
            self.assertEqual(n, 4)

            rows = list(csv.DictReader(open(out_csv, encoding="utf-8-sig")))
            trans = {
                "menu.start": "Bắt đầu",
                "menu.quit": "Thoát",
                "spells[0].name": "Cầu lửa",
                "spells[0].desc": "Gây {0} sát thương",
            }
            for r in rows:
                r["text"] = trans[r["key"]]
            with open(tmp / "vi.csv", "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=["file", "key", "text"])
                w.writeheader()
                w.writerows(rows)

            n = csvtool.import_csv(work, tmp / "vi.csv")
            self.assertEqual(n, 4)

            result = json.loads(
                (work / "translated" / "Lang_En.json").read_text(encoding="utf-8")
            )
            self.assertEqual(result["menu"]["start"], "Bắt đầu")
            self.assertEqual(result["spells"][0]["desc"], "Gây {0} sát thương")
            self.assertEqual(result["count"], 5)  # giữ nguyên giá trị không phải chuỗi

            # sau khi dịch, file phải được nhận là "đã thay đổi"
            changed = textassets.changed_entries(work)
            self.assertEqual([c.file for c in changed], ["Lang_En.json"])


class ApkRepack(unittest.TestCase):
    def test_repack_replaces_and_strips_signature(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            src = tmp / "a.apk"
            dst = tmp / "b.apk"
            with zipfile.ZipFile(src, "w") as z:
                z.writestr("assets/bin/Data/sharedassets0.assets", b"OLD")
                z.writestr("META-INF/CERT.RSA", b"sig")
                z.writestr("META-INF/MANIFEST.MF", b"mf")
                z.writestr("classes.dex", b"dex")

            replaced, total = apkmod.repack(
                src, dst, {"assets/bin/Data/sharedassets0.assets": b"NEW"}
            )
            self.assertEqual(replaced, 1)
            with zipfile.ZipFile(dst) as z:
                names = z.namelist()
                self.assertEqual(
                    z.read("assets/bin/Data/sharedassets0.assets"), b"NEW"
                )
                self.assertNotIn("META-INF/CERT.RSA", names)
                self.assertNotIn("META-INF/MANIFEST.MF", names)
                self.assertIn("classes.dex", names)


class CandidateDetection(unittest.TestCase):
    def test_is_candidate(self):
        yes = [
            "assets/bin/Data/sharedassets0.assets",
            "assets/bin/Data/data.unity3d",
            "assets/bin/Data/globalgamemanagers",
            "assets/bundles/ui.unity3d",
        ]
        no = [
            "assets/bin/Data/sharedassets0.assets.resS",
            "assets/bin/Data/Managed/Assembly-CSharp.dll",
            "assets/bin/Data/RuntimeInitializeOnLoads.json",
            "classes.dex",
            "lib/arm64-v8a/libil2cpp.so",
            "res/values/strings.xml",
        ]
        for name in yes:
            self.assertTrue(apkmod.is_candidate(name), name)
        for name in no:
            self.assertFalse(apkmod.is_candidate(name), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
