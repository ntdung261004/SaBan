# file: utils/camera.py
# PHIÊN BẢN CUỐI CÙNG

import cv2
import logging
import sys

logger = logging.getLogger(__name__)

def _get_os_backend():
    """Lấy backend API phù hợp cho hệ điều hành."""
    if sys.platform == "win32":
        return cv2.CAP_DSHOW
    if sys.platform == "darwin":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY

def count_available_cameras(max_to_check=5) -> int:
    """Quét và đếm số lượng camera đang hoạt động có thể kết nối."""
    count = 0
    api_preference = _get_os_backend()
    for i in range(max_to_check):
        cap = cv2.VideoCapture(i, api_preference)
        if cap is not None and cap.isOpened():
            is_working, _ = cap.read()
            if is_working:
                count += 1
            cap.release()
    return count

class Camera:
    """Lớp bao bọc cho cv2.VideoCapture để quản lý camera."""
    def __init__(self, index: int):
        self.index = index
        api_preference = _get_os_backend()
        self.cap = cv2.VideoCapture(self.index, api_preference)

        if not self.cap.isOpened():
            logger.error(f"CAMERA: Lỗi khi mở camera index {self.index}.")
        else:
            logger.info(f"CAMERA: Đã mở thành công camera index {self.index}.")
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    def isOpened(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    def read(self):
        """Sử dụng grab() và retrieve() để đọc frame một cách an toàn."""
        if not self.isOpened():
            return (False, None)
        
        # Lệnh grab() đáng tin cậy hơn để kiểm tra kết nối vật lý
        is_grabbed = self.cap.grab()
        if not is_grabbed:
            return (False, None)
        
        retval, frame = self.cap.retrieve()
        return (retval, frame)
    
    def release(self):
        if self.isOpened():
            self.cap.release()
            logger.info(f"CAMERA: Đã giải phóng camera index {self.index}.")