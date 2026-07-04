# TTVN — Tool việt hóa Magic Survival (Android)

Bộ công cụ dòng lệnh giúp việt hóa game **Magic Survival** (và các game Unity
khác trên Android): trích xuất văn bản từ APK, dịch bằng file thường hoặc
CSV, chèn bản dịch ngược vào APK và ký lại để cài lên máy.

> ⚠️ **Lưu ý pháp lý**: chỉ dùng cho mục đích cá nhân/học tập trên APK bạn
> tải hợp pháp. Không phân phối lại APK đã sửa — hãy chia sẻ *bản vá/file
> dịch* thay vì file game.

## Nguyên lý

Magic Survival làm bằng **Unity**. Văn bản hiển thị (tên phép, mô tả, UI…)
nằm trong các **TextAsset** — thường là file JSON ngôn ngữ — được đóng gói
trong `assets/bin/Data/` của APK. Tool dùng [UnityPy](https://github.com/K0lb3/UnityPy)
để đọc/ghi các asset này mà không cần Unity Editor.

## Cài đặt

Cần Python ≥ 3.9.

```bash
git clone <repo này>
cd TTVN
pip install -e .
```

Để **ký APK** (bước cuối) cần thêm một trong hai:
- Android SDK build-tools (`zipalign` + `apksigner`) + JDK (`keytool`), hoặc
- [uber-apk-signer](https://github.com/patrickfav/uber-apk-signer) (chỉ cần Java).

## Quy trình việt hóa

### 1. Lấy APK

Kéo APK từ máy đã cài game (cần `adb`):

```bash
adb shell pm path com.nanagames.magicsurvival   # tìm đường dẫn (tên gói có thể khác)
adb pull /data/app/.../base.apk magicsurvival.apk
```

Nếu game phát hành dạng **App Bundle** (nhiều file `.apk`) thì kéo hết về;
text hầu như luôn nằm trong `base.apk`.

### 2. Trích xuất văn bản

```bash
ttvn extract magicsurvival.apk -o work
```

Kết quả:

```
work/
├── index.json      # ánh xạ file ↔ vị trí trong APK (đừng sửa)
├── original/       # bản gốc để đối chiếu (đừng sửa)
└── translated/     # ← SỬA CÁC FILE Ở ĐÂY
```

Mẹo: nếu ra quá nhiều file, lọc theo tên bằng regex:

```bash
ttvn extract magicsurvival.apk -o work -f "lang|locale|english|text"
```

### 3. Dịch

**Cách A — sửa trực tiếp:** mở file trong `work/translated/` (thường là
JSON), dịch các chuỗi sang tiếng Việt. Giữ nguyên key, chỉ dịch value; giữ
nguyên các mã như `{0}`, `%s`, `\n`, thẻ `<color=...>`.

**Cách B — qua CSV (tiện cho Google Sheets / dịch nhóm):**

```bash
ttvn csv-export work -o dich.csv    # xuất mọi chuỗi trong file JSON
# ... dịch cột "text" trong dich.csv ...
ttvn csv-import work dich.csv       # ghi bản dịch vào translated/
```

Tham khảo bảng thuật ngữ thống nhất ở [`data/glossary.csv`](data/glossary.csv).

Xem tiến độ:

```bash
ttvn status work
```

### 4. Kiểm tra font

```bash
ttvn fontcheck work
```

Liệt kê các ký tự có dấu đang dùng. Nếu game dùng font TTF động thì tiếng
Việt hiển thị ổn; nếu dùng **TextMeshPro atlas** thiếu ký tự, chữ sẽ thành
ô vuông — khi đó cần vá thêm font asset (lệnh trên in hướng dẫn chi tiết).

### 5. Đóng gói và ký APK

```bash
ttvn apply magicsurvival.apk work -o magicsurvival-vi.apk
ttvn sign magicsurvival-vi.apk
```

`sign` tự tạo debug keystore (`~/.ttvn/debug.keystore`) và chạy
zipalign + apksigner. Không có Android SDK thì ký bằng uber-apk-signer:

```bash
java -jar uber-apk-signer.jar -a magicsurvival-vi.apk
```

### 6. Cài lên máy

Chữ ký đã đổi nên phải **gỡ bản gốc trước** (sao lưu save nếu cần —
Magic Survival có cloud save qua Google Play Games):

```bash
adb uninstall <tên.gói.game>
adb install magicsurvival-vi-signed.apk
```

## Khi game cập nhật phiên bản mới

Chạy lại `extract` với APK mới vào **cùng thư mục work** — tool không ghi
đè file đã có trong `translated/`, nên bản dịch cũ được giữ; chỉ cần dịch
bổ sung chuỗi mới rồi `apply` như thường.

## Game không có TextAsset?

Một số game giấu text ở chỗ khác:

- **MonoBehaviour**: dùng [UABEA](https://github.com/nesrak1/UABEA) xem thử
  các MonoBehaviour, hoặc mở rộng `ttvn/textassets.py` đọc typetree.
- **Hardcode trong code C#**: file `assets/bin/Data/Managed/Assembly-CSharp.dll`
  — sửa bằng dnSpy; nếu là IL2CPP (`libil2cpp.so`) thì tra chuỗi trong
  `global-metadata.dat`.
- **Tải từ server**: phải chặn/sửa response, ngoài phạm vi tool này.

## Các lệnh

| Lệnh | Chức năng |
|---|---|
| `ttvn extract <apk> -o work` | Trích TextAsset từ APK |
| `ttvn status work` | Liệt kê file đã dịch/chỉnh |
| `ttvn csv-export work -o file.csv` | Xuất chuỗi JSON ra CSV |
| `ttvn csv-import work file.csv` | Nhập CSV đã dịch |
| `ttvn fontcheck work` | Kiểm tra ký tự có dấu / font |
| `ttvn apply <apk> work -o out.apk` | Chèn bản dịch vào APK mới |
| `ttvn sign <apk>` | Zipalign + ký APK bằng debug key |

## Cấu trúc mã nguồn

```
ttvn/
├── cli.py         # điểm vào dòng lệnh
├── apk.py         # đọc/đóng gói lại APK (zip)
├── textassets.py  # trích xuất / vá TextAsset (UnityPy)
├── csvtool.py     # chuyển JSON ↔ CSV để dịch
├── fontcheck.py   # kiểm tra ký tự tiếng Việt
└── signer.py      # zipalign + apksigner
```
