"""
Script zip từng thư mục app trong Apps/ để upload lên GitHub Release.
Chạy: python installer/zip_apps.py
Output: installer/zips/*.zip
"""
import os
import zipfile
import sys

APPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Apps")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zips")
os.makedirs(OUT_DIR, exist_ok=True)


def zip_app(app_name: str) -> None:
    app_path = os.path.join(APPS_DIR, app_name)
    if not os.path.isdir(app_path):
        print(f"  ✗ Không tìm thấy: {app_path}")
        return
    out_file = os.path.join(OUT_DIR, f"{app_name}.zip")
    print(f"  Đang zip {app_name}...", end=" ", flush=True)
    with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(app_path):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, APPS_DIR)
                zf.write(full_path, arcname)
    size_mb = os.path.getsize(out_file) / 1024 / 1024
    print(f"✓ {size_mb:.1f} MB → {out_file}")


if __name__ == "__main__":
    apps = sys.argv[1:] or [d for d in os.listdir(APPS_DIR) if os.path.isdir(os.path.join(APPS_DIR, d))]
    print(f"Zipping {len(apps)} apps từ {APPS_DIR}")
    for app in sorted(apps):
        zip_app(app)
    print(f"\nDone! Upload các file .zip trong {OUT_DIR} lên GitHub Release tag 'apps'")
    print("Sau đó commit catalog.json lên repo hoặc upload lên release tag 'catalog'")
