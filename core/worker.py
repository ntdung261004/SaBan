# file: core/worker.py

import logging
import os
import cv2
import numpy as np
from datetime import datetime
from PySide6.QtCore import QObject, Signal, Slot
from platformdirs import user_data_dir
from utils.resource_path import resource_path

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False

logger = logging.getLogger(__name__)

class ProcessingWorker(QObject):
    # Signal trả về: {cam_index, status_text, result_frame, template_result, hit_coordinates}
    practice_finished = Signal(dict)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.ai_model = None
        self.template_image = None
        
        APP_DATA_DIR = user_data_dir("ShootingAppLite", "LuanTung")
        self.DATASET_DIR = os.path.join(APP_DATA_DIR, "dataset_yolo")
        os.makedirs(self.DATASET_DIR, exist_ok=True)
        
        self._init_resources()

    def _init_resources(self):
        if HAS_YOLO:
            path = resource_path(self.config.get("ai_model_path", "biachido.pt"))
            if not os.path.exists(path): path = "biachido.pt"
            if os.path.exists(path):
                try: self.ai_model = YOLO(path); logger.info("Worker: AI Loaded.")
                except Exception as e: logger.error(f"AI Error: {e}")
        
        tpl_path = resource_path(self.config.get("template_image_path", "assets/images/original/biachido.png"))
        if os.path.exists(tpl_path):
            self.template_image = cv2.imread(tpl_path)

    @Slot(np.ndarray, str, str, object)
    def process_image(self, clean_frame, dummy_status, mode, metadata):
        cam_index = metadata.get('cam_index', 0)
        aim_point = metadata.get('aim_point', (0, 0))
        
        status_text = "TRƯỢT BIA"
        template_result = None
        hit_coordinates = None # Quan trọng: Dữ liệu để đếm điểm
        result_frame = clean_frame.copy()
        
        try:
            self._save_dataset(clean_frame)
            
            target_box = None
            if self.ai_model:
                results = self.ai_model.predict(clean_frame, conf=0.5, verbose=False)
                ax, ay = aim_point
                
                if len(results) > 0 and len(results[0].boxes) > 0:
                    for box in results[0].boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        if x1 <= ax <= x2 and y1 <= ay <= y2:
                            status_text = "TRÚNG BIA"
                            target_box = (x1, y1, x2, y2)
                            break
            
            if target_box:
                x1, y1, x2, y2 = target_box
                
                # 1. Xử lý ảnh Crop để hiện Popup
                h, w = clean_frame.shape[:2]
                c_x1, c_y1 = max(0, x1), max(0, y1)
                c_x2, c_y2 = min(w, x2), min(h, y2)
                
                if c_x2 > c_x1 and c_y2 > c_y1:
                    template_result = clean_frame[c_y1:c_y2, c_x1:c_x2].copy()
                    crop_ax, crop_ay = ax - c_x1, ay - c_y1
                    cv2.circle(template_result, (crop_ax, crop_ay), 2, (0, 255, 0), -1, cv2.LINE_AA)

                # 2. Tính tọa độ chuẩn hóa (Neo Tâm) để trả về cho Grouping logic
                if self.template_image is not None:
                    box_w, box_h = x2 - x1, y2 - y1
                    box_cx, box_cy = x1 + box_w/2, y1 + box_h/2
                    
                    dx, dy = ax - box_cx, ay - box_cy
                    th, tw = self.template_image.shape[:2]
                    scale_x, scale_y = tw / box_w, th / box_h
                    
                    hit_x = int((tw/2) + (dx * scale_x))
                    hit_y = int((th/2) + (dy * scale_y))
                    
                    hit_x = max(0, min(hit_x, tw - 1))
                    hit_y = max(0, min(hit_y, th - 1))
                    
                    hit_coordinates = (hit_x, hit_y)

        except Exception as e:
            logger.error(f"Worker Error: {e}")
        
        finally:
            self._draw_reticle(result_frame, aim_point, (0, 255, 0), 6, 1)
            
            final_package = {
                'cam_index': cam_index,
                'status_text': status_text,
                'result_frame': result_frame,
                'template_result': template_result,
                'hit_coordinates': hit_coordinates # Trả về dữ liệu này
            }
            self.practice_finished.emit(final_package)

    def _save_dataset(self, img):
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            cv2.imwrite(os.path.join(self.DATASET_DIR, f"data_{ts}.jpg"), img)
        except: pass

    def _draw_reticle(self, img, pt, color, size, thickness):
        cx, cy = pt
        cv2.line(img, (cx - size, cy), (cx + size, cy), color, thickness)
        cv2.line(img, (cx, cy - size), (cx, cy + size), color, thickness)