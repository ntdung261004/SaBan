# file: app_lite.py

import sys
import logging
import cv2
import numpy as np
import os
import json
from datetime import datetime
from platformdirs import user_data_dir

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QInputDialog
from PySide6.QtCore import Signal, Slot, QPoint, Qt, QThread, QObject, QTimer
from PySide6.QtGui import QScreen, QIcon, QPixmap

from gui.ui.ui_practice import MainGui
from utils.audio import AudioManager
from utils.camera import count_available_cameras, Camera
from core.triggers import BluetoothTrigger
from core.worker import ProcessingWorker
from utils.license_manager import verify_key
from utils.resource_path import resource_path

# --- Các hàm cấu hình và license ---
APP_DATA_DIR = user_data_dir("ShootingAppLite", "LuanTung")
os.makedirs(APP_DATA_DIR, exist_ok=True)

# Tạo thư mục chứa dữ liệu train YOLO
DATASET_DIR = os.path.join(APP_DATA_DIR, "dataset_yolo")
os.makedirs(DATASET_DIR, exist_ok=True)

log_file_path = os.path.join(APP_DATA_DIR, "app_log_lite.txt")
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] (%(name)s) - %(message)s'))
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), file_handler])
logging.info("--- Application Lite Started ---")
logging.info(f"Thư mục lưu dataset: {DATASET_DIR}")

def _load_config() -> dict:
    config_path = os.path.join(APP_DATA_DIR, "config.json")
    defaults = {
        "camera_index": 0,
        "logo_size": { "width": 150, "height": 150 }
    }
    try:
        if not os.path.exists(config_path):
            with open(config_path, "w", encoding='utf-8') as f:
                json.dump(defaults, f, indent=4, ensure_ascii=False)
            return defaults
        with open(config_path, "r", encoding='utf-8') as f:
            loaded_config = json.load(f)
        config_updated = False
        for key, value in defaults.items():
            if key not in loaded_config:
                loaded_config[key] = value
                config_updated = True
        if config_updated:
            with open(config_path, "w", encoding='utf-8') as f:
                json.dump(loaded_config, f, indent=4, ensure_ascii=False)
        return loaded_config
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Lỗi config: {e}. Dùng mặc định.")
        return defaults

def check_or_request_license() -> bool:
    license_file_path = os.path.join(APP_DATA_DIR, 'license.key')
    if os.path.exists(license_file_path):
        with open(license_file_path, 'r', encoding='utf-8') as f: key = f.read().strip()
        if verify_key(key): return True
        else: os.remove(license_file_path)
    while True:
        key, ok = QInputDialog.getText(None, "Yêu cầu Kích hoạt", "Vui lòng nhập License Key:")
        if not ok: return False
        if verify_key(key):
            with open(license_file_path, 'w', encoding='utf-8') as f: f.write(key)
            QMessageBox.information(None, "Thành công", "Kích hoạt thành công!")
            return True
        else: QMessageBox.warning(None, "Lỗi", "License Key không hợp lệ.")

class PracticeLiteWindow(QMainWindow):
    request_processing = Signal(np.ndarray, str, str, object)

    def __init__(self, config: dict, worker: ProcessingWorker, trigger: BluetoothTrigger):
        super().__init__()
        self.setStyleSheet("background-color: #f5f6fa;")
        self.setWindowTitle("Phần Mềm Luyện Tập Ngắm Bia Chỉ Đỏ")
        self.setWindowIcon(QIcon(resource_path("assets/app_icon.ico")))
        
        self.config = config
        self.audio_manager = AudioManager()
        self.trigger = trigger
        self.worker = worker
        self.gui = MainGui(self.config)
        self.setCentralWidget(self.gui)

        self.cam = None
        self.is_camera_connected = False
        self.final_size = (640, 640)
        self.zoom_level = 1.0
        self.calibrated_center = None
        self.is_processing = False

        self.video_timer = QTimer(self)
        self.video_timer.timeout.connect(self.update_frame)
        
        self.setup_connections()
        self.start_camera()

    def setup_connections(self):
        # --- Chung ---
        self.gui.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        self.trigger.triggered.connect(self.capture_photo)
        self.request_processing.connect(self.worker.process_image)
        self.worker.practice_finished.connect(self.on_processing_finished)

        # --- Trang 1: Practice ---
        self.gui.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        self.gui.calibrate_button.clicked.connect(self.toggle_calibration_mode)
        self.gui.refresh_button.clicked.connect(self.start_camera)
        self.gui.close_button.clicked.connect(self.close)
        self.gui.camera_view_label.clicked.connect(self.on_camera_view_clicked)

        # --- Trang 2: Grouping (Kết nối mới) ---
        self.gui.grouping_zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        self.gui.grouping_refresh_btn.clicked.connect(self.start_camera)
        self.gui.grouping_calibrate_btn.clicked.connect(self.toggle_calibration_mode)
        self.gui.grouping_camera_view.clicked.connect(self.on_camera_view_clicked)
        self.gui.grouping_close_btn.clicked.connect(self.close)
        self.gui.grouping_reset_btn.clicked.connect(self.reset_grouping_session)

    @Slot(int)
    def on_mode_changed(self, index):
        """Xử lý khi chuyển trang"""
        self.gui.stacked_widget.setCurrentIndex(index)
        if index == 0:
            self.gui.zoom_slider.setValue(self.gui.grouping_zoom_slider.value())
        else:
            self.gui.grouping_zoom_slider.setValue(self.gui.zoom_slider.value())
        logging.info(f"Chuyển chế độ: Index {index}")

    def start_camera(self):
        self.disconnect_camera()
        if count_available_cameras() < 2:
            self.disconnect_camera("Vui lòng kết nối USB camera và nhấn 'Làm mới'")
            return
        cam_index = self.config.get('camera_index', 0)
        self.cam = Camera(cam_index)
        if not self.cam.isOpened():
            self.disconnect_camera(f"Lỗi: Không thể mở Camera index {cam_index}.")
            return
        if self.cam.read()[0]:
            self.video_timer.start(30)
            self.is_camera_connected = True
            self.trigger.activate()
            logging.info(f"Camera {cam_index} connected.")
        else:
            self.disconnect_camera(f"Lỗi đọc ảnh từ camera {cam_index}")

    def disconnect_camera(self, message="Mất kết nối camera"):
        self.video_timer.stop()
        self.trigger.deactivate()
        if self.cam: self.cam.release()
        self.cam = None
        self.is_camera_connected = False
        
        self.gui.camera_view_label.setText(message)
        self.gui.camera_view_label.setPixmap(QPixmap())
        self.gui.grouping_camera_view.setText(message)
        self.gui.grouping_camera_view.setPixmap(QPixmap())

    def update_frame(self):
        if not self.is_camera_connected or self.cam is None: return
        ret, frame = self.cam.read()
        if not ret or frame is None:
            self.disconnect_camera()
            return

        frame_cropped = self._crop_frame_to_square(frame)
        frame_resized = cv2.resize(frame_cropped, self.final_size)
        
        # Hiển thị frame đã xử lý zoom và vẽ tâm ngắm
        display_frame = self.get_display_frame(frame_resized)
        self.gui.display_frame(display_frame)

    @Slot()
    def capture_photo(self):
        """
        Xử lý khi nhận tín hiệu bắn (Trigger).
        - Chế độ 1: Lưu ảnh sạch (đã zoom, không reticle) để train YOLO, sau đó vẽ reticle và hiển thị.
        """
        if self.is_processing or not self.is_camera_connected: return
        
        current_page = self.gui.stacked_widget.currentIndex()
        
        # --- Chế độ 1: Kiểm tra đường ngắm (Practice) ---
        if current_page == 0:
            self.is_processing = True
            ret, frame = self.cam.read()
            if ret:
                frame_sq = self._crop_frame_to_square(frame)
                frame_rs = cv2.resize(frame_sq, self.final_size)
                
                # 1. Áp dụng Zoom để lấy frame SẠCH (Dùng cho training)
                clean_zoomed_frame, aim_point = self._apply_zoom_logic(frame_rs)
                
                # 2. Lưu frame sạch vào thư mục dataset
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = f"data_{timestamp}.jpg"
                save_path = os.path.join(DATASET_DIR, filename)
                # Dùng cv2.imwrite để lưu (async hoặc trong luồng khác sẽ tốt hơn, nhưng ở đây làm đơn giản)
                try:
                    cv2.imwrite(save_path, clean_zoomed_frame)
                    logging.info(f"[DATASET] Đã lưu ảnh mẫu: {filename}")
                except Exception as e:
                    logging.error(f"Lỗi lưu ảnh dataset: {e}")

                # 3. Vẽ tâm ngắm lên bản sao để hiển thị cho người dùng
                final_display_frame = clean_zoomed_frame.copy()
                self.draw_custom_reticle(final_display_frame, aim_point)
                
                # 4. Gửi kết quả hiển thị
                self.request_processing.emit(final_display_frame, "", 'practice', {})
            else: 
                self.is_processing = False
        
        # --- Chế độ 2: Kiểm tra độ chụm (Grouping) ---
        elif current_page == 1:
            logging.info("Nút chụp được nhấn ở chế độ Kiểm tra độ chụm (Chưa có logic).")

    @Slot(dict)
    def on_processing_finished(self, result: dict):
        self.gui.update_results(time_str=result.get('time_str'), result_frame=result.get('result_frame'))
        self.is_processing = False
        
    def reset_grouping_session(self):
        logging.info("Reset bài bắn kiểm tra độ chụm.")
        self.gui.grouping_shot_count_lbl.setText("Số phát bắn: 0")

    def shutdown_components(self):
        self.disconnect_camera()
        
    def _crop_frame_to_square(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]; min_dim = min(h, w)
        start_x = (w - min_dim) // 2; start_y = (h - min_dim) // 2
        return frame[start_y : start_y + min_dim, start_x : start_x + min_dim]

    def draw_custom_reticle(self, image, center_point):
        """Vẽ tâm ngắm đơn giản: Dấu cộng (+) màu xanh lá cây."""
        cx, cy = center_point
        color = (0, 255, 0)  # Green
        length = 10; thickness = 1
        cv2.line(image, (cx - length, cy), (cx + length, cy), color, thickness)
        cv2.line(image, (cx, cy - length), (cx, cy + length), color, thickness)

    def _apply_zoom_logic(self, base_frame: np.ndarray):
        """
        Hàm tính toán zoom và tọa độ tâm ngắm, KHÔNG VẼ GÌ CẢ.
        Trả về: (zoomed_frame, display_aim_point)
        """
        h, w, _ = base_frame.shape
        aim_point = self.calibrated_center if self.calibrated_center else (w // 2, h // 2)
        zoomed_frame = base_frame.copy()
        
        if self.zoom_level > 1.0:
            zoomed_w = int(w / self.zoom_level)
            zoomed_h = int(h / self.zoom_level)
            crop_start_x = (w - zoomed_w) // 2
            crop_start_y = (h - zoomed_h) // 2
            
            transformed_x = aim_point[0] - crop_start_x
            transformed_y = aim_point[1] - crop_start_y
            
            display_aim_point = (int(transformed_x * self.zoom_level), int(transformed_y * self.zoom_level))
            
            zoomed_frame = zoomed_frame[crop_start_y:crop_start_y + zoomed_h, crop_start_x:crop_start_x + zoomed_w]
            zoomed_frame = cv2.resize(zoomed_frame, (w, h))
            return zoomed_frame, display_aim_point
        else:
            return zoomed_frame, aim_point

    def get_display_frame(self, base_frame: np.ndarray) -> np.ndarray:
        """
        Hàm tiện ích dùng cho luồng stream video:
        1. Lấy ảnh đã zoom.
        2. Vẽ tâm ngắm luôn.
        """
        frame_to_display, display_aim_point = self._apply_zoom_logic(base_frame)
        self.draw_custom_reticle(frame_to_display, display_aim_point)
        return frame_to_display

    def on_zoom_slider_changed(self, value):
        self.zoom_level = value / 10.0
        self.gui.zoom_value_label.setText(f"{self.zoom_level:.1f}x")
        self.gui.grouping_zoom_val_lbl.setText(f"{self.zoom_level:.1f}x")
        
        if self.sender() == self.gui.zoom_slider:
            self.gui.grouping_zoom_slider.blockSignals(True)
            self.gui.grouping_zoom_slider.setValue(value)
            self.gui.grouping_zoom_slider.blockSignals(False)
        elif self.sender() == self.gui.grouping_zoom_slider:
            self.gui.zoom_slider.blockSignals(True)
            self.gui.zoom_slider.setValue(value)
            self.gui.zoom_slider.blockSignals(False)

    def toggle_calibration_mode(self, force_off=False):
        current_idx = self.gui.stacked_widget.currentIndex()
        target_label = self.gui.camera_view_label if current_idx == 0 else self.gui.grouping_camera_view
        target_btn = self.gui.calibrate_button if current_idx == 0 else self.gui.grouping_calibrate_btn
        
        new_state_is_on = not target_label._is_calibrating
        if force_off: new_state_is_on = False
        
        target_label.set_calibration_mode(new_state_is_on)
        target_btn.setText("Hủy" if new_state_is_on else "Hiệu chỉnh tâm")
        
        if new_state_is_on: QMessageBox.information(self, "Hiệu chỉnh", "Click vào vị trí tâm ngắm mong muốn trên màn hình camera.")
        elif not force_off: self.calibrated_center = None; logging.info("Hủy hiệu chỉnh.")

    def on_camera_view_clicked(self, point: QPoint):
        sender_label = self.sender()
        if not sender_label._is_calibrating: return
        
        pixmap = sender_label._pixmap
        if pixmap.isNull(): return
        
        frame_h, frame_w = self.final_size
        scaled_pixmap = pixmap.scaled(sender_label.size(), Qt.KeepAspectRatio)
        offset_x = (sender_label.width() - scaled_pixmap.width()) // 2
        offset_y = (sender_label.height() - scaled_pixmap.height()) // 2
        
        if not (offset_x <= point.x() < offset_x + scaled_pixmap.width()): return
        
        relative_x = (point.x() - offset_x) / scaled_pixmap.width()
        relative_y = (point.y() - offset_y) / scaled_pixmap.height()
        
        zoomed_w = frame_w / self.zoom_level
        zoomed_h = frame_h / self.zoom_level
        
        crop_start_x = (frame_w - zoomed_w) // 2
        crop_start_y = (frame_h - zoomed_h) // 2
        
        final_x = crop_start_x + (relative_x * zoomed_w)
        final_y = crop_start_y + (relative_y * zoomed_h)
        
        self.calibrated_center = (int(final_x), int(final_y))
        logging.info(f"Hiệu chỉnh tâm mới: {self.calibrated_center}")
        self.toggle_calibration_mode(force_off=True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    if check_or_request_license():
        config = _load_config()
        processing_thread = QThread()
        processing_worker = ProcessingWorker(config=config)
        processing_worker.moveToThread(processing_thread)
        
        bt_trigger = BluetoothTrigger()
        window = PracticeLiteWindow(config, processing_worker, bt_trigger)
        
        app.aboutToQuit.connect(window.shutdown_components)
        app.aboutToQuit.connect(bt_trigger.stop_global_listener)
        app.aboutToQuit.connect(processing_thread.quit)
        app.aboutToQuit.connect(processing_thread.wait)
        
        processing_thread.start()
        bt_trigger.start_global_listener()
        window.showMaximized()
        sys.exit(app.exec())
    else:
        sys.exit()