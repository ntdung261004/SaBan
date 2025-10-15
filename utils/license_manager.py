import hashlib
from getmac import get_mac_address as gma # <<< THAY THẾ uuid BẰNG getmac

SECRET_SALT = "0986534710" # Giữ nguyên chuỗi bí mật của bạn

def get_mac_address():
    """
    Lấy địa chỉ MAC chính của máy tính một cách đáng tin cậy hơn.
    Hàm này sẽ ưu tiên lấy MAC của card mạng đang hoạt động.
    """
    try:
        # gma() sẽ trả về địa chỉ MAC dạng 'XX:XX:XX:XX:XX:XX'
        mac = gma()
        if mac:
            # Chuẩn hóa về dạng chuỗi liền không phân cách, viết hoa
            return mac.replace(':', '').upper()
        # Nếu không tìm thấy, trả về một giá trị mặc định để tránh crash
        return "MAC_NOT_FOUND" 
    except Exception:
        return "MAC_ERROR"

def generate_key(mac_address: str) -> str:
    """Tạo license key từ địa chỉ MAC và chuỗi bí mật."""
    # Luôn xóa các dấu phân cách khỏi MAC address đầu vào
    clean_mac = mac_address.upper().replace(':', '').replace('-', '')
    
    s = hashlib.sha256()
    data = f"{clean_mac}-{SECRET_SALT}"
    s.update(data.encode('utf-8'))
    return s.hexdigest()[:24].upper()

def verify_key(license_key: str) -> bool:
    """Kiểm tra xem license key có hợp lệ với máy tính hiện tại không."""
    current_mac = get_mac_address()
    if "MAC_" in current_mac: # Xử lý trường hợp không lấy được MAC
        return False
        
    expected_key = generate_key(current_mac)
    return license_key.upper() == expected_key