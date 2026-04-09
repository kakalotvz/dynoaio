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
# SSL helper
# ---------------------------------------------------------------------------

def _make_ssl_ctx():
    """Tạo SSL context với certifi CA bundle, hỗ trợ cả dev và PyInstaller."""
    import ssl
    ca_file = None
    # Ưu tiên SSL_CERT_FILE env (set bởi main.py khi frozen)
    env_ca = os.environ.get("SSL_CERT_FILE")
    if env_ca and os.path.isfile(env_ca):
        ca_file = env_ca
    else:
        try:
            import certifi
            ca_file = certifi.where()
        except ImportError:
            pass
    if ca_file and os.path.isfile(ca_file):
        return ssl.create_default_context(cafile=ca_file)
    # Fallback: không verify (tránh crash hoàn toàn)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


# ---------------------------------------------------------------------------
# App catalog
# ---------------------------------------------------------------------------

@dataclass
class VersionEntry:
    name: str
    zip_url: str
    size_mb: int


@dataclass
class AppEntry:
    name: str
    display_name: str
    description: str
    versions: list[VersionEntry]


def fetch_catalog() -> list[AppEntry] | None:
    """Tải catalog.json từ GitHub. Trả về None nếu lỗi."""
    try:
        ctx = _make_ssl_ctx()
        req = urllib.request.Request(CATALOG_URL, headers={
            "User-Agent": "Mozilla/5.0 DynoAIO/1.0",
            "Accept": "application/json, */*",
        })
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            raw = r.read()
        data = json.loads(raw)
        base_url = data.get("base_url", "")
        entries = []
        for item in data.get("apps", []):
            try:
                versions = [
                    VersionEntry(
                        name=str(v["name"]),
                        zip_url=f"{base_url}/{v['zip']}",
                        size_mb=int(v.get("size_mb", 0) or 0),
                    )
                    for v in item.get("versions", [])
                ]
                entries.append(AppEntry(
                    name=item["name"],
                    display_name=item.get("display_name", item["name"]),
                    description=item.get("description", ""),
                    versions=versions,
                ))
            except Exception as item_err:
                logging.warning("fetch_catalog item error: %s item=%s", item_err, item)
        logging.warning("fetch_catalog entries count: %d", len(entries))
        return entries if entries else []
    except Exception as e:
        logging.warning("fetch_catalog error type=%s msg=%s", type(e).__name__, e)
        return None


def find_version_entry(catalog: list[AppEntry], app_name: str, version_name: str) -> VersionEntry | None:
    """Tìm VersionEntry theo tên app và tên version."""
    for app in catalog:
        if app.name.lower() == app_name.lower():
            for v in app.versions:
                if v.name.lower() == version_name.lower():
                    return v
    return None


def download_version(version_entry: VersionEntry, apps_dir: str, app_name: str,
                     on_progress: callable = None) -> tuple[bool, str]:
    """Tải zip của 1 version về và giải nén vào apps_dir/app_name/version_name/."""
    try:
        version_dir = os.path.join(apps_dir, app_name, version_entry.name)
        os.makedirs(version_dir, exist_ok=True)

        ctx = _make_ssl_ctx()
        req = urllib.request.Request(version_entry.zip_url, headers={
            "User-Agent": "Mozilla/5.0 DynoAIO/1.0",
            "Accept": "*/*",
        })

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with urllib.request.urlopen(req, timeout=120, context=ctx) as response:
                total = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                with open(tmp_path, "wb") as f:
                    while True:
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if on_progress:
                            on_progress(downloaded, total)

            with zipfile.ZipFile(tmp_path, "r") as zf:
                zf.extractall(version_dir)

            return True, f"Đã tải {version_entry.name} thành công"
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    except Exception as e:
        logging.warning("download_version %s error type=%s msg=%s", version_entry.name, type(e).__name__, e)
        return False, f"Lỗi tải {version_entry.name}: {type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# App update checker
# ---------------------------------------------------------------------------

def check_app_update(version: str) -> tuple[str | None, str | None]:
    """Kiểm tra bản cập nhật — lọc release có tag dạng version số."""
    import re
    VERSION_RE = re.compile(r'^v?(\d+\.\d+(?:\.\d+)?)$')
    try:
        req = urllib.request.Request(
            f"{GITHUB_API}?per_page=20",
            headers={"User-Agent": "DynoAIO/1.0"}
        )
        ctx = _make_ssl_ctx()
        with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
            releases = json.loads(r.read())

        latest_data = None
        latest_ver = None
        for release in releases:
            tag = release.get("tag_name", "")
            m = VERSION_RE.match(tag)
            if not m:
                continue
            ver = m.group(1)
            if latest_ver is None or _ver_tuple(ver) > _ver_tuple(latest_ver):
                latest_ver = ver
                latest_data = release

        if not latest_ver or _ver_tuple(latest_ver) <= _ver_tuple(version):
            return None, None

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
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return (0,)


def download_and_replace_exe(download_url: str,
                              on_progress: callable = None) -> tuple[bool, str]:
    """Tải exe mới về và thay thế exe hiện tại."""
    try:
        current_exe = sys.executable if getattr(sys, "frozen", False) else None
        if not current_exe:
            return False, "Chỉ hỗ trợ cập nhật khi chạy từ file .exe đã build."

        exe_dir = os.path.dirname(current_exe)
        new_exe = os.path.join(exe_dir, "_update_new.exe")
        old_exe = os.path.join(exe_dir, "_update_old.exe")

        ctx = _make_ssl_ctx()
        req = urllib.request.Request(download_url, headers={"User-Agent": "DynoAIO/1.0"})
        with urllib.request.urlopen(req, timeout=120, context=ctx) as response:
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
