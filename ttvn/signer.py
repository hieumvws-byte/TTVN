"""Zipalign + ký APK sau khi vá.

APK đã sửa nội dung sẽ mất chữ ký gốc, Android sẽ từ chối cài nếu không ký
lại. Module này tự tìm zipalign/apksigner trong PATH hoặc Android SDK
(ANDROID_HOME/ANDROID_SDK_ROOT) và ký bằng debug keystore (tự tạo nếu chưa
có). APK ký bằng key debug chỉ cài được sau khi gỡ bản gốc trên máy.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

DEBUG_KEYSTORE = Path.home() / ".ttvn" / "debug.keystore"
KS_PASS = "ttvndebug"


def _find_build_tool(name: str) -> Optional[str]:
    path = shutil.which(name)
    if path:
        return path
    for env in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        sdk = os.environ.get(env)
        if not sdk:
            continue
        build_tools = Path(sdk) / "build-tools"
        if not build_tools.is_dir():
            continue
        # lấy phiên bản mới nhất
        for ver in sorted(build_tools.iterdir(), reverse=True):
            cand = ver / name
            if cand.exists():
                return str(cand)
    return None


def _ensure_keystore() -> Path:
    if DEBUG_KEYSTORE.exists():
        return DEBUG_KEYSTORE
    keytool = shutil.which("keytool")
    if not keytool:
        raise RuntimeError(
            "Không tìm thấy 'keytool' (đi kèm JDK). Cài JDK hoặc tự ký APK "
            "bằng uber-apk-signer: java -jar uber-apk-signer.jar -a file.apk"
        )
    DEBUG_KEYSTORE.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            keytool, "-genkeypair", "-v",
            "-keystore", str(DEBUG_KEYSTORE),
            "-alias", "ttvn",
            "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
            "-storepass", KS_PASS, "-keypass", KS_PASS,
            "-dname", "CN=TTVN Debug,O=TTVN",
        ],
        check=True,
        capture_output=True,
    )
    return DEBUG_KEYSTORE


def sign(apk: Path, out: Optional[Path] = None) -> Path:
    """Zipalign (nếu có) rồi ký APK. Trả về đường dẫn APK đã ký."""
    apk = Path(apk)
    out = Path(out) if out else apk.with_name(apk.stem + "-signed.apk")

    zipalign = _find_build_tool("zipalign")
    work = apk
    if zipalign:
        aligned = apk.with_name(apk.stem + "-aligned.apk")
        subprocess.run(
            [zipalign, "-f", "-p", "4", str(apk), str(aligned)],
            check=True,
            capture_output=True,
        )
        work = aligned
        print(f"✓ zipalign -> {aligned.name}")
    else:
        print("! Không tìm thấy zipalign - bỏ qua (đa số máy vẫn cài được).")

    apksigner = _find_build_tool("apksigner")
    if not apksigner:
        raise RuntimeError(
            "Không tìm thấy 'apksigner'. Cài Android SDK build-tools, hoặc "
            "ký thủ công bằng uber-apk-signer:\n"
            f"  java -jar uber-apk-signer.jar -a {work}"
        )

    ks = _ensure_keystore()
    if work != out:
        shutil.copyfile(work, out)
    subprocess.run(
        [
            apksigner, "sign",
            "--ks", str(ks),
            "--ks-key-alias", "ttvn",
            "--ks-pass", f"pass:{KS_PASS}",
            "--key-pass", f"pass:{KS_PASS}",
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    if work != apk and work.exists() and work != out:
        work.unlink()
    print(f"✓ Đã ký: {out}")
    return out
