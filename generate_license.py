from utils.license_manager import generate_key

customer_mac_input = input("Nhập địa chỉ MAC của khách hàng: ").strip()

if customer_mac_input:
    # <<< THAY ĐỔI: Chuẩn hóa MAC address trước khi tạo key
    clean_mac = customer_mac_input.upper().replace(':', '').replace('-', '')
    license_key = generate_key(clean_mac)

    print("\n======================================")
    print(f"  Địa chỉ MAC: {clean_mac}")
    print(f"  LICENSE KEY: {license_key}")
    print("======================================")
    print("\n>> Gửi LICENSE KEY này cho khách hàng.")
else:
    print("Địa chỉ MAC không được để trống.")