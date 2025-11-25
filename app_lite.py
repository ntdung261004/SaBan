# file: app_lite.py

import sys
import logging
import cv2
import numpy as np
import os
import json
from datetime import datetime
from platformdirs import user_data_dir
from functools import partial

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QInputDialog
from PySide6.QtCore import Signal, Slot, QPoint, Qt, QThread, QObject, QTimer
from PySide6.QtGui import QScreen, QIcon, QPixmap

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    logging.warning("Chưa cài đặt thư viện 'ultralytics'.")

from gui.ui.ui_practice import MainGui
from utils.audio import AudioManager
from utils.camera import count_available_cameras, Camera, get_available_camera_indexes
from core.triggers import BluetoothTrigger
from core.worker import ProcessingWorker
from utils.license_manager import verify_key
from utils.resource_path import resource_path

APP_DATA_DIR = user_data_dir("ShootingAppLite", "LuanTung")
os.makedirs(APP_DATA_DIR, exist_ok=True)
DATASET_DIR = os.path.join(APP_DATA_DIR, "dataset_yolo")
os.makedirs(DATASET_DIR, exist_ok=True)

log_file_path = os.path.join(APP_DATA_DIR, "app_log_lite.txt")
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), logging.FileHandler(log_file_path, encoding='utf-8')])
logging.info("--- Application Lite Started (Final Optimization) ---")

def _load_config() -> dict:
    config_path = os.path.join(APP_DATA_DIR, "config.json")
    defaults = {
        "camera_indexes": [],
        "ai_model_path": "biachido.pt"
    }
    try:
        if not os.path.exists(config_path):
            with open(config_path, "w", encoding='utf-8') as f: json.dump(defaults, f, indent=4)
            return defaults
        with open(config_path, "r", encoding='utf-8') as f:
            cfg = json.load(f)
            if "camera_indexes" not in cfg: cfg["camera_indexes"] = []
            return cfg
    except: return defaults

def _save_config(config: dict):
    try:
        config_path = os.path.join(APP_DATA_DIR, "config.json")
        with open(config_path, "w", encoding='utf-8') as f: json.dump(config, f, indent=4)
    except: pass

def check_or_request_license() -> bool:
    license_file_path = os.path.join(APP_DATA_DIR, 'license.key')
    if os.path.exists(license_file_path):
        with open(license_file_path, 'r', encoding='utf-8') as f: key = f.read().strip()
        if verify_key(key): return True
        else: os.remove(license_file_path)
    while True:
        key, ok = QInputDialog.getText(None, "Yêu cầu Kích hoạt", "Nhập License Key:")
        if not ok: return False
        if verify_key(key):
            with open(license_file_path, 'w', encoding='utf-8') as f: f.write(key)
            QMessageBox.information(None, "Thành công", "OK")
            return True
        else: QMessageBox.warning(None, "Lỗi", "Key sai")

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

        self.cams = [None, None]
        self.is_connected = [False, False]
        self.final_size = (640, 640)
        
        self.zoom_levels = [1.0, 1.0]
        self.calib_centers = [None, None]
        self.is_processing_cam = [False, False]
        self.available_sources = [] 

        self.video_timer = QTimer(self)
        self.video_timer.timeout.connect(self.update_frames)
        
        self.setup_connections()
        self.scan_and_init_cameras()

    def scan_and_init_cameras(self):
        self.available_sources = get_available_camera_indexes()
        for i in range(2):
            cb_p = self.gui.practice_widgets[i]['source_combo']
            cb_p.clear(); cb_g = self.gui.grouping_widgets[i]['source_combo']; cb_g.clear()
            for src_idx in self.available_sources:
                txt = f"Camera {src_idx}"
                cb_p.addItem(txt, src_idx); cb_g.addItem(txt, src_idx)

        saved = self.config.get("camera_indexes", [])
        target = [0, 0]
        if len(saved) >= 2 and saved[0] in self.available_sources: target = saved
        else:
            if len(self.available_sources) >= 2:
                usb = [x for x in self.available_sources if x != 0]
                if len(usb) >= 1: target[0] = usb[0]
                if len(usb) >= 2: target[1] = usb[1]
                elif len(self.available_sources) >= 2:
                    rem = [x for x in self.available_sources if x != target[0]]
                    if rem: target[1] = rem[0]
            elif len(self.available_sources) == 1: target = [self.available_sources[0]] * 2

        for i in range(2):
            idx = target[i]
            c_idx = self.gui.practice_widgets[i]['source_combo'].findData(idx)
            if c_idx >= 0:
                self.gui.practice_widgets[i]['source_combo'].setCurrentIndex(c_idx)
                self.gui.grouping_widgets[i]['source_combo'].setCurrentIndex(c_idx)
        
        self.config["camera_indexes"] = target
        _save_config(self.config)
        self.start_cameras()

    def setup_connections(self):
        self.gui.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        self.gui.cam_count_combo.currentIndexChanged.connect(self.on_cam_count_changed)
        
        self.trigger.triggered_1.connect(partial(self.capture_photo, 0))
        self.trigger.triggered_2.connect(partial(self.capture_photo, 1))
        
        self.request_processing.connect(self.worker.process_image)
        self.worker.practice_finished.connect(self.on_processing_finished)
        self.gui.close_button.clicked.connect(self.close)

        for i in range(2):
            p = self.gui.practice_widgets[i]
            p['zoom_slider'].valueChanged.connect(partial(self.on_zoom_changed, i))
            p['refresh_btn'].clicked.connect(self.start_cameras)
            p['calib_btn'].clicked.connect(partial(self.toggle_calib, i))
            p['cam_view'].clicked.connect(partial(self.on_cam_clicked, i))
            p['source_combo'].currentIndexChanged.connect(partial(self.on_source_changed, i))
            
            g = self.gui.grouping_widgets[i]
            g['zoom_slider'].valueChanged.connect(partial(self.on_zoom_changed, i))
            g['refresh_btn'].clicked.connect(self.start_cameras)
            g['calib_btn'].clicked.connect(partial(self.toggle_calib, i))
            g['cam_view'].clicked.connect(partial(self.on_cam_clicked, i))
            g['reset_btn'].clicked.connect(partial(self.reset_grouping, i))
            g['source_combo'].currentIndexChanged.connect(partial(self.on_source_changed, i))

    @Slot(int)
    def on_source_changed(self, row_index, combo_index):
        p_combo = self.gui.practice_widgets[row_index]['source_combo']
        g_combo = self.gui.grouping_widgets[row_index]['source_combo']
        cam_id = p_combo.itemData(combo_index)
        if cam_id is None: return
        
        p_combo.blockSignals(True); g_combo.blockSignals(True)
        p_combo.setCurrentIndex(combo_index); g_combo.setCurrentIndex(combo_index)
        p_combo.blockSignals(False); g_combo.blockSignals(False)
        
        curr = self.config.get("camera_indexes", [0, 0])
        curr[row_index] = cam_id
        self.config["camera_indexes"] = curr
        _save_config(self.config)
        self._start_single_cam(row_index, cam_id)

    @Slot(int)
    def on_cam_count_changed(self, index):
        is_2cam = (index == 1)
        self.gui.practice_rows[1].setVisible(is_2cam)
        self.gui.grouping_rows[1].setVisible(is_2cam)
        self.start_cameras()

    @Slot(int)
    def on_mode_changed(self, index):
        self.gui.stacked_widget.setCurrentIndex(index)
        for i in range(2):
            val = self.gui.grouping_widgets[i]['zoom_slider'].value() if index == 0 else self.gui.practice_widgets[i]['zoom_slider'].value()
            if index == 0: self.gui.practice_widgets[i]['zoom_slider'].setValue(val)
            else: self.gui.grouping_widgets[i]['zoom_slider'].setValue(val)

    def start_cameras(self):
        indexes = self.config.get("camera_indexes", [0, 0])
        target = self.gui.cam_count_combo.currentIndex() + 1 
        for i in range(2):
            if i < target:
                cid = indexes[i] if i < len(indexes) else 0
                self._start_single_cam(i, cid)
            else:
                if self.cams[i]: self.cams[i].release()
                self.is_connected[i] = False
                self._update_cam_msg(i, "Đã tắt")

    def _start_single_cam(self, i, usb_index):
        if self.is_connected[i] and self.cams[i] and self.cams[i].index == usb_index and self.cams[i].isOpened(): return
        if self.cams[i]: self.cams[i].release()
        try:
            self.cams[i] = Camera(usb_index)
            if self.cams[i].isOpened() and self.cams[i].read()[0]:
                self.is_connected[i] = True
            else:
                self.is_connected[i] = False
                self._update_cam_msg(i, "Lỗi kết nối")
        except: 
            self.is_connected[i] = False
            self._update_cam_msg(i, "Không tìm thấy")
        if any(self.is_connected) and not self.video_timer.isActive():
            self.video_timer.start(30)
            self.trigger.activate()

    def _update_cam_msg(self, i, msg):
        self.gui.practice_widgets[i]['cam_view'].setText(msg)
        self.gui.grouping_widgets[i]['cam_view'].setText(msg)
        self.gui.practice_widgets[i]['cam_view'].setPixmap(QPixmap())
        self.gui.grouping_widgets[i]['cam_view'].setPixmap(QPixmap())

    def update_frames(self):
        for i in range(2):
            if self.is_connected[i] and self.cams[i]:
                ret, frame = self.cams[i].read()
                if ret:
                    frame_sq = self._crop_square(frame)
                    frame_rs = cv2.resize(frame_sq, self.final_size)
                    display = self.get_display_frame(frame_rs, i)
                    self.gui.display_frame(display, i)
                else:
                    self.is_connected[i] = False
                    self._update_cam_msg(i, "Mất tín hiệu")

    @Slot(int)
    def capture_photo(self, i):
        if self.is_processing_cam[i]: return
        mode_idx = self.gui.stacked_widget.currentIndex()
        
        if self.is_connected[i]:
            ret, frame = self.cams[i].read()
            if ret:
                self.is_processing_cam[i] = True
                frame_rs = cv2.resize(self._crop_square(frame), self.final_size)
                clean_frame, aim_pt = self._apply_zoom(frame_rs, i)
                
                if mode_idx == 0: # Practice
                    metadata = {'cam_index': i, 'aim_point': aim_pt}
                    self.request_processing.emit(clean_frame, "", 'practice', metadata)
                elif mode_idx == 1: # Grouping
                    self.is_processing_cam[i] = False

    @Slot(dict)
    def on_processing_finished(self, result: dict):
        idx = result.get('cam_index', 0)
        status = result.get('status_text', "")
        frame = result.get('result_frame', None)
        template = result.get('template_result', None)
        if frame is not None:
            self.gui.update_results(status, frame, template, idx)
        self.is_processing_cam[idx] = False

    def _save_dataset(self, img): pass

    def _apply_zoom(self, base_frame, i):
        h, w = base_frame.shape[:2]
        center = self.calib_centers[i] if self.calib_centers[i] else (w//2, h//2)
        zoom = self.zoom_levels[i]
        if zoom > 1.0:
            zw, zh = int(w/zoom), int(h/zoom)
            sx, sy = (w-zw)//2, (h-zh)//2
            tx, ty = center[0]-sx, center[1]-sy
            display_pt = (int(tx*zoom), int(ty*zoom))
            crop = base_frame[sy:sy+zh, sx:sx+zw]
            return cv2.resize(crop, (w, h)), display_pt
        return base_frame.copy(), center

    def get_display_frame(self, frame, i):
        d_frame, pt = self._apply_zoom(frame, i)
        self._draw_reticle(d_frame, pt)
        return d_frame

    def on_zoom_changed(self, i, value):
        self.zoom_levels[i] = value / 10.0
        txt = f"{self.zoom_levels[i]:.1f}x"
        self.gui.practice_widgets[i]['zoom_val'].setText(txt)
        self.gui.grouping_widgets[i]['zoom_val'].setText(txt)
        p_sld = self.gui.practice_widgets[i]['zoom_slider']
        g_sld = self.gui.grouping_widgets[i]['zoom_slider']
        if self.sender() == p_sld: g_sld.setValue(value)
        else: p_sld.setValue(value)

    def toggle_calib(self, i, force_off=False):
        current_idx = self.gui.stacked_widget.currentIndex()
        if current_idx == 0: current = self.gui.practice_widgets[i]['cam_view']
        else: current = self.gui.grouping_widgets[i]['cam_view']
        
        new_state = not current._is_calibrating
        if force_off: new_state = False
        current.set_calibration_mode(new_state)
        txt = "Hủy" if new_state else "Hiệu chỉnh"
        self.gui.practice_widgets[i]['calib_btn'].setText(txt)
        self.gui.grouping_widgets[i]['calib_btn'].setText(txt)
        if new_state:
            msg = QMessageBox(self)
            msg.setWindowTitle(f"Camera {i+1}")
            msg.setText("Click vào tâm ngắm mong muốn trên màn hình.")
            msg.setIcon(QMessageBox.Information)
            msg.setStyleSheet("background-color: #f5f6fa; color: #2c3e50; font-size: 14px; font-weight: bold;")
            msg.exec()
        elif not force_off: self.calib_centers[i] = None

    def on_cam_clicked(self, i, point: QPoint):
        current_idx = self.gui.stacked_widget.currentIndex()
        if current_idx == 0: sender = self.gui.practice_widgets[i]['cam_view']
        else: sender = self.gui.grouping_widgets[i]['cam_view']
        if not sender._is_calibrating: return
        pix = sender._pixmap
        if pix.isNull(): return
        fw, fh = self.final_size
        sp = pix.scaled(sender.size(), Qt.KeepAspectRatio)
        off_x, off_y = (sender.width()-sp.width())//2, (sender.height()-sp.height())//2
        if not (off_x <= point.x() < off_x + sp.width()): return
        rx = (point.x() - off_x) / sp.width()
        ry = (point.y() - off_y) / sp.height()
        zw, zh = fw/self.zoom_levels[i], fh/self.zoom_levels[i]
        csx, csy = (fw-zw)//2, (fh-zh)//2
        fx = csx + (rx * zw)
        fy = csy + (ry * zh)
        self.calib_centers[i] = (int(fx), int(fy))
        self.toggle_calib(i, force_off=True) 

    def reset_grouping(self, i):
        self.gui.grouping_widgets[i]['shot_count'].setText("0")
        self.gui.grouping_widgets[i]['result_view'].setPixmap(QPixmap())

    def _crop_square(self, frame):
        h, w = frame.shape[:2]; m = min(h, w)
        sx, sy = (w-m)//2, (h-m)//2
        return frame[sy:sy+m, sx:sx+m]

    def _draw_reticle(self, img, pt, color=(0,255,0), size=6, thickness=1):
        cx, cy = pt
        cv2.line(img, (cx-size, cy), (cx+size, cy), color, thickness)
        cv2.line(img, (cx, cy-size), (cx, cy+size), color, thickness)

    def shutdown_components(self): 
        for c in self.cams: 
            if c: c.release()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    if check_or_request_license():
        config = _load_config()
        t = QThread()
        w = ProcessingWorker(config); w.moveToThread(t)
        bt = BluetoothTrigger()
        win = PracticeLiteWindow(config, w, bt)
        app.aboutToQuit.connect(win.shutdown_components)
        app.aboutToQuit.connect(bt.stop_global_listener)
        app.aboutToQuit.connect(t.quit)
        app.aboutToQuit.connect(t.wait)
        t.start(); bt.start_global_listener()
        win.showMaximized()
        sys.exit(app.exec())
    else: sys.exit()