import io
import json
import time
import os
import smtplib
import threading
import requests
import base64
from urllib.parse import urlparse, parse_qs
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import win32clipboard
from PIL import ImageGrab, Image
import pyautogui
import pyperclip
import ctypes
import tkinter as tk

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

def draw_circle_overlay(x, y, radius=15, duration_sec=0.8, color="red"):
    """Vẽ một vòng tròn đỏ tạm thời tại (x, y) để chỉ thị điểm nhấp chuột."""
    def task():
        try:
            root = tk.Tk()
            root.overrideredirect(True)
            root.wm_attributes("-topmost", True)
            root.wm_attributes("-transparentcolor", "white")
            
            size = radius * 2 + 10
            pos_x = x - size // 2
            pos_y = y - size // 2
            root.geometry(f"{size}x{size}+{pos_x}+{pos_y}")
            
            canvas = tk.Canvas(root, width=size, height=size, bg="white", highlightthickness=0)
            canvas.pack()
            
            canvas.create_oval(5, 5, size - 5, size - 5, outline=color, width=3)
            root.after(int(duration_sec * 1000), root.destroy)
            root.mainloop()
        except:
            pass

    threading.Thread(target=task, daemon=True).start()

# ==============================================================================
# HỆ THỐNG LỚP HỖ TRỢ THEO NGUYÊN LÝ SOLID
# ==============================================================================

class GUIHelper:
    """
    Lớp hỗ trợ toàn bộ các thao tác giao diện người dùng (PyAutoGUI).
    Tuân thủ nguyên tắc Single Responsibility (SRP): Chỉ chịu trách nhiệm về tương tác GUI.
    """
    FCS_GEM_LMS = (1183, 603)      # Tọa độ focus trình duyệt chứa LMS và NBLM (Trái)
    FCS_ON_NBLM = (895, 401)       # Tọa độ focus NotebookLM
    FCS_ON_EDIT_LMS = (989, 544)   # Tọa độ focus giữa Modal Edit câu hỏi trên LMS
    FCS_LMS_CANCEL = (24, 702)     # Tọa độ focus an toàn để đóng modal bằng nút Cancel
    FCS_ON_GEM = (1607, 297)       # Tọa độ focus Gemini
    
    GEMINI_CHATBOX = (1526, 445)   # Tọa độ ô chat Gemini (Phải trên)
    GEMINI_SEND_BTN = (1872, 455)  # Tọa độ nút gửi của Gemini
    GEMINI_SEND_PIXEL = (1862, 469) # Tọa độ pixel kiểm tra nút Send của Gemini
    
    NBLM_CHATBOX = (530, 936)      # Tọa độ ô chat NotebookLM
    NBLM_SEND_BTN = (889, 922)     # Tọa độ nút gửi của NotebookLM
    NBLM_IDLE_COLOR = (245, 245, 245) # Màu gốc của nút gửi NBLM khi đã phản hồi xong
    
    GEMINI_COPY_REGION = (1294, 107, 585, 320) # Vùng tìm ảnh copy Gemini
    GEMINI_COPY_FALLBACK = (1482, 335)
    
    NBLM_COPY_REGION = (354, 447, 598, 455)    # Vùng tìm ảnh copy NotebookLM mới

    @classmethod
    def focus(cls, coords):
        """Lấy focus tại tọa độ chỉ định bằng một cú click chuột."""
        log(f"Lấy focus tại tọa độ: {coords}", "GUI")
        draw_circle_overlay(coords[0], coords[1], radius=15, duration_sec=0.8, color="red")
        pyautogui.moveTo(coords[0], coords[1])
        pyautogui.click()
        time.sleep(0.3)

    @classmethod
    def focus_gem_lms(cls):
        cls.focus(cls.FCS_GEM_LMS)

    @classmethod
    def focus_on_nblm(cls):
        cls.focus(cls.FCS_ON_NBLM)

    @classmethod
    def focus_on_edit_lms(cls):
        cls.focus(cls.FCS_ON_EDIT_LMS)

    @classmethod
    def focus_lms_cancel(cls):
        cls.focus(cls.FCS_LMS_CANCEL)

    @classmethod
    def scroll_down_strongly(cls, seconds=3.0):
        """Lăn chuột xuống dưới cùng liên tục trong khoảng thời gian chỉ định."""
        log(f"Lăn chuột xuống dưới mạnh mẽ trong {seconds} giây...", "GUI")
        start_roll = time.time()
        while time.time() - start_roll < seconds:
            pyautogui.scroll(-5000)
            time.sleep(0.05)

    @classmethod
    def tab_swap(cls, direction="forward"):
        """Đảo tab trình duyệt bằng phím tắt."""
        if direction == "forward":
            log("Chuyển tab kế tiếp (Ctrl + Tab)...", "GUI")
            pyautogui.hotkey('ctrl', 'tab')
        else:
            log("Chuyển tab phía trước (Ctrl + Shift + Tab)...", "GUI")
            pyautogui.hotkey('ctrl', 'shift', 'tab')
        time.sleep(0.5)

    @classmethod
    def check_nblm_done(cls):
        """Kiểm tra xem NotebookLM đã phản hồi xong chưa dựa vào màu pixel nút Send."""
        return pyautogui.pixelMatchesColor(cls.NBLM_SEND_BTN[0], cls.NBLM_SEND_BTN[1], cls.NBLM_IDLE_COLOR, tolerance=10)

    @classmethod
    def cancel_modal(cls):
        """Quy trình hủy/đóng modal soạn thảo LMS an toàn bằng phím ESC."""
        log("Bắt đầu quy trình đóng modal hủy bỏ (Cancel)...", "ACTION")
        try:
            cls.focus_on_edit_lms()
            pyautogui.press('esc')
            time.sleep(0.5)
            cls.focus_lms_cancel()
            pyautogui.press('esc')
            log("Đã đóng modal hủy bỏ thành công bằng ESC.", "OK")
        except Exception as e:
            log(f"Lỗi khi đóng modal: {e}", "WARN")


class ClipboardHelper:
    """
    Lớp hỗ trợ thao tác với Windows Clipboard.
    SRP: Chỉ chịu trách nhiệm trao đổi dữ liệu qua Clipboard.
    """
    @staticmethod
    def copy_text(text):
        """Sao chép văn bản vào clipboard."""
        pyperclip.copy(text)

    @staticmethod
    def paste_text():
        """Lấy văn bản từ clipboard."""
        try:
            return pyperclip.paste()
        except:
            return ""

    @staticmethod
    def write_base64_image(img_base64):
        """Giải mã ảnh base64 và lưu vào clipboard dưới định dạng CF_DIB."""
        try:
            if ',' in img_base64:
                img_base64 = img_base64.split(',')[1]
            img_data = base64.b64decode(img_base64)
            img = Image.open(io.BytesIO(img_data))
            
            output = io.BytesIO()
            img.convert("RGB").save(output, "BMP")
            data_bmp = output.getvalue()[14:]
            
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data_bmp)
            win32clipboard.CloseClipboard()
            log("Đã lưu ảnh base64 giải mã vào Clipboard thành công.", "OK")
            return True
        except Exception as e:
            log(f"Lỗi khi ghi ảnh base64 vào Clipboard: {e}", "ERROR")
            return False


class LMSBroker:
    """
    Lớp giao tiếp trung gian với Tampermonkey Extension (LMS).
    SRP: Chỉ chịu trách nhiệm quản lý hàng đợi và bắt kết quả từ trình duyệt.
    """
    @staticmethod
    def search(question_id):
        log(f"Gửi lệnh tìm kiếm ID {question_id} cho Tampermonkey...", "LMS")
        session_id, evt = enqueue_lms_command('search', {'id': question_id})
        return wait_for_lms_result(session_id, timeout=30)

    @staticmethod
    def capture():
        log("Gửi lệnh chụp ảnh câu hỏi cho Tampermonkey...", "LMS")
        session_id, evt = enqueue_lms_command('capture')
        return wait_for_lms_result(session_id, timeout=30)

    @staticmethod
    def edit():
        log("Gửi lệnh mở Edit (2 bút chì) cho Tampermonkey...", "LMS")
        session_id, evt = enqueue_lms_command('edit')
        return wait_for_lms_result(session_id, timeout=30)

    @staticmethod
    def autofill(parsed_data):
        log("Gửi lệnh điền autofill siêu việt cho Tampermonkey...", "LMS")
        session_id, evt = enqueue_lms_command('autofill', parsed_data)
        return session_id

# ==========================================
# HỆ THỐNG LOG TẬP TRUNG
# ==========================================
_log_buffer = []
_log_lock = threading.Lock()
_log_counter = 0

# Hàng đợi lệnh LMS và event mapping để giao tiếp bất đồng bộ với Tampermonkey
lms_queues = {
    'findopen': [],
    'autofill': []
}
lms_event_map = {}
lms_lock = threading.Lock()

def enqueue_lms_command(action, payload=None):
    global lms_queues, lms_event_map
    session_id = int(time.time() * 1000)
    evt = threading.Event()
    
    # Lệnh search, capture, edit -> findopen; lệnh autofill -> autofill
    tool = 'autofill' if action == 'autofill' else 'findopen'
    
    with lms_lock:
        lms_event_map[session_id] = {
            'event': evt,
            'result': None
        }
        lms_queues[tool].append({
            'action': action,
            'session': session_id,
            'payload': payload
        })
    return session_id, evt

def wait_for_lms_result(session_id, timeout=30):
    global lms_event_map
    evt_data = None
    with lms_lock:
        evt_data = lms_event_map.get(session_id)
    if evt_data:
        success = evt_data['event'].wait(timeout=timeout)
        with lms_lock:
            res = lms_event_map.pop(session_id, None)
        if success and res:
            return res['result']
    return None

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

def create_history_file(total_ids, custom_filename=None):
    """Tạo file history mới và ghi header."""
    global current_history_file, current_batch_start_time, current_failed_items
    current_batch_start_time = time.time()
    current_failed_items = []
    
    if custom_filename and custom_filename.strip():
        filename = custom_filename.strip()
        if not filename.endswith('.txt'):
            filename += '.txt'
        filename = os.path.basename(filename)
    else:
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
GEMINI_CHATBOX_X = 1526
GEMINI_CHATBOX_Y = 445

# 5. Tọa độ nút Send của Gemini (Dùng để check màu xanh)
GEMINI_SEND_BTN_X = 1872
GEMINI_SEND_BTN_Y = 455
GEMINI_SEND_PIXEL_X = 1862
GEMINI_SEND_PIXEL_Y = 469

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
NBLM_COPY_REGION = (354, 447, 598, 455) # Vùng tìm ảnh copy NotebookLM mới

# ==========================================

CURRENT_TAB = 'LMS'

def fallback_cancel_routine():
    global CURRENT_TAB
    log(f"CHẠY QUY TRÌNH HỦY KHẨN CẤP (FALLBACK CANCEL) - ĐANG Ở TAB: {CURRENT_TAB}", "ACTION")
    try:
        if CURRENT_TAB == 'NBLM':
            log("Đang ở NBLM, quay lại tab LMS...", "ACTION")
            pyautogui.hotkey('ctrl', 'shift', 'tab')
            time.sleep(0.5)
            CURRENT_TAB = 'LMS'
            
        GUIHelper.cancel_modal()
        log("Đã hoàn tất quy trình hủy khẩn cấp, sẵn sàng cho ID tiếp theo!", "OK")
    except Exception as e:
        log(f"Lỗi trong quy trình hủy khẩn cấp: {e}", "ERROR")

class CaptureHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-type')
        self.end_headers()

    def do_POST(self):
        global STOP_FLAG, CURRENT_TAB
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        if path == '/stop':
            STOP_FLAG = True
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "Đã ra lệnh dừng quy trình."}).encode('utf-8'))
            return
        if path == '/lms/poll':
            tool = query_params.get('tool', ['findopen'])[0]
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            cmd = None
            with lms_lock:
                queue = lms_queues.get(tool, [])
                if len(queue) > 0:
                    cmd = queue.pop(0)
            
            self.wfile.write(json.dumps({"command": cmd} if cmd else {}).encode('utf-8'))
            return
            
        if path == '/lms/done':
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                res_data = json.loads(post_data.decode('utf-8'))
                session_id = res_data.get('session')
                with lms_lock:
                    if session_id in lms_event_map:
                        lms_event_map[session_id]['result'] = res_data
                        lms_event_map[session_id]['event'].set()
            except Exception as e:
                log(f"Lỗi done lms: {e}", "ERROR")
                
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            return

        if path == '/search_id':
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
                log(f"=== BẮT ĐẦU XỬ LÝ ID: {question_id} ===", "STATUS")
                
                # 1. Gọi Tampermonkey qua DOM để tìm kiếm ID (Không scroll, click thẳng input)
                log(f"Tìm kiếm ID {question_id} trên LMS...", "STATUS")
                res_search = LMSBroker.search(question_id)
                if not res_search or res_search.get('error'):
                    err = res_search.get('error') if res_search else "Timeout tìm kiếm ID"
                    raise Exception(f"Lỗi tìm kiếm ID: {err}")
                log("Đã tìm thấy câu hỏi trên LMS.", "OK")
                
                # 2. Gọi Tampermonkey qua DOM để chụp ảnh câu hỏi dạng base64
                log("Đang chụp ảnh câu hỏi bằng Tampermonkey...", "STATUS")
                res_capture = LMSBroker.capture()
                if not res_capture or res_capture.get('error') or 'image' not in res_capture:
                    err = res_capture.get('error') if res_capture else "Timeout chụp ảnh"
                    raise Exception(f"Lỗi chụp ảnh: {err}")
                
                img_b64 = res_capture['image']
                if not ClipboardHelper.write_base64_image(img_b64):
                    raise Exception("Không thể lưu ảnh chụp vào Clipboard!")
                
                # 3. Gọi Tampermonkey qua DOM để mở chế độ sửa (Click 2 lần cây bút)
                # Bắt đầu bất đồng bộ, Python không chờ mà tiến hành dán Gemini ngay
                log("Gửi lệnh mở Edit (2 bút chì) cho Tampermonkey...", "STATUS")
                session_id_edit, evt_edit = enqueue_lms_command('edit')

                # Lưu màu rảnh rỗi động của Gemini trước khi dán ảnh
                try:
                    gemini_idle_color = pyautogui.pixel(GUIHelper.GEMINI_SEND_PIXEL[0], GUIHelper.GEMINI_SEND_PIXEL[1])
                    log(f"Đã lưu màu rảnh rỗi của Gemini: {gemini_idle_color}", "OK")
                except Exception as e:
                    gemini_idle_color = None
                    log(f"Không thể đọc màu rảnh rỗi động của Gemini: {e}", "WARN")

                # 4. Tranh thủ thời gian đợi LMS load -> Đi qua Gemini (Phải) dán ảnh
                log("Tranh thủ chuyển sang dán ảnh vào Gemini...", "STATUS")
                GUIHelper.focus(GUIHelper.GEMINI_CHATBOX)
                pyautogui.hotkey('ctrl', 'v')
                
                # Chờ đúng 3s để Gemini load ảnh xong theo yêu cầu
                log("Chờ đúng 3s để Gemini load ảnh...", "STATUS")
                time.sleep(3.0)
                
                # Kiểm tra màu pixel tại GEMINI_SEND_PIXEL xem đã khớp với màu rảnh rỗi chưa
                log("Kiểm tra trạng thái load ảnh bằng pixel check...", "STATUS")
                load_ok = False
                if gemini_idle_color:
                    for _ in range(14): # Poll tối đa 7s (14 * 0.5s)
                        try:
                            if pyautogui.pixelMatchesColor(GUIHelper.GEMINI_SEND_PIXEL[0], GUIHelper.GEMINI_SEND_PIXEL[1], gemini_idle_color, tolerance=15):
                                load_ok = True
                                log("Phát hiện Gemini đã load ảnh xong (Khớp màu Send rảnh rỗi)!", "OK")
                                break
                        except Exception:
                            pass
                        time.sleep(0.5)
                
                if not load_ok:
                    log("Không thấy màu Send rảnh rỗi khớp, tiến hành bấm Enter cưỡng bức...", "WARN")

                # Bấm enter gửi ảnh
                pyautogui.press('enter')
                log("Đã gửi ảnh lên Gemini.", "OK")
                
                # 5. Chờ Tampermonkey mở hoàn tất modal soạn thảo (Edit) trên LMS
                log("Chờ Tampermonkey mở hoàn tất modal soạn thảo (Pencil 2)...", "STATUS")
                res_edit = wait_for_lms_result(session_id_edit, timeout=30)
                if not res_edit or res_edit.get('error'):
                    err = res_edit.get('error') if res_edit else "Timeout mở modal soạn thảo"
                    raise Exception(f"Lỗi mở modal Edit: {err}")
                log("Tampermonkey đã mở modal soạn thảo thành công.", "OK")
                msg_extra = "Đã tìm & mở Edit (DOM) | Đã gửi Gemini."

                # 6. Đợi Gemini xử lý xong (5s sau khi nhấn Enter + check màu rảnh rỗi)
                log("Chờ Gemini xử lý phản hồi (nghỉ 5s)...", "STATUS")
                time.sleep(5.0)
                
                log("Kiểm tra xem Gemini đã phản hồi xong chưa...", "STATUS")
                gemini_done = False
                if gemini_idle_color:
                    for _ in range(20): # Poll tối đa 10s (20 * 0.5s)
                        try:
                            if pyautogui.pixelMatchesColor(GUIHelper.GEMINI_SEND_PIXEL[0], GUIHelper.GEMINI_SEND_PIXEL[1], gemini_idle_color, tolerance=15):
                                gemini_done = True
                                log("Phát hiện Gemini đã phản hồi xong (Khớp màu Send rảnh rỗi)!", "OK")
                                break
                        except Exception:
                            pass
                        time.sleep(0.5)
                
                if not gemini_done:
                    log("Hết 10s kiểm tra màu nhưng chưa khớp, vẫn tiến hành quy trình lấy output...", "WARN")
                
                # Lấy focus tại FCS_ON_GEM trước khi gửi phím End
                log("Focus vào vùng Gemini (FCS_ON_GEM) để chuẩn bị copy...", "ACTION")
                GUIHelper.focus(GUIHelper.FCS_ON_GEM)
                time.sleep(0.1)
                
                # Bấm phím End lần 1
                log("Nhấn phím End lần 1...", "ACTION")
                pyautogui.press('end')
                time.sleep(1.0) # Đợi đúng 1.0s
                
                # Tìm nút Copy Gemini lần 1
                log("Tìm nút Copy Gemini (Lần 1)...", "SEARCH")
                copy_pos = None
                for _ in range(25): # Thử quét trong 2.5s
                    try:
                        copy_pos = pyautogui.locateCenterOnScreen('gemini_copy.png', region=GUIHelper.GEMINI_COPY_REGION, confidence=0.8)
                        if copy_pos:
                            break
                    except Exception:
                        pass
                    time.sleep(0.1)
                
                if not copy_pos:
                    log("Không tìm thấy nút Copy lần 1. Nhấn phím End lần 2...", "WARN")
                    pyautogui.press('end')
                    time.sleep(1.0) # Đợi tiếp 1.0s
                    
                    log("Tìm nút Copy Gemini (Lần 2)...", "SEARCH")
                    for _ in range(25): # Thử quét tiếp trong 2.5s
                        try:
                            copy_pos = pyautogui.locateCenterOnScreen('gemini_copy.png', region=GUIHelper.GEMINI_COPY_REGION, confidence=0.8)
                            if copy_pos:
                                break
                        except Exception:
                            pass
                        time.sleep(0.1)
                
                if copy_pos:
                    pyautogui.click(copy_pos)
                    log("Đã click nút Copy của Gemini.", "OK")
                    msg_extra += " | Đã Copy kết quả Gemini."
                    
                    # Refresh Gemini
                    time.sleep(0.5)
                    pyautogui.press('f5')
                    log("Đã bấm F5 tải lại Gemini.", "ACTION")
                else:
                    raise Exception("Không tìm thấy nút Copy của Gemini sau 2 lần bấm End!")

                # 7. Chuyển sang NotebookLM để dán gửi
                log("Focus lại cửa sổ chứa LMS & NBLM (Fcs_Gem_LMS)...", "ACTION")
                GUIHelper.focus(GUIHelper.FCS_GEM_LMS)
                
                log("Chuyển sang tab NotebookLM (Ctrl + Tab)...", "ACTION")
                GUIHelper.tab_swap(direction="forward")
                CURRENT_TAB = 'NBLM'
                
                # Đợi NBLM load ổn định (nút Send hiện màu gốc)
                log("Đang kiểm tra xem NotebookLM đã load xong chưa...", "STATUS")
                for _ in range(10):
                    if GUIHelper.check_nblm_done():
                        log("NotebookLM đã sẵn sàng!", "STATUS")
                        break
                    time.sleep(0.5)
                
                # Click vào ô chat NotebookLM và dán gửi
                pyautogui.click(GUIHelper.NBLM_CHATBOX[0], GUIHelper.NBLM_CHATBOX[1])
                time.sleep(0.3)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.3)
                pyautogui.press('enter')
                log("Đã dán và gửi nội dung vào NotebookLM.", "OK")
                msg_extra += " | Đã gửi NBLM."

                # Sau khi gửi xong, lập tức lấy focus tại FCS_ON_NBLM
                log("Lập tức focus NotebookLM (FCS_ON_NBLM)...", "ACTION")
                GUIHelper.focus(GUIHelper.FCS_ON_NBLM)

                # Sau đó đợi cứng 10s rồi mới bắt đầu quy trình đảo tab
                log("Đợi cứng 10s sau khi gửi NotebookLM...", "STATUS")
                time.sleep(10.0)
                
                nblm_done = False
                # Vòng lặp tối đa 10 chu kỳ đảo tab (Không lấy focus gì nữa trong suốt quá trình này)
                for cycle in range(10):
                    if STOP_FLAG:
                        raise Exception("Bị dừng bởi người dùng!")
                    
                    log(f"Kiểm tra trạng thái NotebookLM (Chu kỳ {cycle + 1}/10)...", "STATUS")
                    # Ở lại NBLM tối đa 60s để theo dõi pixel nút send
                    for _ in range(120): # 120 * 0.5s = 60s
                        if GUIHelper.check_nblm_done():
                            nblm_done = True
                            log("NotebookLM đã hoàn tất xử lý!", "OK")
                            break
                        time.sleep(0.5)
                    
                    if nblm_done:
                        break
                    
                    # Nếu hết 60s chưa xong, đảo sang tab LMS 3s chống timeout
                    log("Chưa hoàn tất, đảo sang tab LMS 3s chống timeout...", "STATUS")
                    GUIHelper.tab_swap(direction="backward")
                    CURRENT_TAB = 'LMS'
                    
                    for _ in range(3):
                        if STOP_FLAG:
                            raise Exception("Bị dừng bởi người dùng!")
                        time.sleep(1.0)
                    
                    # Quay lại NBLM (chỉ đảo tab, không lấy focus)
                    log("Quay lại NotebookLM...", "STATUS")
                    GUIHelper.tab_swap(direction="forward")
                    CURRENT_TAB = 'NBLM'
                    time.sleep(1.0) # Chờ render tab
                
                if not nblm_done:
                    raise Exception("Chờ quá lâu mà NotebookLM không phản hồi (Timeout 10 chu kỳ)!")

                # 9. Lấy Output của NotebookLM
                log("Focus NotebookLM (FCS_ON_NBLM) trước khi nhấn End...", "ACTION")
                GUIHelper.focus(GUIHelper.FCS_ON_NBLM)
                time.sleep(0.1)

                # Bấm phím End lần 1
                log("Nhấn phím End lần 1...", "ACTION")
                pyautogui.press('end')
                time.sleep(1.0) # Đợi đúng 1.0s
                
                # Tìm nút Copy NBLM lần 1
                log("Tìm nút Copy NotebookLM (Lần 1)...", "SEARCH")
                nblm_copy_pos = None
                for _ in range(30):
                    try:
                        nblm_copy_pos = pyautogui.locateCenterOnScreen('notebooklm_copy.png', region=GUIHelper.NBLM_COPY_REGION, confidence=0.8)
                        if nblm_copy_pos:
                            break
                    except Exception:
                        pass
                    time.sleep(0.1)
                
                if not nblm_copy_pos:
                    log("Không tìm thấy nút Copy NBLM lần 1. Nhấn phím End lần 2...", "WARN")
                    pyautogui.press('end')
                    time.sleep(1.0) # Đợi tiếp 1.0s
                    
                    log("Tìm nút Copy NotebookLM (Lần 2)...", "SEARCH")
                    for _ in range(30):
                        try:
                            nblm_copy_pos = pyautogui.locateCenterOnScreen('notebooklm_copy.png', region=GUIHelper.NBLM_COPY_REGION, confidence=0.8)
                            if nblm_copy_pos:
                                break
                        except Exception:
                            pass
                        time.sleep(0.1)
                
                if nblm_copy_pos:
                    pyautogui.click(nblm_copy_pos)
                    log("Đã click Copy từ NotebookLM.", "OK")
                    msg_extra += " | Đã Copy từ NBLM."
                    time.sleep(0.5)
                    
                    # Chuyển tab về LMS ngay lập tức
                    log("Quay lại tab LMS ngay sau khi copy (Ctrl + Shift + Tab)...", "ACTION")
                    GUIHelper.tab_swap(direction="backward")
                    CURRENT_TAB = 'LMS'
                    time.sleep(0.5)
                else:
                    raise Exception("Không tìm thấy nút Copy của NotebookLM sau 2 lần bấm End!")

                # Đọc kết quả từ Clipboard trả về cho index.html
                copied_text = ClipboardHelper.paste_text()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "message": f"ID: {question_id} - {msg_extra}",
                    "notebook_output": copied_text
                }).encode('utf-8'))

            except Exception as e:
                log(f"LỖI HỆ THỐNG TẠI SEARCH_ID: {e}", "ERROR")
                if not STOP_FLAG:
                    fallback_cancel_routine()
                self.wfile.write(json.dumps({"status": "error", "message": f"Lỗi: {str(e)}"}).encode('utf-8'))

        elif path == '/paste_lms':
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                parsed_data = data.get('parsed_data', {})
                type_code = parsed_data.get('typeCode', 'UNKNOWN')
                
                log(f"Nhận lệnh điền LMS với dạng câu: {type_code}", "ACTION")
                
                # Đưa chuỗi JSON vào Clipboard để sẵn sàng dán
                json_str = json.dumps(parsed_data, ensure_ascii=False)
                ClipboardHelper.copy_text(json_str)
                
                # Click vào nút dán 1 lần duy nhất tại tọa độ (649, 147)
                log("Click nút dán tại tọa độ (649, 147)...", "ACTION")
                pyautogui.click(x=649, y=147)
                
                # Chờ đợi Tampermonkey điền dữ liệu xong tùy theo loại câu
                if type_code == 'DIEN_DAPAN':
                    wait_time = 7.0
                else: # TRAC_NGHIEM hoặc DUNG_SAI
                    wait_time = 14.0
                    
                log(f"Chờ {wait_time} giây để Tampermonkey hoàn tất điền dữ liệu...", "STATUS")
                time.sleep(wait_time)
                
                # Thực hiện hàm cancel an toàn để đóng modal
                fallback_cancel_routine()
                
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
                
            except Exception as e:
                log(f"LỖI TẠI PASTE_LMS: {e}", "ERROR")
                fallback_cancel_routine()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
        elif path == '/test_search_id':
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
        elif path == '/batch_start':
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
                custom_filename = data.get('custom_filename')
                
                filepath = create_history_file(total_ids, custom_filename)
                
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
        elif path == '/batch_item_start':
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
        elif path == '/batch_log':
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
        elif path == '/batch_end':
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
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        if path == '/capture':
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
        elif path.startswith('/logs'):
            # Endpoint: Frontend poll log mới
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Parse query param ?after=<id>
            after_id = 0
            try:
                params = parse_qs(parsed_url.query)
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
