import io
import json
import time
import os
import smtplib
import threading
import requests
from urllib.parse import urlparse, parse_qs
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import win32clipboard
from PIL import ImageGrab
import pyautogui
import pyperclip
import ctypes

# ==========================================
# CẤU HÌNH THEO DÕI QUA DISCORD
# ==========================================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1517741146816778305/YK4Vxd1u5Ld0rlj-nD-1XsYd3KHtf5K2xULso8e3iof5auLIB6gTZT1RKgGds_plBgtm"

def send_discord(content):
    """Gửi 1 tin nhắn riêng lẻ lên Discord Webhook.
    Sử dụng Discord markdown để định dạng đẹp.
    Giới hạn 2000 ký tự."""
    if not DISCORD_WEBHOOK_URL:
        return
    # Cắt gọn nếu quá dài
    if len(content) > 1950:
        content = content[:1900] + "\n...[BI CAT BOT]..."
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=5)
    except:
        pass  # Im lặng nếu lỗi mạng

# ==========================================
# HỆ THỐNG LOG TẬP TRUNG
# ==========================================
_log_buffer = []
_log_lock = threading.Lock()
_log_counter = 0

def log(msg, level="INFO"):
    """Hàm log tập trung. Xuất ra 2 nơi:
    1. Terminal (print) - plain text, không icon
    2. Frontend (qua endpoint /logs để index.html poll)
    """
    global _log_counter
    timestamp = time.strftime('%H:%M:%S')

    formatted = f"[{timestamp}] [{level}] {msg}"

    # 1. Terminal
    print(formatted)

    # 2. Buffer cho Frontend
    with _log_lock:
        _log_counter += 1
        _log_buffer.append({
            "id": _log_counter,
            "time": timestamp,
            "level": level,
            "msg": msg,
        })
        # Giữ tối đa 500 dòng log gần nhất cho frontend
        if len(_log_buffer) > 500:
            _log_buffer.pop(0)


# ==========================================
# CẤU HÌNH GHI LỊCH SỬ (HISTORY)
# ==========================================
HISTORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'history')
os.makedirs(HISTORY_DIR, exist_ok=True)

# Biến toàn cục lưu đường dẫn file history hiện tại
current_history_file = None
current_batch_start_time = 0
current_failed_items = []

def format_duration(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    parts = []
    if hours > 0:
        parts.append(f"{hours} giờ")
    if minutes > 0 or hours > 0:
        parts.append(f"{minutes} phút")
    parts.append(f"{secs} giây")
    return " ".join(parts)

def create_history_file(total_ids):
    """Tạo file history mới và ghi header."""
    global current_history_file, current_batch_start_time, current_failed_items
    current_batch_start_time = time.time()
    current_failed_items = []
    now = time.strftime('%d-%m-%Y_%Hh%Mm%Ss')
    filename = f"{now}.txt"
    filepath = os.path.join(HISTORY_DIR, filename)
    current_history_file = filepath
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("=" * 30 + "\n")
        f.write(f"PHIẾU TỰ ĐỘNG - {time.strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write(f"Phiếu gồm {total_ids} ID\n")
        f.write("=" * 30 + "\n\n")
    
    log(f"Đã tạo file history: {filepath}", "INFO")
    return filepath

def append_history_entry(stt, question_id, status, content):
    """Ghi kết quả 1 ID vào file history."""
    global current_history_file, current_failed_items
    if not current_history_file:
        return
        
    if "thành công" not in status.lower():
        current_failed_items.append({"stt": stt, "id": question_id, "status": status})
    
    with open(current_history_file, 'a', encoding='utf-8') as f:
        f.write(f"- STT: {stt}\n")
        f.write(f"- ID: {question_id}\n")
        f.write(f"- Trạng thái: {status}\n")
        f.write(f"- Nội dung: {content}\n")
        f.write("\n")
        f.write("-" * 50 + "\n")
        f.write("\n")
    
    log(f"Đã ghi history: STT {stt} - {question_id} - {status}", "INFO")

def finalize_history(success_count, total_count):
    """Ghi footer vào cuối file history."""
    global current_history_file, current_batch_start_time, current_failed_items
    if not current_history_file:
        return
        
    end_time = time.time()
    total_time_seconds = end_time - current_batch_start_time if current_batch_start_time > 0 else 0
    duration_str = format_duration(total_time_seconds)
    
    with open(current_history_file, 'a', encoding='utf-8') as f:
        f.write("\n")
        f.write("=" * 30 + "\n")
        f.write(f"KẾT QUẢ: {success_count}/{total_count}\n")
        f.write(f"Tổng thời gian: {duration_str}\n")
        f.write(f"Hoàn thành lúc: {time.strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write("=" * 30 + "\n")
        f.write("DANH SÁCH CÁC CÂU LỖI/THẤT BẠI (ĐỂ BIÊN TẬP LẠI):\n")
        if not current_failed_items:
            f.write("Không có câu nào bị lỗi.\n")
        else:
            for item in current_failed_items:
                f.write(f"{item['id']}\n")
        f.write("=" * 30 + "\n")
    
    log(f"Đã hoàn tất file history: {success_count}/{total_count}", "OK")

def send_gmail_notification(subject, body):
    """Gửi email thông báo tự động về GMAIL_USER đã cấu hình."""
    # Để sử dụng tính năng này, bạn cần:
    # 1. Bật 2FA trên tài khoản Google
    # 2. Tạo App Password tại: https://myaccount.google.com/apppasswords
    # 3. Điền thông tin bên dưới
    GMAIL_USER = "kazismini@gmail.com"  # Email Gmail của bạn (cũng là người nhận)
    GMAIL_APP_PASSWORD = "cevoacfzqofsftst"  # App Password
    
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        log(f"Chưa cấu hình Gmail! Bỏ qua gửi thông báo.", "WARN")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = GMAIL_USER  # Tự gửi cho chính mình
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        log(f"Đã gửi email thông báo tới {GMAIL_USER}", "OK")
        return True
    except Exception as e:
        log(f"Lỗi gửi email: {str(e)}", "ERROR")
        return False

# ==========================================
# CƠ CHẾ DỪNG KHẨN CẤP
# ==========================================
STOP_FLAG = False
original_sleep = time.sleep

def safe_sleep(seconds):
    global STOP_FLAG
    # Bắt buộc tối thiểu 0.3s theo yêu cầu
    seconds = max(0.3, seconds)
    loops = int(seconds * 10)
    remainder = seconds - (loops / 10.0)
    for _ in range(loops):
        if STOP_FLAG:
            raise Exception("Đã bị người dùng huỷ thủ công!")
        original_sleep(0.1)
    if remainder > 0:
        if STOP_FLAG:
            raise Exception("Đã bị người dùng huỷ thủ công!")
        original_sleep(remainder)

# ==========================================
# WRAPPER PYAUTOGUI ĐỂ TỰ ĐỘNG GHI LOG MỌI THAO TÁC
# ==========================================
original_locateCenterOnScreen = pyautogui.locateCenterOnScreen
original_locateOnScreen = pyautogui.locateOnScreen
original_click = pyautogui.click
original_doubleClick = pyautogui.doubleClick
original_press = pyautogui.press
original_hotkey = pyautogui.hotkey
original_moveTo = pyautogui.moveTo

def logged_locateCenterOnScreen(*args, **kwargs):
    img = args[0] if len(args) > 0 else kwargs.get('image', 'unknown')
    conf = kwargs.get('confidence', 'default')
    log(f"Đang quét tìm TÂM ảnh: {img} (confidence={conf})...", "SEARCH")
    res = original_locateCenterOnScreen(*args, **kwargs)
    if res:
        log(f"=> TÌM THẤY {img} tại tọa độ {res}", "SEARCH")
    else:
        log(f"=> KHÔNG THẤY {img}", "WARN")
    return res

def logged_locateOnScreen(*args, **kwargs):
    img = args[0] if len(args) > 0 else kwargs.get('image', 'unknown')
    conf = kwargs.get('confidence', 'default')
    log(f"Đang quét tìm VÙNG ảnh: {img} (confidence={conf})...", "SEARCH")
    res = original_locateOnScreen(*args, **kwargs)
    if res:
        log(f"=> TÌM THẤY {img} tại box {res}", "SEARCH")
    else:
        log(f"=> KHÔNG THẤY {img}", "WARN")
    return res

def logged_click(*args, **kwargs):
    log(f"CLICK CHUỘT vào: args={args}, kwargs={kwargs}", "ACTION")
    return original_click(*args, **kwargs)

def logged_doubleClick(*args, **kwargs):
    log(f"DOUBLE CLICK vào: args={args}, kwargs={kwargs}", "ACTION")
    return original_doubleClick(*args, **kwargs)

def logged_press(*args, **kwargs):
    log(f"⌨️ NHẤN PHÍM: {args}", "ACTION")
    return original_press(*args, **kwargs)

def logged_hotkey(*args, **kwargs):
    log(f"⌨️ NHẤN TỔ HỢP PHÍM: {args}", "ACTION")
    return original_hotkey(*args, **kwargs)

def logged_moveTo(*args, **kwargs):
    log(f"DI CHUYỂN CHUỘT tới: args={args}, kwargs={kwargs}", "ACTION")
    return original_moveTo(*args, **kwargs)

pyautogui.locateCenterOnScreen = logged_locateCenterOnScreen
pyautogui.locateOnScreen = logged_locateOnScreen
pyautogui.click = logged_click
pyautogui.doubleClick = logged_doubleClick
pyautogui.press = logged_press
pyautogui.hotkey = logged_hotkey
pyautogui.moveTo = logged_moveTo

time.sleep = safe_sleep

# ==========================================
# CẤU HÌNH TỌA ĐỘ CHUỘT
# Bạn hãy dùng 1 tool chụp ảnh màn hình (như Lightshot, Snipping Tool) 
# để xem tọa độ (X, Y) của các ô trên màn hình thật của bạn nhé.
# ==========================================
# 1. Vùng tìm kiếm và toạ độ dự phòng của ô "Nhập nội dung muốn tìm kiếm"
SEARCH_BOX_REGION = (328, 334, 247, 59) # Từ (328,334) đến (575,393)
SEARCH_BOX_FALLBACK = (410, 375)

# 2. Tọa độ nút "Tìm kiếm" (Hiện tại đang dùng phím Enter thay thế)
SEARCH_BTN_X = 886
SEARCH_BTN_Y = 476

# 3. Tọa độ vùng muốn chụp lại (Khung câu hỏi)
# Trái, Trên, Phải, Dưới
CAPTURE_BBOX = (7, 117, 1252, 1013)

# 4. Tọa độ ô nhập chat của Gemini (Góc phải trên)
GEMINI_CHATBOX_X = 1536
GEMINI_CHATBOX_Y = 470

# 5. Tọa độ nút Send của Gemini (Dùng để check màu xanh)
GEMINI_SEND_BTN_X = 1868
GEMINI_SEND_BTN_Y = 458

# 6. Vùng tìm kiếm nhanh cho nút Bút (Left, Top, Width, Height)
PENCIL1_REGION = (1009, 181, 92, 802) # Từ (1009,181) đến (1101, 983)
PENCIL2_REGION = (792, 232, 143, 48)  # Từ (792,232) đến (935, 280)
PENCIL2_FALLBACK = (893, 252)

# 7. Vùng tìm kiếm nút Copy của Gemini
GEMINI_COPY_REGION = (1294, 107, 585, 320)
GEMINI_COPY_FALLBACK = (1482, 335)

# 8. Tọa độ và Vùng tìm kiếm của NotebookLM
NBLM_SEND_BTN_X = 889
NBLM_SEND_BTN_Y = 922
NBLM_COPY_REGION = (18, 605, 1165, 82) # Từ (18, 605) đến (1183, 687)

# ==========================================

CURRENT_TAB = 'LMS'

def fallback_cancel_routine():
    global CURRENT_TAB
    log(f"CHAY QUY TRINH HUY KHAN CAP (FALLBACK CANCEL) TU TAB: {CURRENT_TAB}", "ACTION")
    
    if CURRENT_TAB == 'NBLM':
        log(f"F5 trang NBLM va quay ve LMS...", "ACTION")
        pyautogui.press('f5')
        time.sleep(2)
        pyautogui.hotkey('ctrl', 'shift', 'tab')
        time.sleep(1)
        CURRENT_TAB = 'LMS'
    
    log(f"Thuc hien huy bang phim ESC...", "ACTION")
    # Lấy focus tại điểm (1268, 587)
    pyautogui.click(1268, 587)
    time.sleep(0.25)
    # Bấm nút esc lần 1
    pyautogui.press('esc')
    time.sleep(0.5)
    
    # Tiếp tục lấy focus tại điểm (1268, 587)
    pyautogui.click(1268, 587)
    time.sleep(0.25)
    # Bấm nút esc lần 2
    pyautogui.press('esc')
    time.sleep(0.5)
    
    # Bấm esc lần 3
    pyautogui.press('esc')
    time.sleep(0.5)
    
    log(f"Da hoan tat quy trinh huy bang ESC, san sang cho ID tiep theo!", "OK")

def old_fallback_cancel_routine():
    """Quy trình hủy khẩn cấp khi gặp lỗi (Timeout hoặc không tìm thấy đối tượng).
    Thực hiện Update trước, sau đó mới Cancel 2 lần."""
    global CURRENT_TAB
    log(f"CHAY QUY TRINH HUY KHAN CAP (FALLBACK CANCEL) TU TAB: {CURRENT_TAB}", "ACTION")
    
    if CURRENT_TAB == 'NBLM':
        log(f"F5 trang NBLM va quay ve LMS...", "ACTION")
        pyautogui.press('f5')
        time.sleep(2)
        pyautogui.hotkey('ctrl', 'shift', 'tab')
        time.sleep(1)
        CURRENT_TAB = 'LMS'
    
    # === BẤM UPDATE TRƯỚC KHI CANCEL ===
    log(f"Thuc hien Update truoc khi Cancel...", "ACTION")
    try:
        # Cuộn xuống dưới cùng để tìm nút Cập nhật
        pyautogui.moveTo(1920//2, 1080//2)
        for _ in range(5):
            pyautogui.scroll(-5000)
            time.sleep(0.05)
        pyautogui.move(300, 0)
        for _ in range(15):
            pyautogui.scroll(-5000)
            time.sleep(0.05)
        
        # Click nút Update
        try:
            update_pos = pyautogui.locateCenterOnScreen('update_btn.png', region=(284, 914, 626, 76), confidence=0.8)
            if update_pos:
                pyautogui.click(update_pos.x, update_pos.y + 10)
                log(f"Fallback: Da click nut Cap nhat bang anh.", "ACTION")
            else:
                raise Exception("Not found")
        except Exception:
            pyautogui.click(650, 973)
            log(f"Fallback: Da click nut Cap nhat bang toa do du phong (650, 973).", "ACTION")
        
        # Chờ phản hồi tối đa 10s
        for _ in range(50):
            try:
                if pyautogui.locateOnScreen('update_success.png', region=(871, 861, 404, 139), confidence=0.8):
                    log(f"Fallback: Cap nhat thanh cong!", "OK")
                    break
                if pyautogui.locateOnScreen('update_fail.png', region=(871, 861, 404, 139), confidence=0.8):
                    log(f"Fallback: Cap nhat that bai!", "ERROR")
                    break
            except Exception:
                pass
            time.sleep(0.2)
    except Exception as ue:
        log(f"Fallback: Loi khi thuc hien Update: {str(ue)}", "ERROR")
    
    time.sleep(1)
    
    # === SAU ĐÓ MỚI CANCEL 2 LẦN ===
    log(f"Thuc hien Cancel 2 lan tren LMS...", "ACTION")
    pyautogui.moveTo(x=875, y=246)
    pyautogui.click()
    time.sleep(0.5)
    
    for i in range(2):
        try:
            cancel_pos = pyautogui.locateCenterOnScreen('cancel.png', confidence=0.8)
            if cancel_pos:
                pyautogui.click(cancel_pos)
                log(f"Da click Cancel lan {i+1}", "ACTION")
                time.sleep(1)
        except:
            pass
            
    time.sleep(2)
    log(f"Da hoan tat quy trinh huy, san sang cho ID tiep theo!", "OK")

class CaptureHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-type')
        self.end_headers()

    def do_POST(self):
        global STOP_FLAG, CURRENT_TAB
        if self.path == '/stop':
            STOP_FLAG = True
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "Đã ra lệnh dừng quy trình."}).encode('utf-8'))
            return
            
        if self.path == '/search_id':
            STOP_FLAG = False
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                question_id = data.get('id', '')
            except:
                question_id = ''
            
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            if not question_id:
                self.wfile.write(json.dumps({"status": "error", "message": "Thiếu ID câu hỏi"}).encode('utf-8'))
                return
            
            try:
                # 0. Đảm bảo trang cuộn lên trên cùng trước khi tìm kiếm
                # Di chuyển chuột ra giữa màn hình LMS và cuộn ngược lên thật mạnh
                pyautogui.moveTo(x=875, y=246)
                pyautogui.click() # Lấy Focus cho LMS
                pyautogui.scroll(5000) # Cuộn lên (số dương là cuộn lên)
                time.sleep(1) # Chờ cuộn mượt xong

                # 1. Click vào ô tìm kiếm (Sử dụng Image Recognition)
                search_box_pos = None
                try:
                    search_box_pos = pyautogui.locateCenterOnScreen('search_box.png', region=SEARCH_BOX_REGION, confidence=0.8)
                except:
                    pass
                    
                if not search_box_pos:
                    try:
                        search_region = (CAPTURE_BBOX[0], CAPTURE_BBOX[1], 
                                         CAPTURE_BBOX[2] - CAPTURE_BBOX[0], CAPTURE_BBOX[3] - CAPTURE_BBOX[1])
                        search_box_pos = pyautogui.locateCenterOnScreen('search_box.png', region=search_region, confidence=0.8)
                    except:
                        pass
                        
                if search_box_pos:
                    pyautogui.click(search_box_pos)
                else:
                    # CLICK DỰ PHÒNG nếu không tìm thấy ảnh
                    pyautogui.click(x=SEARCH_BOX_FALLBACK[0], y=SEARCH_BOX_FALLBACK[1])
                    
                time.sleep(0.5)
                
                # 2. Xóa text cũ
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.2)
                pyautogui.press('backspace')
                time.sleep(0.2)
                
                # 3. Dán ID mới
                pyperclip.copy(question_id)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.5)
                
                # 4. Phát hiện Load (Kiểm tra màu nút Tìm kiếm)
                # Lấy màu xanh gốc của nút Tìm Kiếm trước khi ấn Enter
                idle_color = pyautogui.pixel(SEARCH_BTN_X, SEARCH_BTN_Y)

                # Nhấn Enter để bắt đầu tìm
                pyautogui.press('enter')
                time.sleep(0.5)
                
                # Chờ 0.5s/lượt, kiểm tra xem nút đã về màu xanh chưa, tối đa 10 lần (5s)
                for _ in range(10):
                    time.sleep(1)
                    if pyautogui.pixelMatchesColor(SEARCH_BTN_X, SEARCH_BTN_Y, idle_color, tolerance=10):
                        break # Nút đã xanh lại -> Xong!
                
                # 6. Di chuyển chuột ra giữa trang và cuộn xuống
                pyautogui.moveTo(x=875, y=246)
                pyautogui.click() # Lấy Focus cho LMS
                pyautogui.scroll(-5000) # Cuộn xuống (số âm là cuộn xuống)
                time.sleep(1) # Chờ cuộn mượt xong
                
                # 7. Chụp ảnh vùng chỉ định
                img = ImageGrab.grab(bbox=CAPTURE_BBOX)
                
                # Lấy màu gốc của nút Send bên Gemini ngay khi vừa chụp ảnh xong
                gemini_idle_color = pyautogui.pixel(GEMINI_SEND_BTN_X, GEMINI_SEND_BTN_Y)
                
                # 8. Lưu vào Clipboard
                output = io.BytesIO()
                img.convert("RGB").save(output, "BMP")
                data_bmp = output.getvalue()[14:]
                
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data_bmp)
                win32clipboard.CloseClipboard()

                # 9. Tìm và Click nút Edit lần 1 trên LMS trước tiên
                # Khoanh vùng tìm kiếm bằng đúng khu vực LMS (giúp tìm nhanh hơn)
                search_region = (CAPTURE_BBOX[0], CAPTURE_BBOX[1], 
                                 CAPTURE_BBOX[2] - CAPTURE_BBOX[0], 
                                 CAPTURE_BBOX[3] - CAPTURE_BBOX[1])
                
                try:
                    # 1. Tìm ảnh pencil.png ở vùng tối ưu trước
                    pencil_pos = None
                    try:
                        pencil_pos = pyautogui.locateCenterOnScreen('pencil.png', region=PENCIL1_REGION, confidence=0.8)
                    except:
                        pass
                        
                    # Nếu không thấy, mở rộng tìm kiếm toàn bộ khung LMS
                    if not pencil_pos:
                        search_region = (CAPTURE_BBOX[0], CAPTURE_BBOX[1], 
                                         CAPTURE_BBOX[2] - CAPTURE_BBOX[0], CAPTURE_BBOX[3] - CAPTURE_BBOX[1])
                        try:
                            pencil_pos = pyautogui.locateCenterOnScreen('pencil.png', region=search_region, confidence=0.8)
                        except:
                            pass
                    
                    if pencil_pos:
                        # Click lần 1 (lúc này LMS bắt đầu load trang)
                        pyautogui.click(pencil_pos)
                        
                        # ==================================================
                        # 10. TRANH THỦ THỜI GIAN ĐỢI LMS LOAD -> GỬI ẢNH CHO GEMINI
                        pyautogui.click(x=GEMINI_CHATBOX_X, y=GEMINI_CHATBOX_Y)
                        time.sleep(0.3)
                        pyautogui.hotkey('ctrl', 'v')
                        
                        # Chờ 2.5s để ảnh bắt đầu load lên Gemini
                        time.sleep(2.5)
                        
                        # Kiểm tra xem nút Send đã sẵn sàng (cùng màu gốc) chưa
                        for _ in range(10):
                            if pyautogui.pixelMatchesColor(GEMINI_SEND_BTN_X, GEMINI_SEND_BTN_Y, gemini_idle_color, tolerance=10):
                                break
                            time.sleep(0.2)
                            
                        # Gửi ảnh cho Gemini
                        pyautogui.press('enter')
                        time.sleep(0.5)
                        # ==================================================

                        # 11. Trở về tìm và Click nút Edit lần 2 (pencil2.png)
                        pencil2_pos = None
                        for _ in range(10): 
                            time.sleep(0.5)
                            try:
                                # Ưu tiên tìm trong vùng nhỏ
                                pencil2_pos = pyautogui.locateCenterOnScreen('pencil2.png', region=PENCIL2_REGION, confidence=0.8)
                            except:
                                pass
                                
                            if not pencil2_pos:
                                try:
                                    # Mở rộng vùng tìm kiếm nếu vùng nhỏ không thấy
                                    pencil2_pos = pyautogui.locateCenterOnScreen('pencil2.png', region=search_region, confidence=0.8)
                                except:
                                    pass
                                    
                            if pencil2_pos:
                                break # Đã tìm thấy thì thoát vòng lặp chờ
                                
                        if pencil2_pos:
                            # Click lần 2
                            pyautogui.click(pencil2_pos)
                            msg_extra = "Đã gửi Gemini & Mở Edit (2 lớp)."
                        else:
                            # CLICK DỰ PHÒNG nếu không tìm thấy ảnh
                            pyautogui.click(x=PENCIL2_FALLBACK[0], y=PENCIL2_FALLBACK[1])
                            msg_extra = "Đã gửi Gemini & Click Bút 2 (Dự phòng)."
                        log(f"Đã Click xong Bút 2!", "ACTION")
                            
                        # ==================================================
                        # ==================================================
                        # 12. CHỜ GEMINI TRẢ LỜI VÀ COPY NỘI DUNG
                        log(f"Đang chờ Gemini trả lời (theo dõi nút Send tối đa 10s)...", "STATUS")
                        
                        # BƯỚC 1: Đợi nút Send về màu gốc (Tín hiệu đã trả lời xong)
                        gemini_done = False
                        for _ in range(150):
                            if pyautogui.pixelMatchesColor(GEMINI_SEND_BTN_X, GEMINI_SEND_BTN_Y, gemini_idle_color, tolerance=10):
                                gemini_done = True
                                log(f"Phát hiện tín hiệu màu gốc từ Gemini (Đã xử lý xong)!", "STATUS")
                                break
                            time.sleep(0.1)
                            
                        if not gemini_done:
                            log(f"LỖI: Hết 15s nhưng nút Send chưa xanh. Hủy copy!", "ERROR")
                            raise Exception("Gemini phản hồi quá chậm (quá 15s). Vui lòng đổi câu hỏi!")
                            
                        # BƯỚC 2: Khi đã chắc chắn xong, mới cuộn và tìm nút Copy (tối đa 5s)
                        log(f"Đang cuộn chuột và tìm nút Copy (tối đa 5s)...", "SEARCH")
                        copy_pos = None
                        for _ in range(50):
                            # Click nhẹ một cái để ĐẢM BẢO giữ Focus cho cửa sổ Gemini
                            pyautogui.click(x=1587, y=240)
                            
                            # Lăn chuột tại chính vị trí (1587, 240)
                            pyautogui.scroll(-5000)
                            
                            try:
                                copy_pos = pyautogui.locateCenterOnScreen('gemini_copy.png', region=GEMINI_COPY_REGION, confidence=0.8)
                            except:
                                pass
                                
                            if copy_pos:
                                log(f"Đã thấy nút Copy mới nhất!", "INFO")
                                break
                                
                            time.sleep(0.1)
                            
                        if copy_pos:
                            pyautogui.click(copy_pos)
                            log(f"Đã Click Copy bằng mắt thần!", "OK")
                            msg_extra += " | Đã Copy kết quả Gemini."
                            
                            # Tải lại trang Gemini sau khi copy thành công
                            time.sleep(0.5)
                            pyautogui.press('f5')
                            log(f"Đã bấm F5 tải lại Gemini.", "ACTION")
                        else:
                            log(f"LỖI: Hết 5s vẫn chưa thấy nút Copy, dùng toạ độ dự phòng!", "ERROR")
                            # Click dự phòng
                            pyautogui.click(x=GEMINI_COPY_FALLBACK[0], y=GEMINI_COPY_FALLBACK[1])
                            msg_extra += " | Đã Copy kết quả Gemini (Dự phòng)."
                            
                            # Vẫn cố gắng F5 dù lỗi
                            time.sleep(0.5)
                            pyautogui.press('f5')
                            log(f"Đã bấm F5 tải lại Gemini.", "ACTION")
                            
                        # ==================================================
                        # 13. CHUYỂN SANG TAB NOTEBOOK LM VÀ DÁN NỘI DUNG
                        log(f"Chuyển sang tab NotebookLM để dán nội dung...", "ACTION")
                        
                        # Lấy lại Focus cho cửa sổ bên trái (chứa LMS và NotebookLM)
                        pyautogui.click(x=875, y=246)
                        time.sleep(0.3)
                        
                        # Ấn Ctrl + Tab để chuyển sang tab bên phải (NotebookLM)
                        pyautogui.hotkey('ctrl', 'tab')
                        CURRENT_TAB = 'NBLM'
                        
                        # TỪ TỪ HẴNG DÁN: Kiểm tra xem NBLM có đang load không
                        # Chờ đến khi nút Send hiện đúng màu (245, 245, 245) - tối đa 4s
                        log(f"Đang kiểm tra xem NotebookLM đã load xong chưa...", "STATUS")
                        nblm_idle_color = (245, 245, 245)
                        for _ in range(10): # Chờ tối đa 5 giây
                            if pyautogui.pixelMatchesColor(NBLM_SEND_BTN_X, NBLM_SEND_BTN_Y, nblm_idle_color, tolerance=5):
                                log(f"NotebookLM đã load xong (nút Send hiện màu gốc)!", "STATUS")
                                break
                            time.sleep(0.5)
                        
                        # Click vào ô chat của NotebookLM
                        pyautogui.click(x=530, y=936)
                        time.sleep(0.3)
                        
                        # Dán nội dung đã Copy từ Gemini và Enter
                        pyautogui.hotkey('ctrl', 'v')
                        time.sleep(0.3)
                        pyautogui.press('enter')
                        log(f"Đã dán nội dung vào NotebookLM và nhấn Enter.", "OK")
                        msg_extra += " | Đã gửi NBLM."
                        
                        # ==================================================
                        # 14. CHỜ NOTEBOOK LM TRẢ LỜI (Vòng lặp 20s soi - 5s chống timeout)
                        log(f"Bắt đầu vòng lặp chờ NotebookLM xử lý (tối đa 500s)...", "STATUS")
                        
                        nblm_done = False
                        # Chờ tối đa 20 chu kỳ (mỗi chu kỳ khoảng 25s = 500s)
                        for cycle in range(20):
                            if STOP_FLAG:
                                raise Exception("Bị dừng bởi người dùng!")
                                
                            log(f"Đang soi kết quả NotebookLM (Chu kỳ {cycle + 1}/20)...", "STATUS")
                            # Đang ở tab NotebookLM, kiểm tra liên tục trong 20 giây
                            for _ in range(200): # 200 * 0.1s = 20s
                                if pyautogui.pixelMatchesColor(NBLM_SEND_BTN_X, NBLM_SEND_BTN_Y, nblm_idle_color, tolerance=10):
                                    nblm_done = True
                                    break
                                time.sleep(0.1)
                                
                            if nblm_done:
                                log(f"Phát hiện NotebookLM đã thực sự xử lý xong!", "STATUS")
                                break
                                
                            # Nếu hết 15s mà chưa xong -> nhảy sang LMS 5s để chống timeout
                            log(f"Chưa xong, đảo sang tab LMS 5s để chống timeout...", "STATUS")
                            pyautogui.click(x=875, y=246) # Focus vào màn hình
                            time.sleep(0.2)
                            pyautogui.hotkey('ctrl', 'shift', 'tab') # Chuyển về LMS
                            CURRENT_TAB = 'LMS'
                            
                            # Đứng chơi bên LMS 5 giây
                            for _ in range(5):
                                if STOP_FLAG:
                                    raise Exception("Bị dừng bởi người dùng!")
                                time.sleep(1)
                                
                            # Hết 5s, quay lại tab NotebookLM để chuẩn bị soi tiếp
                            log(f"Quay lại NotebookLM...", "INFO")
                            pyautogui.click(x=875, y=246)
                            time.sleep(0.5)
                            pyautogui.hotkey('ctrl', 'tab')
                            CURRENT_TAB = 'NBLM'
                            time.sleep(1) # Chờ 1s để tab NBLM render lại giao diện ổn định
                            
                        if not nblm_done:
                            log(f"LỖI: Đã chờ 500s nhưng NotebookLM vẫn chưa xong!", "ERROR")
                            raise Exception("NotebookLM quá tải hoặc mạng lỗi!")
                            
                        # ==================================================
                        # 15. LĂN CHUỘT VÀ COPY TỪ NOTEBOOK LM
                        log(f"Đang lăn chuột và tìm nút Copy NotebookLM (tối đa 5s)...", "SEARCH")
                        nblm_copy_pos = None
                        for _ in range(50):
                            # Click nhẹ vào khoảng giữa màn hình LMS/NBLM để giữ focus cho lăn chuột
                            pyautogui.click(x=875, y=246)
                            
                            # Lăn mạnh xuống dưới cùng
                            pyautogui.scroll(-5000)
                            
                            # Tìm nút Copy NBLM trong vùng ưu tiên
                            try:
                                nblm_copy_pos = pyautogui.locateCenterOnScreen('notebooklm_copy.png', region=NBLM_COPY_REGION, confidence=0.8)
                            except:
                                pass
                                
                            # Mở rộng vùng tìm kiếm nếu không thấy
                            if not nblm_copy_pos:
                                try:
                                    search_region = (CAPTURE_BBOX[0], CAPTURE_BBOX[1], CAPTURE_BBOX[2]-CAPTURE_BBOX[0], CAPTURE_BBOX[3]-CAPTURE_BBOX[1])
                                    nblm_copy_pos = pyautogui.locateCenterOnScreen('notebooklm_copy.png', region=search_region, confidence=0.8)
                                except:
                                    pass
                                    
                            if nblm_copy_pos:
                                log(f"Đã tìm thấy nút Copy của NotebookLM!", "SEARCH")
                                break
                            time.sleep(0.1)
                            
                        if nblm_copy_pos:
                            pyautogui.click(nblm_copy_pos)
                            log(f"Đã Click Copy thành công từ NotebookLM!", "OK")
                            msg_extra += " | Đã Copy từ NBLM."
                            time.sleep(0.5) # Đợi 0.5s để text kịp lưu vào Clipboard
                        else:
                            log(f"LOI: Khong tim thay anh 'notebooklm_copy.png'! Huy qua trinh.", "ERROR")
                            raise Exception("Khong tim thay anh 'notebooklm_copy.png'")
                        # ==================================================
                    else:
                        log(f"LOI: Khong tim thay anh 'pencil.png' (Cay but 1)!", "ERROR")
                        raise Exception("Khong tim thay anh 'pencil.png' (Cay but 1)")
                        
                except Exception as ex:
                    log(f"LỖI TOÀN CỤC: {str(ex)}", "ERROR")
                    raise ex

                # Lấy nội dung NotebookLM từ Clipboard để gửi về Frontend
                try:
                    copied_text = pyperclip.paste()
                except:
                    copied_text = ""

                self.wfile.write(json.dumps({
                    "status": "success", 
                    "message": f"ID: {question_id} - {msg_extra}",
                    "notebook_output": copied_text
                }).encode('utf-8'))
            except Exception as e:
                log(f"BẮT ĐƯỢC LỖI TẠI SEARCH_ID: {str(e)}", "ERROR")
                if not STOP_FLAG:
                    fallback_cancel_routine()
                self.wfile.write(json.dumps({"status": "error", "message": f"Lỗi: {str(e)}"}).encode('utf-8'))
        elif self.path == '/paste_lms':
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                parsed_data = data.get('parsed_data', {})
                
                log(f"Nhận lệnh dán LMS từ Frontend (index.html)...", "ACTION")
                # Đưa chuỗi JSON vào Clipboard để sẵn sàng dán
                json_str = json.dumps(parsed_data, ensure_ascii=False)
                pyperclip.copy(json_str)
                
                # Trở lại tab LMS (vì hiện tại đang ở NBLM)
                pyautogui.hotkey('ctrl', 'shift', 'tab')
                CURRENT_TAB = 'LMS'
                time.sleep(0.5)
                
                # Bấm vào nút dán của Tampermonkey
                log(f"Click toạ độ dán lần 1 (649, 147)...", "ACTION")
                pyautogui.click(x=649, y=147)
                
                # Đợi 3 giây rồi bấm lần nữa
                time.sleep(3)
                log(f"Click toạ độ dán lần 2 (649, 147)...", "ACTION")
                pyautogui.click(x=649, y=147)
                
                # --- XỬ LÝ RIÊNG CHO TRẮC NGHIỆM ---
                if parsed_data.get('typeCode') == 'TRAC_NGHIEM':
                    options = parsed_data.get('options', [])
                    correct_ans = parsed_data.get('correct_answer', 1)
                    
                    if len(options) == 4:
                        log(f"Phát hiện câu TRẮC NGHIỆM. Bắt đầu lăn chuột tìm 4 phương án...", "SEARCH")
                        
                        # Cài đặt hàm phụ trợ kiểm tra con trỏ chuột I-Beam
                        import ctypes
                        def is_editing_cursor():
                            class POINT(ctypes.Structure):
                                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                            class CURSORINFO(ctypes.Structure):
                                _fields_ = [("cbSize", ctypes.c_uint), ("flags", ctypes.c_uint), ("hCursor", ctypes.c_void_p), ("ptScreenPos", POINT)]
                            info = CURSORINFO()
                            info.cbSize = ctypes.sizeof(CURSORINFO)
                            ctypes.windll.user32.GetCursorInfo(ctypes.byref(info))
                            
                            h_current = info.hCursor
                            h_ibeam = ctypes.windll.user32.LoadCursorW(None, 32513)
                            h_arrow = ctypes.windll.user32.LoadCursorW(None, 32512)
                            h_hand = ctypes.windll.user32.LoadCursorW(None, 32649)
                            
                            if h_current == h_ibeam:
                                return True
                            # Nếu khác Mũi tên và Bàn tay thì 90% là con trỏ I-Beam custom của trình duyệt
                            if h_current != 0 and h_current != h_arrow and h_current != h_hand:
                                return True
                            return False

                        pyautogui.moveTo(x=1920//2, y=1080//2)
                        
                        scan_region = (306, 239, 722, 769)
                        
                        found_boundary = False
                        log(f"Cuộn LÊN từ từ để tìm khung 4 phương án...", "SEARCH")
                        for _ in range(25):
                            try:
                                top_marker = pyautogui.locateOnScreen('danh_sach_cau_tra_loi.png', region=scan_region, confidence=0.85)
                                bot_marker = pyautogui.locateOnScreen('lua_chon_them.png', region=scan_region, confidence=0.85)
                                if top_marker and bot_marker:
                                    found_boundary = True
                                    break
                            except:
                                pass
                            pyautogui.scroll(150) # Lướt LÊN
                            time.sleep(0.02)
                            
                        if not found_boundary:
                            log(f"Không thấy ở trên, cuộn XUỐNG từ từ để tìm...", "SEARCH")
                            for _ in range(40):
                                try:
                                    top_marker = pyautogui.locateOnScreen('danh_sach_cau_tra_loi.png', region=scan_region, confidence=0.85)
                                    bot_marker = pyautogui.locateOnScreen('lua_chon_them.png', region=scan_region, confidence=0.85)
                                    if top_marker and bot_marker:
                                        found_boundary = True
                                        break
                                except:
                                    pass
                                pyautogui.scroll(-150) # Lướt XUỐNG
                                time.sleep(0.02)
                                
                        try:
                            if found_boundary:
                                log(f"Đã đóng khung toàn bộ 4 phương án!", "SEARCH")
                            # --- QUÉT TÌM CÂY BÚT ---
                            raw_pencils = list(pyautogui.locateAllOnScreen('pencil.png', region=scan_region, confidence=0.85))
                            unique_pencils = []
                            for b in raw_pencils:
                                if not any(abs(b.top - ub.top) < 20 for ub in unique_pencils):
                                    unique_pencils.append(b)
                            found_pencils = sorted(unique_pencils, key=lambda b: b.top)[:4]
                            
                            # --- QUÉT TÌM CÂY BÚT ---
                            raw_pencils = list(pyautogui.locateAllOnScreen('pencil.png', region=scan_region, confidence=0.85))
                            unique_pencils = []
                            for b in raw_pencils:
                                if not any(abs(b.top - ub.top) < 20 for ub in unique_pencils):
                                    unique_pencils.append(b)
                            found_pencils = sorted(unique_pencils, key=lambda b: b.top)[:4]
                            
                            if len(found_pencils) == 4:
                                # ==============================================
                                # TASK 1: XỬ LÝ CHECKBOX TRƯỚC TIÊN
                                # ==============================================
                                log(f"Bắt đầu xử lý task Checkbox (Quét trực tiếp trạng thái)...", "SEARCH")
                                
                                # Lấy mốc từ top_marker và bot_marker để thu hẹp vùng quét
                                top_marker = pyautogui.locateOnScreen('danh_sach_cau_tra_loi.png', region=scan_region, confidence=0.8)
                                bot_marker = pyautogui.locateOnScreen('lua_chon_them.png', region=scan_region, confidence=0.8)
                                
                                cb_region = scan_region
                                if top_marker and bot_marker:
                                    # Vị trí bắt đầu: mép trái dịch sang trái 100px. Kéo sang phải 300px. Quét xuống lua_chon_them.
                                    cb_region = (max(0, int(top_marker.left) - 100), int(top_marker.top), 300, int(bot_marker.top - top_marker.top + bot_marker.height))
                                
                                log(f"[DEBUG] Tọa độ top_marker: {top_marker}", "STATUS")
                                log(f"[DEBUG] Tọa độ bot_marker: {bot_marker}", "STATUS")
                                log(f"[DEBUG] Vùng quét Checkbox (cb_region) X,Y,W,H: {cb_region}", "SEARCH")
                                
                                for attempt in range(2):
                                
                                    log(f"--- BẮT ĐẦU QUÉT CHECKBOX LẦN {attempt + 1} ---", "SEARCH")
                                
                                    cb_objects = []
                                    
                                    # Quét tất cả các ô TRỐNG (Tìm cả 2 mẫu ảnh)
                                    for img_name in ['checkbox_empty.png', 'checkbox_empty2.png']:
                                        try:
                                            raw_empty = list(pyautogui.locateAllOnScreen(img_name, region=cb_region, confidence=0.8))
                                            log(f"[DEBUG] Raw locate {img_name} tìm thấy {len(raw_empty)} kết quả: {raw_empty}", "SEARCH")
                                            for b in raw_empty:
                                                # Bổ sung điều kiện CHẮC CHẮN nằm giữa 2 marker
                                                if top_marker and bot_marker:
                                                    if not (top_marker.top <= b.top <= bot_marker.top + bot_marker.height):
                                                        continue
                                                if not any(abs(b.top - obj['box'].top) < 20 for obj in cb_objects):
                                                    cb_objects.append({'type': 'empty', 'box': b})
                                                    log(f"[DEBUG] + Ghi nhận 1 ô TRỐNG hợp lệ tại: {b} từ ảnh {img_name}", "SEARCH")
                                        except Exception as e:
                                            log(f"[DEBUG] Không tìm thấy {img_name}: {e}", "ERROR")
                                            pass
                                            
                                    # Quét tất cả các ô ĐÃ TICK (Tìm cả 2 mẫu ảnh)
                                    for img_name in ['checkbox_checked.png', 'checkbox_checked2.png']:
                                        try:
                                            raw_checked = list(pyautogui.locateAllOnScreen(img_name, region=cb_region, confidence=0.8))
                                            log(f"[DEBUG] Raw locate {img_name} tìm thấy {len(raw_checked)} kết quả: {raw_checked}", "SEARCH")
                                            for b in raw_checked:
                                                # Bổ sung điều kiện CHẮC CHẮN nằm giữa 2 marker
                                                if top_marker and bot_marker:
                                                    if not (top_marker.top <= b.top <= bot_marker.top + bot_marker.height):
                                                        continue
                                                # Tránh trường hợp nhận diện trùng lặp
                                                if not any(abs(b.top - obj['box'].top) < 20 for obj in cb_objects):
                                                    cb_objects.append({'type': 'checked', 'box': b})
                                                    log(f"[DEBUG] + Ghi nhận 1 ô ĐÃ TICK hợp lệ tại: {b} từ ảnh {img_name}", "OK")
                                        except Exception as e:
                                            log(f"[DEBUG] Không tìm thấy {img_name}: {e}", "ERROR")
                                            pass
                                        
                                    # Sắp xếp TẤT CẢ các checkbox từ trên xuống dưới
                                    cb_objects = sorted(cb_objects, key=lambda obj: obj['box'].top)
                                    
                                    ans_idx = int(correct_ans) - 1
                                    log(f"Phân tích Checkbox: Đáp án ĐÚNG={ans_idx+1}. Tìm thấy {len(cb_objects)} ô checkbox trên màn hình.", "SEARCH")
                                    
                                    # Thực thi hành động Checkbox
                                    for idx, obj in enumerate(cb_objects):
                                        center_x, center_y = pyautogui.center(obj['box'])
                                        
                                        if obj['type'] == 'checked':
                                            if idx != ans_idx:
                                                # Đang bị tick mà KHÔNG PHẢI đáp án đúng -> BỎ TICK
                                                pyautogui.click(center_x, center_y)
                                                log(f"Đã BỎ TICK phương án sai (Vị trí {idx + 1}).", "OK")
                                                time.sleep(0.2)
                                        elif obj['type'] == 'empty':
                                            if idx == ans_idx:
                                                # Đang rỗng mà LÀ ĐÁP ÁN ĐÚNG -> TICK
                                                pyautogui.click(center_x, center_y)
                                                log(f"Đã TICK đáp án đúng (Vị trí {idx + 1}).", "OK")
                                                time.sleep(0.1)
                                
                                    if attempt == 0:
                                
                                        log(f"Đợi 1.5 giây để LMS ghi nhận và quét lại lần 2...", "SEARCH")
                                
                                        time.sleep(1.5)
                                            
                                # ==============================================
                                # TASK 2: DÁN NGƯỢC TỪ DƯỚI LÊN BẰNG CÂY BÚT VÀ I-BEAM
                                # ==============================================
                                log(f"Đã xong Checkbox, bắt đầu dán ngược từ dưới lên...", "OK")
                                
                                for i in range(3, -1, -1):
                                    pencil_box = found_pencils[i]
                                    mouse_x, mouse_y = pyautogui.center(pencil_box)
                                    
                                    # Click vào cây bút
                                    pyautogui.click(mouse_x, mouse_y)
                                    time.sleep(0.5) # Delay 0.7s để load vùng nhập liệu
                                    
                                    mouse_x -= 20 # Di chuột sang trái 20 pixel
                                    pyautogui.moveTo(mouse_x, mouse_y)
                                    time.sleep(0.2)
                                    
                                    # Rà chuột tìm I-Beam
                                    found_ibeam = False
                                    # Kiểm tra TRƯỚC XEM có phải I-beam ngay không
                                    if is_editing_cursor():
                                        found_ibeam = True
                                    else:
                                        # Nếu chưa phải, di chuột xuống dưới (mỗi lần 40px)
                                        for _ in range(4): # Thử xuống tối đa 4 lần (200 pixel)
                                            mouse_y += 50
                                            pyautogui.moveTo(mouse_x, mouse_y)
                                            time.sleep(0.2)
                                            if is_editing_cursor():
                                                found_ibeam = True
                                                break
                                        
                                    if found_ibeam:
                                        # Click thêm 1 phát nữa tại vùng I-Beam để trỏ chuột nhấp nháy
                                        pyautogui.click(mouse_x, mouse_y)
                                        time.sleep(0.2)
                                        
                                        pyautogui.hotkey('ctrl', 'a')
                                        time.sleep(0.2)
                                        pyautogui.press('delete')
                                        time.sleep(0.2)
                                        
                                        text_to_paste = options[i]
                                        log(f"[DEBUG] Copying to clipboard: {text_to_paste}", "STATUS")
                                        pyperclip.copy(text_to_paste)
                                        time.sleep(0.2) # Chờ Windows cập nhật clipboard
                                        
                                        pyautogui.keyDown('ctrl')
                                        pyautogui.press('v')
                                        pyautogui.keyUp('ctrl')
                                        
                                        log(f"Đã dán phương án {i+1} bằng I-Beam!", "OK")
                                        time.sleep(0.2)
                                    else:
                                        log(f"Loi: Do xuong ma khong thay I-Beam o phuong an {i+1}!", "ERROR")
                                        raise Exception(f"Khong tim thay I-Beam o phuong an {i+1}")
                            else:
                                log(f"Loi: Tim thay {len(found_pencils)} cay but (anh 'pencil.png'), yeu cau 4.", "ERROR")
                                raise Exception(f"Tim thay {len(found_pencils)} cay but 'pencil.png' (yeu cau 4)")
                        except Exception as e:
                            log(f"Lỗi nhận diện: {e}", "ERROR")
                            raise e

                # --- XỬ LÝ RIÊNG CHO ĐÚNG / SAI ---
                elif parsed_data.get('typeCode') == 'DUNG_SAI':
                    options = parsed_data.get('options', [])
                    correct_ans = parsed_data.get('correct_answer', [])
                    
                    if len(options) == 4 and isinstance(correct_ans, list) and len(correct_ans) == 4:
                        log(f"Phát hiện câu ĐÚNG/SAI. Bắt đầu lăn chuột tìm 4 phương án...", "SEARCH")

                        
                        import ctypes
                        def is_editing_cursor():
                            class POINT(ctypes.Structure):
                                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                            class CURSORINFO(ctypes.Structure):
                                _fields_ = [("cbSize", ctypes.c_uint), ("flags", ctypes.c_uint), ("hCursor", ctypes.c_void_p), ("ptScreenPos", POINT)]
                            info = CURSORINFO()
                            info.cbSize = ctypes.sizeof(CURSORINFO)
                            ctypes.windll.user32.GetCursorInfo(ctypes.byref(info))
                            
                            h_current = info.hCursor
                            h_ibeam = ctypes.windll.user32.LoadCursorW(None, 32513)
                            h_arrow = ctypes.windll.user32.LoadCursorW(None, 32512)
                            h_hand = ctypes.windll.user32.LoadCursorW(None, 32649)
                            
                            if h_current == h_ibeam:
                                return True
                            if h_current != 0 and h_current != h_arrow and h_current != h_hand:
                                return True
                            return False

                        pyautogui.moveTo(x=1920//2, y=1080//2)
                        scan_region = (300, 150, 1500, 900) # Mở rộng toàn khung LMS
                        
                        found_boundary = False
                        log(f"Cuộn LÊN từ từ để tìm khung ĐÚNG/SAI...", "SEARCH")
                        for _ in range(25):
                            try:
                                top_marker = pyautogui.locateOnScreen('TF_top.png', region=scan_region, confidence=0.8)
                                bot_marker = pyautogui.locateOnScreen('TF_bot.png', region=scan_region, confidence=0.8)
                                if top_marker and bot_marker:
                                    found_boundary = True
                                    break
                            except:
                                pass
                            pyautogui.scroll(200)
                            time.sleep(0.05)
                            
                        if not found_boundary:
                            log(f"Không thấy ở trên, cuộn XUỐNG từ từ để tìm...", "SEARCH")
                            for _ in range(40):
                                try:
                                    top_marker = pyautogui.locateOnScreen('TF_top.png', region=scan_region, confidence=0.8)
                                    bot_marker = pyautogui.locateOnScreen('TF_bot.png', region=scan_region, confidence=0.8)
                                    if top_marker and bot_marker:
                                        found_boundary = True
                                        break
                                except:
                                    pass
                                pyautogui.scroll(-200)
                                time.sleep(0.05)
                                
                        try:
                            if found_boundary:
                                log(f"Đã đóng khung vùng ĐÚNG/SAI!", "SEARCH")
                            
                            # ==============================================
                            # TASK 1: XỬ LÝ CHECKBOX ĐÚNG/SAI
                            # ==============================================
                            log(f"Bắt đầu xử lý task Checkbox ĐÚNG/SAI...", "INFO")
                            
                            top_marker = pyautogui.locateOnScreen('TF_top.png', region=scan_region, confidence=0.8)
                            bot_marker = pyautogui.locateOnScreen('TF_bot.png', region=scan_region, confidence=0.8)
                            
                            if top_marker and bot_marker:
                                cb_region = (int(top_marker.left), int(top_marker.top), 1200, int(bot_marker.top - top_marker.top))
                                log(f"Vùng quét circle: {cb_region}", "SEARCH")
                                
                                valid_circles_found = False
                                
                                for attempt in range(2):
                                    log(f"--- BẮT ĐẦU QUÉT CIRCLE LẦN {attempt + 1} ---", "SEARCH")
                                    
                                    cb_objects = []
                                    for img_name, status in [('circle_empty.png', 'empty'), ('circle_checked.png', 'checked')]:
                                        try:
                                            raw_circles = list(pyautogui.locateAllOnScreen(img_name, region=cb_region, confidence=0.8))
                                            for b in raw_circles:
                                                if not any(abs(b.top - obj['box'].top) < 15 and abs(b.left - obj['box'].left) < 15 for obj in cb_objects):
                                                    cb_objects.append({'type': status, 'box': b})
                                        except Exception: pass
                                        
                                    cb_objects = sorted(cb_objects, key=lambda obj: obj['box'].top)
                                    
                                    rows = []
                                    current_row = []
                                    for obj in cb_objects:
                                        if not current_row:
                                            current_row.append(obj)
                                        else:
                                            if abs(obj['box'].top - current_row[0]['box'].top) < 20:
                                                current_row.append(obj)
                                            else:
                                                rows.append(current_row)
                                                current_row = [obj]
                                    if current_row:
                                        rows.append(current_row)
                                        
                                    # THỰC HIỆN "TỰ DÓNG" (INTERPOLATION) NẾU HÀNG BỊ THIẾU CIRCLE
                                    ref_distance = None
                                    ref_left_x = None
                                    ref_width = None
                                    ref_height = None
                                    for r in rows:
                                        if len(r) == 2:
                                            sorted_r = sorted(r, key=lambda obj: obj['box'].left)
                                            ref_left_x = sorted_r[0]['box'].left
                                            ref_right_x = sorted_r[1]['box'].left
                                            ref_distance = ref_right_x - ref_left_x
                                            ref_width = sorted_r[0]['box'].width
                                            ref_height = sorted_r[0]['box'].height
                                            break
                                            
                                    if ref_distance is None:
                                        ref_distance = 125
                                        ref_left_x = int(top_marker.left) + 65
                                        ref_width = rows[0][0]['box'].width if hasattr(rows[0][0]['box'], 'width') else 20
                                        ref_height = rows[0][0]['box'].height if hasattr(rows[0][0]['box'], 'height') else 20
                                        log(f"KÍCH HOẠT FALLBACK: Dùng khoảng cách {ref_distance}px và mốc trái {ref_left_x}", "ACTION")
                                            
                                    if ref_distance is not None:
                                        from collections import namedtuple
                                        DummyBox = namedtuple('DummyBox', ['left', 'top', 'width', 'height'])

                                        for i, r in enumerate(rows):
                                            if len(r) == 1:
                                                c = r[0]
                                                c_left = c['box'].left
                                                c_top = c['box'].top
                                                c_width = c['box'].width if hasattr(c['box'], 'width') else ref_width
                                                c_height = c['box'].height if hasattr(c['box'], 'height') else ref_height
                                                
                                                if abs(c_left - ref_left_x) < abs(c_left - (ref_left_x + ref_distance)):
                                                    # Thiếu circle PHẢI
                                                    missing_box = DummyBox(c_left + ref_distance, c_top, c_width, c_height)
                                                    r.append({'type': 'unknown', 'box': missing_box})
                                                    log(f"Đã tự dóng bù circle PHẢI cho phương án {i+1}.", "SEARCH")
                                                else:
                                                    # Thiếu circle TRÁI
                                                    missing_box = DummyBox(c_left - ref_distance, c_top, c_width, c_height)
                                                    r.append({'type': 'unknown', 'box': missing_box})
                                                    log(f"Đã tự dóng bù circle TRÁI cho phương án {i+1}.", "SEARCH")
                                        
                                    log(f"Tìm thấy {len(rows)} hàng circle.", "SEARCH")
                                    
                                    if len(rows) == 4:
                                        valid_circles_found = True
                                        
                                        # 1. In tóm tắt trạng thái trước
                                        log(f"\\n--- BẢNG TÓM TẮT TRẠNG THÁI TRƯỚC KHI CLICK ---", "STATUS")
                                        for i in range(4):
                                            row_cbs = sorted(rows[i], key=lambda obj: obj['box'].left)
                                            if len(row_cbs) >= 2:
                                                is_dung_checked = (row_cbs[0]['type'] == 'checked')
                                                is_sai_checked = (row_cbs[1]['type'] == 'checked')
                                                
                                                current_state_str = "Chưa chọn"
                                                if is_dung_checked: current_state_str = "ĐÚNG"
                                                elif is_sai_checked: current_state_str = "SAI"
                                                
                                                target_state_str = "ĐÚNG" if correct_ans[i] else "SAI"
                                                action_str = "CẦN SỬA" if current_state_str != target_state_str else "GIỮ NGUYÊN"
                                                log(f" - Phương án {i+1}: Hiện tại [{current_state_str}] | Đáp án chuẩn [{target_state_str}] ==> {action_str}", "INFO")
                                            else:
                                                log(f" - Phương án {i+1}: LỖI! Chỉ tìm thấy {len(row_cbs)} vòng tròn. Bỏ qua phương án này.", "ERROR")
                                        log(f"-------------------------------------------------\\n", "INFO")

                                        # 2. Bắt đầu click
                                        for i in range(4):
                                            row_cbs = sorted(rows[i], key=lambda obj: obj['box'].left)
                                            if len(row_cbs) >= 2:
                                                box_dung = row_cbs[0]
                                                box_sai = row_cbs[1]
                                                
                                                is_dung_checked = (box_dung['type'] == 'checked')
                                                is_sai_checked = (box_sai['type'] == 'checked')
                                                
                                                target_state = correct_ans[i]
                                                
                                                needs_click = False
                                                if target_state == True and not is_dung_checked:
                                                    needs_click = True
                                                elif target_state == False and not is_sai_checked:
                                                    needs_click = True
                                                    
                                                if needs_click:
                                                    target_box = box_dung if target_state else box_sai
                                                    center_x, center_y = pyautogui.center(target_box['box'])
                                                    
                                                    pyautogui.click(center_x, center_y)
                                                    time.sleep(0.3)
                                                    pyautogui.click(center_x, center_y)
                                                    
                                                    ans_str = "ĐÚNG" if target_state else "SAI"
                                                    log(f"Đã CLICK đổi trạng thái thành {ans_str} cho phương án {i + 1}.", "OK")
                                                    time.sleep(0.1)
                                                else:
                                                    ans_str = "ĐÚNG" if target_state else "SAI"
                                                    log(f"Phương án {i + 1} đã ở đúng trạng thái {ans_str}, bỏ qua.", "STATUS")
                                        
                                        if attempt == 0:
                                            log(f"Đợi 1.5 giây để LMS ghi nhận và quét lại lần 2...", "SEARCH")
                                            time.sleep(1.5)
                                    else:
                                        log(f"Lỗi: Tìm thấy {len(rows)} hàng circle, yêu cầu 4.", "ERROR")
                                        valid_circles_found = False
                                        raise Exception(f"Tìm thấy {len(rows)} hàng circle (yêu cầu 4)")
                                
                                if valid_circles_found:
                                    # ==============================================
                                    # TASK 2: DÁN ĐÁP ÁN (TỪ DƯỚI LÊN TRÊN)
                                    # ==============================================
                                    log(f"Bắt đầu dán văn bản từ dưới lên trên...", "ACTION")
                                    for i in range(3, -1, -1):
                                        row_cbs = sorted(rows[i], key=lambda obj: obj['box'].left)
                                        if len(row_cbs) >= 1:
                                            box_right = row_cbs[-1] # Lấy circle bên phải
                                            center_x, center_y = pyautogui.center(box_right['box'])
                                            
                                            target_x = int(center_x) - 250
                                            target_y = int(center_y)
                                            pyautogui.moveTo(target_x, target_y)
                                            time.sleep(0.1)
                                            
                                            # Double click, chờ 0.2s, lại double click tiếp để mở trình edit
                                            pyautogui.doubleClick()
                                            time.sleep(0.2)
                                            pyautogui.doubleClick()
                                            time.sleep(0.2)
                                            
                                            pyautogui.hotkey('ctrl', 'a')
                                            time.sleep(0.1)
                                            pyautogui.press('delete')
                                            time.sleep(0.1)
                                            
                                            text_to_paste = options[i]
                                            log(f"[DEBUG] Copying to clipboard: {text_to_paste}", "STATUS")
                                            pyperclip.copy(text_to_paste)
                                            time.sleep(0.2) # Chờ Windows cập nhật clipboard
                                            
                                            pyautogui.keyDown('ctrl')
                                            pyautogui.press('v')
                                            pyautogui.keyUp('ctrl')
                                            
                                            log(f"Đã dán phương án {i+1}!", "OK")
                                            time.sleep(0.2)
                                            
                                            if i == 0:
                                                pyautogui.press('enter')
                                                time.sleep(0.2)
                                                log(f"Đã ấn Enter sau phương án cuối!", "OK")
                            else:
                                missing_imgs = []
                                if not top_marker:
                                    missing_imgs.append("'TF_top.png'")
                                if not bot_marker:
                                    missing_imgs.append("'TF_bot.png'")
                                missing_str = " va ".join(missing_imgs) if missing_imgs else "'TF_top.png' va/hoac 'TF_bot.png'"
                                log(f"Khong tim thay anh {missing_str} khi quet circle.", "ERROR")
                                raise Exception(f"Khong tim thay anh {missing_str}")
                        except Exception as e:
                            log(f"Lỗi nhận diện: {e}", "ERROR")
                            raise e
                    else:
                        log(f"Bỏ qua vì dữ liệu DUNG_SAI không hợp lệ. Số lượng options: {len(options)}, Kiểu correct_ans: {type(correct_ans)}, Dữ liệu correct_ans: {correct_ans}", "ERROR")
                        raise Exception("Dữ liệu DUNG_SAI từ NBLM không hợp lệ")

                # ==============================================
                # TASK 3: TỰ ĐỘNG BẤM CẬP NHẬT
                # ==============================================
                def perform_update_sequence():
                    log(f"Bắt đầu chu trình Cập nhật...", "ACTION")
                    
                    def click_update_btn(force_backup=False):
                        # 1. Cuộn thanh cuộn thứ nhất (giữa màn hình)
                        pyautogui.moveTo(1920//2, 1080//2)
                        for _ in range(5):
                            pyautogui.scroll(-5000)
                            time.sleep(0.05)
                            
                        # 2. Cuộn thanh cuộn thứ hai (dịch phải 300px)
                        pyautogui.move(300, 0)
                        for _ in range(15):
                            pyautogui.scroll(-5000)
                            time.sleep(0.05)
                        
                        if force_backup:
                            pyautogui.click(650, 973)
                            log(f"Đã click nút Cập nhật bằng tọa độ dự phòng (650, 973).", "ACTION")
                            return

                        try:
                            # Thu hẹp vùng scan nút cập nhật: (284, 914) đến (910, 990)
                            update_pos = pyautogui.locateCenterOnScreen('update_btn.png', region=(284, 914, 626, 76), confidence=0.8)
                            if update_pos:
                                # Cộng thêm 10 pixel vào trục Y để bù trừ viền ảnh bị lệch lên trên
                                pyautogui.click(update_pos.x, update_pos.y + 10)
                                log(f"Đã click nút Cập nhật bằng ảnh (có bù trừ +10px Y).", "ACTION")
                            else:
                                raise Exception("Not found")
                        except Exception:
                            pyautogui.click(650, 973)
                            log(f"Đã click nút Cập nhật bằng tọa độ dự phòng (650, 973).", "ACTION")

                    def wait_for_status(timeout=10):
                        log(f"Đang chờ phản hồi Cập nhật (tối đa {timeout}s)...", "STATUS")
                        for _ in range(int(timeout / 0.2)):
                            try:
                                # Ưu tiên quét success trước và hạ confidence xuống 0.8 theo yêu cầu
                                if pyautogui.locateOnScreen('update_success.png', region=(871, 861, 404, 139), confidence=0.8):
                                    return 'success'
                                if pyautogui.locateOnScreen('update_fail.png', region=(871, 861, 404, 139), confidence=0.8):
                                    return 'fail'
                            except Exception:
                                pass
                            time.sleep(0.2)
                        return None

                    def old_do_cancel_success():
                        log(f"Đang click Cancel thành công...", "OK")
                        try:
                            cancel_pos = pyautogui.locateCenterOnScreen('cancel.png', region=(1083, 137, 229, 76), confidence=0.8)
                            if cancel_pos:
                                pyautogui.click(cancel_pos)
                                log(f"Đã click Cancel thành công bằng ảnh.", "OK")
                            else:
                                raise Exception("Not found")
                        except Exception:
                            pyautogui.click(1270, 176)
                            log(f"Đã click Cancel (tọa độ dự phòng).", "ACTION")

                    def do_double_cancel():
                        log(f"Đang thực hiện Cancel bằng phím ESC...", "ACTION")
                        # Lấy focus tại điểm (1268, 587)
                        pyautogui.click(1268, 587)
                        time.sleep(0.25)
                        # Bấm nút esc lần 1
                        pyautogui.press('esc')
                        time.sleep(0.5)
                        
                        # Tiếp tục lấy focus tại điểm (1268, 587)
                        pyautogui.click(1268, 587)
                        time.sleep(0.25)
                        # Bấm nút esc lần 2
                        pyautogui.press('esc')
                        time.sleep(0.5)
                        
                        # Bấm esc lần 3
                        pyautogui.press('esc')
                        time.sleep(0.5)
                        log(f"Đã hoàn tất thao tác Cancel bằng ESC.", "OK")

                    def old_do_double_cancel():
                        log(f"Đang thực hiện Double Cancel (Click cả 2 vị trí để đảm bảo thoát)...", "ACTION")
                        try:
                            cancel_icon = pyautogui.locateCenterOnScreen('cancel.png', region=(817, 123, 248, 114), confidence=0.8)
                            if cancel_icon:
                                pyautogui.click(cancel_icon)
                                log(f"Đã tắt thông báo lỗi bằng ảnh icon.", "ERROR")
                            else:
                                raise Exception("Not found")
                        except Exception:
                            pyautogui.click(1009, 175)
                            log(f"Đã tắt thông báo lỗi bằng tọa độ dự phòng.", "ERROR")
                        
                        time.sleep(1.5)
                        old_do_cancel_success()

                    # Lần 1
                    click_update_btn()
                    status = wait_for_status(10)
                    
                    if status == 'success':
                        log(f"Trạng thái: CẬP NHẬT THÀNH CÔNG!", "OK")
                        do_double_cancel()
                    elif status == 'fail':
                        log(f"Trạng thái: CẬP NHẬT THẤT BẠI! Thử bấm lại lần 2...", "ERROR")
                        click_update_btn()
                        status2 = wait_for_status(5)
                        
                        if status2 == 'success':
                            log(f"Trạng thái Lần 2: CẬP NHẬT THÀNH CÔNG!", "OK")
                            do_double_cancel()
                        else:
                            # Cả fail và None (timeout) đều tính là thất bại ở lần 2
                            log(f"Trạng thái Lần 2: THẤT BẠI HOẶC QUÁ HẠN! Hủy bỏ...", "ERROR")
                            do_double_cancel()
                    else:
                        log(f"Lần 1 hết thời gian chờ (10s)! Bấm cập nhật lại bằng tọa độ dự phòng...", "STATUS")
                        click_update_btn(force_backup=True)
                        status2 = wait_for_status(5)
                        
                        if status2 == 'success':
                            log(f"Trạng thái Lần 2: CẬP NHẬT THÀNH CÔNG!", "OK")
                            do_double_cancel()
                        else:
                            # Cả fail và None (timeout) đều tính là thất bại ở lần 2
                            log(f"Trạng thái Lần 2: THẤT BẠI HOẶC QUÁ HẠN! Hủy bỏ...", "ERROR")
                            do_double_cancel()

                perform_update_sequence()

                log(f"HOAN TAT CHU TRINH DAN LMS!", "OK")
                
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            except Exception as e:
                log(f"BẮT ĐƯỢC LỖI TẠI PASTE_LMS: {str(e)}", "ERROR")
                fallback_cancel_routine()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
        elif self.path == '/test_search_id':
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                copied_text = pyperclip.paste()
                self.wfile.write(json.dumps({
                    "status": "success", 
                    "message": "Đã giả lập nhận kết quả NBLM",
                    "notebook_output": copied_text
                }).encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
        elif self.path == '/batch_start':
            # Endpoint: Bắt đầu phiên batch mới, tạo file history
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                total_ids = data.get('total_ids', 0)
                
                filepath = create_history_file(total_ids)
                
                # Gửi tin nhắn Discord: Bắt đầu phiên
                discord_msg = (
                    f"**== BAT DAU PHIEN BIEN TAP ==**\n"
                    f"```\n"
                    f"Thoi gian : {time.strftime('%d/%m/%Y %H:%M:%S')}\n"
                    f"So luong  : {total_ids} ID\n"
                    f"```"
                )
                send_discord(discord_msg)
                
                self.wfile.write(json.dumps({
                    "status": "success",
                    "message": f"Đã tạo file history cho {total_ids} ID",
                    "history_file": filepath
                }).encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
        elif self.path == '/batch_item_start':
            # Endpoint: Gửi tin nhắn Discord khi bắt đầu xử lý 1 câu
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                stt = data.get('stt', 0)
                question_id = data.get('id', '')
                total = data.get('total', 0)
                
                discord_msg = f"**[{stt}/{total}] Dang xu li cau {stt} - {question_id}** ({time.strftime('%H:%M:%S')})"
                send_discord(discord_msg)
                
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
        elif self.path == '/batch_log':
            # Endpoint: Ghi kết quả 1 ID vào file history
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                stt = data.get('stt', 0)
                question_id = data.get('id', '')
                status = data.get('status', 'Không rõ')
                content = data.get('content', '')
                type_code = data.get('type_code', 'N/A')
                error_detail = data.get('error_detail', '')
                item_start_time = data.get('start_time', '')
                item_end_time = data.get('end_time', '')
                item_duration = data.get('duration', '')
                
                append_history_entry(stt, question_id, status, content)
                
                # Gửi tin nhắn Discord: Tổng kết câu
                type_names = {
                    'TRAC_NGHIEM': 'Trac nghiem',
                    'DUNG_SAI': 'Dung/Sai',
                    'DIEN_TU': 'Dien tu',
                }
                type_display = type_names.get(type_code, type_code)
                
                status_line = f"Trang thai : {'Thanh cong' if 'thành công' in status.lower() else 'THAT BAI'}"
                if error_detail:
                    status_line += f"\nLoi        : {error_detail}"
                
                discord_msg = (
                    f"**Cau {stt} - {question_id}**\n"
                    f"```\n"
                    f"Loai cau   : {type_display}\n"
                    f"{status_line}\n"
                    f"Bat dau    : {item_start_time}\n"
                    f"Ket thuc   : {item_end_time}\n"
                    f"Thoi gian  : {item_duration}\n"
                    f"```"
                )
                send_discord(discord_msg)
                
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
        elif self.path == '/batch_end':
            # Endpoint: Kết thúc phiên batch, ghi footer + TỰ ĐỘNG gửi Gmail + Discord
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                success_count = data.get('success_count', 0)
                total_count = data.get('total_count', 0)
                reason = data.get('reason', 'completed')  # 'completed' hoặc 'stopped'
                
                finalize_history(success_count, total_count)
                
                end_time = time.time()
                total_time_seconds = end_time - current_batch_start_time if current_batch_start_time > 0 else 0
                duration_str = format_duration(total_time_seconds)
                
                # Gửi tin nhắn Discord: Tổng kết phiên
                status_text = "DA DUNG GIUA CHUNG" if reason == 'stopped' else "HOAN TAT"
                failed_list_str = "Khong co cau nao bi loi."
                if current_failed_items:
                    failed_list_str = "\n".join([item['id'] for item in current_failed_items])
                
                discord_msg = (
                    f"**== {status_text} ==**\n"
                    f"```\n"
                    f"Ket qua    : {success_count}/{total_count}\n"
                    f"Thanh cong : {success_count}\n"
                    f"That bai   : {total_count - success_count}\n"
                    f"Thoi gian  : {duration_str}\n"
                    f"Hoan thanh : {time.strftime('%d/%m/%Y %H:%M:%S')}\n"
                    f"```\n"
                    f"**Danh sach cau loi (de bien tap lai):**\n"
                    f"```\n"
                    f"{failed_list_str}\n"
                    f"```"
                )
                send_discord(discord_msg)
                
                # Tự động gửi Gmail thông báo (GIỮ ICON cho email)
                if reason == 'stopped':
                    subject = f"[Auto Edit Tool] ⛔ ĐÃ DỪNG - {success_count}/{total_count} ID - {time.strftime('%d/%m/%Y %H:%M')}"
                    body = f"Quy trình đã bị DỪNG giữa chừng!\n\n"
                else:
                    subject = f"[Auto Edit Tool] ✅ Hoàn tất {success_count}/{total_count} ID - {time.strftime('%d/%m/%Y %H:%M')}"
                    body = f"Quy trình đã hoàn tất!\n\n"
                
                body += f"📊 Kết quả: {success_count}/{total_count}\n"
                body += f"✅ Thành công: {success_count}\n"
                body += f"❌ Thất bại: {total_count - success_count}\n"
                body += f"⏱️ Tổng thời gian: {duration_str}\n"
                body += f"⏰ Thời điểm: {time.strftime('%d/%m/%Y %H:%M:%S')}\n"
                body += f"\n📁 File history: {current_history_file}\n"
                
                if current_failed_items:
                    body += f"\n❌ Danh sách câu lỗi:\n"
                    for item in current_failed_items:
                        body += f"  - {item['id']}\n"
                
                email_sent = send_gmail_notification(subject, body)
                
                self.wfile.write(json.dumps({
                    "status": "success",
                    "message": f"Hoàn tất {success_count}/{total_count}",
                    "email_sent": email_sent
                }).encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == '/capture':
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            try:
                img = ImageGrab.grab(bbox=CAPTURE_BBOX)
                output = io.BytesIO()
                img.convert("RGB").save(output, "BMP")
                data = output.getvalue()[14:]
                
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                win32clipboard.CloseClipboard()
                
                self.wfile.write(json.dumps({"status": "success", "message": "Đã chụp và lưu vào Clipboard"}).encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
        elif self.path.startswith('/logs'):
            # Endpoint: Frontend poll log mới
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Parse query param ?after=<id>
            after_id = 0
            try:
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                after_id = int(params.get('after', [0])[0])
            except:
                pass
            
            with _log_lock:
                new_logs = [entry for entry in _log_buffer if entry['id'] > after_id]
            
            self.wfile.write(json.dumps({"logs": new_logs}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def prevent_sleep():
    """Ngăn máy tính Windows tự động chuyển sang chế độ Sleep."""
    # ES_CONTINUOUS (0x80000000) kết hợp với ES_SYSTEM_REQUIRED (0x00000001)
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)

def allow_sleep():
    """Cho phép máy tính ngủ lại bình thường sau khi tool chạy xong."""
    # Chỉ gọi ES_CONTINUOUS (0x80000000) để reset trạng thái
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)

if __name__ == '__main__':
    prevent_sleep()
    
    server = ThreadingHTTPServer(('localhost', 5050), CaptureHandler)
    log("=" * 60, "INFO")
    log("SERVER TU DONG CHUOT (PYAUTOGUI) DANG CHAY", "INFO")
    log("Vui long giu trinh duyet mo tren man hinh (khong bi che day).", "INFO")
    log("He thong da duoc thiet lap de CHONG NGU (Anti-Sleep) trong luc chay.", "INFO")
    log("Da kich hoat THEO DOI QUA DISCORD", "OK")
    log("Bạn có thể sửa tọa độ chuột trong file capture_server.py", "INFO")
    log("=" * 60, "INFO")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Đang tắt server và cho phép máy tính ngủ lại bình thường...", "INFO")
    finally:
        allow_sleep()
