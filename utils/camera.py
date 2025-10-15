# file: utils/camera.py
import cv2
import logging
import sys
from typing import List

logger = logging.getLogger(__name__)

def _get_os_backend():
    """Lấy backend API phù hợp cho hệ điều hành."""
    if sys.platform == "win32":
        return cv2.CAP_DSHOW
    if sys.platform == "darwin":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY

def count_available_cameras(max_to_check=5) -> int:
    """
    Quét và đếm số lượng camera đang hoạt động có thể kết nối.
    Hàm này rất quan trọng để xác định có USB camera hay không.
    """
    logger.info("CAMERA: Bắt đầu đếm số lượng camera có sẵn...")
    count = 0
    api_preference = _get_os_backend()
    for i in range(max_to_check):
        cap = cv2.VideoCapture(i, api_preference)
        if cap is not None and cap.isOpened():
            # Đảm bảo camera thực sự hoạt động bằng cách đọc thử 1 frame
            is_working, _ = cap.read()
            if is_working:
                count += 1
            cap.release()
    logger.info(f"CAMERA: Tìm thấy tổng cộng {count} camera hoạt động.")
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
        if not self.isOpened():
            return (False, None)
        ret, frame = self.cap.read()
        return (ret, frame)
    
    def release(self):
        if self.isOpened():
            self.cap.release()
            logger.info(f"CAMERA: Đã giải phóng camera index {self.index}.")