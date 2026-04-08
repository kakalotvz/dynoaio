"""Entry point — Dyno All In One launcher."""
from __future__ import annotations

import os
import sys


def _resource_path(relative: str) -> str:
    """Return absolute path to a resource, works in dev and PyInstaller bundle."""
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative)


def main() -> None:
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
    from src.core import AppScanner
    apps_dir = _resource_path("Apps")
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
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
