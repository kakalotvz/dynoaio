# Tasks — Dyno All In One

## Task List

- [x] 1. Khởi tạo project và cấu trúc thư mục
  - [x] 1.1 Tạo cấu trúc project Python: `src/`, `tests/`, `images/`, `Apps/`
  - [x] 1.2 Tạo `requirements.txt` với các dependency: `PyQt6`, `hypothesis`, `pytest`, `pyinstaller`
  - [x] 1.3 Tạo `theme.json` mặc định với các giá trị màu sắc dark theme

- [x] 2. Implement Core Logic Layer
  - [x] 2.1 Implement `AppScanner` — quét thư mục `Apps/` và trả về `list[AppInfo]`
  - [x] 2.2 Implement `AppTypeDetector` — phân loại PORTABLE vs INSTALLABLE dựa trên tên file
  - [x] 2.3 Implement `PortableRunner` — tìm và chạy file `.exe` đầu tiên không phải setup
  - [x] 2.4 Implement `SilentInstaller` — chạy setup file với tham số `/S` hoặc `/quiet /norestart`
  - [x] 2.5 Implement `InstallPathResolver` — tra registry rồi fallback sang Program Files
  - [x] 2.6 Implement `AppLauncher` — điều phối PortableRunner và InstallableRunner

- [x] 3. Implement Config Layer
  - [x] 3.1 Implement `ThemeLoader` — đọc `theme.json`, fallback về default khi lỗi
  - [x] 3.2 Định nghĩa `ThemeConfig` dataclass với tất cả các field bắt buộc

- [x] 4. Implement UI Layer (PyQt6)
  - [x] 4.1 Implement `HeaderWidget` — hiển thị logo từ `images/logo.png` và tiêu đề
  - [x] 4.2 Implement `AppCard` — thẻ ứng dụng với gradient background từ ThemeConfig
  - [x] 4.3 Implement `AppListScreen` — màn hình danh sách app, hiển thị thông báo khi rỗng
  - [x] 4.4 Implement `VersionCard` — thẻ phiên bản với badge loại (Portable/Installable)
  - [x] 4.5 Implement `VersionListScreen` — màn hình danh sách phiên bản với nút Quay lại
  - [x] 4.6 Implement `InstallDialog` — hộp thoại xác nhận cài đặt với nút Cài đặt / Hủy
  - [x] 4.7 Implement `MainWindow` — cửa sổ chính, điều phối navigation giữa các screen
  - [x] 4.8 Áp dụng dark theme từ ThemeConfig lên toàn bộ UI, set icon từ `images/icon.ico`

- [x] 5. Unit Tests và Property-Based Tests
  - [x] 5.1 Viết unit tests cho `AppScanner` — mock filesystem, kiểm tra edge cases (thư mục rỗng, không tồn tại)
  - [x] 5.2 Viết property test cho Property 1: App scan phản ánh đúng cấu trúc thư mục
  - [x] 5.3 Viết property test cho Property 2: Version scan phản ánh đúng cấu trúc thư mục phiên bản
  - [x] 5.4 Viết property test cho Property 3: Phân loại Installable khi có setup file
  - [x] 5.5 Viết property test cho Property 4: Phân loại Portable khi không có setup file
  - [x] 5.6 Viết property test cho Property 5: Silent install truyền đúng tham số theo extension
  - [x] 5.7 Viết property test cho Property 6: ThemeConfig fallback khi file không hợp lệ
  - [x] 5.8 Viết property test cho Property 7: ThemeConfig round-trip serialization
  - [x] 5.9 Viết unit tests cho `InstallPathResolver` — mock winreg, kiểm tra thứ tự lookup

- [ ] 6. Integration Tests
  - [ ] 6.1 Viết integration test toàn bộ luồng scan → detect → launch với fixture thư mục thật
  - [ ] 6.2 Viết integration test luồng install: mock subprocess, kiểm tra InstallResult và path resolution

- [ ] 7. Đóng gói và phân phối
  - [ ] 7.1 Tạo `build.spec` cho PyInstaller — bundle icon, logo, theme.json vào exe
  - [ ] 7.2 Kiểm tra exe chạy được trên Windows sạch (không cần Python)
  - [ ] 7.3 Đặt exe output vào thư mục `dist/`
