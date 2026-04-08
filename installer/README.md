# Hướng dẫn build installer

## Yêu cầu
1. **Inno Setup 6+** — https://jrsoftware.org/isdl.php
2. **Pillow** (để tạo ảnh wizard) — `pip install pillow`
3. Đã build `dist/DynoAllInOne.exe` bằng PyInstaller

## Các bước

### 1. Tạo ảnh wizard
```bash
cd installer
python create_wizard_images.py
```
Sẽ tạo ra `wizard_banner.bmp` và `wizard_icon.bmp`.

### 2. Build installer
Mở **Inno Setup Compiler**, chọn `installer.iss`, nhấn **Build → Compile** (F9).

Hoặc chạy từ command line:
```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

### 3. Kết quả
File `installer/output/DynoAllInOne_Setup_v1.0.exe` sẽ được tạo ra.

## Cấu trúc sau khi cài đặt
```
C:\Program Files\Dyno All In One\
├── DynoAllInOne.exe     ← exe đã bundle sẵn images/ và theme.json bên trong
├── Apps\                ← extract từ installer, chứa phần mềm dyno thực tế
│   ├── Redleo\
│   ├── Apitech\
│   ├── ATE\
│   └── ...
└── Drivers\             ← extract từ installer, chứa driver FTDI, CP210x
    ├── ftdi\
    └── ...
```

## Tùy chỉnh
- **Logo/banner**: Sửa `create_wizard_images.py` rồi chạy lại
- **Điều khoản**: Sửa `license.txt`
- **Thông tin app**: Sửa các `#define` ở đầu `installer.iss`
