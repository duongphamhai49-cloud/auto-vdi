# Viết lại Auto Edit Tool — 3 Tampermonkey Scripts + Python Orchestrator

## Vấn đề & Ràng buộc

| Ràng buộc | Giải thích |
|---|---|
| NotebookLM **phải giữ** | Đã train nhiều tháng, không thể thay API |
| Gemini custom Gem **phải giữ** | Prompt tùy chỉnh, nhận ảnh |
| Câu hỏi **có hình ảnh** | Bắt buộc chụp ảnh gửi Gemini |
| LMS **chặn F12/incognito** | Tampermonkey vẫn hoạt động (không phải DevTools) |
| RAM **8GB (1GB free)** | Không đủ cho VM |

## Giải pháp: 3 Tampermonkey Scripts

Thay vì PyAutoGUI điều khiển chuột/phím **thật**, ta dùng 3 Tampermonkey userscript chạy **trực tiếp trên DOM** của từng trang:

```
                    Python Server (localhost:5050)
                    ┌────────────────────────┐
                    │   ORCHESTRATOR         │
                    │                        │
                    │  Hàng đợi lệnh:       │
                    │  ┌──────────────────┐  │
                    │  │ LMS: search X    │  │
                    │  │ GEMINI: send img │  │
                    │  │ NBLM: send text  │  │
                    │  │ LMS: fill data   │  │
                    │  └──────────────────┘  │
                    │                        │
                    │  Lưu trữ tạm:         │
                    │  - Ảnh chụp câu hỏi   │
                    │  - Text từ Gemini      │
                    │  - Text từ NBLM        │
                    └───┬──────┬──────┬──────┘
                        │      │      │
              GET /poll │      │      │ GET /poll
              POST /done│      │      │ POST /done
                        │      │      │
              ┌─────────┴┐ ┌───┴────┐ ┌┴──────────┐
              │Tampermonkey│ │Tamper- │ │Tampermonkey│
              │  trên LMS │ │monkey  │ │ trên NBLM │
              │           │ │trên    │ │           │
              │·Tìm kiếm  │ │Gemini  │ │·Dán text  │
              │·Chụp DOM  │ │        │ │·Bấm gửi  │
              │·Click Edit│ │·Dán ảnh│ │·Chờ xong  │
              │·Điền form │ │·Bấm gửi│ │·Copy text │
              │·Checkbox  │ │·Chờ xong│ │·Báo server│
              │·Cập nhật  │ │·Copy   │ │           │
              │·Báo server│ │·Báo svr│ │           │
              └───────────┘ └────────┘ └───────────┘
                 Tab 1        Tab 2      Tab 3

     → Chuột/phím thật KHÔNG BỊ CHIẾM
     → Tất cả chạy qua DOM manipulation
     → Bạn dùng laptop BÌNH THƯỜNG
```

## User Review Required

> [!IMPORTANT]
> **Chụp ảnh câu hỏi:** Tool hiện dùng `ImageGrab.grab()` (chụp pixel màn hình). Phương án mới sẽ dùng **`html2canvas`** (chụp DOM element thành ảnh) chạy trong Tampermonkey. Ảnh capture từ DOM có thể hơi khác so với ảnh chụp pixel (font rendering, CSS...). Cần test xem Gemini có đọc được hay không.

> [!IMPORTANT]
> **Gửi ảnh cho Gemini qua Tampermonkey:** Đây là thách thức kỹ thuật lớn nhất. Ta sẽ dùng cơ chế **File Upload simulation** — tìm nút upload trên Gemini, tự động bơm file ảnh vào. Nếu không được, sẽ dùng **Clipboard API + Paste event simulation**. Cần test trên trang Gemini thật.

> [!WARNING]
> **Rủi ro: Google anti-bot.** Tampermonkey thao tác DOM trên Gemini/NotebookLM. Google CÓ THỂ phát hiện hành vi tự động và yêu cầu CAPTCHA hoặc chặn. Tuy nhiên, Tampermonkey khác với Selenium — nó chạy như extension hợp pháp, khó bị phát hiện hơn nhiều.

> [!WARNING]
> **Rủi ro: DOM selector thay đổi.** Google thường xuyên cập nhật giao diện Gemini/NotebookLM. Khi Google đổi HTML, Tampermonkey script có thể bị lỗi và cần cập nhật selector.

## Open Questions

> [!IMPORTANT]
> 1. **Trên trang Gemini Gem của bạn, có nút upload file (📎 hoặc +) không?** Hay chỉ paste ảnh vào chat? — Cần biết để chọn cách gửi ảnh.
> 2. **Trang NotebookLM: Ô chat của bạn có selector cụ thể không?** (ví dụ: `textarea`, `div[contenteditable]`...)
> 3. **Khi Gemini trả lời xong, dấu hiệu nhận biết là gì trên DOM?** (Nút "Copy" xuất hiện? Nội dung ngừng thay đổi? Loading spinner biến mất?)
> 4. **Tương tự cho NotebookLM: Khi NBLM trả lời xong, dấu hiệu DOM là gì?**

---

## Proposed Changes

### Component 1: Tampermonkey Script — LMS (`lms_automation.user.js`)

#### [NEW] lms_automation.user.js

**`@match`**: `https://*.lotuslms.com/*`, `https://daymai.vn/*`

**Chức năng:**

```
1. KHỞI ĐỘNG
   - Inject html2canvas library (CDN)
   - Bắt đầu poll server: GET localhost:5050/lms/poll mỗi 2s
   - Hiển thị badge trạng thái trên góc trang

2. LỆNH "search" — Tìm kiếm ID
   - Tìm ô input search trên DOM
   - Set value = question_id
   - Trigger event 'input' + 'change' + submit/enter
   - Chờ kết quả load (MutationObserver hoặc polling DOM)

3. LỆNH "capture" — Chụp câu hỏi
   - Tìm container câu hỏi trên DOM
   - Dùng html2canvas để chụp thành canvas
   - Convert canvas → blob → base64
   - POST base64 lên server: POST /lms/capture_done

4. LỆNH "edit" — Click nút Edit (cây bút)
   - document.querySelector cho nút pencil/edit
   - element.click() — DOM click, không phải mouse click
   - Chờ trang edit load xong

5. LỆNH "fill" — Điền form
   - Nhận JSON data từ server
   - Tìm tất cả .ql-editor trên trang
   - Dùng logic insertIntoQuill() (giữ nguyên từ v10.2)
   - Xử lý checkbox/radio (querySelector + click)
   - Điền 4 phương án (tìm ô edit cho mỗi option)

6. LỆNH "update" — Bấm Cập nhật
   - querySelector nút "Cập nhật"
   - element.click()
   - Chờ kết quả (success/fail popup)
   - Tự đóng dialog
   - POST kết quả lên server

7. LỆNH "cancel" — Hủy bỏ (fallback khi lỗi)
   - querySelector nút Cancel
   - click + chờ
```

---

### Component 2: Tampermonkey Script — Gemini (`gemini_automation.user.js`)

#### [NEW] gemini_automation.user.js

**`@match`**: `https://gemini.google.com/*`

**Chức năng:**

```
1. KHỞI ĐỘNG
   - Poll server: GET localhost:5050/gemini/poll mỗi 2s

2. LỆNH "send_image" — Gửi ảnh cho Gemini
   - Nhận ảnh base64 từ server
   - Convert base64 → Blob → File object
   
   Cách A: File Upload Simulation
   - Tìm nút upload (📎 hoặc +) → click
   - Tìm input[type="file"] ẩn → set files
   - Trigger event change

   Cách B: Clipboard Paste (fallback)
   - Viết blob vào clipboard: navigator.clipboard.write()
   - Focus vào chat input
   - Dispatch paste event
   
   Cách C: Drag & Drop (fallback 2)
   - Tạo DragEvent với file data
   - Dispatch lên chat area

   Sau khi ảnh đã vào chat:
   - Chờ ảnh load (preview xuất hiện)
   - Tìm nút Send → click (hoặc simulate Enter)

3. LỆNH "wait_and_copy" — Chờ + Copy kết quả
   - MutationObserver theo dõi chat container
   - Phát hiện "đang typing" → "đã xong" (loading state biến mất)
   - Hoặc: polling DOM, kiểm tra nội dung mới nhất ngừng thay đổi
   - Trích xuất text từ DOM element cuối cùng (response message)
   - POST text lên server: POST /gemini/done
   
4. LỆNH "reload" — Tải lại trang (tương tự F5 hiện tại)
   - location.reload()
```

---

### Component 3: Tampermonkey Script — NotebookLM (`nblm_automation.user.js`)

#### [NEW] nblm_automation.user.js

**`@match`**: `https://notebooklm.google.com/*`

**Chức năng:**

```
1. KHỞI ĐỘNG
   - Poll server: GET localhost:5050/nblm/poll mỗi 2s

2. LỆNH "send_text" — Gửi text vào chat NBLM
   - Nhận text từ server (text = kết quả Gemini)
   - Tìm ô chat input trên DOM
   - Set value / textContent
   - Trigger input event
   - Tìm nút Send → click

3. LỆNH "wait_and_copy" — Chờ + Copy kết quả
   - Tương tự Gemini script
   - MutationObserver / polling DOM
   - Phát hiện NBLM đã trả lời xong
   - Trích xuất text response
   - POST text lên server: POST /nblm/done
```

---

### Component 4: Python Server v2 (`capture_server.py`)

#### [MODIFY] capture_server.py

**Bỏ hoàn toàn:**
- `import pyautogui, pyperclip, PIL, win32clipboard, ctypes`
- Tất cả tọa độ chuột, region, pixel matching
- Tất cả `logged_*` wrapper
- `prevent_sleep()`, `allow_sleep()`
- `safe_sleep()`, `STOP_FLAG` logic cũ

**Vai trò mới: Pure HTTP Orchestrator**

```python
# Trạng thái toàn cục
command_queues = {
    'lms': [],      # Hàng đợi lệnh cho LMS Tampermonkey
    'gemini': [],   # Hàng đợi lệnh cho Gemini Tampermonkey
    'nblm': [],     # Hàng đợi lệnh cho NBLM Tampermonkey
}
data_store = {}     # Lưu trữ tạm (ảnh, text)
```

**Endpoints mới:**

| Endpoint | Mô tả |
|---|---|
| `GET /{agent}/poll` | Tampermonkey poll lệnh tiếp theo (LMS/Gemini/NBLM) |
| `POST /{agent}/done` | Tampermonkey báo hoàn thành + gửi data |
| `POST /queue_batch` | Frontend gửi danh sách ID để xử lý |
| `POST /stop` | Dừng khẩn cấp |
| `GET /logs` | Frontend poll log |
| `GET /status` | Trạng thái hiện tại |

**Flow xử lý 1 ID:**

```python
async def process_one_id(question_id):
    # Bước 1: Ra lệnh cho LMS tìm kiếm + chụp ảnh
    enqueue('lms', {'action': 'search', 'id': question_id})
    enqueue('lms', {'action': 'capture'})
    await wait_for('lms', 'capture_done')  # Chờ LMS báo xong
    
    # Bước 2: Ra lệnh cho LMS click Edit
    enqueue('lms', {'action': 'edit'})
    await wait_for('lms', 'edit_done')
    
    # Bước 3: Ra lệnh cho Gemini gửi ảnh
    image_b64 = data_store['captured_image']
    enqueue('gemini', {'action': 'send_image', 'image': image_b64})
    enqueue('gemini', {'action': 'wait_and_copy'})
    await wait_for('gemini', 'copy_done')  # Chờ Gemini trả lời
    
    # Bước 4: Ra lệnh cho NBLM gửi text
    gemini_text = data_store['gemini_response']
    enqueue('nblm', {'action': 'send_text', 'text': gemini_text})
    enqueue('nblm', {'action': 'wait_and_copy'})
    await wait_for('nblm', 'copy_done')  # Chờ NBLM trả lời
    
    # Bước 5: Parse kết quả NBLM (giữ nguyên logic hiện tại)
    nblm_text = data_store['nblm_response']
    parsed = parse_notebook_output(nblm_text)
    
    # Bước 6: Ra lệnh cho LMS điền form + cập nhật
    enqueue('lms', {'action': 'fill', 'data': parsed})
    await wait_for('lms', 'fill_done')
    
    enqueue('lms', {'action': 'update'})
    result = await wait_for('lms', 'update_done')
    
    # Bước 7: Ra lệnh Gemini reload
    enqueue('gemini', {'action': 'reload'})
    
    return result
```

**Giữ nguyên:**
- Hệ thống log (`_log_buffer`, endpoint `/logs`)
- History file (create, append, finalize)
- Discord webhook notification
- Gmail notification
- Batch processing logic (batch_start, batch_log, batch_end)

---

### Component 5: Frontend v2 (`index.html`)

#### [MODIFY] index.html

**Thay đổi:**
- Bỏ nút chụp ảnh, Snipping Tool (không cần)
- Bỏ nút Stop cũ (thay bằng POST /stop mới)
- Thay endpoint `/search_id` → `/queue_batch`
- Thêm hiển thị trạng thái 3 Tampermonkey (connected/disconnected)
- Giữ nguyên: danh sách ID, parse output, thanh tiến độ, history

**Thêm mới: Status bar**
```html
<div id="agent_status">
  <span id="lms_status">🔴 LMS</span>
  <span id="gemini_status">🔴 Gemini</span>
  <span id="nblm_status">🔴 NBLM</span>
</div>
```
Server track heartbeat từ mỗi Tampermonkey script. Frontend poll và hiển thị kết nối.

---

### Component 6: Start Script

#### [MODIFY] Start_Workspace.bat

```batch
@echo off
chcp 65001 >nul

echo Dang khoi dong Server...
cd /d "E:\Download\VDII\Auto_Edit_Tool"
start "Server" python capture_server.py
timeout /t 2 >nul

echo Dang mo cac tab...
start chrome --new-window ^
 "https://aeglobal.lotuslms.com/admin/content-manager/folder/..." ^
 "https://notebooklm.google.com/notebook/..." ^
 "file:///E:/Download/VDII/Auto_Edit_Tool/index.html"

timeout /t 1 >nul
start chrome --new-window ^
 "https://gemini.google.com/gem/507de5d07544"

exit
```

> [!NOTE]
> Không cần Google Sheets, Latex Editor, hay vị trí cửa sổ cụ thể nữa. Các tab có thể ở bất kỳ vị trí nào, kể cả bị che khuất.

---

## So sánh chi tiết

| Khía cạnh | Hiện tại (PyAutoGUI) | Mới (3 Tampermonkey) |
|---|---|---|
| Điều khiển LMS | Click pixel chuột | DOM querySelector + click() |
| Tìm nút Edit | Quét ảnh `pencil.png` | `querySelector('.edit-btn')` |
| Chụp câu hỏi | `ImageGrab.grab(bbox)` | `html2canvas(element)` |
| Gửi ảnh Gemini | Paste clipboard + Enter | File upload simulation |
| Chờ Gemini xong | Kiểm tra màu pixel nút | MutationObserver trên DOM |
| Copy từ Gemini | Quét ảnh `gemini_copy.png` | Extract `textContent` từ DOM |
| Gửi text NBLM | Paste clipboard + Enter | Set input.value + click Send |
| Chờ NBLM xong | Kiểm tra màu pixel nút | MutationObserver trên DOM |
| Điền form LMS | Click pencil → I-beam → paste | `insertIntoQuill()` (đã có!) |
| Tick checkbox | Quét ảnh checkbox → click pixel | `querySelector('input') + click()` |
| Bấm Cập nhật | Quét ảnh `update_btn.png` → click | `querySelector('.update-btn') + click()` |
| **Chuột/phím** | **❌ Bị chiếm hoàn toàn** | **✅ Tự do hoàn toàn** |
| **Dùng laptop** | **❌ KHÔNG THỂ** | **✅ BÌNH THƯỜNG** |
| **Tab phải hiện** | **❌ Bắt buộc** | **✅ Chạy nền OK** |

---

## Rủi ro & Giải pháp

| Rủi ro | Xác suất | Giải pháp |
|---|---|---|
| html2canvas chụp ảnh khác pixel | Trung bình | Test trước, điều chỉnh CSS capture |
| File upload Gemini không hoạt động | Trung bình | Có 3 phương án backup (upload, clipboard paste, drag-drop) |
| Google chặn automation | Thấp | Tampermonkey = extension hợp pháp, thêm random delay |
| DOM selector thay đổi | Thấp-TB | Dùng selector tổng quát, dễ cập nhật |
| Background tab bị throttle | Thấp | DOM operations không bị throttle, chỉ timer bị |

---

## Kế hoạch thực hiện

```
Giai đoạn 1: Nghiên cứu DOM (1-2 ngày)
├── Khảo sát DOM trang LMS edit
├── Khảo sát DOM trang Gemini (selector ô chat, nút upload, nút send)
├── Khảo sát DOM trang NotebookLM (selector ô chat, nút send)
└── Test html2canvas trên LMS

Giai đoạn 2: Server Orchestrator (1 ngày)
├── Viết lại capture_server.py (bỏ PyAutoGUI)
├── Implement command queue system
└── Implement poll/done endpoints

Giai đoạn 3: Tampermonkey LMS (2-3 ngày)
├── Viết lms_automation.user.js
├── Test search, capture, edit, fill, update
└── Integrate với server

Giai đoạn 4: Tampermonkey Gemini (1-2 ngày)
├── Viết gemini_automation.user.js
├── Test gửi ảnh + copy kết quả
└── Integrate với server

Giai đoạn 5: Tampermonkey NBLM (1-2 ngày)
├── Viết nblm_automation.user.js
├── Test gửi text + copy kết quả
└── Integrate với server

Giai đoạn 6: Test End-to-End (1-2 ngày)
├── Chạy 1 ID → kiểm tra flow
├── Chạy batch 5 ID
├── Test dùng laptop cùng lúc
└── Test edge cases
```

---

## Verification Plan

### Phase 1 - Từng component
- Mỗi Tampermonkey script test độc lập trước
- Kiểm tra server endpoints bằng curl/Postman

### Phase 2 - End-to-End
1. Chạy 1 ID đầu → kiểm tra kết quả trên LMS
2. Chạy 5 ID liên tiếp → batch flow
3. **Quan trọng nhất:** Trong khi tool chạy, mở tab mới lướt web/làm việc → xác nhận laptop hoạt động bình thường
4. Test dừng khẩn cấp
5. Kiểm tra Discord + Gmail notification
