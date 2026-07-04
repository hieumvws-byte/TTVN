# Ký APK không cần Android SDK

Chỉ cần JDK (java + javac + keytool). Thư viện apksig của Google tải từ
Maven Central:

```bash
curl -L -o apksig.jar \
  https://repo1.maven.org/maven2/com/android/tools/build/apksig/2.3.0/apksig-2.3.0.jar
javac -cp apksig.jar SignApk.java VerifyApk.java
```

Ký (chữ ký v2 — đủ cho Android 7 trở lên):

```bash
java -cp apksig.jar:. SignApk ttvn.p12 ttvndebug ttvn input.apk output-signed.apk
java -cp apksig.jar:. VerifyApk output-signed.apk
```

## Quan trọng: giữ file `ttvn.p12`

Đây là keystore đã dùng ký bản việt hóa Magic Survival (mật khẩu:
`ttvndebug`, alias: `ttvn`). **Mọi bản cập nhật sau phải ký bằng đúng
keystore này** — nếu ký key khác, Android bắt gỡ game (mất save cục bộ)
mới cài được bản mới.

## Cài đặt bản dịch (2 file APK)

Game phát hành dạng split APK nên phải cài cả `base.apk` (đã việt hóa) và
`config.armeabi_v7a.apk` (thư viện native) **cùng lúc, cùng chữ ký**:

1. Cài app [SAI - Split APKs Installer](https://play.google.com/store/apps/details?id=com.aefyr.sai)
   từ CH Play.
2. Mở SAI → **Install APKs** → chọn file `.apks` (hoặc chọn cả 2 file apk).
3. Gỡ bản Magic Survival gốc trước khi cài (chữ ký khác nhau).
