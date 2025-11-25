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
    # Signal trả về: {cam_index, status_text, result_frame, template_result}
    practice_finished = Signal(dict)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.ai_model = None
        
        APP_DATA_DIR = user_data_dir("ShootingAppLite", "LuanTung")
        self.DATASET_DIR = os.path.join(APP_DATA_DIR, "dataset_yolo")
        os.makedirs(self.DATASET_DIR, exist_ok=True)
        
        self._init_ai()

    def _init_ai(self):
        if HAS_YOLO:
            path = resource_path(self.config.get("ai_model_path", "biachido.pt"))
            if not os.path.exists(path): path = "biachido.pt"
            if os.path.exists(path):
                try:
                    self.ai_model = YOLO(path)
                    logger.info("Worker: AI Model loaded.")
                except Exception as e: logger.error(f"Worker AI Error: {e}")

    @Slot(np.ndarray, str, str, object)
    def process_image(self, clean_frame, dummy_status, mode, metadata):
        cam_index = metadata.get('cam_index', 0)
        aim_point = metadata.get('aim_point', (0, 0))
        
        status_text = "TRƯỢT BIA"
        template_result = None
        
        # Tạo bản sao để vẽ kết quả chính (Dấu cộng)
        result_frame = clean_frame.copy()
        
        try:
            # 1. Lưu Dataset
            self._save_dataset(clean_frame)
            
            # 2. AI Detect
            target_box = None
            if self.ai_model:
                results = self.ai_model.predict(clean_frame, conf=0.5, verbose=False)
                ax, ay = aim_point
                
                if len(results) > 0 and len(results[0].boxes) > 0:
                    for box in results[0].boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        # Kiểm tra tâm ngắm nằm trong box
                        if x1 <= ax <= x2 and y1 <= ay <= y2:
                            status_text = "TRÚNG BIA"
                            target_box = (x1, y1, x2, y2)
                            break
            
            # 3. Xử lý CẮT ẢNH (CROP) nếu trúng
            if target_box:
                x1, y1, x2, y2 = target_box
                
                # Cắt vùng bia từ ảnh SẠCH (chưa vẽ gì)
                # Để đảm bảo an toàn biên (không crash nếu box sát mép)
                h, w = clean_frame.shape[:2]
                x1 = max(0, x1); y1 = max(0, y1)
                x2 = min(w, x2); y2 = min(h, y2)
                
                crop_img = clean_frame[y1:y2, x1:x2].copy()
                
                # Tính tọa độ tâm ngắm TRÊN ẢNH CẮT
                # Tọa độ mới = Tọa độ gốc - Tọa độ góc trên trái của box
                crop_ax = ax - x1
                crop_ay = ay - y1
                
                # Vẽ DẤU CHẤM TRÒN XANH LÁ lên ảnh cắt
                # Radius=4, Thickness=-1 (Filled), Color=(0,255,0)
                cv2.circle(crop_img, (crop_ax, crop_ay), 1, (0, 255, 0), -1, lineType=cv2.LINE_AA)
                template_result = crop_img

        except Exception as e:
            logger.error(f"Worker Process Error: {e}")
        
        finally:
            # 4. Vẽ tâm lên Frame chính (Dấu cộng mảnh như Livestream)
            # Size 6, Thickness 1, Màu Xanh (0,255,0)
            self._draw_reticle(result_frame, aim_point, (0, 255, 0), 6, 1)
            
            final_package = {
                'cam_index': cam_index,
                'status_text': status_text,
                'result_frame': result_frame,
                'template_result': template_result
            }
            self.practice_finished.emit(final_package)

    def _save_dataset(self, img):
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = os.path.join(self.DATASET_DIR, f"data_{ts}.jpg")
            cv2.imwrite(path, img)
        except: pass

    def _draw_reticle(self, img, pt, color, size, thickness):
        cx, cy = pt
        cv2.line(img, (cx - size, cy), (cx + size, cy), color, thickness)
        cv2.line(img, (cx, cy - size), (cx, cy + size), color, thickness)