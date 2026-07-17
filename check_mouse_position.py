import pyautogui
import time
import os
import sys

# Đảm bảo in có hỗ trợ tiếng Việt UTF-8
if sys.platform.startswith('win'):
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

print("=" * 60)
print("              CÔNG CỤ KIỂM TRA TỌA ĐỘ CHUỘT REAL-TIME")
print("=" * 60)
print("Hướng dẫn:")
print("1. Di chuyển chuột đến vị trí mong muốn trên màn hình.")
print("2. Đọc tọa độ X, Y hiển thị bên dưới.")
print("3. Nhấn Ctrl + C để dừng công cụ.")
print("-" * 60)

try:
    while True:
        x, y = pyautogui.position()
        # Lấy màu của pixel tại tọa độ chuột để người dùng tiện kiểm tra màu nút gửi
        try:
            r, g, b = pyautogui.pixel(x, y)
            color_str = f"| Màu RGB: ({r}, {g}, {b})"
        except Exception:
            color_str = ""
            
        print(f"Tọa độ hiện tại: X = {x:4d}, Y = {y:4d} {color_str}        ", end="\r", flush=True)
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\n\nĐã dừng công cụ kiểm tra tọa độ.")
