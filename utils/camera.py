# file: utils/camera.py

import cv2
import logging
import sys

logger = logging.getLogger(__name__)

def _get_os_backend():
    """Lấy backend API phù hợp cho hệ điều hành."""
    if sys.platform == "win32":
        return cv2.CAP_DSHOW # DirectShow (Windows) nhanh hơn
    if sys.platform == "darwin":
        return cv2.CAP_AVFOUNDATION # macOS
    return cv2.CAP_ANY

def get_available_camera_indexes(max_check=4) -> list:
    """
    Quét và trả về danh sách các index camera đang hoạt động.
    Ví dụ: [0, 1, 2]
    """
    available_indexes = []
    api_preference = _get_os_backend()
    
    # Quét nhanh các cổng từ 0 đến max_check
    for i in range(max_check):
        cap = cv2.VideoCapture(i, api_preference)
        if cap.isOpened():
            # Đọc thử 1 frame để chắc chắn camera hoạt động
            ret, _ = cap.read()
            if ret:
                available_indexes.append(i)
            cap.release()
            
    return available_indexes

def count_available_cameras(max_to_check=5) -> int:
    """Đếm số lượng camera (giữ lại để tương thích code cũ nếu cần)."""
    return len(get_available_camera_indexes(max_to_check))

class Camera:
    """Lớp bao bọc cho cv2.VideoCapture để quản lý camera."""
    def __init__(self, index: int):
        self.index = index
        api_preference = _get_os_backend()
        self.cap = cv2.VideoCapture(self.index, api_preference)

        if not self.cap.isOpened():
            logger.error(f"CAMERA: Lỗi khi mở camera index {self.index}.")
        else:
            # Cấu hình độ phân giải mong muốn (HD)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            # Tắt tự động lấy nét nếu có thể (để tránh bị focus hunting khi bắn)
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)

    def isOpened(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    def read(self):
        if not self.isOpened():
            return (False, None)
        
        is_grabbed = self.cap.grab()
        if not is_grabbed:
            return (False, None)
        
        retval, frame = self.cap.retrieve()
        return (retval, frame)
    
    def release(self):
        if self.isOpened():
            self.cap.release()