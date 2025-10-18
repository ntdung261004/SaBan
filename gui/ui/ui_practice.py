# file: gui/ui/ui_practice.py

import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFrame,
    QGraphicsDropShadowEffect, QGroupBox, QSizePolicy
)
from PySide6.QtGui import QFont, QImage, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt, QPoint, Signal

from utils.resource_path import resource_path

class VideoLabel(QLabel):
    clicked = Signal(QPoint)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setScaledContents(False)
        self.aspect_ratio = 1.0
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAlignment(Qt.AlignCenter)
        self._is_calibrating = False

    def set_calibration_mode(self, active: bool):
        self._is_calibrating = active
        self.setCursor(Qt.CrossCursor if active else Qt.ArrowCursor)
        self.setToolTip("Click để chọn tâm ngắm mới" if active else "")

    def mousePressEvent(self, event):
        if self._is_calibrating and event.button() == Qt.LeftButton: self.clicked.emit(event.pos())
        super().mousePressEvent(event)

    def hasHeightForWidth(self): return True
    def heightForWidth(self, width): return int(width * self.aspect_ratio)
    def setPixmap(self, pixmap: QPixmap): self._pixmap = pixmap; self.update()

    def paintEvent(self, event):
        if self._pixmap.isNull():
            super().paintEvent(event)
            return
        painter = QPainter(self)
        scaled_pixmap = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        point = QPoint(int((self.width() - scaled_pixmap.width()) / 2), int((self.height() - scaled_pixmap.height()) / 2))
        painter.drawPixmap(point, scaled_pixmap)

class MainGui(QWidget):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config # Lưu config để lấy logo_size
        
        self.setStyleSheet("""
            QWidget { background-color: #2c3e50; color: #ecf0f1; font-family: 'Segoe UI'; }
            QFrame#panel { background-color: #34495e; border-radius: 12px; border: 1px solid #4a6278; }
            QLabel#title { color: #ecf0f1; padding: 10px; }
            QLabel.panel-title { font-size: 16px; font-weight: bold; color: #ecf0f1; padding: 8px 15px; background-color: #415a72; border-radius: 6px; }
            QPushButton { background-color: #1abc9c; color: white; font-size: 14px; font-weight: bold; border: none; padding: 10px 20px; border-radius: 8px; }
            QPushButton:hover { background-color: #16a085; }
            QPushButton#danger { background-color: #e74c3c; }
            QPushButton#danger:hover { background-color: #c0392b; }
            QSlider::groove:horizontal { border: 1px solid #4a6278; height: 4px; background: #2c3e50; margin: 2px 0; border-radius: 2px; }
            QSlider::handle:horizontal { background: #1abc9c; border: 1px solid #1abc9c; width: 18px; margin: -7px 0; border-radius: 9px; }
            VideoLabel { background-color: #212f3d; border: 1px solid #4a6278; border-radius: 8px; color: #95a5a6; font-size: 24px; }
            #zoomValueLabel { font-size: 13px; font-weight: bold; color: #1abc9c; min-width: 45px; }
            QGroupBox { font-size: 14px; font-weight: bold; border: 1px solid #4a6278; border-radius: 8px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 2px 8px; background-color: #415a72; border-radius: 4px; }
        """)
        self.setupUi()

    def setupUi(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 10, 20, 20)
        root_layout.setSpacing(15)

        title_label = QLabel("PHẦN MỀM BẮN PHÁO SA BÀN")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont('Segoe UI', 18, QFont.Bold))
        root_layout.addWidget(title_label)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        columns_layout.addWidget(self._create_camera_column(), 6)
        columns_layout.addWidget(self._create_right_column(), 4)
        root_layout.addLayout(columns_layout)

    def _create_styled_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        panel.setGraphicsEffect(shadow)
        return panel

    def _create_camera_column(self) -> QWidget:
        panel = self._create_styled_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        
        title = QLabel("Đường ngắm trực tiếp")
        title.setProperty("class", "panel-title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.camera_view_label = VideoLabel("Vui lòng kết nối camera và nhấn làm mới.")
        layout.addWidget(self.camera_view_label, 1)
        
        controls_container = QWidget()
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setContentsMargins(0, 5, 0, 0)
        
        self.refresh_button = QPushButton("Làm mới")
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 50)
        self.zoom_slider.setValue(10)
        self.zoom_value_label = QLabel("1.0x")
        self.zoom_value_label.setObjectName("zoomValueLabel")
        
        self.calibrate_button = QPushButton("Hiệu chỉnh tâm")
        
        controls_layout.addWidget(self.refresh_button)
        controls_layout.addWidget(QLabel("Khoảng cách:"))
        controls_layout.addWidget(self.zoom_slider, 1)
        controls_layout.addWidget(self.zoom_value_label)
        controls_layout.addSpacing(15)
        controls_layout.addWidget(self.calibrate_button)
        
        layout.addWidget(controls_container)
        return panel

    def _create_right_column(self) -> QWidget:
        panel = self._create_styled_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setSpacing(15)
        top_layout.setContentsMargins(0, 15, 0, 15)

        logo_h_layout = QHBoxLayout()
        logo_label = QLabel()
        pixmap = QPixmap(resource_path("assets/images/logo.png"))
        logo_label.setPixmap(pixmap)
        logo_label.setScaledContents(True)

        # Đọc kích thước logo từ config
        logo_size_config = self.config.get("logo_size", {"width": 150, "height": 150})
        logo_width = logo_size_config.get("width", 150)
        logo_height = logo_size_config.get("height", 150)
        logo_label.setMaximumSize(logo_width, logo_height)
        
        logo_label.setAlignment(Qt.AlignCenter)
        logo_h_layout.addStretch()
        logo_h_layout.addWidget(logo_label)
        logo_h_layout.addStretch()
        
        name_label = QLabel("Tác giả: Nguyễn Trung Trực")
        name_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        name_label.setAlignment(Qt.AlignCenter)

        top_layout.addLayout(logo_h_layout)
        top_layout.addWidget(name_label)
        top_layout.addStretch()

        result_box = QGroupBox("Điểm nổ:")
        result_layout = QVBoxLayout(result_box)
        self.time_label = QLabel("Thời gian: --:--:--")
        self.result_image_label = VideoLabel("Chưa có ảnh kết quả")
        result_layout.addWidget(self.time_label)
        result_layout.addWidget(self.result_image_label, 1)

        self.close_button = QPushButton("Đóng ứng dụng")
        self.close_button.setObjectName("danger")
        
        layout.addWidget(top_container, 4)
        layout.addWidget(result_box, 6)
        layout.addWidget(self.close_button)
        
        return panel

    def _convert_cv_to_pixmap(self, cv_img) -> QPixmap:
        if cv_img is None: return QPixmap()
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(qt_image)

    def display_frame(self, frame_bgr):
        if frame_bgr is None: return
        pixmap = self._convert_cv_to_pixmap(frame_bgr)
        self.camera_view_label.setPixmap(pixmap)

    def update_results(self, time_str, result_frame):
        self.time_label.setText(f"Thời gian: {time_str}")
        pixmap = self._convert_cv_to_pixmap(result_frame)
        self.result_image_label.setPixmap(pixmap)
        if pixmap.isNull(): self.result_image_label.setText("Không có ảnh")