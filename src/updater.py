"""OTA updater — kiểm tra GitHub Release và tải về bản mới."""
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass

CURRENT_VERSION = "1.0"
GITHUB_API = "https://api.github.com/repos/kakalotvz/dynoaio/releases"
CATALOG_URL = "https://github.com/kakalotvz/dynoaio/releases/download/catalog/catalog.json"


# ---------------------------------------------------------------------------
# App catalog
# ---------------------------------------------------------------------------

@dataclass
class AppEntry:
    name: str
    display_name: str
    description: str
    zip_url: str
    size_mb: int
    versions: list[str]


def fetch_catalog() -> list[AppEntry] | None:
    """Tải catalog.json từ GitHub. Trả về None nếu lỗi."""
    try:
        req = urllib.request.Request(CATALOG_URL, headers={"User-Agent": "DynoAIO/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        base_url = data.get("base_url", "")
        entries = []
        for item in data.get("apps", []):
            entries.append(AppEntry(
                name=item["name"],
                display_name=item.get("display_name", item["name"]),
                description=item.get("description", ""),
                zip_url=f"{base_url}/{item['zip']}",
                size_mb=item.get("size_mb", 0),
                versions=item.get("versions", []),
            ))
        return entries
    except Exception as e:
        logging.warning("fetch_catalog error: %s", e)
        return None


def download_app(entry: AppEntry, apps_dir: str,
                 on_progress: callable = None) -> tuple[bool, str]:
    """Tải zip của app về và giải nén vào apps_dir.
    
    on_progress(downloaded_bytes, total_bytes) — callback tiến trình.
    Trả về (success, message).
    """
    try:
        os.makedirs(apps_dir, exist_ok=True)
        req = urllib.request.Request(entry.zip_url, headers={"User-Agent": "DynoAIO/1.0"})

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                total = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                chunk = 65536  # 64KB chunks
                with open(tmp_path, "wb") as f:
                    while True:
                        data = response.read(chunk)
                        if not data:
                            break
                        f.write(data)
                        downloaded += len(data)
                        if on_progress:
                            on_progress(downloaded, total)

            # Giải nén vào Apps/
            with zipfile.ZipFile(tmp_path, "r") as zf:
                zf.extractall(apps_dir)

            return True, f"Đã tải và cài đặt {entry.display_name}"
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    except Exception as e:
        logging.warning("download_app %s error: %s", entry.name, e)
        return False, f"Lỗi tải {entry.display_name}: {e}"


# ---------------------------------------------------------------------------
# App update checker
# ---------------------------------------------------------------------------

def check_app_update(version: str) -> tuple[str | None, str | None]:
    """Kiểm tra bản cập nhật — lọc release có tag dạng version (1.0, v1.1, ...).
    
    Trả về (latest_version, download_url) hoặc (None, None) nếu lỗi/không có bản mới.
    """
    import re
    VERSION_RE = re.compile(r'^v?(\d+\.\d+(?:\.\d+)?)$')

    try:
        # Lấy danh sách tất cả releases, lọc tag dạng version
        req = urllib.request.Request(
            f"{GITHUB_API}?per_page=20",
            headers={"User-Agent": "DynoAIO/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            releases = json.loads(r.read())

        # Tìm release mới nhất có tag dạng version số
        latest_data = None
        latest_ver = None
        for release in releases:
            tag = release.get("tag_name", "")
            m = VERSION_RE.match(tag)
            if not m:
                continue  # bỏ qua "catalog", "apps", v.v.
            ver = m.group(1)
            if latest_ver is None or _ver_tuple(ver) > _ver_tuple(latest_ver):
                latest_ver = ver
                latest_data = release

        if not latest_ver or _ver_tuple(latest_ver) <= _ver_tuple(version):
            return None, None

        # Tìm asset .exe trong release đó
        exe_url = None
        for asset in latest_data.get("assets", []):
            name = asset.get("name", "").lower()
            if name.endswith(".exe") and "setup" not in name:
                exe_url = asset.get("browser_download_url")
                break
        if not exe_url:
            for asset in latest_data.get("assets", []):
                if asset.get("name", "").lower().endswith(".exe"):
                    exe_url = asset.get("browser_download_url")
                    break

        return latest_ver, exe_url
    except Exception as e:
        logging.warning("check_app_update error: %s", e)
        return None, None


def _ver_tuple(v: str) -> tuple:
    """Chuyển '1.2.3' thành (1, 2, 3) để so sánh."""
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return (0,)


def download_and_replace_exe(download_url: str,
                              on_progress: callable = None) -> tuple[bool, str]:
    """Tải exe mới về và thay thế exe hiện tại (chỉ thay exe, không đụng Apps/Drivers).
    
    Dùng batch script để rename sau khi app thoát.
    """
    try:
        current_exe = sys.executable if getattr(sys, "frozen", False) else None
        if not current_exe:
            return False, "Chỉ hỗ trợ cập nhật khi chạy từ file .exe đã build."

        exe_dir = os.path.dirname(current_exe)
        new_exe = os.path.join(exe_dir, "_update_new.exe")
        old_exe = os.path.join(exe_dir, "_update_old.exe")

        req = urllib.request.Request(download_url, headers={"User-Agent": "DynoAIO/1.0"})
        with urllib.request.urlopen(req, timeout=120) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            with open(new_exe, "wb") as f:
                while True:
                    data = response.read(65536)
                    if not data:
                        break
                    f.write(data)
                    downloaded += len(data)
                    if on_progress:
                        on_progress(downloaded, total)

        # Tạo batch script để swap exe sau khi app thoát
        bat_path = os.path.join(exe_dir, "_update.bat")
        bat_content = f"""@echo off
timeout /t 2 /nobreak >nul
move /y "{current_exe}" "{old_exe}"
move /y "{new_exe}" "{current_exe}"
del "{old_exe}" 2>nul
start "" "{current_exe}"
del "%~f0"
"""
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)

        return True, bat_path

    except Exception as e:
        logging.warning("download_and_replace_exe error: %s", e)
        return False, str(e)
