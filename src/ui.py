"""UI Layer — Dyno All In One (PyQt6)"""
from __future__ import annotations

import subprocess
import sys
import os

from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QLinearGradient, QMovie, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel,
    QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QStackedWidget, QVBoxLayout, QWidget,
)

from src.config import ThemeConfig
from src.core import AppInfo, AppType, VersionInfo
from src.launcher import AppLauncher, is_installed


def _resource_path(relative: str) -> str:
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base, relative)


# ---------------------------------------------------------------------------
# HeaderWidget
# ---------------------------------------------------------------------------

class HeaderWidget(QWidget):
    def __init__(self, theme: ThemeConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(14)

        logo_label = QLabel()
        pixmap = QPixmap(_resource_path(self._theme.logo_path))
        if not pixmap.isNull():
            pixmap = pixmap.scaled(220, 120, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        else:
            logo_label.setText("🏎")
            logo_label.setFont(QFont(self._theme.font_family, 28))
        logo_label.setFixedSize(210, 110)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("background: transparent;")

        title_label = QLabel("Dyno All In One")
        title_label.setFont(QFont(self._theme.font_family, self._theme.font_size + 8, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {self._theme.text_color}; background: transparent;")

        layout.addWidget(logo_label)
        layout.addWidget(title_label)
        layout.addStretch()
        self.setFixedHeight(100)

    def paintEvent(self, event) -> None:
        from PyQt6.QtCore import QRectF
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor("#0d1b3e"))
        gradient.setColorAt(1, QColor("#1a1a2e"))
        painter.fillRect(self.rect(), gradient)
        painter.end()
        super().paintEvent(event)


# ---------------------------------------------------------------------------
# AppCard
# ---------------------------------------------------------------------------

class AppCard(QFrame):
    clicked = pyqtSignal(object)

    def __init__(self, app_info: AppInfo, theme: ThemeConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._app_info = app_info
        self._theme = theme
        self._hovered = False
        self._build_ui()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 16, 0)
        layout.setSpacing(0)

        # Left: app name
        name_label = QLabel(self._app_info.name)
        name_label.setFont(QFont(self._theme.font_family, self._theme.font_size + 2, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: {self._theme.text_color}; background: transparent;")
        layout.addWidget(name_label)
        layout.addStretch()

        # Right: logo badge area
        badge = QWidget()
        badge.setFixedSize(140, 56)
        badge.setStyleSheet("background: transparent;")
        badge_layout = QHBoxLayout(badge)
        badge_layout.setContentsMargins(0, 0, 0, 0)

        if self._app_info.logo_path and os.path.isfile(self._app_info.logo_path):
            logo_label = QLabel()
            pixmap = QPixmap(self._app_info.logo_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(130, 52, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(pixmap)
                logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                logo_label.setStyleSheet("background: transparent;")
                badge_layout.addWidget(logo_label)
        layout.addWidget(badge)
        self.setFrameShape(QFrame.Shape.NoFrame)

    def paintEvent(self, event) -> None:
        from PyQt6.QtCore import QRectF
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        if self._hovered:
            # Hover: gradient đỏ-xanh đậm như hình
            gradient.setColorAt(0, QColor("#1a1a3e"))
            gradient.setColorAt(0.5, QColor("#1e2a5e"))
            gradient.setColorAt(1, QColor("#c0392b"))
        else:
            gradient.setColorAt(0, QColor(self._theme.card_gradient_start))
            gradient.setColorAt(1, QColor(self._theme.card_gradient_end))
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(self.rect()), 8, 8)
        # Viền đỏ khi hover
        if self._hovered:
            from PyQt6.QtGui import QPen
            painter.setPen(QPen(QColor("#e94560"), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.75, 0.75, -0.75, -0.75), 8, 8)
        painter.end()
        super().paintEvent(event)

    def enterEvent(self, event) -> None:
        self._hovered = True; self.update()

    def leaveEvent(self, event) -> None:
        self._hovered = False; self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._app_info)


# ---------------------------------------------------------------------------
# AppListScreen
# ---------------------------------------------------------------------------

class AppListScreen(QWidget):
    app_selected = pyqtSignal(object)

    def __init__(self, apps: list[AppInfo], theme: ThemeConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._apps = apps
        self._theme = theme
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Subtitle
        subtitle = QLabel("CHỌN PHẦN MỀM DYNO MÀ BẠN CẦN")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont(self._theme.font_family, self._theme.font_size - 1, QFont.Weight.Bold))
        subtitle.setStyleSheet("color: #8899bb; background: transparent; letter-spacing: 2px;")
        subtitle.setContentsMargins(0, 0, 0, 12)

        if not self._apps:
            layout.addStretch()
            layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignHCenter)
            lbl = QLabel("Không tìm thấy ứng dụng nào")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont(self._theme.font_family, self._theme.font_size + 2))
            lbl.setStyleSheet(f"color: {self._theme.text_color}; background: transparent;")
            layout.addWidget(lbl)
            layout.addStretch()
        else:
            panel = QWidget()
            panel.setFixedWidth(480)
            panel.setStyleSheet("background: transparent;")
            inner = QVBoxLayout(panel)
            inner.setContentsMargins(0, 0, 0, 0)
            inner.setSpacing(10)
            inner.addWidget(subtitle)
            for app_info in self._apps:
                card = AppCard(app_info, self._theme)
                card.clicked.connect(self.app_selected)
                inner.addWidget(card)

            layout.addStretch(1)
            layout.addWidget(panel, alignment=Qt.AlignmentFlag.AlignHCenter)
            layout.addStretch(1)


# ---------------------------------------------------------------------------
# VersionCard  (fix 1: badge text + tooltip)
# ---------------------------------------------------------------------------

class VersionCard(QFrame):
    clicked = pyqtSignal(object)
    uninstall_requested = pyqtSignal(object)  # emit VersionInfo

    def __init__(self, version: VersionInfo, theme: ThemeConfig,
                 installed: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._version = version
        self._theme = theme
        self._installed = installed
        self._hovered = False
        self._badge_label: QLabel | None = None
        self._uninstall_btn: QPushButton | None = None
        self._build_ui()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        name_label = QLabel(self._version.name)
        name_label.setFont(QFont(self._theme.font_family, self._theme.font_size + 1, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: {self._theme.text_color}; background: transparent;")

        self._badge_label = QLabel()
        self._badge_label.setFont(QFont(self._theme.font_family, self._theme.font_size - 1, QFont.Weight.Bold))
        self._badge_label.setFixedHeight(22)

        # Nút gỡ cài đặt — chỉ hiện khi installed
        self._uninstall_btn = QPushButton("Gỡ cài đặt")
        self._uninstall_btn.setFont(QFont(self._theme.font_family, self._theme.font_size - 1, QFont.Weight.Bold))
        self._uninstall_btn.setFixedHeight(26)
        self._uninstall_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._uninstall_btn.setStyleSheet(
            "QPushButton { color: #fff; background-color: #7f1d1d; border: none;"
            " border-radius: 4px; padding: 0 10px; }"
            "QPushButton:hover { background-color: #b91c1c; }"
        )
        self._uninstall_btn.clicked.connect(self._on_uninstall_clicked)

        self._refresh_badge()

        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(self._uninstall_btn)
        layout.addWidget(self._badge_label)
        self.setFrameShape(QFrame.Shape.NoFrame)

    def _on_uninstall_clicked(self) -> None:
        # Chặn click lan ra card (không trigger mở app)
        self.uninstall_requested.emit(self._version)

    def _refresh_badge(self) -> None:
        if self._installed:
            badge_color, badge_text = "#2980b9", "Đã cài ✓"
            tooltip = "Nhấp chuột vào để mở"
            clickable = True
        elif self._version.app_type == AppType.INSTALLABLE:
            badge_color, badge_text = "#e94560", "Cài đặt"
            tooltip = "Phần mềm chưa được cài đặt, nhấp chuột vào để cài"
            clickable = True
        elif self._version.app_type == AppType.PORTABLE:
            badge_color, badge_text = "#27ae60", "Portable"
            tooltip = "Nhấp chuột vào để mở"
            clickable = True
        else:
            badge_color, badge_text = "#666688", "Chưa có dữ liệu"
            tooltip = "Thư mục chưa có tệp phần mềm"
            clickable = False

        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor if clickable
                       else Qt.CursorShape.ForbiddenCursor)
        self.setEnabled(clickable)
        if self._badge_label:
            self._badge_label.setText(badge_text)
            self._badge_label.setStyleSheet(
                f"color: #ffffff; background-color: {badge_color};"
                "border-radius: 4px; padding: 2px 8px;"
            )
        if self._uninstall_btn:
            self._uninstall_btn.setVisible(self._installed)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        from PyQt6.QtCore import QRectF
        gradient = QLinearGradient(0, 0, self.width(), 0)
        if self._hovered:
            gradient.setColorAt(0, QColor("#1a1a3e"))
            gradient.setColorAt(0.5, QColor("#1e2a5e"))
            gradient.setColorAt(1, QColor("#c0392b"))
        else:
            gradient.setColorAt(0, QColor(self._theme.card_gradient_start))
            gradient.setColorAt(1, QColor(self._theme.card_gradient_end))
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(self.rect()), 8, 8)
        if self._hovered:
            from PyQt6.QtGui import QPen
            painter.setPen(QPen(QColor("#e94560"), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.75, 0.75, -0.75, -0.75), 8, 8)
        painter.end()
        super().paintEvent(event)

    def enterEvent(self, event) -> None:
        self._hovered = True; self.update()

    def leaveEvent(self, event) -> None:
        self._hovered = False; self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Không emit nếu click trúng nút gỡ cài đặt
            if self._uninstall_btn and self._uninstall_btn.geometry().contains(event.pos()):
                return
            self.clicked.emit(self._version)

    def event(self, event) -> bool:
        from PyQt6.QtCore import QEvent
        from PyQt6.QtWidgets import QToolTip
        if event.type() == QEvent.Type.ToolTip and self.toolTip():
            QToolTip.showText(event.globalPos(), self.toolTip(), self)
            return True
        return super().event(event)


# ---------------------------------------------------------------------------
# LoadingOverlay  (fix 3)
# ---------------------------------------------------------------------------

class LoadingOverlay(QWidget):
    """Full-window overlay with animated GIF and progress bar."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background-color: rgba(10, 10, 30, 220);")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        self._anim_label = QLabel()
        self._anim_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._anim_label.setStyleSheet("background: transparent;")
        self._movie: QMovie | None = None

        gif_path = _resource_path("images/loading.gif")
        if os.path.isfile(gif_path):
            self._movie = QMovie(gif_path)
            self._anim_label.setMovie(self._movie)
            self._anim_label.setFixedSize(160, 160)
        else:
            self._anim_label.setText("🔧")
            self._anim_label.setFont(QFont("Segoe UI", 36))

        layout.addWidget(self._anim_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._title_lbl = QLabel("ĐANG CÀI ĐẶT")
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet("color: #e94560; background: transparent; letter-spacing: 3px;")
        layout.addWidget(self._title_lbl)

        self._sub_lbl = QLabel("Vui lòng chờ trong giây lát...")
        self._sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub_lbl.setFont(QFont("Segoe UI", 11))
        self._sub_lbl.setStyleSheet("color: #a0a0c0; background: transparent;")
        layout.addWidget(self._sub_lbl)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedSize(360, 8)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet("""
            QProgressBar { background-color: #1a1a3a; border-radius: 4px; border: none; }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e94560, stop:0.5 #ff6b35, stop:1 #e94560);
                border-radius: 4px;
            }
        """)
        layout.addWidget(self._progress, alignment=Qt.AlignmentFlag.AlignCenter)

        self._warn_lbl = QLabel("⚠  Không đóng ứng dụng trong khi cài đặt")
        self._warn_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._warn_lbl.setFont(QFont("Segoe UI", 9))
        self._warn_lbl.setStyleSheet("color: #666688; background: transparent;")
        layout.addWidget(self._warn_lbl)

        self.hide()

    def show_blocking(self, mode: str = "install") -> None:
        if mode == "uninstall":
            self._title_lbl.setText("ĐANG GỠ CÀI ĐẶT")
            self._sub_lbl.setText("Vui lòng chờ trong giây lát...")
            self._warn_lbl.setText("⚠  Không đóng ứng dụng trong khi gỡ cài đặt")
        else:
            self._title_lbl.setText("ĐANG CÀI ĐẶT")
            self._sub_lbl.setText("Vui lòng chờ trong giây lát...")
            self._warn_lbl.setText("⚠  Không đóng ứng dụng trong khi cài đặt")
        parent = self.parent()
        if parent:
            self.setGeometry(parent.rect())
        self.raise_()
        if self._movie:
            self._movie.start()
        self.show()
        QApplication.processEvents()

    def hide(self) -> None:
        if self._movie:
            self._movie.stop()
        super().hide()

    def resizeEvent(self, event) -> None:
        if self.parent():
            self.setGeometry(self.parent().rect())

    def mousePressEvent(self, event) -> None:
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        event.accept()

    def keyPressEvent(self, event) -> None:
        event.accept()


# ---------------------------------------------------------------------------
# VersionListScreen  (fix 4: mark_installed properly rebuilds)
# ---------------------------------------------------------------------------

class VersionListScreen(QWidget):
    back_requested = pyqtSignal()
    version_selected = pyqtSignal(object)
    uninstall_requested = pyqtSignal(object)  # emit VersionInfo

    def __init__(self, app_info: AppInfo, theme: ThemeConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._app_info = app_info
        self._theme = theme
        self._cards: list[VersionCard] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar
        top_bar = QWidget()
        top_bar.setStyleSheet(f"background-color: {self._theme.background_color};")
        top_bar.setFixedHeight(52)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 0, 16, 0)
        top_layout.setSpacing(8)
        back_btn = QPushButton("← Quay lại")
        back_btn.setFont(QFont(self._theme.font_family, self._theme.font_size, QFont.Weight.Bold))
        back_btn.setFixedHeight(34)
        back_btn.setMinimumWidth(120)
        back_btn.setStyleSheet(
            f"QPushButton {{"
            f"  color: {self._theme.text_color};"
            f"  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f"    stop:0 {self._theme.card_gradient_start},"
            f"    stop:1 {self._theme.card_gradient_end});"
            f"  border: 1px solid {self._theme.accent_color};"
            f"  border-radius: 8px;"
            f"  padding: 0 16px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f"    stop:0 {self._theme.card_gradient_end},"
            f"    stop:1 {self._theme.accent_color});"
            f"  border: 1px solid {self._theme.accent_color};"
            f"  color: #ffffff;"
            f"}}"
            f"QPushButton:pressed {{"
            f"  background: {self._theme.accent_color};"
            f"  color: #ffffff;"
            f"}}"
        )
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.back_requested)
        app_name_label = QLabel(self._app_info.name)
        app_name_label.setFont(QFont(self._theme.font_family, self._theme.font_size + 3, QFont.Weight.Bold))
        app_name_label.setStyleSheet(f"color: {self._theme.text_color};")
        top_layout.addWidget(back_btn)
        top_layout.addWidget(app_name_label)
        top_layout.addStretch()
        layout.addWidget(top_bar)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 16, 0, 16)

        if not self._app_info.versions:
            lbl = QLabel("Không có phiên bản nào")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont(self._theme.font_family, self._theme.font_size + 2))
            lbl.setStyleSheet(f"color: {self._theme.text_color};")
            outer.addStretch(); outer.addWidget(lbl); outer.addStretch()
        else:
            panel = QWidget()
            panel.setFixedWidth(480)
            panel.setStyleSheet("background: transparent;")
            self._card_layout = QVBoxLayout(panel)
            self._card_layout.setContentsMargins(0, 0, 0, 0)
            self._card_layout.setSpacing(10)
            for version in self._app_info.versions:
                already = bool(is_installed(self._app_info.name, version.name))
                card = VersionCard(version, self._theme, installed=already)
                card.clicked.connect(self.version_selected)
                card.uninstall_requested.connect(self.uninstall_requested)
                self._card_layout.addWidget(card)
                self._cards.append(card)
            self._card_layout.addStretch()
            row = QHBoxLayout()
            row.addStretch(); row.addWidget(panel); row.addStretch()
            outer.addLayout(row); outer.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def mark_installed(self, version_name: str) -> None:
        """Update the badge on the matching card to 'Đã cài ✓' immediately."""
        for card in self._cards:
            if card._version.name == version_name:
                card._installed = True
                card._refresh_badge()
                card.update()
                break

    def mark_uninstalled(self, version_name: str) -> None:
        """Reset badge về trạng thái chưa cài."""
        for card in self._cards:
            if card._version.name == version_name:
                card._installed = False
                card._refresh_badge()
                card.update()
                break


# ---------------------------------------------------------------------------
# InstallDialog
# ---------------------------------------------------------------------------

class InstallDialog(QDialog):
    def __init__(self, version: VersionInfo, theme: ThemeConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._version = version
        self._theme = theme
        self.setWindowTitle("Xác nhận cài đặt")
        self.setModal(True)
        self.setFixedSize(420, 180)
        self._build_ui()
        self.setStyleSheet(f"background-color: {self._theme.background_color};")

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        msg = QLabel(f"Phần mềm <b>{self._version.name}</b> chưa được cài đặt,\nbạn có muốn cài không?")
        msg.setWordWrap(True)
        msg.setFont(QFont(self._theme.font_family, self._theme.font_size + 1))
        msg.setStyleSheet(f"color: {self._theme.text_color};")
        layout.addWidget(msg)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        install_btn = QPushButton("Cài đặt")
        install_btn.setFont(QFont(self._theme.font_family, self._theme.font_size, QFont.Weight.Bold))
        install_btn.setFixedHeight(36)
        install_btn.setStyleSheet(
            f"QPushButton {{ background-color: {self._theme.accent_color}; color: #fff;"
            f" border: none; border-radius: 6px; padding: 0 20px; }}"
            f"QPushButton:hover {{ background-color: #c73652; }}"
        )
        install_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Hủy")
        cancel_btn.setFont(QFont(self._theme.font_family, self._theme.font_size))
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet(
            f"QPushButton {{ background-color: #444466; color: {self._theme.text_color};"
            f" border: none; border-radius: 6px; padding: 0 20px; }}"
            f"QPushButton:hover {{ background-color: #555577; }}"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(install_btn)
        layout.addLayout(btn_row)


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

class _InstallWorker(QThread):
    finished = pyqtSignal(bool, str, str)  # success, message/exe_path, version_name

    def __init__(self, version: VersionInfo, app_name: str) -> None:
        super().__init__()
        self._version = version
        self._app_name = app_name

    def run(self) -> None:
        try:
            from src.launcher import InstallableRunner
            result = InstallableRunner().run(
                self._version,
                self._app_name,
                on_status=None,
            )
            self.finished.emit(result.success, result.message, self._version.name)
        except Exception as exc:
            import traceback
            self.finished.emit(False, f"Lỗi không xác định: {traceback.format_exc()}", self._version.name)


class _UninstallWorker(QThread):
    finished = pyqtSignal(bool, str, str)  # success, message, version_name

    def __init__(self, version: VersionInfo, app_name: str) -> None:
        super().__init__()
        self._version = version
        self._app_name = app_name

    def run(self) -> None:
        try:
            from src.launcher import SilentUninstaller
            result = SilentUninstaller().uninstall(self._app_name, self._version.name)
            self.finished.emit(result.success, result.message, self._version.name)
        except Exception as exc:
            import traceback
            self.finished.emit(False, f"Lỗi không xác định: {traceback.format_exc()}", self._version.name)


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------
# BodyWidget — body area with background image
# ---------------------------------------------------------------------------

class _BodyWidget(QWidget):
    """Body area that paints background image + grid overlay."""

    def __init__(self, theme: ThemeConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        # WA_StyledBackground cho phép paintEvent hoạt động đúng với stylesheet
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        bg_path = _resource_path("images/background.png")
        self._bg: QPixmap | None = None
        if os.path.isfile(bg_path):
            px = QPixmap(bg_path)
            self._bg = px if not px.isNull() else None
        # Không set background-color ở đây — để paintEvent tự vẽ
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, event) -> None:
        from PyQt6.QtGui import QPen
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Fill màu nền tối
        painter.fillRect(self.rect(), QColor(self._theme.background_color))

        # 2. Ảnh nền
        if self._bg:
            scaled = self._bg.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.setOpacity(0.40)
            painter.drawPixmap(x, y, scaled)
            painter.setOpacity(1.0)

        # 3. Grid overlay
        painter.setPen(QPen(QColor("#1e2a4a"), 0.5))
        cell = 40
        for x in range(0, self.width() + cell, cell):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height() + cell, cell):
            painter.drawLine(0, y, self.width(), y)

        painter.end()


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

class MainWindow(QWidget):
    def __init__(self, apps: list[AppInfo], theme: ThemeConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._apps = apps
        self._theme = theme
        self._worker: _InstallWorker | None = None
        self._uninstall_worker: _UninstallWorker | None = None
        self._current_version_screen: VersionListScreen | None = None
        self._loading: LoadingOverlay | None = None
        self._build_ui()
        self._apply_theme()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._header = HeaderWidget(self._theme)
        root.addWidget(self._header)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {self._theme.card_gradient_end};")
        sep.setFixedHeight(1)
        root.addWidget(sep)

        # Body với background image
        self._body = _BodyWidget(self._theme, self)
        body_layout = QVBoxLayout(self._body)
        body_layout.setContentsMargins(0, 0, 0, 0)

        # QStackedWidget phải transparent để _BodyWidget paintEvent hiện ra
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")
        self._stack.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        body_layout.addWidget(self._stack)
        root.addWidget(self._body)

        self._app_list_screen = AppListScreen(self._apps, self._theme)
        self._app_list_screen.app_selected.connect(self._on_app_selected)
        self._stack.addWidget(self._app_list_screen)
        # Loading overlay lives on top of the whole window
        self._loading = LoadingOverlay(self)

    def _apply_theme(self) -> None:
        icon_path = _resource_path("images/icon.ico")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle("Dyno All In One")
        self.setMinimumSize(640, 480)
        self.setStyleSheet(f"background-color: {self._theme.background_color};")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._loading:
            self._loading.setGeometry(self.rect())

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _on_app_selected(self, app_info: AppInfo) -> None:
        screen = VersionListScreen(app_info, self._theme)
        screen.back_requested.connect(self._go_back)
        screen.version_selected.connect(self._on_version_selected)
        screen.uninstall_requested.connect(self._on_uninstall_requested)
        while self._stack.count() > 1:
            old = self._stack.widget(1)
            self._stack.removeWidget(old)
            old.deleteLater()
        self._stack.addWidget(screen)
        self._current_version_screen = screen
        self._stack.setCurrentIndex(1)

    def _go_back(self) -> None:
        self._stack.setCurrentIndex(0)

    def _on_version_selected(self, version: VersionInfo) -> None:
        if version.app_type == AppType.PORTABLE:
            from src.launcher import PortableRunner
            result = PortableRunner().run(version.path)
            if not result.success:
                QMessageBox.warning(self, "Lỗi", result.message)
            return

        if version.app_type == AppType.EMPTY:
            return

        app_name = self._current_version_screen._app_info.name if self._current_version_screen else ""

        # Already installed → launch directly
        exe = is_installed(app_name, version.name)
        if exe:
            from src.launcher import _launch_exe
            result = _launch_exe(exe)
            if not result.success:
                QMessageBox.warning(self, "Lỗi", result.message)
            return

        # Not installed → confirm then install
        dialog = InstallDialog(version, self._theme, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # Show blocking overlay — prevents all interaction during install
        self._loading.show_blocking()

        self._worker = _InstallWorker(version, app_name)
        self._worker.finished.connect(self._on_install_finished)
        self._worker.start()

    def _on_install_finished(self, success: bool, message: str, version_name: str) -> None:
        self._loading.hide()

        if not success:
            QMessageBox.critical(self, "Lỗi cài đặt", message or "Cài đặt thất bại. Vui lòng thử lại.")
            return

        if self._current_version_screen:
            self._current_version_screen.mark_installed(version_name)

        exe_path = message
        reply = QMessageBox.question(
            self,
            "Cài đặt hoàn tất",
            "Cài đặt hoàn tất! Bạn có muốn khởi chạy ứng dụng ngay không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes and exe_path and os.path.isfile(exe_path):
            from src.launcher import _launch_exe
            result = _launch_exe(exe_path)
            if not result.success:
                QMessageBox.warning(self, "Lỗi", result.message)

    def _on_uninstall_requested(self, version: VersionInfo) -> None:
        app_name = self._current_version_screen._app_info.name if self._current_version_screen else ""
        reply = QMessageBox.question(
            self,
            "Xác nhận gỡ cài đặt",
            f"Bạn có chắc muốn gỡ cài đặt <b>{version.name}</b> không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._loading.show_blocking(mode="uninstall")
        self._uninstall_worker = _UninstallWorker(version, app_name)
        self._uninstall_worker.finished.connect(self._on_uninstall_finished)
        self._uninstall_worker.start()

    def _on_uninstall_finished(self, success: bool, message: str, version_name: str) -> None:
        self._loading.hide()
        if not success:
            QMessageBox.critical(self, "Lỗi gỡ cài đặt", message or "Gỡ cài đặt thất bại. Vui lòng thử lại.")
            return
        if self._current_version_screen:
            self._current_version_screen.mark_uninstalled(version_name)
        QMessageBox.information(self, "Hoàn tất", f"Đã gỡ cài đặt {version_name} thành công.")
