# file: utils/license_manager.py
import hashlib
import logging
import subprocess
import sys # <<< THÊM MỚI để kiểm tra hệ điều hành

logger = logging.getLogger(__name__)
SECRET_SALT = "0986534710" # Giữ nguyên chuỗi bí mật của bạn

# --- BẮT ĐẦU VÙNG SỬA ĐỔI: HỖ TRỢ ĐA NỀN TẢNG (WINDOWS & MACOS) ---
def get_system_uuid() -> str:
    """
    Lấy UUID của bo mạch chủ, hoạt động trên cả Windows và macOS.
    Đây là định danh ổn định và đáng tin cậy.
    """
    platform = sys.platform
    command = ""
    
    if platform == "win32":
        # Lệnh cho Windows
        command = "wmic csproduct get uuid"
    elif platform == "darwin":
        # Lệnh cho macOS
        command = "ioreg -d2 -c IOPlatformExpertDevice | awk -F\\\" '/IOPlatformUUID/{print $(NF-1)}'"
    else:
        logger.error(f"Hệ điều hành không được hỗ trợ: {platform}")
        return "UUID_UNSUPPORTED_OS"

    try:
        # Chạy lệnh tương ứng với hệ điều hành
        uuid_raw = subprocess.check_output(command, shell=True, text=True, stderr=subprocess.DEVNULL)
        
        # Làm sạch kết quả trả về
        clean_uuid = uuid_raw.strip().split('\n')[-1].strip()
        
        if clean_uuid and len(clean_uuid) > 5:
             logger.info(f"Lấy được System UUID ({platform}): {clean_uuid}")
             return clean_uuid
        else:
            logger.error(f"Lệnh ({command}) không trả về UUID hợp lệ.")
            return "UUID_NOT_FOUND"
            
    except Exception as e:
        logger.error(f"Lỗi nghiêm trọng khi lấy System UUID trên {platform}: {e}")
        return "UUID_ERROR"

def generate_key(system_id: str) -> str:
    """Tạo license key từ một định danh hệ thống (UUID) và chuỗi bí mật."""
    s = hashlib.sha256()
    data = f"{system_id.strip().upper()}-{SECRET_SALT}"
    s.update(data.encode('utf-8'))
    return s.hexdigest()[:24].upper()

def verify_key(license_key: str) -> bool:
    """Kiểm tra xem license key có hợp lệ với máy tính hiện tại không."""
    current_uuid = get_system_uuid()
    
    if "UUID_" in current_uuid:
        logger.error(f"Không thể xác thực key vì không lấy được UUID. Mã lỗi: {current_uuid}")
        return False
        
    expected_key = generate_key(current_uuid)
    is_valid = (license_key.strip().upper() == expected_key)
    
    if not is_valid:
        logger.warning(f"Xác thực thất bại. Key cung cấp: {license_key}, Key mong đợi cho UUID ({current_uuid}): {expected_key}")
        
    return is_valid
# --- KẾT THÚC VÙNG SỬA ĐỔI ---