# file: gui/ui/ui_practice.py

import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFrame,
    QGraphicsDropShadowEffect, QGroupBox, QSizePolicy, QComboBox, QStackedWidget, 
    QMessageBox, QDialog
)
from PySide6.QtGui import QFont, QImage, QPixmap, QPainter, QColor, QResizeEvent
from PySide6.QtCore import Qt, QPoint, Signal

from utils.resource_path import resource_path

# --- Class VideoLabel (Dùng chung) ---
class VideoLabel(QLabel):
    clicked = Signal(QPoint)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setScaledContents(False)
        self.aspect_ratio = 1.0
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

# --- Popup hiển thị mặt bia gốc ---
class TargetPopup(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chi tiết điểm chạm")
        self.setModal(True)
        self.resize(800, 600)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.img_label = VideoLabel()
        self.img_label.setPixmap(pixmap)
        layout.addWidget(self.img_label)

class MainGui(QWidget):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.base_width = 1280.0
        self.scale_factor = 1.0
        
        self.practice_widgets = [] 
        self.grouping_widgets = []
        self.practice_rows = []
        self.grouping_rows = []
        
        self.setupUi()
        self.update_responsive_style()

    def resizeEvent(self, event: QResizeEvent):
        new_width = event.size().width()
        self.scale_factor = max(0.6, min(new_width / self.base_width, 1.5))
        self.update_responsive_style()
        super().resizeEvent(event)

    def update_responsive_style(self):
        font_normal = max(9, int(11 * self.scale_factor))
        font_title = max(13, int(15 * self.scale_factor))
        font_panel_title = max(10, int(12 * self.scale_factor))
        font_big = max(16, int(20 * self.scale_factor))
        
        padding_btn_v = int(4 * self.scale_factor)
        padding_btn_h = int(8 * self.scale_factor)
        radius = int(5 * self.scale_factor)

        style_sheet = f"""
            QWidget {{ background-color: #f5f6fa; color: #2c3e50; font-family: 'Segoe UI'; font-size: {font_normal}px; }}
            QFrame#panel {{ background-color: #ffffff; border-radius: {radius}px; border: 1px solid #dcdde1; }}
            QLabel#title {{ color: #2c3e50; padding: 2px; font-size: {font_title}px; font-weight: bold; }}
            QLabel.panel-title {{ 
                font-size: {font_panel_title}px; font-weight: bold; color: #2c3e50; 
                padding: {int(3 * self.scale_factor)}px {int(8 * self.scale_factor)}px; 
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
            QPushButton#viewBtn {{ background-color: #3498db; }}
            QPushButton#viewBtn:hover {{ background-color: #2980b9; }}
            QSlider::groove:horizontal {{ border: 1px solid #bdc3c7; height: 4px; background: #ecf0f1; margin: 2px 0; border-radius: 2px; }}
            QSlider::handle:horizontal {{ background: #1abc9c; border: 1px solid #1abc9c; width: 14px; margin: -5px 0; border-radius: 7px; }}
            VideoLabel {{ background-color: #dfe6e9; border: 1px solid #bdc3c7; border-radius: {radius}px; color: #7f8c8d; }}
            QGroupBox {{ 
                font-size: {font_normal}px; font-weight: bold; 
                border: 1px solid #bdc3c7; border-radius: {radius}px; 
                margin-top: {int(12 * self.scale_factor)}px; 
            }}
            QGroupBox::title {{ 
                subcontrol-origin: margin; subcontrol-position: top left; 
                left: 10px; padding: 0 5px; 
                color: #2c3e50;
            }}
            QComboBox {{
                background-color: #ffffff; border: 1px solid #bdc3c7; border-radius: {radius}px;
                padding: 2px 8px; font-weight: bold; min-width: {int(100 * self.scale_factor)}px;
            }}
            .big-number {{ font-size: {font_big}px; font-weight: bold; color: #2c3e50; }}
            #statusLabel {{ font-size: {font_panel_title}px; font-weight: bold; color: #e74c3c; }}
            QMessageBox {{ background-color: #f5f6fa; color: #2c3e50; }}
            QMessageBox QLabel {{ color: #2c3e50; font-weight: bold; font-size: {font_normal + 2}px; }}
            QMessageBox QPushButton {{ background-color: #1abc9c; color: white; border-radius: 4px; padding: 6px 18px; }}
        """
        self.setStyleSheet(style_sheet)

    def setupUi(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 5, 10, 5)
        root_layout.setSpacing(5)

        header_layout = QHBoxLayout()
        self.cam_count_combo = QComboBox()
        self.cam_count_combo.addItems(["1 Camera", "2 Camera"])
        self.cam_count_combo.setCursor(Qt.PointingHandCursor)
        self.cam_count_combo.setFixedWidth(120)
        
        header_layout.addWidget(self.cam_count_combo)
        header_layout.addStretch(1)
        title_label = QLabel("Phần Mềm Luyện Tập Ngắm Bia Chỉ Đỏ")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label, 2)
        header_layout.addStretch(1)

        mode_container = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Kiểm tra điểm ngắm", "Kiểm tra độ chụm"])
        self.mode_combo.setCursor(Qt.PointingHandCursor)
        mode_container.addWidget(QLabel("Chế độ:"))
        mode_container.addWidget(self.mode_combo)
        header_layout.addLayout(mode_container) 
        
        root_layout.addLayout(header_layout)

        self.stacked_widget = QStackedWidget()
        self.page_practice = self._create_page_layout(is_grouping=False)
        self.stacked_widget.addWidget(self.page_practice)
        self.page_grouping = self._create_page_layout(is_grouping=True)
        self.stacked_widget.addWidget(self.page_grouping)
        
        root_layout.addWidget(self.stacked_widget)
        
        self.close_button = QPushButton("Đóng ứng dụng")
        self.close_button.setObjectName("danger")
        root_layout.addWidget(self.close_button)

    def _create_styled_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 2)
        panel.setGraphicsEffect(shadow)
        return panel

    def _create_page_layout(self, is_grouping: bool) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        if not is_grouping: 
            self.practice_widgets = []
            self.practice_rows = [] 
        else: 
            self.grouping_widgets = []
            self.grouping_rows = []

        for i in range(2):
            row_widget, widgets_dict = self._create_row_ui(index=i+1, is_grouping=is_grouping)
            layout.addWidget(row_widget, 1)
            
            if not is_grouping: 
                self.practice_widgets.append(widgets_dict)
                self.practice_rows.append(row_widget)
            else: 
                self.grouping_widgets.append(widgets_dict)
                self.grouping_rows.append(row_widget)
        
        if not is_grouping: self.practice_rows[1].setVisible(False)
        else: self.grouping_rows[1].setVisible(False)
            
        return page

    def _create_row_ui(self, index: int, is_grouping: bool):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        widgets = {} 

        cam_panel = self._create_styled_panel()
        cam_layout = QVBoxLayout(cam_panel)
        cam_layout.setContentsMargins(8, 8, 8, 8)
        cam_layout.setSpacing(5)
        
        title_text = f"Camera {index} - Kiểm Tra" if is_grouping else f"Camera {index} - Đường Ngắm"
        title = QLabel(title_text)
        title.setProperty("class", "panel-title")
        title.setAlignment(Qt.AlignCenter)
        cam_layout.addWidget(title)
        
        video_label = VideoLabel(f"Đang kết nối Cam {index}...")
        cam_layout.addWidget(video_label, 1)
        
        ctrl_box = QWidget()
        ctrl_layout = QHBoxLayout(ctrl_box)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        
        refresh_btn = QPushButton("Làm mới")
        
        # Thêm Combo chọn Source Camera
        source_combo = QComboBox()
        source_combo.setToolTip("Chọn nguồn camera")
        source_combo.setFixedWidth(100)
        
        zoom_slider = QSlider(Qt.Horizontal)
        zoom_slider.setRange(10, 50)
        zoom_slider.setValue(10)
        zoom_val = QLabel("1.0x")
        zoom_val.setObjectName("zoomValueLabel")
        calib_btn = QPushButton("Hiệu chỉnh")
        
        ctrl_layout.addWidget(refresh_btn)
        ctrl_layout.addWidget(source_combo) # Thêm vào layout
        ctrl_layout.addWidget(QLabel("Zoom:"))
        ctrl_layout.addWidget(zoom_slider, 1)
        ctrl_layout.addWidget(zoom_val)
        ctrl_layout.addSpacing(5)
        ctrl_layout.addWidget(calib_btn)
        cam_layout.addWidget(ctrl_box)
        
        right_panel = self._create_styled_panel()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(8)
        
        if not is_grouping:
            res_box = QGroupBox("Kết quả")
            res_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            res_layout = QVBoxLayout(res_box)
            res_layout.setContentsMargins(5, 10, 5, 5)
            res_layout.setSpacing(5)
            
            status_row = QHBoxLayout()
            status_lbl = QLabel("Sẵn sàng")
            status_lbl.setObjectName("statusLabel")
            view_btn = QPushButton("Xem mặt bia")
            view_btn.setObjectName("viewBtn")
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.setVisible(False) 
            
            status_row.addWidget(status_lbl)
            status_row.addWidget(view_btn)
            status_row.addStretch()
            res_layout.addLayout(status_row)
            res_img = VideoLabel("...")
            res_layout.addWidget(res_img, 1)
            right_layout.addWidget(res_box)
            
            widgets['status_label'] = status_lbl
            widgets['view_btn'] = view_btn
            widgets['result_view'] = res_img
            widgets['template_pixmap'] = None
        else:
            info_box = QGroupBox("Bài bắn")
            info_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            info_layout = QVBoxLayout(info_box)
            info_layout.setContentsMargins(5, 10, 5, 5)
            shot_count = QLabel("0")
            shot_count.setProperty("class", "big-number")
            shot_count.setAlignment(Qt.AlignCenter)
            reset_btn = QPushButton("Reset")
            reset_btn.setObjectName("warning")
            info_layout.addWidget(shot_count)
            info_layout.addWidget(reset_btn)
            
            res_box = QGroupBox("Kết quả")
            res_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            res_layout = QVBoxLayout(res_box)
            res_layout.setContentsMargins(5, 10, 5, 5)
            grp_lbl = QLabel("...")
            grp_img = VideoLabel("...")
            res_layout.addWidget(grp_lbl)
            res_layout.addWidget(grp_img, 1)
            right_layout.addWidget(info_box, 3)
            right_layout.addWidget(res_box, 7)
            
            widgets['shot_count'] = shot_count
            widgets['reset_btn'] = reset_btn
            widgets['grouping_lbl'] = grp_lbl
            widgets['result_view'] = grp_img

        layout.addWidget(cam_panel, 6)
        layout.addWidget(right_panel, 4)
        
        widgets['cam_view'] = video_label
        widgets['refresh_btn'] = refresh_btn
        widgets['source_combo'] = source_combo # Lưu widget source
        widgets['zoom_slider'] = zoom_slider
        widgets['zoom_val'] = zoom_val
        widgets['calib_btn'] = calib_btn
        
        return container, widgets

    def _convert_cv_to_pixmap(self, cv_img) -> QPixmap:
        if cv_img is None: return QPixmap()
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(qt_image)

    def display_frame(self, frame_bgr, cam_index):
        if frame_bgr is None: return
        pixmap = self._convert_cv_to_pixmap(frame_bgr)
        current_idx = self.stacked_widget.currentIndex()
        target = self.practice_widgets[cam_index]['cam_view'] if current_idx == 0 else self.grouping_widgets[cam_index]['cam_view']
        target.setPixmap(pixmap)

    def update_results(self, status_text, result_frame, template_frame, cam_index):
        widgets = self.practice_widgets[cam_index]
        lbl = widgets['status_label']
        lbl.setText(status_text)
        view_btn = widgets['view_btn']
        
        if "TRÚNG" in status_text:
            lbl.setStyleSheet("color: #27ae60; font-weight: bold;")
            if template_frame is not None:
                widgets['template_pixmap'] = self._convert_cv_to_pixmap(template_frame)
                view_btn.setVisible(True)
                try: view_btn.clicked.disconnect() 
                except: pass
                view_btn.clicked.connect(lambda: self.show_target_popup(widgets['template_pixmap']))
        else:
            lbl.setStyleSheet("color: #e74c3c; font-weight: bold;")
            view_btn.setVisible(False)
            widgets['template_pixmap'] = None

        pixmap = self._convert_cv_to_pixmap(result_frame)
        widgets['result_view'].setPixmap(pixmap)
        if pixmap.isNull(): widgets['result_view'].setText("Không ảnh")

    def show_target_popup(self, pixmap):
        if pixmap:
            popup = TargetPopup(pixmap, self)
            popup.exec()