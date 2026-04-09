"""
Script zip từng thư mục VERSION trong Apps/ để upload lên GitHub Release.
Mỗi zip chứa nội dung của 1 phiên bản, tên zip = tên thư mục phiên bản.

Chạy: python installer/zip_apps.py
       python installer/zip_apps.py Redleo          # chỉ zip versions của Redleo
       python installer/zip_apps.py Redleo "REDLEO ECU PRO 9.2"  # chỉ zip 1 version

Output: installer/zips/<VersionName>.zip
"""
import os
import zipfile
import sys

APPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Apps")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zips")
os.makedirs(OUT_DIR, exist_ok=True)


def zip_version(app_name: str, version_name: str) -> None:
    version_path = os.path.join(APPS_DIR, app_name, version_name)
    if not os.path.isdir(version_path):
        print(f"  ✗ Không tìm thấy: {version_path}")
        return
    out_file = os.path.join(OUT_DIR, f"{version_name}.zip")
    print(f"  Đang zip {app_name}/{version_name}...", end=" ", flush=True)
    with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(version_path):
            for file in files:
                full_path = os.path.join(root, file)
                # arcname: đường dẫn tương đối từ version_path (không bao gồm tên version)
                arcname = os.path.relpath(full_path, version_path)
                zf.write(full_path, arcname)
    size_mb = os.path.getsize(out_file) / 1024 / 1024
    print(f"✓ {size_mb:.1f} MB → {out_file}")


def zip_app(app_name: str, only_version: str = None) -> None:
    app_path = os.path.join(APPS_DIR, app_name)
    if not os.path.isdir(app_path):
        print(f"  ✗ Không tìm thấy app: {app_path}")
        return
    versions = [only_version] if only_version else [
        d for d in os.listdir(app_path)
        if os.path.isdir(os.path.join(app_path, d))
    ]
    for version in sorted(versions):
        zip_version(app_name, version)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        # zip 1 version cụ thể
        zip_version(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2:
        # zip tất cả versions của 1 app
        zip_app(sys.argv[1])
    else:
        # zip tất cả
        apps = [d for d in os.listdir(APPS_DIR) if os.path.isdir(os.path.join(APPS_DIR, d))]
        print(f"Zipping tất cả versions từ {APPS_DIR}")
        for app in sorted(apps):
            print(f"\n[{app}]")
            zip_app(app)
    print(f"\nDone! Upload các file .zip trong {OUT_DIR} lên GitHub Release tag 'apps'")
