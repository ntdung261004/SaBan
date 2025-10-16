# file: app_lite.py
# PHIÊN BẢN CUỐI CÙNG - SỬA LỖI TREO MÁY BẰNG CÁCH DÙNG QTIMER

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

# --- Các hàm cấu hình và license (không đổi) ---
APP_DATA_DIR = user_data_dir("ShootingAppLite", "LuanTung")
os.makedirs(APP_DATA_DIR, exist_ok=True)
log_file_path = os.path.join(APP_DATA_DIR, "app_log_lite.txt")
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] (%(name)s) - %(message)s'))
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), file_handler])
logging.info("--- Application Lite Started ---")

def _load_config() -> dict:
    config_path = "config.json"; defaults = {"camera_index": 0}
    try:
        if not os.path.exists(config_path):
            with open(config_path, "w", encoding='utf-8') as f: json.dump(defaults, f, indent=4)
            return defaults
        with open(config_path, "r", encoding='utf-8') as f: loaded_config = json.load(f)
        defaults.update(loaded_config); return defaults
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Lỗi khi đọc file config.json: {e}. Sử dụng giá trị mặc định."); return defaults

def check_or_request_license() -> bool:
    license_file_path = os.path.join(APP_DATA_DIR, 'license.key')
    if os.path.exists(license_file_path):
        with open(license_file_path, 'r', encoding='utf-8') as f: key = f.read().strip()
        if verify_key(key): logging.info("License hợp lệ được tìm thấy."); return True
        else: logging.warning("File license không hợp lệ, đang xóa."); os.remove(license_file_path)
    while True:
        key, ok = QInputDialog.getText(None, "Yêu cầu Kích hoạt", "Vui lòng nhập License Key:")
        if not ok: return False
        if verify_key(key):
            with open(license_file_path, 'w', encoding='utf-8') as f: f.write(key)
            QMessageBox.information(None, "Thành công", "Kích hoạt thành công!"); return True
        else: QMessageBox.warning(None, "Lỗi", "License Key không hợp lệ.")


class PracticeLiteWindow(QMainWindow):
    request_processing = Signal(np.ndarray, str, str, object)

    def __init__(self, config: dict, worker: ProcessingWorker, trigger: BluetoothTrigger):
        super().__init__()
        self.setWindowTitle("Phần Mềm Bắn Pháo Sa Bàn")
        self.setWindowIcon(QIcon(resource_path("assets/app_icon.ico")))
        
        self.config = config
        self.audio_manager = AudioManager()
        self.trigger = trigger
        self.worker = worker
        self.gui = MainGui()
        self.setCentralWidget(self.gui)

        self.cam = None
        self.is_camera_connected = False
        self.final_size = (640, 640)
        self.zoom_level = 1.0
        self.calibrated_center = None
        self.is_processing = False

        # <<< SỬ DỤNG LẠI KIẾN TRÚC QTIMER ỔN ĐỊNH >>>
        self.video_timer = QTimer(self)
        self.video_timer.timeout.connect(self.update_frame)
        
        self.setup_connections()
        self.start_camera()

    def setup_connections(self):
        self.gui.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        self.gui.calibrate_button.clicked.connect(self.toggle_calibration_mode)
        self.gui.refresh_button.clicked.connect(self.start_camera)
        self.gui.close_button.clicked.connect(self.close)
        self.gui.camera_view_label.clicked.connect(self.on_camera_view_clicked)
        self.trigger.triggered.connect(self.capture_photo)
        self.request_processing.connect(self.worker.process_image)
        self.worker.practice_finished.connect(self.on_processing_finished)
    
    def start_camera(self):
        self.disconnect_camera() # Dừng các tiến trình cũ

        if count_available_cameras() < 2:
            self.disconnect_camera("Vui lòng kết nối USB camera và nhấn 'Làm mới'")
            return
        
        cam_index = self.config.get('camera_index', 0)
        self.cam = Camera(cam_index)
        
        if not self.cam.isOpened():
            error_msg = f"Lỗi: Không thể mở Camera index {cam_index}."
            self.disconnect_camera(error_msg)
            QMessageBox.warning(self, "Lỗi kết nối", error_msg)
            return
        
        is_ok, _ = self.cam.read()
        if is_ok:
            self.video_timer.start(30) # ~33 FPS
            self.is_camera_connected = True
            self.trigger.activate()
            logging.info(f"Đã kết nối camera index {cam_index} và bắt đầu cập nhật.")
        else:
            self.disconnect_camera(f"Lỗi: Không đọc được ảnh từ camera index {cam_index}")

    def disconnect_camera(self, message="Vui lòng kết nối USB camera và nhấn 'Làm mới'"):
        self.video_timer.stop()
        self.trigger.deactivate()
        
        if self.cam:
            self.cam.release()
        
        self.cam = None
        self.is_camera_connected = False
        self.gui.camera_view_label.setText(message)
        self.gui.camera_view_label.setPixmap(QPixmap()) # Xóa ảnh cũ

    def update_frame(self):
        if not self.is_camera_connected or self.cam is None: 
            return
        
        # <<< ĐIỂM MẤU CHỐT: cam.read() SẼ TRẢ VỀ FALSE KHI MẤT KẾT NỐI >>>
        ret, frame = self.cam.read()
        if not ret or frame is None:
            logging.warning("update_frame phát hiện đọc frame thất bại. Ngắt kết nối...")
            self.disconnect_camera("Mất kết nối camera.\nVui lòng kết nối lại và nhấn 'Làm mới'")
            return
            
        frame_cropped = self._crop_frame_to_square(frame)
        frame_resized = cv2.resize(frame_cropped, self.final_size)
        display_frame = self.get_display_frame(frame_resized)
        self.gui.display_frame(display_frame)

    @Slot()
    def capture_photo(self):
        if self.is_processing or not self.is_camera_connected or self.cam is None: 
            return
        self.is_processing = True

        ret, frame = self.cam.read()
        if ret and frame is not None:
            frame_cropped = self._crop_frame_to_square(frame)
            frame_resized = cv2.resize(frame_cropped, self.final_size)
            result_frame = self.get_display_frame(frame_resized)
            self.request_processing.emit(result_frame, "", 'practice', {})
        else:
            self.is_processing = False

    @Slot(dict)
    def on_processing_finished(self, result: dict):
        self.gui.update_results(time_str=result.get('time_str'), result_frame=result.get('result_frame'))
        self.is_processing = False
        
    def shutdown_components(self):
        logging.info("Đang tắt các thành phần...")
        self.disconnect_camera()
        
    def _crop_frame_to_square(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]; min_dim = min(h, w)
        start_x = (w - min_dim) // 2; start_y = (h - min_dim) // 2
        return frame[start_y : start_y + min_dim, start_x : start_x + min_dim]

    def draw_custom_reticle(self, image, center_point):
        cx, cy = center_point; h, w, _ = image.shape
        color = (128, 128, 128); thickness = 1; font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.4; axis_len = int(h * 0.4)
        cv2.line(image, (cx, cy - axis_len), (cx, cy + axis_len), color, thickness)
        cv2.line(image, (cx - axis_len, cy), (cx + axis_len, cy), color, thickness)
        num_major_ticks = 5
        for i in range(1, num_major_ticks + 1):
            dist = (i * axis_len) // num_major_ticks; major_tick_size = 8; minor_tick_size = 4
            cv2.line(image, (cx - major_tick_size, cy - dist), (cx + major_tick_size, cy - dist), color, thickness)
            cv2.line(image, (cx - major_tick_size, cy + dist), (cx + major_tick_size, cy + dist), color, thickness)
            cv2.line(image, (cx - dist, cy - major_tick_size), (cx - dist, cy + major_tick_size), color, thickness)
            cv2.line(image, (cx + dist, cy - major_tick_size), (cx + dist, cy + major_tick_size), color, thickness)
            if i <= num_major_ticks:
                mid_dist = dist - (axis_len // num_major_ticks // 2)
                cv2.line(image, (cx - minor_tick_size, cy - mid_dist), (cx + minor_tick_size, cy - mid_dist), color, thickness)
                cv2.line(image, (cx - minor_tick_size, cy + mid_dist), (cx + minor_tick_size, cy + mid_dist), color, thickness)
                cv2.line(image, (cx - mid_dist, cy - minor_tick_size), (cx - mid_dist, cy + minor_tick_size), color, thickness)
                cv2.line(image, (cx + mid_dist, cy - minor_tick_size), (cx + mid_dist, cy + minor_tick_size), color, thickness)
            text = str(i * 10)
            cv2.putText(image, text, (cx + major_tick_size + 5, cy - dist + 4), font, font_scale, color, thickness)
            cv2.putText(image, text, (cx + major_tick_size + 5, cy + dist + 4), font, font_scale, color, thickness)
            cv2.putText(image, text, (cx - dist - 7, cy + major_tick_size + 15), font, font_scale, color, thickness)
            cv2.putText(image, text, (cx + dist - 7, cy + major_tick_size + 15), font, font_scale, color, thickness)

    def get_display_frame(self, base_frame: np.ndarray) -> np.ndarray:
        h, w, _ = base_frame.shape
        aim_point = self.calibrated_center if self.calibrated_center else (w // 2, h // 2)
        frame_to_display = base_frame.copy()
        if self.zoom_level > 1.0:
            zoomed_w, zoomed_h = int(w / self.zoom_level), int(h / self.zoom_level)
            crop_start_x, crop_start_y = (w - zoomed_w) // 2, (h - zoomed_h) // 2
            transformed_x = aim_point[0] - crop_start_x; transformed_y = aim_point[1] - crop_start_y
            display_aim_point = (int(transformed_x * self.zoom_level), int(transformed_y * self.zoom_level))
            frame_to_display = frame_to_display[crop_start_y:crop_start_y + zoomed_h, crop_start_x:crop_start_x + zoomed_w]
            frame_to_display = cv2.resize(frame_to_display, (w, h))
        else:
            display_aim_point = aim_point
        self.draw_custom_reticle(frame_to_display, display_aim_point)
        return frame_to_display

    def on_zoom_slider_changed(self, value):
        self.zoom_level = value / 10.0
        self.gui.zoom_value_label.setText(f"{self.zoom_level:.1f}x")

    def toggle_calibration_mode(self, force_off=False):
        new_state_is_on = not self.gui.camera_view_label._is_calibrating
        if force_off: new_state_is_on = False
        self.gui.camera_view_label.set_calibration_mode(new_state_is_on)
        self.gui.calibrate_button.setText("Hủy" if new_state_is_on else "Hiệu chỉnh tâm")
        if new_state_is_on: QMessageBox.information(self, "Hiệu chỉnh", "Click vào vị trí tâm ngắm mong muốn trên màn hình camera.")
        elif not force_off: self.calibrated_center = None; logging.info("Người dùng đã hủy hiệu chỉnh. Reset tâm ngắm.")

    def on_camera_view_clicked(self, point: QPoint):
        if not self.gui.camera_view_label._is_calibrating: return
        pixmap = self.gui.camera_view_label._pixmap
        if pixmap.isNull(): return
        frame_h, frame_w = self.final_size
        scaled_pixmap = pixmap.scaled(self.gui.camera_view_label.size(), Qt.KeepAspectRatio)
        offset_x = (self.gui.camera_view_label.width() - scaled_pixmap.width()) // 2
        offset_y = (self.gui.camera_view_label.height() - scaled_pixmap.height()) // 2
        if not (offset_x <= point.x() < offset_x + scaled_pixmap.width()): return
        relative_x = (point.x() - offset_x) / scaled_pixmap.width(); relative_y = (point.y() - offset_y) / scaled_pixmap.height()
        zoomed_w = frame_w / self.zoom_level; zoomed_h = frame_h / self.zoom_level
        crop_start_x = (frame_w - zoomed_w) // 2; crop_start_y = (frame_h - zoomed_h) // 2
        final_x = crop_start_x + (relative_x * zoomed_w); final_y = crop_start_y + (relative_y * zoomed_h)
        self.calibrated_center = (int(final_x), int(final_y))
        logging.info(f"Hiệu chỉnh tâm thành công. Tọa độ mới trên ảnh gốc: {self.calibrated_center}")
        self.toggle_calibration_mode(force_off=True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    if check_or_request_license():
        config = _load_config()
        # Worker xử lý ảnh vẫn chạy trên luồng riêng để không làm treo giao diện
        processing_thread = QThread()
        processing_worker = ProcessingWorker(config=config)
        processing_worker.moveToThread(processing_thread)
        
        bt_trigger = BluetoothTrigger()
        window = PracticeLiteWindow(config, processing_worker, bt_trigger)
        
        app.aboutToQuit.connect(window.shutdown_components)
        app.aboutToQuit.connect(bt_trigger.stop_global_listener)
        app.aboutToQuit.connect(processing_thread.quit)
        app.aboutToQuit.connect(processing_thread.wait) # Đảm bảo luồng xử lý kết thúc an toàn
        
        processing_thread.start()
        bt_trigger.start_global_listener()
        window.showMaximized()
        sys.exit(app.exec())
    else:
        sys.exit()