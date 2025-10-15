# file: utils/resource_path.py
import sys
import os

def resource_path(relative_path: str) -> str:
    """ 
    Lấy đường dẫn tuyệt đối tới tài nguyên, hoạt động cho cả môi trường dev và khi đã đóng gói bằng PyInstaller.
    """
    try:
        # PyInstaller tạo một thư mục tạm và lưu đường dẫn trong _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Nếu không được đóng gói, dùng đường dẫn thông thường
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)