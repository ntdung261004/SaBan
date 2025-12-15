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
logging.info("--- Application Lite Started (Popup Title Fix) ---")

def _load_config() -> dict:
    config_path = os.path.join(APP_DATA_DIR, "config.json")
    defaults = {"camera_indexes": [], "ai_model_path": "biachido.pt", "template_image_path": "assets/images/original/biachido.png"}
    try:
        if not os.path.exists(config_path):
            with open(config_path, "w", encoding='utf-8') as f: json.dump(defaults, f, indent=4)
            return defaults
        with open(config_path, "r", encoding='utf-8') as f: return json.load(f)
    except: return defaults

def _save_config(config):
    try:
        with open(os.path.join(APP_DATA_DIR, "config.json"), "w", encoding='utf-8') as f: json.dump(config, f, indent=4)
    except: pass

def check_or_request_license() -> bool:
    path = os.path.join(APP_DATA_DIR, 'license.key')
    if os.path.exists(path):
        with open(path, 'r') as f:
            if verify_key(f.read().strip()): return True
            else: os.remove(path)
    while True:
        key, ok = QInputDialog.getText(None, "Kích hoạt", "Nhập License Key:")
        if not ok: return False
        if verify_key(key):
            with open(path, 'w') as f: f.write(key)
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
        self.gui = MainGui(config)
        self.setCentralWidget(self.gui)

        self.cams = [None, None]; self.is_connected = [False, False]
        self.final_size = (640, 640)
        self.zoom_levels = [1.0, 1.0]; self.calib_centers = [None, None]
        self.is_processing_cam = [False, False]
        self.available_sources = [] 
        
        self.grouping_counts = [0, 0] 
        self.grouping_sessions = [[], []]
        self.template_image = None

        self.video_timer = QTimer(self); self.video_timer.timeout.connect(self.update_frames)
        
        self.ai_model = None; self._init_ai()
        self.setup_connections()
        self.scan_and_init_cameras()

    def _init_ai(self):
        # Load template cho App
        tpl_path = resource_path(self.config.get("template_image_path", "assets/images/original/biachido.png"))
        if os.path.exists(tpl_path):
            self.template_image = cv2.imread(tpl_path)
        else:
            self.template_image = np.zeros((600, 600, 3), dtype=np.uint8)

    def scan_and_init_cameras(self):
        self.available_sources = get_available_camera_indexes()
        for i in range(2):
            cb_p = self.gui.practice_widgets[i]['source_combo']; cb_p.clear()
            cb_g = self.gui.grouping_widgets[i]['source_combo']; cb_g.clear()
            for src_idx in self.available_sources:
                txt = f"Camera {src_idx}"; cb_p.addItem(txt, src_idx); cb_g.addItem(txt, src_idx)
        
        saved = self.config.get("camera_indexes", [])
        target = [0, 0]
        if len(saved) >= 2 and saved[0] in self.available_sources: target = saved
        else:
            if len(self.available_sources) >= 2:
                usb = [x for x in self.available_sources if x != 0]
                if len(usb) >= 1: target[0] = usb[0]
                if len(usb) >= 2: target[1] = usb[1]
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
            p = self.gui.practice_widgets[i]; g = self.gui.grouping_widgets[i]
            for w in [p, g]:
                w['zoom_slider'].valueChanged.connect(partial(self.on_zoom_changed, i))
                w['refresh_btn'].clicked.connect(self.start_cameras)
                w['calib_btn'].clicked.connect(partial(self.toggle_calib, i))
                w['cam_view'].clicked.connect(partial(self.on_cam_clicked, i))
                w['source_combo'].currentIndexChanged.connect(partial(self.on_source_changed, i))
            g['reset_btn'].clicked.connect(partial(self.reset_grouping, i))

    @Slot(int)
    def on_source_changed(self, row, idx):
        cam_id = self.gui.practice_widgets[row]['source_combo'].itemData(idx)
        if cam_id is None: return
        self.gui.practice_widgets[row]['source_combo'].setCurrentIndex(idx)
        self.gui.grouping_widgets[row]['source_combo'].setCurrentIndex(idx)
        curr = self.config.get("camera_indexes", [0, 0])
        curr[row] = cam_id; self.config["camera_indexes"] = curr; _save_config(self.config)
        self._start_single_cam(row, cam_id)

    @Slot(int)
    def on_cam_count_changed(self, idx):
        vis = (idx == 1)
        self.gui.practice_rows[1].setVisible(vis); self.gui.grouping_rows[1].setVisible(vis)
        self.start_cameras()

    @Slot(int)
    def on_mode_changed(self, idx):
        self.gui.stacked_widget.setCurrentIndex(idx)
        for i in range(2):
            v = self.gui.grouping_widgets[i]['zoom_slider'].value() if idx==0 else self.gui.practice_widgets[i]['zoom_slider'].value()
            if idx==0: self.gui.practice_widgets[i]['zoom_slider'].setValue(v)
            else: self.gui.grouping_widgets[i]['zoom_slider'].setValue(v)

    def start_cameras(self):
        indexes = self.config.get("camera_indexes", [0, 0])
        target = self.gui.cam_count_combo.currentIndex() + 1 
        for i in range(2):
            if i < target: 
                cid = indexes[i] if i < len(indexes) else 0
                self._start_single_cam(i, cid)
            else: 
                if self.cams[i]: self.cams[i].release()
                self.is_connected[i] = False; self._update_cam_msg(i, "Đã tắt")

    def _start_single_cam(self, i, idx):
        if self.is_connected[i] and self.cams[i] and self.cams[i].index == idx and self.cams[i].isOpened(): return
        if self.cams[i]: self.cams[i].release()
        try:
            self.cams[i] = Camera(idx)
            if self.cams[i].isOpened() and self.cams[i].read()[0]: self.is_connected[i] = True
            else: self.is_connected[i] = False; self._update_cam_msg(i, "Lỗi")
        except: self.is_connected[i] = False; self._update_cam_msg(i, "Lỗi")
        if any(self.is_connected) and not self.video_timer.isActive(): self.video_timer.start(30); self.trigger.activate()

    def _update_cam_msg(self, i, msg):
        self.gui.practice_widgets[i]['cam_view'].setText(msg); self.gui.grouping_widgets[i]['cam_view'].setText(msg)

    def update_frames(self):
        for i in range(2):
            if self.is_connected[i]:
                ret, frame = self.cams[i].read()
                if ret:
                    f = cv2.resize(self._crop_square(frame), self.final_size)
                    self.gui.display_frame(self.get_display_frame(f, i), i)
                else: self.is_connected[i] = False

    @Slot(int)
    def capture_photo(self, i):
        if self.is_processing_cam[i]: return
        mode_idx = self.gui.stacked_widget.currentIndex()
        
        if mode_idx == 1 and len(self.grouping_sessions[i]) >= 3:
            QMessageBox.warning(self, f"Camera {i+1}", "Đã bắn đủ 3 phát. Vui lòng nhấn Reset.")
            return

        if self.is_connected[i]:
            ret, frame = self.cams[i].read()
            if ret:
                self.is_processing_cam[i] = True
                f_rs = cv2.resize(self._crop_square(frame), self.final_size)
                cl, pt = self._apply_zoom(f_rs, i)
                
                metadata = {'cam_index': i, 'aim_point': pt}
                self.request_processing.emit(cl, "", 'practice', metadata)

    @Slot(dict)
    def on_processing_finished(self, res: dict):
        idx = res.get('cam_index', 0)
        status = res.get('status_text', "")
        frame = res.get('result_frame')
        template = res.get('template_result')
        hit_coords = res.get('hit_coordinates')
        
        mode_idx = self.gui.stacked_widget.currentIndex()
        
        if frame is not None:
            if mode_idx == 0: # Practice
                self.gui.update_ui_result(status, frame, template, idx, False)
                
            elif mode_idx == 1: # Grouping
                # Luôn đếm số phát bắn (Trúng/Trượt)
                self.grouping_counts[idx] += 1
                
                # Chỉ lưu tọa độ nếu trúng
                if status == "TRÚNG BIA" and hit_coords is not None:
                    self.grouping_sessions[idx].append(hit_coords)
                
                cnt = self.grouping_counts[idx]
                shot_txt = f"Số phát: {cnt}/3"
                self.gui.update_ui_result(status, frame, template, idx, True, shot_txt)
                
                if cnt >= 3:
                    self.calculate_grouping_result(idx)
            
        self.is_processing_cam[idx] = False

    def calculate_grouping_result(self, idx):
        points = self.grouping_sessions[idx]
        if self.template_image is None: return
        
        final_img = self.template_image.copy()
        pts_array = []
        
        for pt in points:
            cv2.circle(final_img, pt, 1, (0, 255, 0), -1, cv2.LINE_AA)
            pts_array.append(list(pt))
            
        score_text = "KHÔNG ĐẠT"
        diameter = 0.0
        
        if len(points) >= 3:
            pts_np = np.array(pts_array, dtype=np.int32)
            (x, y), radius = cv2.minEnclosingCircle(pts_np)
            center = (int(x), int(y))
            radius = int(radius)
            diameter = radius * 2
            
            overlay = final_img.copy()
            cv2.circle(overlay, center, radius, (0, 0, 255), -1)
            cv2.addWeighted(overlay, 0.1, final_img, 0.7, 0, final_img)
            cv2.circle(final_img, center, radius, (0, 0, 255), 1, cv2.LINE_AA)
            
            if diameter < 5: score_text = "GIỎI"
            elif diameter < 10: score_text = "KHÁ"
            elif diameter < 15: score_text = "ĐẠT"
            else: score_text = "KHÔNG ĐẠT"
        else:
            score_text = f"KHÔNG ĐẠT (Trúng {len(points)}/3)"

        # GỌI HÀM POPUP VỚI THAM SỐ IDX
        self.gui.show_final_grouping_popup(final_img, diameter, score_text, idx)
        self.reset_grouping(idx)

    def reset_grouping(self, i):
        self.grouping_counts[i] = 0
        self.grouping_sessions[i] = []
        self.gui.update_ui_result("Sẵn sàng", None, None, i, True, "Số phát: 0/3")

    def _save_dataset(self, img): pass

    def _apply_zoom(self, f, i):
        h, w = f.shape[:2]; z = self.zoom_levels[i]
        c = self.calib_centers[i] if self.calib_centers[i] else (w//2, h//2)
        if z > 1.0:
            zw, zh = int(w/z), int(h/z); sx, sy = (w-zw)//2, (h-zh)//2
            tx, ty = c[0]-sx, c[1]-sy
            return cv2.resize(f[sy:sy+zh, sx:sx+zw], (w, h)), (int(tx*z), int(ty*z))
        return f.copy(), c
    
    def get_display_frame(self, f, i): d, p = self._apply_zoom(f, i); self._draw_reticle(d, p, (0,255,0), 6, 1); return d
    def _draw_reticle(self, i, p, c, s, t): cx, cy = p; cv2.line(i, (cx-s,cy), (cx+s,cy), c, t); cv2.line(i, (cx,cy-s), (cx,cy+s), c, t)
    
    def on_zoom_changed(self, i, v): 
        self.zoom_levels[i] = v/10.0
        self.gui.practice_widgets[i]['zoom_val'].setText(f"{v/10:.1f}x")
        self.gui.grouping_widgets[i]['zoom_val'].setText(f"{v/10:.1f}x")
        if self.sender() == self.gui.practice_widgets[i]['zoom_slider']: self.gui.grouping_widgets[i]['zoom_slider'].setValue(v)
        else: self.gui.practice_widgets[i]['zoom_slider'].setValue(v)

    def toggle_calib(self, i, force=False):
        w = self.gui.practice_widgets[i]['cam_view'] if self.gui.stacked_widget.currentIndex()==0 else self.gui.grouping_widgets[i]['cam_view']
        s = not w._is_calibrating
        if force: s = False
        w.set_calibration_mode(s)
        txt = "Hủy" if s else "Hiệu chỉnh"
        self.gui.practice_widgets[i]['calib_btn'].setText(txt); self.gui.grouping_widgets[i]['calib_btn'].setText(txt)
        if s: 
            msg = QMessageBox(self); msg.setText(f"Cam {i+1}: Click tâm ngắm"); msg.setStyleSheet("background-color: #f5f6fa; color: #2c3e50;"); msg.exec()
        elif not force: self.calib_centers[i] = None

    def on_cam_clicked(self, i, p):
        w = self.gui.practice_widgets[i]['cam_view'] if self.gui.stacked_widget.currentIndex()==0 else self.gui.grouping_widgets[i]['cam_view']
        if not w._is_calibrating: return
        pix = w._pixmap; fw, fh = self.final_size
        sp = pix.scaled(w.size(), Qt.KeepAspectRatio)
        ox, oy = (w.width()-sp.width())//2, (w.height()-sp.height())//2
        if not (ox <= p.x() < ox+sp.width()): return
        rx = (p.x()-ox)/sp.width(); ry = (p.y()-oy)/sp.height()
        z = self.zoom_levels[i]; zw, zh = fw/z, fh/z
        csx, csy = (fw-zw)//2, (fh-zh)//2
        self.calib_centers[i] = (int(csx + rx*zw), int(csy + ry*zh))
        self.toggle_calib(i, True)

    def _crop_square(self, f): h, w = f.shape[:2]; m = min(h, w); s = (w-m)//2; return f[:, s:s+m]
    def shutdown_components(self): 
        for c in self.cams: 
            if c: c.release()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    if check_or_request_license():
        config = _load_config()
        t = QThread(); w = ProcessingWorker(config); w.moveToThread(t)
        bt = BluetoothTrigger(); win = PracticeLiteWindow(config, w, bt)
        app.aboutToQuit.connect(win.shutdown_components)
        app.aboutToQuit.connect(bt.stop_global_listener)
        app.aboutToQuit.connect(t.quit); app.aboutToQuit.connect(t.wait)
        t.start(); bt.start_global_listener(); win.showMaximized(); sys.exit(app.exec())
    else: sys.exit()