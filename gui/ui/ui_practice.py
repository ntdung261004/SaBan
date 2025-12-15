# file: gui/ui/ui_practice.py

import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFrame,
    QGraphicsDropShadowEffect, QGroupBox, QSizePolicy, QComboBox, QStackedWidget, 
    QMessageBox, QDialog
)
from PySide6.QtGui import QFont, QImage, QPixmap, QPainter, QColor, QResizeEvent
from PySide6.QtCore import Qt, QPoint, Signal

# --- Class VideoLabel ---
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

# --- Popup hiển thị 1 điểm chạm ---
class TargetPopup(QDialog):
    def __init__(self, pixmap, cam_name, parent=None):
        super().__init__(parent)
        # Thêm tên Camera vào Title
        self.setWindowTitle(f"Chi tiết điểm chạm - {cam_name}")
        self.resize(600, 600)
        layout = QVBoxLayout(self)
        self.img_label = VideoLabel()
        self.img_label.setPixmap(pixmap)
        layout.addWidget(self.img_label)

# --- Popup hiển thị kết quả tổng hợp (3 phát) ---
class GroupingResultPopup(QDialog):
    def __init__(self, pixmap, diameter, score_text, cam_name, parent=None):
        super().__init__(parent)
        # Thêm tên Camera vào Title
        self.setWindowTitle(f"Kết quả bài bắn ({cam_name}): {score_text}")
        self.resize(800, 700)
        
        layout = QVBoxLayout(self)
        
        # Ảnh kết quả
        self.img_label = VideoLabel()
        self.img_label.setPixmap(pixmap)
        layout.addWidget(self.img_label, 1)
        
        # Thông tin
        info_lbl = QLabel(f"Camera: {cam_name}\nĐường kính độ chụm: {diameter:.2f} px\nĐánh giá: {score_text}")
        info_lbl.setAlignment(Qt.AlignCenter)
        
        color = "#e74c3c" # Đỏ
        if "GIỎI" in score_text: color = "#27ae60"
        elif "KHÁ" in score_text: color = "#2980b9"
        elif "ĐẠT" in score_text: color = "#f39c12"
            
        info_lbl.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color}; padding: 10px;")
        layout.addWidget(info_lbl)
        
        btn = QPushButton("Bắn lại")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("background-color: #3498db; color: white; font-size: 16px; padding: 10px;")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

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
        radius = int(5 * self.scale_factor)

        style_sheet = f"""
            QWidget {{ background-color: #f5f6fa; color: #2c3e50; font-family: 'Segoe UI'; font-size: {font_normal}px; }}
            QFrame#panel {{ background-color: #ffffff; border-radius: {radius}px; border: 1px solid #dcdde1; }}
            QLabel#title {{ color: #2c3e50; font-size: {font_title}px; font-weight: bold; }}
            QLabel.panel-title {{ background-color: #e5e9f2; border-radius: {radius}px; padding: 3px 8px; font-weight: bold; }}
            QPushButton {{ background-color: #1abc9c; color: white; border-radius: {radius}px; padding: 4px 8px; font-weight: bold; }}
            QPushButton#danger {{ background-color: #e74c3c; }}
            QPushButton#warning {{ background-color: #f39c12; }} 
            QPushButton#viewBtn {{ background-color: #3498db; }}
            QGroupBox {{ border: 1px solid #bdc3c7; border-radius: {radius}px; margin-top: 12px; font-weight: bold; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}
            .big-number {{ font-size: {font_big}px; font-weight: bold; color: #2c3e50; }}
            #statusLabel {{ font-size: {font_panel_title}px; font-weight: bold; color: #e74c3c; }}
            QMessageBox {{ background-color: #f5f6fa; color: #2c3e50; }}
            QMessageBox QLabel {{ color: #2c3e50; font-weight: bold; }}
        """
        self.setStyleSheet(style_sheet)

    def setupUi(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 5, 10, 5)
        
        h_layout = QHBoxLayout()
        self.cam_count_combo = QComboBox()
        self.cam_count_combo.addItems(["1 Camera", "2 Camera"])
        h_layout.addWidget(self.cam_count_combo); h_layout.addStretch(1)
        title = QLabel("Phần Mềm Luyện Tập Ngắm Bia Chỉ Đỏ")
        title.setObjectName("title")
        h_layout.addWidget(title, 2, Qt.AlignCenter); h_layout.addStretch(1)
        
        mode_box = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Kiểm tra điểm ngắm", "Kiểm tra độ chụm"])
        mode_box.addWidget(QLabel("Chế độ:")); mode_box.addWidget(self.mode_combo)
        h_layout.addLayout(mode_box)
        root.addLayout(h_layout)

        self.stacked_widget = QStackedWidget()
        self.page_practice = self._create_page_layout(is_grouping=False)
        self.stacked_widget.addWidget(self.page_practice)
        self.page_grouping = self._create_page_layout(is_grouping=True)
        self.stacked_widget.addWidget(self.page_grouping)
        root.addWidget(self.stacked_widget)
        
        self.close_button = QPushButton("Đóng ứng dụng")
        self.close_button.setObjectName("danger")
        root.addWidget(self.close_button)

    def _create_styled_panel(self):
        p = QFrame(); p.setObjectName("panel")
        eff = QGraphicsDropShadowEffect(p); eff.setBlurRadius(10); eff.setColor(QColor(0,0,0,40)); eff.setOffset(0,2)
        p.setGraphicsEffect(eff)
        return p

    def _create_page_layout(self, is_grouping: bool):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0,0,0,0); layout.setSpacing(8)
        if not is_grouping: self.practice_widgets = []; self.practice_rows = []
        else: self.grouping_widgets = []; self.grouping_rows = []

        for i in range(2):
            row, w = self._create_row_ui(i+1, is_grouping)
            layout.addWidget(row, 1)
            if not is_grouping: self.practice_widgets.append(w); self.practice_rows.append(row)
            else: self.grouping_widgets.append(w); self.grouping_rows.append(row)
        
        if not is_grouping: self.practice_rows[1].setVisible(False)
        else: self.grouping_rows[1].setVisible(False)
        return page

    def _create_row_ui(self, index, is_grouping):
        container = QWidget(); layout = QHBoxLayout(container); layout.setContentsMargins(0,0,0,0); layout.setSpacing(10)
        widgets = {}

        # Cam Col
        cam_p = self._create_styled_panel(); cam_l = QVBoxLayout(cam_p); cam_l.setContentsMargins(8,8,8,8)
        title = QLabel(f"Camera {index} - {'Độ Chụm' if is_grouping else 'Điểm Ngắm'}")
        title.setProperty("class", "panel-title"); title.setAlignment(Qt.AlignCenter)
        cam_l.addWidget(title)
        
        vid = VideoLabel("Connecting..."); cam_l.addWidget(vid, 1)
        
        ctrl = QHBoxLayout(); 
        refresh = QPushButton("Làm mới"); src = QComboBox(); src.setFixedWidth(80)
        zoom_s = QSlider(Qt.Horizontal); zoom_s.setRange(10,50); zoom_s.setValue(10)
        zoom_v = QLabel("1.0x"); calib = QPushButton("Hiệu chỉnh")
        ctrl.addWidget(refresh); ctrl.addWidget(src); ctrl.addWidget(QLabel("Zoom:")); ctrl.addWidget(zoom_s, 1)
        ctrl.addWidget(zoom_v); ctrl.addSpacing(5); ctrl.addWidget(calib)
        cam_l.addLayout(ctrl)

        # Info Col
        right_p = self._create_styled_panel(); right_l = QVBoxLayout(right_p); right_l.setContentsMargins(10,10,10,10)
        
        res_box = QGroupBox("Kết quả")
        res_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        res_l = QVBoxLayout(res_box); res_l.setContentsMargins(5,10,5,5); res_l.setSpacing(5)
        
        head_row = QHBoxLayout()
        
        if not is_grouping:
            stat = QLabel("Sẵn sàng"); stat.setObjectName("statusLabel")
            view = QPushButton("Xem mặt bia"); view.setObjectName("viewBtn"); view.setVisible(False)
            head_row.addWidget(stat); head_row.addWidget(view); head_row.addStretch()
            widgets.update({'status_label': stat, 'view_btn': view})
        else:
            shots = QLabel("Số phát: 0/3"); shots.setProperty("class", "big-number")
            stat = QLabel("Sẵn sàng"); stat.setObjectName("statusLabel")
            view = QPushButton("Xem"); view.setObjectName("viewBtn"); view.setVisible(False)
            reset = QPushButton("Bắn lại"); reset.setObjectName("warning")
            
            head_row.addWidget(shots); head_row.addSpacing(10)
            head_row.addWidget(stat); head_row.addWidget(view)
            head_row.addStretch(); head_row.addWidget(reset)
            
            widgets.update({'shot_count': shots, 'status_label': stat, 'view_btn': view, 'reset_btn': reset})

        res_l.addLayout(head_row)
        res_img = VideoLabel("..."); res_l.addWidget(res_img, 1)
        right_l.addWidget(res_box)

        layout.addWidget(cam_p, 6); layout.addWidget(right_p, 4)
        
        widgets.update({'cam_view': vid, 'refresh_btn': refresh, 'source_combo': src, 
                        'zoom_slider': zoom_s, 'zoom_val': zoom_v, 'calib_btn': calib, 
                        'result_view': res_img, 'template_pixmap': None})
        return container, widgets

    def _to_pixmap(self, img):
        if img is None: return QPixmap()
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, c = rgb.shape
        return QPixmap.fromImage(QImage(rgb.data, w, h, c*w, QImage.Format_RGB888))

    def display_frame(self, frame_bgr, cam_index):
        if frame_bgr is None: return
        pixmap = self._to_pixmap(frame_bgr)
        current_idx = self.stacked_widget.currentIndex()
        target = self.practice_widgets[cam_index]['cam_view'] if current_idx == 0 else self.grouping_widgets[cam_index]['cam_view']
        target.setPixmap(pixmap)

    def update_ui_result(self, status, frame, template, idx, is_grouping=False, shot_txt=None):
        widgets = self.grouping_widgets[idx] if is_grouping else self.practice_widgets[idx]
        
        lbl = widgets['status_label']
        lbl.setText(status)
        if "TRÚNG" in status: lbl.setStyleSheet("color: #27ae60; font-weight: bold;")
        elif "TRƯỢT" in status: lbl.setStyleSheet("color: #e74c3c; font-weight: bold;")
        else: lbl.setStyleSheet("color: #2c3e50;")
        
        if is_grouping and shot_txt: widgets['shot_count'].setText(shot_txt)
        
        btn = widgets['view_btn']
        if "TRÚNG" in status and template is not None:
            widgets['template_pixmap'] = self._to_pixmap(template)
            btn.setVisible(True)
            try: btn.clicked.disconnect() 
            except: pass
            # --- TRUYỀN TÊN CAMERA ---
            cam_name = f"Camera {idx + 1}"
            btn.clicked.connect(lambda: self.show_single_popup(widgets['template_pixmap'], cam_name))
        else:
            btn.setVisible(False)
            widgets['template_pixmap'] = None

        widgets['result_view'].setPixmap(self._to_pixmap(frame))

    def show_single_popup(self, pixmap, cam_name):
        if pixmap: TargetPopup(pixmap, cam_name, self).exec()

    def show_final_grouping_popup(self, template_img, diameter, score_text, idx):
        pix = self._to_pixmap(template_img)
        cam_name = f"Camera {idx + 1}"
        GroupingResultPopup(pix, diameter, score_text, cam_name, self).exec()