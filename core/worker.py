# file: core/worker.py
# NỘI DUNG ĐÃ VÔ HIỆU HÓA HOÀN TOÀN AI

import logging
from datetime import datetime
from PySide6.QtCore import QObject, Signal, Slot
import numpy as np

logger = logging.getLogger(__name__)

class ProcessingWorker(QObject):
    practice_finished = Signal(dict)
    # Không cần competition_finished nữa

    def __init__(self, config: dict):
        super().__init__()
        # Không cần khởi tạo model AI, assets, hay handlers nữa
        logger.info("Worker đã khởi tạo (chế độ không AI).")

    @Slot(np.ndarray, str, str, object)
    def process_image(self, photo_frame, image_path, mode, metadata):
        """
        Trong phiên bản này, hàm chỉ đóng gói lại ảnh nhận được và gửi đi.
        Toàn bộ logic AI và tính điểm đã được loại bỏ.
        """
        
        # Đóng gói kết quả ngay lập tức
        final_package = {
            'time_str': datetime.now().strftime('%H:%M:%S'),
            'result_frame': photo_frame, # Trả về chính ảnh đã được vẽ hiệu ứng
        }
        
        # Gửi tín hiệu hoàn thành
        self.practice_finished.emit(final_package)