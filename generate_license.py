# file: generate_license.py
from utils.license_manager import generate_key
import os
import sys

# --- BẮT ĐẦU VÙNG SỬA ĐỔI: HƯỚNG DẪN LẤY UUID CHO CẢ WINDOWS VÀ MACOS ---
print("=====================================================================")
print(" CÔNG CỤ TẠO LICENSE KEY DỰA TRÊN UUID CỦA MÁY KHÁCH HÀNG")
print("---------------------------------------------------------------------")
print(" Hướng dẫn khách hàng (chọn 1 trong 2 cách tùy theo hệ điều hành):")
print("\n[A] - Nếu khách hàng dùng WINDOWS:")
print(" 1. Mở Command Prompt (CMD) trên máy tính của họ.")
print(" 2. Gõ chính xác lệnh sau rồi nhấn Enter:")
print("    wmic csproduct get uuid")
print(" 3. Sao chép và gửi lại cho bạn chuỗi ký tự UUID hiển thị.")
print("\n[B] - Nếu khách hàng dùng MACOS:")
print(" 1. Mở ứng dụng Terminal trên máy Mac của họ.")
print(" 2. Gõ chính xác lệnh sau rồi nhấn Enter:")
print("    ioreg -d2 -c IOPlatformExpertDevice | awk -F\\\" '/IOPlatformUUID/{print $(NF-1)}'")
print(" 3. Sao chép và gửi lại cho bạn chuỗi ký tự UUID hiển thị.")
print("=====================================================================")
# --- KẾT THÚC VÙNG SỬA ĐỔI ---

customer_uuid_input = input("\nNhập System UUID của khách hàng: ").strip()

if customer_uuid_input:
    license_key = generate_key(customer_uuid_input)

    print("\n--------------------------------------")
    print(f"  System UUID: {customer_uuid_input.upper()}")
    print(f"  LICENSE KEY: {license_key}")
    print("--------------------------------------")
    print("\n>> Gửi LICENSE KEY này cho khách hàng.")
else:
    print("\nLỗi: System UUID không được để trống.")

# Giữ cửa sổ console mở để người dùng có thể copy key
# Sử dụng input() thay vì os.system("pause") để tương thích đa nền tảng
try:
    input("\nNhấn Enter để thoát...")
except KeyboardInterrupt:
    sys.exit(0)