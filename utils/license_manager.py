# file: utils/license_manager.py
import hashlib
import psutil  # Sử dụng psutil để quét tất cả các card mạng
import re

SECRET_SALT = "0986534710"  # Giữ nguyên chuỗi bí mật của bạn

def get_all_mac_addresses():
    """
    Quét và trả về một danh sách tất cả các địa chỉ MAC vật lý có trên máy.
    Hàm này là cốt lõi cho việc xác thực bền vững.
    """
    mac_addresses = set()  # Dùng set để tránh trùng lặp
    # Biểu thức chính quy để nhận diện một địa chỉ MAC hợp lệ
    mac_pattern = re.compile(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})')
    
    try:
        for interface, snics in psutil.net_if_addrs().items():
            for snic in snics:
                if snic.family == psutil.AF_LINK and mac_pattern.match(snic.address):
                    # Chuẩn hóa MAC về dạng chuỗi liền, viết hoa
                    clean_mac = snic.address.upper().replace(':', '').replace('-', '')
                    # Bỏ qua các địa chỉ MAC ảo hoặc loopback phổ biến
                    if not clean_mac.startswith('00000000') and not clean_mac.startswith('0242'):
                        mac_addresses.add(clean_mac)
    except Exception:
        # Trong trường hợp không thể quét, thử dùng getmac như một phương án dự phòng
        from getmac import get_mac_address
        try:
            mac = get_mac_address()
            if mac:
                mac_addresses.add(mac.replace(':', '').upper())
        except Exception:
            pass # Bỏ qua nếu cả hai đều lỗi

    return list(mac_addresses)

def generate_key(mac_address: str) -> str:
    """Tạo license key từ địa chỉ MAC và chuỗi bí mật."""
    # Luôn xóa các dấu phân cách khỏi MAC address đầu vào
    clean_mac = mac_address.upper().replace(':', '').replace('-', '')
    
    s = hashlib.sha256()
    data = f"{clean_mac}-{SECRET_SALT}"
    s.update(data.encode('utf-8'))
    return s.hexdigest()[:24].upper()

def verify_key(license_key: str) -> bool:
    """
    TỐI ƯU: Kiểm tra xem license key có hợp lệ với BẤT KỲ địa chỉ MAC nào
    của máy tính hiện tại không.
    """
    if not license_key:
        return False
        
    # Lấy danh sách tất cả các địa chỉ MAC có trên máy
    all_macs = get_all_mac_addresses()
    
    if not all_macs:
        # Nếu không tìm thấy MAC nào, không thể xác thực
        return False

    # Duyệt qua từng địa chỉ MAC tìm được
    for mac in all_macs:
        # Tạo một key thử nghiệm từ địa chỉ MAC đó
        test_key = generate_key(mac)
        
        # Nếu key thử nghiệm khớp với license key đã cho, xác thực thành công
        if test_key == license_key.upper():
            return True
            
    # Nếu không có địa chỉ MAC nào khớp, xác thực thất bại
    return False