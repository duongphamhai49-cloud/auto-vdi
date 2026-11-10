// ==UserScript==
// @name         LMS_NOTE
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Bảng ghi chú nổi chia 5 thẻ nháp chính (N1 - N5) cho web LMS (LotusLMS & Daymai) với giao diện kính mờ viền xanh sang trọng, tự động lưu và hỗ trợ copy nhanh.
// @author       PhamHaiDuong
// @match        https://*.lotuslms.com/*
// @match        http://*.lotuslms.com/*
// @match        https://daymai.vn/*
// @match        http://daymai.vn/*
// @include      *://*.lotuslms.com/*
// @include      *://daymai.vn/*
// @grant        GM_setClipboard
// @run-at       document-start
// ==/UserScript==

(function () {
    'use strict';

    console.log('[LMS_NOTE v1.0] Loaded on:', window.location.href);

    const STORAGE_KEY_SECTIONS = 'lms_quick_note_sections';
    const STORAGE_KEY_POS = 'lms_quick_note_pos';
    const STORAGE_KEY_STATE = 'lms_quick_note_state';
    const STORAGE_KEY_ACTIVE_TAB = 'lms_quick_note_active_tab';

    const SECTION_NAMES = [
        'Nháp 1',
        'Nháp 2',
        'Nháp 3',
        'Nháp 4',
        'Nháp 5'
    ];

    function getDisplayName(secName) {
        return secName.replace('Nháp ', 'N');
    }

    function injectNoteStyles() {
        if (document.getElementById('lms-note-styles')) return;
        const style = document.createElement('style');
        style.id = 'lms-note-styles';
        style.textContent = `
            .lms-hidden {
                display: none !important;
            }

            #lms-note-card {
                position: fixed !important;
                z-index: 2147483646 !important;
                width: 345px !important;
                height: 400px !important;
                min-width: 300px !important;
                min-height: 300px !important;
                max-width: 95vw !important;
                max-height: 95vh !important;
                resize: both !important;
                background: rgba(255, 255, 255, 0.25) !important;
                backdrop-filter: blur(14px) !important;
                -webkit-backdrop-filter: blur(14px) !important;
                border: 1.5px solid rgba(59, 130, 246, 0.5) !important;
                border-radius: 16px !important;
                box-shadow: 0 12px 32px rgba(15, 23, 42, 0.15), 0 0 0 1px rgba(15, 23, 42, 0.05) !important;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
                box-sizing: border-box !important;
            }

            #lms-note-header {
                padding: 10px 14px !important;
                background: rgba(241, 245, 249, 0.35) !important;
                border-bottom: 1px solid rgba(15, 23, 42, 0.08) !important;
                display: flex !important;
                align-items: center !important;
                justify-content: space-between !important;
                cursor: grab !important;
                user-select: none !important;
                flex-shrink: 0 !important;
            }

            #lms-note-header:active {
                cursor: grabbing !important;
            }

            .lms-note-title {
                font-size: 13.5px !important;
                font-weight: 700 !important;
                color: #0f172a !important;
                display: flex !important;
                align-items: center !important;
                gap: 6px !important;
                white-space: nowrap !important;
            }

            .lms-note-controls {
                display: flex !important;
                align-items: center !important;
                gap: 6px !important;
            }

            /* CẤU HÌNH NÚT ĐIỀU KHIỂN */
            .lms-note-btn {
                background: transparent !important;
                border: 1.2px solid rgba(100, 116, 139, 0.35) !important;
                color: #475569 !important;
                height: 28px !important;
                width: 32px !important;
                padding: 0 !important;
                border-radius: 8px !important;
                font-size: 13px !important;
                font-weight: 600 !important;
                cursor: pointer !important;
                transition: all 0.15s ease !important;
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                outline: none !important;
                user-select: none !important;
            }

            .lms-note-btn:active {
                transform: translateY(1px) scale(0.94) !important;
            }

            /* NÚT COPY (📋) - VIỀN XANH DƯƠNG */
            .lms-note-btn-copy {
                background: transparent !important;
                border: 1.2px solid #3b82f6 !important;
                color: #3b82f6 !important;
            }

            .lms-note-btn-copy:hover {
                background: #3b82f6 !important;
                color: #ffffff !important;
                box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3) !important;
            }

            /* NÚT XÓA SẠCH (🗑️) - VIỀN ĐỎ */
            .lms-note-btn-clear {
                background: transparent !important;
                border: 1.2px solid #ef4444 !important;
                color: #ef4444 !important;
            }

            .lms-note-btn-clear:hover {
                background: #ef4444 !important;
                color: #ffffff !important;
                box-shadow: 0 2px 8px rgba(239, 68, 68, 0.4) !important;
            }

            /* NÚT THU GỌN (➖) - VIỀN XÁM */
            .lms-note-btn-toggle {
                background: transparent !important;
                border: 1.2px solid #64748b !important;
                color: #64748b !important;
            }

            .lms-note-btn-toggle:hover {
                background: #64748b !important;
                color: #ffffff !important;
                box-shadow: 0 2px 8px rgba(100, 116, 139, 0.3) !important;
            }

            /* THANH MENU TABS HÀNG NGANG (N1 -> N5) */
            #lms-note-tabs {
                padding: 6px 8px !important;
                background: rgba(241, 245, 249, 0.25) !important;
                border-bottom: 1px solid rgba(15, 23, 42, 0.08) !important;
                display: flex !important;
                flex-wrap: nowrap !important;
                align-items: center !important;
                justify-content: space-between !important;
                gap: 5px !important;
                user-select: none !important;
                flex-shrink: 0 !important;
                overflow-x: auto !important;
            }

            #lms-note-tabs::-webkit-scrollbar {
                height: 3px !important;
            }

            #lms-note-tabs::-webkit-scrollbar-thumb {
                background: rgba(15, 23, 42, 0.12) !important;
                border-radius: 2px !important;
            }

            .lms-tab-btn {
                flex: 1 !important;
                min-width: 0 !important;
                background: rgba(255, 255, 255, 0.3) !important;
                color: #475569 !important;
                border: 1px solid rgba(15, 23, 42, 0.08) !important;
                border-radius: 6px !important;
                padding: 5px 2px !important;
                font-size: 12px !important;
                font-weight: 700 !important;
                cursor: pointer !important;
                transition: all 0.15s ease !important;
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                gap: 4px !important;
                white-space: nowrap !important;
                outline: none !important;
            }

            .lms-tab-btn:hover {
                background: rgba(219, 234, 254, 0.75) !important;
                color: #1e3a8a !important;
                border-color: #93c5fd !important;
            }

            .lms-tab-btn.active {
                background: #3b82f6 !important;
                color: #ffffff !important;
                border-color: #60a5fa !important;
                box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3) !important;
            }

            .lms-tab-dot {
                width: 5px !important;
                height: 5px !important;
                background: #10b981 !important;
                border-radius: 50% !important;
                display: inline-block !important;
                box-shadow: 0 0 5px #10b981 !important;
                flex-shrink: 0 !important;
            }

            /* NỘI DUNG GHI CHÚ ĐANG CHỌN */
            #lms-note-body {
                flex: 1 !important;
                display: flex !important;
                flex-direction: column !important;
                padding: 10px !important;
                gap: 8px !important;
                overflow: hidden !important;
                position: relative !important;
            }

            #lms-active-tab-bar {
                display: flex !important;
                align-items: center !important;
                justify-content: space-between !important;
                flex-shrink: 0 !important;
            }

            #lms-active-tab-title {
                font-size: 13px !important;
                font-weight: 700 !important;
                color: #0284c7 !important;
                display: flex !important;
                align-items: center !important;
                gap: 6px !important;
            }

            #lms-active-textarea {
                flex: 1 !important;
                width: 100% !important;
                height: 100% !important;
                background: rgba(255, 255, 255, 0.3) !important;
                color: #0f172a !important;
                border: 1px solid rgba(15, 23, 42, 0.1) !important;
                border-radius: 10px !important;
                padding: 10px 12px !important;
                font-size: 13.5px !important;
                line-height: 1.5 !important;
                font-family: inherit !important;
                resize: none !important;
                outline: none !important;
                box-sizing: border-box !important;
                transition: border-color 0.15s ease, background 0.15s ease !important;
            }

            #lms-active-textarea:focus {
                border-color: #3b82f6 !important;
                background: rgba(255, 255, 255, 0.6) !important;
            }

            #lms-active-textarea::-webkit-scrollbar {
                width: 6px !important;
            }

            #lms-active-textarea::-webkit-scrollbar-thumb {
                background: rgba(15, 23, 42, 0.15) !important;
                border-radius: 3px !important;
            }

            /* THÔNG BÁO TOAST NỔI */
            #lms-note-toast {
                position: absolute !important;
                bottom: 16px !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
                background: #10b981 !important;
                color: #ffffff !important;
                font-size: 11.5px !important;
                font-weight: 700 !important;
                padding: 6px 14px !important;
                border-radius: 12px !important;
                box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15) !important;
                display: none !important;
                pointer-events: none !important;
                z-index: 20 !important;
                white-space: nowrap !important;
            }

            /* NÚT THU GỌN BẢNG GHI CHÚ (MINIMIZED PILL - GRADIENT VÀNG CAM, CHỮ ĐEN) */
            #lms-note-min-btn {
                position: fixed !important;
                z-index: 2147483646 !important;
                height: 38px !important;
                padding: 0 18px !important;
                background: linear-gradient(135deg, #fbbf24 0%, #f97316 100%) !important;
                color: #0f172a !important;
                border: 1.5px solid rgba(255, 255, 255, 0.6) !important;
                border-radius: 19px !important;
                font-size: 13px !important;
                font-weight: 700 !important;
                cursor: grab !important;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 6px 20px rgba(249, 115, 22, 0.3) !important;
                outline: none !important;
                transition: transform 0.15s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.15s ease !important;
                user-select: none !important;
                -webkit-user-select: none !important;
            }

            #lms-note-min-btn:active {
                cursor: grabbing !important;
            }

            #lms-note-min-btn:hover {
                transform: translateY(-2px) scale(1.04) !important;
                box-shadow: 0 8px 24px rgba(249, 115, 22, 0.45) !important;
            }
        `;
        (document.head || document.documentElement).appendChild(style);
    }

    function createNoteCard() {
        if (document.getElementById('lms-note-card') || document.getElementById('lms-note-min-btn')) return;

        injectNoteStyles();

        const card = document.createElement('div');
        card.id = 'lms-note-card';

        const minBtn = document.createElement('button');
        minBtn.id = 'lms-note-min-btn';
        minBtn.title = 'Bấm để mở rộng | Giữ chuột để di chuyển vị trí';
        minBtn.innerHTML = `<span>Note LMS</span>`;

        // Kích thước mặc định
        let cardWidth = 345;
        let cardHeight = 400;

        // Đọc vị trí lưu trữ
        let cardPos = { right: 20, bottom: 20 };
        try {
            const rawCardPos = localStorage.getItem(STORAGE_KEY_POS);
            if (rawCardPos) cardPos = JSON.parse(rawCardPos);
        } catch (e) { }

        // Chuyển đổi vị trí right/bottom sang left/top
        if (cardPos.left === undefined || cardPos.top === undefined) {
            const right = cardPos.right !== undefined ? cardPos.right : 20;
            const bottom = cardPos.bottom !== undefined ? cardPos.bottom : 20;
            cardPos.left = window.innerWidth - right - cardWidth;
            cardPos.top = window.innerHeight - bottom - cardHeight;
            cardPos.right = undefined;
            cardPos.bottom = undefined;
        }

        let isCollapsed = false;
        try {
            const rawState = localStorage.getItem(STORAGE_KEY_STATE);
            if (rawState === 'collapsed') isCollapsed = true;
        } catch (e) { }

        let activeTab = 'Nháp 1';
        try {
            const savedTab = localStorage.getItem(STORAGE_KEY_ACTIVE_TAB);
            if (savedTab && SECTION_NAMES.includes(savedTab)) {
                activeTab = savedTab;
            }
        } catch (e) { }

        // Hàm áp dụng tọa độ
        function applyPositions() {
            card.style.left = cardPos.left + 'px';
            card.style.top = cardPos.top + 'px';
            card.style.right = 'auto';
            card.style.bottom = 'auto';

            const minBtnWidth = minBtn.offsetWidth || 86;
            const offset = (cardWidth - minBtnWidth) / 2;

            minBtn.style.left = (cardPos.left + offset) + 'px';
            minBtn.style.top = cardPos.top + 'px';
            minBtn.style.right = 'auto';
            minBtn.style.bottom = 'auto';
        }

        // Tạo 5 Tab Buttons (N1 -> N5)
        let tabsHTML = '';
        SECTION_NAMES.forEach((secName) => {
            tabsHTML += `
                <button class="lms-tab-btn" data-tab="${secName}" title="${secName}">
                    <span class="lms-tab-dot lms-hidden" data-dot="${secName}"></span>
                    <span>${getDisplayName(secName)}</span>
                </button>
            `;
        });

        card.innerHTML = `
            <div id="lms-note-header">
                <div class="lms-note-title">
                    📌 <span>LMS Note</span>
                </div>
                <div class="lms-note-controls">
                    <button class="lms-note-btn lms-note-btn-copy" id="lms-note-copy-btn" title="Copy toàn bộ 5 thẻ nháp">📋</button>
                    <button class="lms-note-btn lms-note-btn-clear" id="lms-note-clear-btn" title="Xóa sạch toàn bộ 5 thẻ nháp">🗑️</button>
                    <button class="lms-note-btn lms-note-btn-toggle" id="lms-note-toggle-btn" title="Thu gọn thành nút nhỏ">➖</button>
                </div>
            </div>
            <div id="lms-note-tabs">
                ${tabsHTML}
            </div>
            <div id="lms-note-body">
                <div id="lms-active-tab-bar">
                    <span id="lms-active-tab-title">📌 Ghi chú: Nháp 1</span>
                    <button class="lms-note-btn lms-note-btn-copy" id="lms-section-copy-btn" title="Copy nội dung phần này">📋</button>
                </div>
                <textarea id="lms-active-textarea" placeholder="Nhập ghi chú..."></textarea>
                <div id="lms-note-toast">✅ Đã copy ghi chú!</div>
            </div>
        `;

        document.body.appendChild(card);
        document.body.appendChild(minBtn);

        const header = document.getElementById('lms-note-header');
        const copyBtn = document.getElementById('lms-note-copy-btn');
        const clearBtn = document.getElementById('lms-note-clear-btn');
        const toggleBtn = document.getElementById('lms-note-toggle-btn');
        const toast = document.getElementById('lms-note-toast');
        const activeTabTitle = document.getElementById('lms-active-tab-title');
        const activeTextarea = document.getElementById('lms-active-textarea');
        const sectionCopyBtn = document.getElementById('lms-section-copy-btn');
        const tabBtns = card.querySelectorAll('.lms-tab-btn');

        // Toast Helper
        function showToast(msg, bgColor = '#10b981') {
            toast.textContent = msg;
            toast.style.background = bgColor;
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 2000);
        }

        // Copy Helper function
        async function copyToClipboard(text) {
            let success = false;
            try {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    await navigator.clipboard.writeText(text);
                    success = true;
                }
            } catch (err) { }

            if (!success && typeof GM_setClipboard !== 'undefined') {
                try {
                    GM_setClipboard(text, 'text');
                    success = true;
                } catch (err) { }
            }
            return success;
        }

        // Tải dữ liệu ghi chú từ localStorage
        let noteData = {};
        SECTION_NAMES.forEach(sec => noteData[sec] = '');

        try {
            const raw = localStorage.getItem(STORAGE_KEY_SECTIONS);
            if (raw) {
                const parsed = JSON.parse(raw);
                SECTION_NAMES.forEach(sec => {
                    if (parsed[sec] !== undefined) {
                        noteData[sec] = parsed[sec];
                    }
                });
            }
        } catch (e) { }

        // Cập nhật chấm xanh báo hiệu các phần có dữ liệu
        function updateTabDots() {
            SECTION_NAMES.forEach(sec => {
                const dot = card.querySelector(`[data-dot="${sec}"]`);
                if (dot) {
                    const content = (noteData[sec] || '').trim();
                    if (content.length > 0) {
                        dot.classList.remove('lms-hidden');
                    } else {
                        dot.classList.add('lms-hidden');
                    }
                }
            });
        }

        // Chuyển Tab active
        function switchTab(secName) {
            activeTab = secName;
            try { localStorage.setItem(STORAGE_KEY_ACTIVE_TAB, activeTab); } catch (e) { }

            tabBtns.forEach(btn => {
                if (btn.getAttribute('data-tab') === activeTab) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });

            activeTabTitle.textContent = `📌 Ghi chú: ${activeTab}`;
            activeTextarea.placeholder = `Nhập ghi chú cho ${activeTab}...`;
            activeTextarea.value = noteData[activeTab] || '';
            sectionCopyBtn.title = `Copy nội dung ${activeTab}`;

            updateTabDots();
        }

        // Cấu hình hiển thị theo trạng thái thu gọn / mở rộng
        function setVisibility(collapsed) {
            isCollapsed = collapsed;
            if (collapsed) {
                card.classList.add('lms-hidden');
                card.style.display = 'none';
                minBtn.classList.remove('lms-hidden');
                minBtn.style.display = 'inline-flex';
                applyPositions();
            } else {
                minBtn.classList.add('lms-hidden');
                minBtn.style.display = 'none';
                card.classList.remove('lms-hidden');
                card.style.display = 'flex';
                applyPositions();
            }
        }

        // Đồng bộ kích thước khi người dùng kéo dãn card
        if (typeof ResizeObserver !== 'undefined') {
            const ro = new ResizeObserver(() => {
                if (card.offsetWidth > 0) {
                    cardWidth = card.offsetWidth;
                    cardHeight = card.offsetHeight;
                }
            });
            ro.observe(card);
        }

        // Khởi tạo hiển thị & tab ban đầu
        setVisibility(isCollapsed);
        switchTab(activeTab);
        applyPositions();

        // Sự kiện gõ nội dung vào textarea
        activeTextarea.addEventListener('input', () => {
            noteData[activeTab] = activeTextarea.value;
            updateTabDots();
            try {
                localStorage.setItem(STORAGE_KEY_SECTIONS, JSON.stringify(noteData));
            } catch (e) { }
        });

        // Gắn sự kiện click chọn Tab
        tabBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const secName = btn.getAttribute('data-tab');
                switchTab(secName);
            });
        });

        // 1. Copy toàn bộ 5 thẻ nháp (Header Copy 📋)
        copyBtn.addEventListener('click', async (e) => {
            e.stopPropagation();

            const outputParts = [];
            SECTION_NAMES.forEach(secName => {
                const content = (noteData[secName] || '').trim();
                if (content.length > 0) {
                    outputParts.push(`${secName}:\n${content}`);
                }
            });

            if (outputParts.length === 0) {
                showToast('⚠️ Chưa có ghi chú nào để copy!', '#f59e0b');
                return;
            }

            const combinedText = outputParts.join('\n\n');
            await copyToClipboard(combinedText);
            showToast('✅ Đã copy toàn bộ ghi chú!', '#10b981');
        });

        // 2. Copy riêng thẻ nháp đang mở (📋 tại thanh tiêu đề nội dung)
        sectionCopyBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const content = (noteData[activeTab] || '').trim();

            if (content.length === 0) {
                showToast(`⚠️ ${activeTab} chưa có nội dung!`, '#f59e0b');
                return;
            }

            // Copy trực tiếp nội dung thuần túy của thẻ để tiện dán vào các ô LMS
            await copyToClipboard(content);
            showToast(`✅ Đã copy nội dung ${activeTab}!`, '#10b981');
        });

        // 3. Xóa sạch toàn bộ 5 thẻ nháp (🗑️)
        clearBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (confirm('⚠️ Bạn có chắc chắn muốn XÓA SẠCH toàn bộ ghi chú ở cả 5 thẻ nháp không? (Hành động này không thể khôi phục)')) {
                SECTION_NAMES.forEach(sec => {
                    noteData[sec] = '';
                });

                activeTextarea.value = '';
                updateTabDots();

                try {
                    localStorage.setItem(STORAGE_KEY_SECTIONS, JSON.stringify(noteData));
                } catch (err) { }

                showToast('🗑️ Đã xóa toàn bộ ghi chú!', '#ef4444');
            }
        });

        // 4. Thu gọn Card thành Nút nhỏ (➖)
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            e.preventDefault();
            setVisibility(true);
            try { localStorage.setItem(STORAGE_KEY_STATE, 'collapsed'); } catch (err) { }
        });

        // ==========================================
        // DI CHUYỂN CARD KHI Ở DẠNG THẺ (HEADER DRAG)
        // ==========================================
        let isCardDragging = false;
        let cardOffsetX = 0;
        let cardOffsetY = 0;

        header.addEventListener('mousedown', (e) => {
            if (e.target.closest('button')) return;
            isCardDragging = true;
            const rect = card.getBoundingClientRect();
            cardOffsetX = e.clientX - rect.left;
            cardOffsetY = e.clientY - rect.top;
        });

        document.addEventListener('mousemove', (e) => {
            if (!isCardDragging) return;
            e.preventDefault();

            let newLeft = e.clientX - cardOffsetX;
            let newTop = e.clientY - cardOffsetY;

            const maxLeft = window.innerWidth - cardWidth;
            const maxTop = window.innerHeight - cardHeight;

            newLeft = Math.max(0, Math.min(newLeft, maxLeft));
            newTop = Math.max(0, Math.min(newTop, maxTop));

            cardPos = { left: newLeft, top: newTop };
            applyPositions();
        });

        document.addEventListener('mouseup', () => {
            if (isCardDragging) {
                isCardDragging = false;
                try {
                    localStorage.setItem(STORAGE_KEY_POS, JSON.stringify(cardPos));
                } catch (err) { }
            }
        });

        // ==========================================
        // DI CHUYỂN & CLICK KHI Ở DẠNG NÚT THU GỌN (MINBTN DRAG & CLICK)
        // ==========================================
        let isMinBtnDragging = false;
        let minBtnMoved = false;
        let minBtnStartX = 0;
        let minBtnStartY = 0;
        let minBtnOffsetX = 0;
        let minBtnOffsetY = 0;

        minBtn.addEventListener('mousedown', (e) => {
            isMinBtnDragging = true;
            minBtnMoved = false;
            minBtnStartX = e.clientX;
            minBtnStartY = e.clientY;

            const rect = minBtn.getBoundingClientRect();
            minBtnOffsetX = e.clientX - rect.left;
            minBtnOffsetY = e.clientY - rect.top;
        });

        document.addEventListener('mousemove', (e) => {
            if (!isMinBtnDragging) return;

            const dist = Math.hypot(e.clientX - minBtnStartX, e.clientY - minBtnStartY);
            if (dist > 4) {
                minBtnMoved = true;
            }

            if (minBtnMoved) {
                e.preventDefault();

                let newLeft = e.clientX - minBtnOffsetX;
                let newTop = e.clientY - minBtnOffsetY;

                const maxLeft = window.innerWidth - minBtn.offsetWidth;
                const maxTop = window.innerHeight - minBtn.offsetHeight;

                newLeft = Math.max(0, Math.min(newLeft, maxLeft));
                newTop = Math.max(0, Math.min(newTop, maxTop));

                const offset = (cardWidth - minBtn.offsetWidth) / 2;

                cardPos = {
                    left: newLeft - offset,
                    top: newTop
                };
                applyPositions();
            }
        });

        document.addEventListener('mouseup', () => {
            if (isMinBtnDragging) {
                isMinBtnDragging = false;
                if (minBtnMoved) {
                    try {
                        localStorage.setItem(STORAGE_KEY_POS, JSON.stringify(cardPos));
                    } catch (err) { }
                }
            }
        });

        minBtn.addEventListener('click', (e) => {
            if (minBtnMoved) {
                e.stopPropagation();
                e.preventDefault();
                minBtnMoved = false;
                return;
            }

            e.stopPropagation();
            e.preventDefault();
            setVisibility(false);
            try { localStorage.setItem(STORAGE_KEY_STATE, 'expanded'); } catch (err) { }
        });

        window.addEventListener('resize', () => {
            if (cardPos.left !== undefined && cardPos.top !== undefined) {
                const maxLeft = window.innerWidth - cardWidth;
                const maxTop = window.innerHeight - cardHeight;
                cardPos.left = Math.max(0, Math.min(cardPos.left, maxLeft));
                cardPos.top = Math.max(0, Math.min(cardPos.top, maxTop));
                applyPositions();
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createNoteCard);
    } else {
        createNoteCard();
    }

})();

