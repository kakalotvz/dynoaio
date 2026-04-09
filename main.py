"""Entry point — Dyno All In One launcher."""
from __future__ import annotations

import logging
import os
import sys

# Setup logging to file for debugging
logging.basicConfig(
    filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), "dyno_debug.log"),
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8",
)


def _is_admin() -> bool:
    """Return True if the current process has administrator privileges."""
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _relaunch_as_admin() -> None:
    """Re-launch this script/exe with UAC elevation and exit current process."""
    import ctypes
    params = " ".join(f'"{a}"' for a in sys.argv[1:])
    exe = sys.executable
    script = os.path.abspath(sys.argv[0])
    # If frozen (PyInstaller exe), launch the exe directly
    if getattr(sys, "frozen", False):
        ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params or None, None, 1)
    else:
        # Use pythonw.exe if available to avoid console window
        pythonw = exe.replace("python.exe", "pythonw.exe")
        if os.path.isfile(pythonw):
            exe = pythonw
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe, f'"{script}" {params}'.strip(), None, 1
        )
    sys.exit(0)


def _resource_path(relative: str) -> str:
    """Return absolute path to a bundled resource (images, theme.json).
    
    Bundled resources (images/, theme.json) are in _MEIPASS when frozen.
    External resources (Apps/, Drivers/) are always next to the exe.
    """
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative)


def _exe_dir() -> str:
    """Directory of the running exe (or project root in dev mode)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    # Fix SSL certificates for PyInstaller bundle
    import certifi, ssl, os as _os
    _os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    _os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont, QPalette, QColor

    app = QApplication(sys.argv)
    app.setStyleSheet("")  # reset before applying custom

    # Fix chớp nền trắng: set palette tối ngay từ đầu trước khi bất kỳ widget nào hiện
    palette = QPalette()
    dark = QColor("#1a1a2e")
    palette.setColor(QPalette.ColorRole.Window, dark)
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e0e0e0"))
    palette.setColor(QPalette.ColorRole.Base, dark)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#16213e"))
    palette.setColor(QPalette.ColorRole.Button, dark)
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e0e0e0"))
    app.setPalette(palette)

    # --- Config layer ---
    from src.config import ThemeLoader
    theme = ThemeLoader().load(_resource_path("theme.json"))

    # --- Core layer: scan Apps/ ---
    # Apps/ nằm cạnh exe (không bundle vào exe)
    from src.core import AppScanner
    apps_dir = os.path.join(_exe_dir(), "Apps")
    apps = AppScanner().scan(apps_dir)

    # --- Apply global stylesheet (dark theme) ---
    global_style = f"""
        QWidget {{
            background-color: {theme.background_color};
            color: {theme.text_color};
            font-family: "{theme.font_family}";
            font-size: {theme.font_size}pt;
        }}
        QToolTip {{
            background-color: #2a2a4a;
            color: #e0e0e0;
            border: 1px solid #555577;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: {theme.font_size}pt;
        }}
        QScrollBar:vertical {{
            background: {theme.background_color};
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {theme.card_gradient_end};
            border-radius: 4px;
            min-height: 20px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QMessageBox {{
            background-color: {theme.background_color};
            color: {theme.text_color};
        }}
    """
    app.setStyleSheet(global_style)

    # Set default font
    font = QFont(theme.font_family, theme.font_size)
    app.setFont(font)

    # --- UI layer ---
    from src.ui import MainWindow
    window = MainWindow(apps, theme)
    window.resize(720, 540)
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    # Request admin elevation at startup — needed for driver installation
    if not _is_admin():
        _relaunch_as_admin()
    main()
