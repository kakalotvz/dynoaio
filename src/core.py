from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum


class AppType(Enum):
    PORTABLE = "portable"
    INSTALLABLE = "installable"
    EMPTY = "empty"  # no usable exe found — folder has no data yet


@dataclass
class VersionInfo:
    name: str
    path: str
    app_type: AppType


@dataclass
class AppInfo:
    name: str
    path: str
    versions: list[VersionInfo] = field(default_factory=list)
    logo_path: str = ""  # optional: Apps/<AppName>/logo.png|jpg|ico


class AppTypeDetector:
    """Classify a version directory.

    - INSTALLABLE: contains a .exe/.msi file with "setup" in the name
    - PORTABLE:    contains at least one .exe that is NOT a setup file
    - EMPTY:       no usable .exe found (folder empty or only sub-dirs)
    """

    def detect(self, version_path: str) -> AppType:
        try:
            entries = list(os.scandir(version_path))
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            return AppType.EMPTY

        has_setup = False
        has_runnable_exe = False

        for entry in entries:
            if not entry.is_file():
                continue
            lower = entry.name.lower()
            if "setup" in lower and (lower.endswith(".exe") or lower.endswith(".msi")):
                has_setup = True
            elif lower.endswith(".exe"):
                has_runnable_exe = True

        if has_setup:
            return AppType.INSTALLABLE
        if has_runnable_exe:
            return AppType.PORTABLE
        return AppType.EMPTY


class AppScanner:
    """Scan an Apps/ directory and return one AppInfo per app sub-directory."""

    def __init__(self) -> None:
        self._detector = AppTypeDetector()

    def scan(self, apps_dir: str) -> list[AppInfo]:
        if not os.path.isdir(apps_dir):
            return []
        try:
            app_entries = sorted(os.scandir(apps_dir), key=lambda e: e.name)
        except PermissionError:
            return []
        return [
            self._scan_app(e.name, e.path)
            for e in app_entries if e.is_dir()
        ]

    def _scan_app(self, app_name: str, app_path: str) -> AppInfo:
        try:
            children = list(os.scandir(app_path))
        except PermissionError:
            return AppInfo(name=app_name, path=app_path)

        # Optional logo file in the app directory
        logo_path = ""
        for ext in (".png", ".jpg", ".jpeg", ".ico"):
            candidate = os.path.join(app_path, f"logo{ext}")
            if os.path.isfile(candidate):
                logo_path = candidate
                break

        # Tất cả sub-dir đều là version (kể cả rỗng — sẽ hiển thị "Chưa có dữ liệu" để tải về)
        # Chỉ loại trừ các thư mục driver/tool đặc biệt không phải phiên bản phần mềm
        EXCLUDED_DIRS = {"driver", "drivers", "ftdi_ft232_drive", "ilink driver",
                         "dotnetfx40", "windowsinstaller3_1"}
        sub_dirs = [
            e for e in children
            if e.is_dir() and e.name.lower() not in EXCLUDED_DIRS
        ]

        if sub_dirs:
            versions = [
                VersionInfo(name=e.name, path=e.path,
                            app_type=self._detector.detect(e.path))
                for e in sorted(sub_dirs, key=lambda e: e.name)
            ]
        else:
            # Flat layout: the app dir itself is the single version
            versions = [
                VersionInfo(name=app_name, path=app_path,
                            app_type=self._detector.detect(app_path))
            ]

        return AppInfo(name=app_name, path=app_path, versions=versions, logo_path=logo_path)
