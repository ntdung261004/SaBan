# file: gui/ui/ui_practice.py

import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFrame,
    QGraphicsDropShadowEffect, QGroupBox, QSizePolicy, QComboBox, QStackedWidget, QLayout
)
from PySide6.QtGui import QFont, QImage, QPixmap, QPainter, QColor, QResizeEvent
from PySide6.QtCore import Qt, QPoint, Signal

from utils.resource_path import resource_path

class VideoLabel(QLabel):
    clicked = Signal(QPoint)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setScaledContents(False)
        self.aspect_ratio = 1.0
        # Quan trọng: Ignored để widget không tự push kích thước, tuân thủ layout cha
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
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
        self.config = config
        self.base_width = 1280.0
        self.scale_factor = 1.0
        self.setupUi()
        self.update_responsive_style()

    def resizeEvent(self, event: QResizeEvent):
        new_width = event.size().width()
        # Tính lại scale factor
        self.scale_factor = max(0.6, min(new_width / self.base_width, 1.5))
        self.update_responsive_style()
        super().resizeEvent(event)

    def update_responsive_style(self):
        """Điều chỉnh kích thước CSS nhỏ gọn hơn"""
        # Giảm base size xuống: 12px cho chữ thường, 16px cho tiêu đề
        font_normal = max(10, int(12 * self.scale_factor))
        font_title = max(14, int(16 * self.scale_factor))
        font_panel_title = max(12, int(14 * self.scale_factor))
        font_big = max(18, int(24 * self.scale_factor))
        
        padding_btn_v = int(6 * self.scale_factor) # Padding dọc nhỏ hơn
        padding_btn_h = int(12 * self.scale_factor)
        radius = int(6 * self.scale_factor)

        style_sheet = f"""
            QWidget {{ background-color: #f5f6fa; color: #2c3e50; font-family: 'Segoe UI'; font-size: {font_normal}px; }}
            
            QFrame#panel {{ background-color: #ffffff; border-radius: {radius + 2}px; border: 1px solid #dcdde1; }}
            
            QLabel#title {{ color: #2c3e50; padding: 5px; font-size: {font_title}px; font-weight: bold; }}
            
            QLabel.panel-title {{ 
                font-size: {font_panel_title}px; font-weight: bold; color: #2c3e50; 
                padding: {int(5 * self.scale_factor)}px {int(10 * self.scale_factor)}px; 
                background-color: #e5e9f2; border-radius: {radius}px; 
            }}
            
            QPushButton {{ 
                background-color: #1abc9c; color: white; font-size: {font_normal}px; font-weight: bold; 
                border: none; padding: {padding_btn_v}px {padding_btn_h}px; border-radius: {radius}px; 
            }}
            QPushButton:hover {{ background-color: #16a085; }}
            
            QPushButton#danger {{ background-color: #e74c3c; }}
            QPushButton#danger:hover {{ background-color: #c0392b; }}
            
            QPushButton#warning {{ background-color: #f39c12; }} 
            QPushButton#warning:hover {{ background-color: #d35400; }}
            
            QSlider::groove:horizontal {{ border: 1px solid #bdc3c7; height: 4px; background: #ecf0f1; margin: 2px 0; border-radius: 2px; }}
            QSlider::handle:horizontal {{ background: #1abc9c; border: 1px solid #1abc9c; width: 16px; margin: -6px 0; border-radius: 8px; }}
            
            VideoLabel {{ background-color: #dfe6e9; border: 1px solid #bdc3c7; border-radius: {radius}px; color: #7f8c8d; }}
            
            QGroupBox {{ 
                font-size: {font_normal}px; font-weight: bold; 
                border: 1px solid #bdc3c7; border-radius: {radius}px; 
                margin-top: {int(18 * self.scale_factor)}px; 
            }}
            QGroupBox::title {{ 
                subcontrol-origin: margin; subcontrol-position: top left; 
                left: 10px; padding: 0 5px; 
                color: #2c3e50;
            }}
            
            QComboBox {{
                background-color: #ffffff; border: 1px solid #bdc3c7; border-radius: {radius}px;
                padding: 3px 10px; font-weight: bold; min-width: {int(120 * self.scale_factor)}px;
            }}
            
            .big-number {{ font-size: {font_big}px; font-weight: bold; color: #2c3e50; }}
        """
        self.setStyleSheet(style_sheet)

    def setupUi(self):
        root_layout = QVBoxLayout(self)
        # Giảm margin tổng thể
        root_layout.setContentsMargins(10, 5, 10, 10)
        root_layout.setSpacing(10)

        # --- Header ---
        header_layout = QHBoxLayout()
        header_layout.addStretch(1)
        title_label = QLabel("PHẦN MỀM LUYỆN TẬP NGẮM BIA CHỈ ĐỎ")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label, 2)

        mode_container = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Kiểm tra điểm ngắm", "Kiểm tra độ chụm"])
        self.mode_combo.setCursor(Qt.PointingHandCursor)
        mode_container.addWidget(QLabel("Chế độ:"))
        mode_container.addWidget(self.mode_combo)
        header_layout.addLayout(mode_container, 1) 
        root_layout.addLayout(header_layout)

        # --- Content Stack ---
        self.stacked_widget = QStackedWidget()
        self.page_practice = self._create_practice_page()
        self.stacked_widget.addWidget(self.page_practice)
        self.page_grouping = self._create_grouping_page()
        self.stacked_widget.addWidget(self.page_grouping)
        
        root_layout.addWidget(self.stacked_widget)

    def _create_styled_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 3)
        panel.setGraphicsEffect(shadow)
        return panel

    def _create_practice_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        layout.addWidget(self._create_camera_column(is_grouping=False), 6)
        layout.addWidget(self._create_right_column_practice(), 4)
        return page

    def _create_grouping_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        layout.addWidget(self._create_camera_column(is_grouping=True), 6)
        layout.addWidget(self._create_right_column_grouping(), 4)
        return page

    # Gộp hàm tạo cột Camera vì giống nhau 99%
    def _create_camera_column(self, is_grouping: bool) -> QWidget:
        panel = self._create_styled_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        title_text = "Camera Kiểm Tra" if is_grouping else "Đường ngắm trực tiếp"
        title = QLabel(title_text)
        title.setProperty("class", "panel-title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        video_label = VideoLabel("Đang tải...")
        layout.addWidget(video_label, 1)
        
        # Controls
        controls_container = QWidget()
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        refresh_btn = QPushButton("Làm mới")
        zoom_slider = QSlider(Qt.Horizontal)
        zoom_slider.setRange(10, 50)
        zoom_slider.setValue(10)
        zoom_val_lbl = QLabel("1.0x")
        zoom_val_lbl.setObjectName("zoomValueLabel")
        calibrate_btn = QPushButton("Hiệu chỉnh tâm")
        
        controls_layout.addWidget(refresh_btn)
        controls_layout.addWidget(QLabel("Zoom:"))
        controls_layout.addWidget(zoom_slider, 1)
        controls_layout.addWidget(zoom_val_lbl)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(calibrate_btn)
        layout.addWidget(controls_container)

        # Gán biến vào class để controller gọi được
        if not is_grouping:
            self.camera_view_label = video_label
            self.refresh_button = refresh_btn
            self.zoom_slider = zoom_slider
            self.zoom_value_label = zoom_val_lbl
            self.calibrate_button = calibrate_btn
        else:
            self.grouping_camera_view = video_label
            self.grouping_refresh_btn = refresh_btn
            self.grouping_zoom_slider = zoom_slider
            self.grouping_zoom_val_lbl = zoom_val_lbl
            self.grouping_calibrate_btn = calibrate_btn

        return panel

    # --- CỘT PHẢI PAGE 1: PRACTICE ---
    def _create_right_column_practice(self) -> QWidget:
        panel = self._create_styled_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 1. Phần Trên (Tỷ lệ 3) - ĐỂ TRỐNG theo yêu cầu
        top_box = QGroupBox("Thông tin")
        # Quan trọng: Expanding để chiếm đúng tỷ lệ 3 phần
        top_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 2. Phần Dưới (Tỷ lệ 7) - KẾT QUẢ
        result_box = QGroupBox("Kết quả điểm ngắm")
        result_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        r_layout = QVBoxLayout(result_box)
        r_layout.setContentsMargins(10, 15, 10, 10)
        self.time_label = QLabel("Thời gian: --:--:--")
        self.result_image_label = VideoLabel("Chưa có ảnh")
        r_layout.addWidget(self.time_label)
        r_layout.addWidget(self.result_image_label, 1)

        self.close_button = QPushButton("Đóng ứng dụng")
        self.close_button.setObjectName("danger")

        # SET TỶ LỆ CỨNG 3/7
        layout.addWidget(top_box, 3)
        layout.addWidget(result_box, 7)
        layout.addWidget(self.close_button)
        return panel

    # --- CỘT PHẢI PAGE 2: GROUPING ---
    def _create_right_column_grouping(self) -> QWidget:
        panel = self._create_styled_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 1. Phần Trên (Tỷ lệ 3) - THÔNG TIN & RESET
        info_box = QGroupBox("Thông tin bài bắn")
        info_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        i_layout = QVBoxLayout(info_box)
        i_layout.setContentsMargins(10, 15, 10, 10)
        i_layout.addStretch()
        
        self.grouping_shot_count_lbl = QLabel("Số phát bắn: 0")
        self.grouping_shot_count_lbl.setProperty("class", "big-number")
        self.grouping_shot_count_lbl.setAlignment(Qt.AlignCenter)
        
        self.grouping_reset_btn = QPushButton("Bắn lại (Reset)")
        self.grouping_reset_btn.setObjectName("warning")
        self.grouping_reset_btn.setCursor(Qt.PointingHandCursor)

        i_layout.addWidget(self.grouping_shot_count_lbl)
        i_layout.addWidget(self.grouping_reset_btn)
        i_layout.addStretch()

        # 2. Phần Dưới (Tỷ lệ 7) - KẾT QUẢ
        result_box = QGroupBox("Kết quả điểm ngắm")
        result_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        r_layout = QVBoxLayout(result_box)
        r_layout.setContentsMargins(10, 15, 10, 10)
        
        self.grouping_result_lbl = QLabel("Chưa có dữ liệu")
        self.grouping_result_view = VideoLabel("Chưa có ảnh")
        
        r_layout.addWidget(self.grouping_result_lbl)
        r_layout.addWidget(self.grouping_result_view, 1)

        self.grouping_close_btn = QPushButton("Đóng ứng dụng")
        self.grouping_close_btn.setObjectName("danger")

        # SET TỶ LỆ CỨNG 3/7
        layout.addWidget(info_box, 3)
        layout.addWidget(result_box, 7)
        layout.addWidget(self.grouping_close_btn)
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
        current_idx = self.stacked_widget.currentIndex()
        if current_idx == 0:
            self.camera_view_label.setPixmap(pixmap)
        elif current_idx == 1:
            self.grouping_camera_view.setPixmap(pixmap)

    def update_results(self, time_str, result_frame):
        self.time_label.setText(f"Thời gian: {time_str}")
        pixmap = self._convert_cv_to_pixmap(result_frame)
        self.result_image_label.setPixmap(pixmap)
        if pixmap.isNull(): self.result_image_label.setText("Không có ảnh")