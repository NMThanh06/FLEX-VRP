"""
FLEX-VRP — AI Logistics Chatbot
Hỗ trợ Dual AI Engine: Google Gemini 2.0 & OpenRouter.
Trích xuất đơn hàng từ ngôn ngữ tự nhiên (text) hoặc file,
tự động kiểm tra thiếu trường, gán mã 6 ký tự và lưu vào SQLite DB.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from db import (
    save_order, save_order_item, get_orders, get_order_by_code, update_order,
    save_customer, get_customers, update_customer,
    save_chat_session, get_chat_session, update_chat_session,
    _generate_order_code, _get_conn, find_order_in_optimization_runs
)


def _load_env_keys():
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8', errors='ignore').splitlines():
            line = line.strip()
            if line.startswith('GEMINI_API_KEY=') and not gemini_key:
                val = line.split('=', 1)[1].strip().strip('"').strip("'")
                if val and val != 'your_gemini_api_key_here':
                    gemini_key = val
            elif line.startswith('OPENROUTER_API_KEY=') and not openrouter_key:
                val = line.split('=', 1)[1].strip().strip('"').strip("'")
                if val and val != 'your_openrouter_api_key_here':
                    openrouter_key = val
    return gemini_key, openrouter_key


GEMINI_API_KEY, OPENROUTER_API_KEY = _load_env_keys()


import requests

def call_gemini(prompt: str, system_prompt: str = "", api_key: str = None) -> str:
    """Gọi Google Gemini REST API (gemini-3.6-flash)."""
    key = api_key or GEMINI_API_KEY
    if not key:
        raise ValueError("Chưa có GEMINI_API_KEY")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={key}"
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048}
    }

    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data['candidates'][0]['content']['parts'][0]['text']


import re

def _parse_fallback_local(text: str) -> dict | None:
    """Fallback rule-based parser khi mất kết nối internet hoặc API hết quota.
    Trả về None nếu tin nhắn không phải yêu cầu tạo đơn hàng."""
    t = text.strip()
    t_lower = t.lower()

    # ── Intent Detection: phát hiện chào hỏi / hỏi chung ──
    greeting_patterns = [
        'chào', 'xin chào', 'hello', 'hi ', 'hey', 'alo', 'chao',
        'xin chao', 'good morning', 'good afternoon', 'bạn ơi',
        'bot ơi', 'ê ', 'ơi', 'nhờ', 'giúp tôi', 'help', 'hỏi',
        'kiểm tra', 'tra cứu', 'tình trạng', 'lịch xe', 'thời tiết',
        'tắc đường', 'giao thông', 'cảm ơn', 'thanks', 'ok', 'được',
        'tạm biệt', 'bye'
    ]
    # ── Intent Detection: Tra cứu đơn hàng / hỏi lịch giao ──
    lookup_keywords = ['tra cứu', 'kiểm tra', 'tìm đơn', 'xem đơn', 'khi nào giao', 'ngày giao', 'giờ giao', 'lịch giao']
    if any(kw in t_lower for kw in lookup_keywords):
        q = t
        for prefix in ['tra cứu đơn hàng', 'tra cứu đơn', 'kiểm tra đơn hàng', 'kiểm tra đơn', 'tìm đơn', 'xem đơn', 'lịch giao đơn', 'lịch giao', 'ngày giao', 'giờ giao']:
            if prefix in t_lower:
                q = t[t_lower.index(prefix) + len(prefix):].strip(" :?.,'\"")
                break
        return {"type": "lookup_order", "query": q or t}

    # Nếu tin nhắn chỉ là chào hỏi đơn giản (không chứa keyword đặt hàng)
    is_greeting = any(t_lower.startswith(g) or t_lower == g.strip() for g in greeting_patterns)

    # ── Keyword đặt hàng: phải có ít nhất 1 keyword liên quan ──
    order_keywords = [
        'thùng', 'kiện', 'hộp', 'bịch', 'gói', 'chai', 'sp',
        'đơn', 'giao', 'tạo đơn', 'đặt hàng', 'cho tiệm', 'cho khách',
        'cho đại lý', 'xuất hàng', 'chuyển hàng', 'gửi hàng',
        'tạo', 'mì gói', 'sữa', 'bia', 'nước ngọt', 'dầu ăn',
        'nước suối', 'coca', 'pepsi', 'hảo hảo',
        'kg', 'tấn', 'lô hàng', 'xuất kho'
    ]
    has_order_intent = any(kw in t_lower for kw in order_keywords)

    # Nếu không có ý định đặt hàng → trả None để chatbot reply chào hỏi
    if not has_order_intent:
        return None

    qty_match = re.search(r'(\d+)\s*(thùng|kiện|hộp|sp|bịch|gói|chai)?', t, re.IGNORECASE)
    qty = int(qty_match.group(1)) if qty_match else 50
    unit = qty_match.group(2) if qty_match and qty_match.group(2) else "thùng"

    cust_name = "Khách Hàng Mới"
    for prefix in ["cho tiệm tạp hóa", "cho tiệm", "cho khách hàng", "cho khách", "cho đại lý", "cho"]:
        if prefix in t.lower():
            after = t[t.lower().index(prefix) + len(prefix):].strip()
            # Cắt trước "tại", "ở", số lượng
            for stop_word in [" tại ", " ở ", " số lượng ", " giao "]:
                if stop_word in after.lower():
                    after = after[:after.lower().index(stop_word)].strip()
            if after:
                cust_name = after.title()
            break

    addr = "TP. Hồ Chí Minh"
    for prefix in ["tại", "ở", "địa chỉ"]:
        pat = rf'\b{prefix}\s+([^,.\n]+(?:,\s*[^,.\n]+)*)'
        m = re.search(pat, t, re.IGNORECASE)
        if m:
            raw_addr = m.group(1).strip()
            for stop in [" số lượng", " giao", " thùng"]:
                if stop in raw_addr.lower():
                    raw_addr = raw_addr[:raw_addr.lower().index(stop)].strip()
            if raw_addr:
                addr = raw_addr
            break

    # Phát hiện sản phẩm
    item_name = "Hàng hóa tổng hợp"
    for it_name in ["mì gói", "hảo hảo", "nước ngọt", "coca", "pepsi", "sữa vinamilk", "bia tiger", "dầu ăn", "nước suối"]:
        if it_name in t.lower():
            item_name = it_name.title()
            break

    # Khung giờ
    t_start, t_end = "08:00", "17:00"
    if "buổi sáng" in t.lower() or "sáng" in t.lower():
        t_start, t_end = "08:00", "12:00"
    elif "buổi chiều" in t.lower() or "chiều" in t.lower():
        t_start, t_end = "13:00", "17:00"

    return {
        "type": "create_order",
        "customer_name": cust_name,
        "customer_address": addr,
        "customer_phone": "0900000000",
        "items": [
            {"name": f"Thùng {item_name}", "quantity": qty, "weight_kg": 6.0, "volume_cbm": 0.04}
        ],
        "time_window_start": t_start,
        "time_window_end": t_end,
        "preferred_date": datetime.now().strftime("%Y-%m-%d"),
        "notes": "Đơn tạo qua Chatbot",
        "missing_fields": []
    }


def call_openrouter(prompt: str, system_prompt: str = "", api_key: str = None, model: str = None) -> str:
    """Gọi OpenRouter API với cơ chế tự động thử danh sách model free khả dụng."""
    key = api_key or OPENROUTER_API_KEY
    if not key:
        raise ValueError("Chưa có OPENROUTER_API_KEY")

    models_to_try = [model] if model else [
        "nex-agi/nex-n2.5-mini:free",
        "google/gemma-4-31b-it:free",
        "google/gemma-4-26b-a4b-it:free",
        "meta-llama/llama-3.1-8b-instruct:free"
    ]
    url = "https://openrouter.ai/api/v1/chat/completions"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    last_err = None
    for model_name in models_to_try:
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.2
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "FLEX-VRP Logistics Hub"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data['choices'][0]['message']['content']
        except Exception as e:
            last_err = e
            continue

    raise last_err or RuntimeError("Không thể gọi OpenRouter API với các model khả dụng.")


def call_llm(prompt: str, system_prompt: str = "", preferred_provider: str = "gemini",
             gemini_key: str = None, openrouter_key: str = None) -> tuple[str, str]:
    """
    Gọi LLM với Dual Engine và cơ chế Fallback tự động.
    Trả về (response_text, provider_used).
    """
    g_key = gemini_key or GEMINI_API_KEY
    o_key = openrouter_key or OPENROUTER_API_KEY

    # 1. Thử provider ưu tiên
    if preferred_provider == "openrouter":
        if o_key:
            try:
                return call_openrouter(prompt, system_prompt, api_key=o_key), "OpenRouter"
            except Exception as e:
                print(f"[Chatbot] OpenRouter error: {e}, falling back to Gemini...")
        if g_key:
            return call_gemini(prompt, system_prompt, api_key=g_key), "Gemini (Fallback)"
        raise RuntimeError("Cả OpenRouter và Gemini đều không khả dụng.")
    else:
        # Ưu tiên Gemini
        if g_key:
            try:
                return call_gemini(prompt, system_prompt, api_key=g_key), "Gemini 2.0"
            except Exception as e:
                print(f"[Chatbot] Gemini error: {e}, falling back to OpenRouter...")
        if o_key:
            return call_openrouter(prompt, system_prompt, api_key=o_key), "OpenRouter (Fallback)"
        raise RuntimeError("Cả Gemini và OpenRouter đều không khả dụng. Vui lòng kiểm tra API Key.")


# ═══════════════════════════════════════════════════
# ORDER EXTRACTION & CONVERSATION HANDLING
# ═══════════════════════════════════════════════════

SYSTEM_ORDER_PROMPT = """
Bạn là Trợ lý AI Điều phối Logistics B2B của hệ thống FLEX-VRP tại TP.HCM.
Nhiệm vụ của bạn là bóc tách thông tin tạo đơn hàng, sửa đơn, tra cứu đơn, hoặc trả lời thắc mắc của người dùng.

KHI NGƯỜI DÙNG MUỐN TẠO HOẶC BỔ SUNG ĐƠN HÀNG:
Trả về JSON:
{
  "type": "create_order",
  "customer_name": "Tên khách hàng hoặc tiệm tạp hóa",
  "customer_address": "Địa chỉ giao tại TP.HCM (nếu có)",
  "customer_phone": "Số điện thoại nếu có",
  "items": [
    {"name": "Tên sản phẩm", "quantity": 100, "weight_kg": 5.0, "volume_cbm": 0.04}
  ],
  "time_window_start": "08:00",
  "time_window_end": "12:00",
  "preferred_date": "YYYY-MM-DD",
  "notes": "Ghi chú nếu có",
  "missing_fields": ["customer_address", ...] (liệt kê các trường bắt buộc còn thiếu: customer_name, customer_address, items)
}

KHI NGƯỜI DÙNG MUỐN TRA CỨU ĐƠN HÀNG (VD: Tìm đơn MT, tra cứu đơn 6K4U00, hỏi ngày và giờ giao dự kiến của đơn B2B-10932):
Trả về JSON:
{
  "type": "lookup_order",
  "query": "Tên khách hàng hoặc mã đơn hàng"
}

KHI NGƯỜI DÙNG MUỐN SỬA ĐƠN HÀNG (VD: Đổi thành 100 thùng, sửa địa chỉ thành Q1):
Trả về JSON:
{
  "type": "update_order",
  "customer_name": "Tên khách hàng (nếu có)",
  "updates": {
    "quantity": 100,
    "customer_address": "Q1"
  }
}

Nếu người dùng chỉ chào hỏi hoặc hỏi chung, trả về JSON:
{
  "type": "general_chat",
  "reply_text": "Nội dung trả lời lịch sự"
}
"""


def _format_delivery_info(order: dict) -> str:
    """
    Format chi tiết thông tin lịch giao, ngày & giờ giao dự kiến (ETA), 
    khung giờ hẹn trước, xe vận chuyển và trạm giao.
    """
    order_code = order.get('order_code', '')
    status = order.get('status', 'pending')
    scheduled = str(order.get('scheduled_delivery') or '').strip()
    order_date = order.get('order_date') or 'N/A'
    pref_date = order.get('delivery_date_preferred') or ''
    tw_start = order.get('time_window_start') or ''
    tw_end = order.get('time_window_end') or ''
    
    # Kiểm tra lịch tối ưu từ optimization runs (đã xếp xe và có ETA cụ thể)
    opt = order.get('opt_schedule')
    if not opt and order_code:
        opt = find_order_in_optimization_runs(order_code)
        
    lines = []
    
    if opt:
        d_date = opt.get('delivery_date') or pref_date or order_date
        d_name = opt.get('day_name') or ''
        date_display = f"{d_name}, {d_date}" if d_name and d_name not in str(d_date) else str(d_date)
        eta = opt.get('eta') or '08:00'
        tw = opt.get('time_window') or (f"{tw_start} - {tw_end}" if tw_start and tw_end else '')
        v_name = opt.get('vehicle_name') or 'Xe tải chuyên dụng'
        step = opt.get('stop_step')
        waybill = opt.get('waybill_code') or ''

        lines.append(f"• 📅 **Ngày giao dự kiến:** {date_display}")
        lines.append(f"• ⏰ **Giờ giao dự kiến (ETA):** {eta}")
        if tw:
            lines.append(f"• 🕐 **Khung giờ hẹn giao:** {tw}")
        lines.append(f"• 🚛 **Xe vận chuyển:** {v_name}")
        if step is not None:
            lines.append(f"• 📍 **Thứ tự dừng:** Trạm #{step}")
        if waybill:
            lines.append(f"• 🏷️ **Mã chuyến / Vận đơn:** `{waybill}`")
        lines.append("• ✅ **Trạng thái:** Đã xếp xe & lên lịch giao tối ưu")
        
    elif scheduled:
        lines.append(f"• 📅 **Ngày & Giờ giao dự kiến:** {scheduled}")
        if tw_start and tw_end:
            lines.append(f"• 🕐 **Khung giờ hẹn giao:** {tw_start} - {tw_end}")
        lines.append("• ✅ **Trạng thái:** Đã lên lịch giao hàng")
        
    elif pref_date or (tw_start and tw_end):
        d_display = pref_date if pref_date else order_date
        lines.append(f"• 📅 **Ngày giao dự kiến:** {d_display}")
        if tw_start and tw_end:
            lines.append(f"• ⏰ **Khung giờ hẹn giao:** {tw_start} - {tw_end}")
        elif tw_start or tw_end:
            lines.append(f"• ⏰ **Khung giờ hẹn giao:** {tw_start or ''} - {tw_end or ''}")
            
        if status == 'optimizing':
            lines.append("• ⏳ **Trạng thái:** Đang chạy thuật toán tối ưu xếp chuyến xe...")
        elif status == 'confirmed':
            lines.append("• 📋 **Trạng thái:** Đã xác nhận khung giờ hẹn, chờ xuất chuyến xe")
        else:
            lines.append("• 📋 **Trạng thái:** Đã có khung giờ hẹn giao, chờ xếp chuyến")
    else:
        lines.append(f"• 📅 **Ngày đặt hàng:** {order_date}")
        if status == 'optimizing':
            lines.append("• ⏳ **Trạng thái:** Đang chạy thuật toán tối ưu xếp xe...")
        elif status == 'confirmed':
            lines.append("• 📋 **Trạng thái:** Đã xác nhận đơn, chờ điều phối phân tuyến")
        else:
            lines.append("• 🕐 **Trạng thái:** Chưa lên lịch giao / Chờ điều phối")

    return "\n".join(lines)


def _format_order_card(order: dict) -> str:
    """Format thẻ hiển thị chi tiết đơn hàng cho chatbot."""
    delivery_info = _format_delivery_info(order)
    cust_name = order.get('customer_name') or 'N/A'
    cust_phone = order.get('customer_phone') or ''
    cust_addr = order.get('customer_address') or 'N/A'
    items = order.get('item_summary') or ''
    qty = order.get('total_quantity', 0)
    weight = order.get('total_weight_kg', 0)
    
    phone_str = f" ({cust_phone})" if cust_phone else ""
    items_str = f"\n• 📦 **Sản phẩm:** {items}" if items else ""
    weight_str = f" ({weight} kg)" if weight else ""
    
    return (
        f"📦 **Thông tin đơn hàng `{order['order_code']}`**:\n"
        f"• 👤 **Khách hàng:** {cust_name}{phone_str}\n"
        f"• 📍 **Địa chỉ giao:** {cust_addr}\n"
        f"• 📊 **Số lượng:** {qty} kiện/thùng{weight_str}"
        f"{items_str}\n"
        f"{delivery_info}"
    )


def process_user_chat(message: str, session_id: str = "default",
                      preferred_provider: str = "gemini",
                      gemini_key: str = None, openrouter_key: str = None) -> dict:
    """
    Xử lý tin nhắn của người dùng trong Chatbot.
    Tự động lưu lịch sử hội thoại, tạo đơn vào DB khi đủ thông tin.
    """
    # 1. Tra cứu xem tin nhắn có chứa mã đơn để tra cứu trực tiếp không (VD: B2B-10932, 2O5WZ0, UDS-0001, v.v.)
    candidates = re.findall(r'\b[A-Za-z0-9][A-Za-z0-9\-_]{3,24}\b', message)
    common_words = {"tra", "cuu", "don", "hang", "ngay", "gio", "giao", "khi", "nao", "xem", "cho", "toi", "biet", "chua", "chuyen", "khung"}
    for cand in candidates:
        if cand.lower() in common_words:
            continue
        order_found = get_order_by_code(cand)
        if order_found:
            return {
                "success": True,
                "reply": _format_order_card(order_found),
                "provider": "Local DB",
                "action": "order_lookup",
                "order": order_found
            }

    # 2. Gọi AI phân tích
    raw_reply = None
    parsed = {}
    provider_used = "Local Parser"
    try:
        # Inject historical context vào system prompt
        historical = _get_historical_context()
        enriched_prompt = SYSTEM_ORDER_PROMPT + historical
        raw_reply, provider_used = call_llm(
            prompt=f"Tin nhắn người dùng: \"{message}\"",
            system_prompt=enriched_prompt,
            preferred_provider=preferred_provider,
            gemini_key=gemini_key,
            openrouter_key=openrouter_key
        )
    except Exception as e:
        print(f"[Chatbot] LLM call failed: {e}. Switching to Local NLP Parser...")
        # Local rule-based parser fallback
        parsed_local = _parse_fallback_local(message)
        if parsed_local:
            parsed = parsed_local
            provider_used = "NLP Parser (Local)"
        else:
            # Tin nhắn không phải tạo đơn (chào hỏi, hỏi chung) → reply thân thiện
            return {
                "success": True,
                "reply": (
                    "👋 **Xin chào!** Tôi là Trợ lý AI Logistics B2B.\n\n"
                    "Tôi có thể giúp bạn:\n"
                    "• **Tạo đơn hàng** — VD: _\"Tạo đơn cho tiệm Cô Ba 80 thùng sữa tại Quận 3\"_\n"
                    "• **Tra cứu đơn** — Nhập mã 6 ký tự (VD: _\"LN1669\"_)\n"
                    "• **Tải file đơn hàng** — Upload CSV/Excel bên dưới\n\n"
                    "Hãy nhập yêu cầu tạo đơn để bắt đầu! 🚛"
                ),
                "provider": "Local (Offline)",
                "action": "chat"
            }

    # 3. Parse JSON từ AI (nếu chưa có từ fallback parser)
    if not parsed and raw_reply:
        clean_text = raw_reply.strip()
        if clean_text.startswith("```"):
            clean_text = clean_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        start_idx = clean_text.find('{')
        end_idx = clean_text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            try:
                parsed = json.loads(clean_text[start_idx:end_idx+1])
            except Exception:
                pass

    if not parsed:
        # Phản hồi dạng văn bản thuần nếu AI không trả JSON
        return {
            "success": True,
            "reply": raw_reply or "Không thể phân tích yêu cầu.",
            "provider": provider_used,
            "action": "chat"
        }

    # 4. Xử lý tạo đơn
    if parsed.get("type") == "create_order":
        missing = parsed.get("missing_fields", [])
        c_name = parsed.get("customer_name")
        c_addr = parsed.get("customer_address")
        items = parsed.get("items", [])

        # Kiểm tra điều kiện
        if not c_name:
            missing.append("Tên khách hàng / Đại lý")
        if not c_addr:
            missing.append("Địa chỉ nhận hàng tại TP.HCM")
        if not items:
            missing.append("Danh sách sản phẩm & số lượng")

        missing = list(set(missing))

        if missing:
            # Còn thiếu thông tin
            missing_str = ", ".join(f"**{m}**" for m in missing)
            reply = (
                f"📝 Tôi đã ghi nhận yêu cầu tạo đơn cho khách **{c_name or 'Chưa rõ'}**.\n\n"
                f"⚠️ **Tuy nhiên còn thiếu các thông tin bắt buộc:** {missing_str}.\n"
                f"👉 Vui lòng cung cấp thêm để tôi hoàn tất lưu đơn hàng và lập lịch tối ưu!"
            )
            return {
                "success": True,
                "reply": reply,
                "provider": provider_used,
                "action": "order_incomplete",
                "missing_fields": missing,
                "draft": parsed
            }

        # Đầy đủ thông tin -> Lưu vào DB
        # Tìm hoặc tạo Customer
        existing_custs = get_customers()
        cust_id = None
        for c in existing_custs:
            if c_name.lower() in c["name"].lower():
                cust_id = c["id"]
                break

        if not cust_id:
            # Tọa độ mặc định trung tâm HCM nếu không có geocoder
            cust_id = save_customer(
                name=c_name,
                address=c_addr,
                lat=10.776,
                lon=106.699,
                phone=parsed.get("customer_phone", ""),
                time_start=parsed.get("time_window_start", "08:00"),
                time_end=parsed.get("time_window_end", "17:00"),
                notes=parsed.get("notes", "")
            )

        total_qty = sum(int(it.get("quantity") or 0) for it in items)
        total_wt = sum(int(it.get("quantity") or 0) * float(it.get("weight_kg") or 5.0) for it in items)
        total_vol = sum(int(it.get("quantity") or 0) * float(it.get("volume_cbm") or 0.04) for it in items)

        order_code = _generate_order_code()
        order_row = save_order(
            customer_id=cust_id,
            order_code=order_code,
            status="confirmed",
            total_quantity=total_qty,
            total_weight_kg=total_wt,
            total_volume_cbm=total_vol,
            time_window_start=parsed.get("time_window_start", "08:00"),
            time_window_end=parsed.get("time_window_end", "17:00"),
            delivery_date_preferred=parsed.get("preferred_date"),
            notes=parsed.get("notes", ""),
            source=f"chatbot_{provider_used.lower()}"
        )

        for it in items:
            save_order_item(
                order_id=order_row["id"],
                product_name=it.get("name") or "Sản phẩm B2B",
                quantity=int(it.get("quantity") or 1),
                weight_per_unit_kg=float(it.get("weight_kg") or 5.0),
                volume_per_unit_cbm=float(it.get("volume_cbm") or 0.04)
            )

        reply = (
            f"🎉 **Đã tạo thành công đơn hàng `{order_code}`!**\n\n"
            f"• **Khách hàng:** {c_name}\n"
            f"• **Địa chỉ:** {c_addr}\n"
            f"• **Tổng số lượng:** {total_qty} kiện / thùng (~{total_wt:.1f} kg)\n"
            f"• **Khung giờ:** {parsed.get('time_window_start', '08:00')} - {parsed.get('time_window_end', '17:00')}\n"
            f"• **Trạng thái:** ✅ Đã xác nhận\n\n"
            f"🚀 Đơn hàng đã sẵn sàng để đưa vào **Thuật toán Phân chia Dinic & Matheuristic**!"
        )

        return {
            "success": True,
            "reply": reply,
            "provider": provider_used,
            "action": "order_created",
            "order": {
                "order_code": order_code,
                "customer_name": c_name,
                "total_quantity": total_qty,
                "total_weight_kg": total_wt
            }
        }

    elif parsed.get("type") == "lookup_order":
        query = parsed.get("query", "").strip()
        if not query:
            return {"success": True, "reply": "Vui lòng cung cấp mã đơn hoặc tên khách hàng cần tra cứu.", "provider": provider_used, "action": "chat"}
        
        # Thử tìm chính xác theo mã đơn trước
        exact_order = get_order_by_code(query)
        if exact_order:
            return {
                "success": True,
                "reply": _format_order_card(exact_order),
                "provider": provider_used,
                "action": "order_lookup",
                "order": exact_order
            }

        q_lower = query.lower()
        q_cleaned = re.sub(r'^(tiệm|quán|cửa hàng|đại lý|nhà thuốc|tạp hóa)\s+', '', q_lower).strip()
        all_orders = get_orders()
        found = []
        for o in all_orders:
            c_name = (o.get("customer_name") or "").lower()
            o_code = (o.get("order_code") or "").lower()
            c_addr = (o.get("customer_address") or "").lower()
            if (q_lower in o_code or 
                q_lower in c_name or 
                (c_name and c_name in q_lower) or 
                (q_cleaned and (q_cleaned in c_name or q_cleaned in c_addr))):
                found.append(o)
        
        if not found:
            return {"success": True, "reply": f"Không tìm thấy đơn hàng nào khớp với '{query}'.", "provider": provider_used, "action": "chat"}
        
        reply = f"🔍 **Đã tìm thấy {len(found)} đơn hàng khớp với '{query}':**\n\n"
        for o in found[:5]: # Chỉ hiện 5 đơn gần nhất
            reply += _format_order_card(o) + "\n\n"
        
        return {
            "success": True,
            "reply": reply.strip(),
            "provider": provider_used,
            "action": "order_lookup",
            "order": found[0]
        }

    elif parsed.get("type") == "update_order":
        c_name = parsed.get("customer_name", "")
        updates = parsed.get("updates", {})
        
        # Tìm đơn hàng gần nhất của khách
        all_orders = get_orders()
        target_order = None
        for o in reversed(all_orders):
            if c_name.lower() in o.get("customer_name", "").lower():
                target_order = o
                break
                
        if not target_order:
            return {"success": True, "reply": f"Không tìm thấy đơn hàng nào của khách '{c_name}' để sửa.", "provider": provider_used, "action": "chat"}
            
        # Cập nhật DB
        reply = f"✏️ **Đã cập nhật đơn hàng `{target_order['order_code']}` của {c_name}:**\n"
        
        # Nếu có số lượng mới
        if "quantity" in updates:
            update_order(target_order["id"], total_quantity=int(updates["quantity"]))
            reply += f"• Số lượng mới: {updates['quantity']} thùng/kiện\n"
        
        # Nếu có địa chỉ mới
        if "customer_address" in updates and target_order.get("customer_id"):
            update_customer(target_order["customer_id"], address=updates["customer_address"])
            reply += f"• Địa chỉ mới: {updates['customer_address']}\n"
            
        reply += "\n✅ Thông tin đã được cập nhật thành công!"
        
        return {
            "success": True,
            "reply": reply,
            "provider": provider_used,
            "action": "order_updated",
            "order": target_order
        }

    # Trường hợp hội thoại chung
    reply_msg = parsed.get("reply_text") or raw_reply
    return {
        "success": True,
        "reply": reply_msg,
        "provider": provider_used,
        "action": "chat"
    }


import pandas as pd
import io

def _load_historical_context() -> str:
    """Load mẫu dữ liệu lịch sử từ uds-orders-aug2024.csv để inject vào AI context."""
    csv_path = Path(__file__).parent.parent / "uds-orders-aug2024.csv"
    if not csv_path.exists():
        return ""
    try:
        df = pd.read_csv(csv_path, nrows=60)
        # Tóm tắt thống kê
        total_rows = len(pd.read_csv(csv_path, usecols=[0]))
        top_items = df['package_name'].value_counts().head(8).to_dict()
        avg_weight = df['weight'].mean()
        avg_distance = df['shippingDistance'].mean()
        
        # Lấy danh sách các địa chỉ phổ biến
        top_receivers = df['receiverAddress'].value_counts().head(5).index.tolist()
        top_senders = df['senderAddress'].value_counts().head(5).index.tolist()
        
        context = (
            f"\n\n=== DỮ LIỆU LỊCH SỬ GIAO HÀNG TPHCM (tham khảo) ===\n"
            f"Tổng đơn lịch sử: {total_rows} đơn\n"
            f"Trọng lượng trung bình: {avg_weight:.1f} kg\n"
            f"Khoảng cách giao trung bình: {avg_distance:.0f} m\n"
            f"Loại hàng phổ biến: {json.dumps(top_items, ensure_ascii=False)}\n"
            f"Điểm gửi thường gặp: {'; '.join(top_senders[:3])}\n"
            f"Điểm nhận thường gặp: {'; '.join(top_receivers[:3])}\n"
            f"=== Sử dụng thông tin trên để ước lượng trọng lượng, khoảng cách khi thiếu dữ liệu ===\n"
        )
        return context
    except Exception as e:
        print(f"[Chatbot] Load historical context failed: {e}")
        return ""


# Cache historical context (load 1 lần duy nhất)
_HISTORICAL_CONTEXT = None

def _get_historical_context() -> str:
    global _HISTORICAL_CONTEXT
    if _HISTORICAL_CONTEXT is None:
        _HISTORICAL_CONTEXT = _load_historical_context()
    return _HISTORICAL_CONTEXT


def _detect_upload_intent(user_message: str) -> str:
    """Phát hiện ý định người dùng khi upload file.
    Returns: 'analyze' | 'create'
    """
    msg = user_message.lower().strip()
    
    # Ý định tạo đơn rõ ràng
    create_keywords = [
        "tạo đơn", "nạp data", "nạp dữ liệu", "import", "nhập đơn",
        "thêm đơn", "tạo data", "làm data", "chuyển thành đơn",
        "tạo đơn mẫu", "tạo đơn từ", "nạp vào", "add order",
        "create order", "tạo hàng loạt"
    ]
    for kw in create_keywords:
        if kw in msg:
            return "create"
    
    # Mặc định: phân tích (an toàn, không tạo đơn)
    return "analyze"


def process_uploaded_file(content_bytes: bytes, filename: str, dataset_id: int = 1, user_message: str = "") -> dict:
    """Đọc file Excel/CSV/Text upload. Hỗ trợ 2 chế độ:
    - analyze: Phân tích nội dung file, trả summary cho người dùng
    - create: Tạo đơn hàng từ dữ liệu file
    """
    # ═══════════════════════════════════════════════════
    # 1. PARSE FILE
    # ═══════════════════════════════════════════════════
    df = None
    raw_text = None
    
    try:
        if filename.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(content_bytes))
        elif filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content_bytes))
        else:
            raw_text = content_bytes.decode('utf-8', errors='ignore')
    except Exception as e:
        try:
            raw_text = content_bytes.decode('utf-8', errors='ignore')
        except Exception:
            return {"success": False, "error": f"Không thể đọc file: {str(e)}", "reply": f"⚠️ Không thể đọc file `{filename}`: {str(e)}"}

    if df is not None and df.empty:
        return {"success": False, "error": "File trống.", "reply": f"⚠️ File `{filename}` không chứa dữ liệu nào."}
    if raw_text is not None and not raw_text.strip():
        return {"success": False, "error": "File trống.", "reply": f"⚠️ File `{filename}` không chứa dữ liệu nào."}

    # ═══════════════════════════════════════════════════
    # 2. TẠO SUMMARY CỦA FILE
    # ═══════════════════════════════════════════════════
    if df is not None:
        total_rows = len(df)
        columns = list(df.columns)
        # Bỏ các cột quá dài (image URL, ID) trong preview để prompt gọn gàng và AI phản hồi nhanh
        clean_cols = [c for c in columns if c.lower() not in ['image', 'id', 'shipper']]
        sample_df = df[clean_cols].head(3) if clean_cols else df.head(3)
        sample_rows = sample_df.to_string(index=False)
        
        # Phân tích độ đầy đủ và các cột bị khuyết (null)
        col_analysis = []
        missing_fields = []
        for col in columns:
            non_null = int(df[col].notna().sum())
            pct = 100 * non_null // total_rows
            col_analysis.append(f"  - `{col}`: {non_null}/{total_rows} giá trị ({pct}%)")
            if non_null < total_rows:
                missing_fields.append(f"`{col}` (thiếu {total_rows - non_null} dòng)")
        
        missing_str = ", ".join(missing_fields) if missing_fields else "Không có cột nào bị thiếu giá trị."
        
        file_summary = (
            f"📊 **Tổng quan file `{filename}`:**\n"
            f"• Số dòng: **{total_rows}** | Số cột: **{len(columns)}**\n"
            f"• Các cột: `{'`, `'.join(columns)}`\n\n"
            f"⚠️ **Các cột bị thiếu giá trị trong file:** {missing_str}\n\n"
            f"📋 **Chi tiết độ đầy đủ từng cột:**\n" + "\n".join(col_analysis) + "\n\n"
            f"📝 **Mẫu 3 dòng dữ liệu:**\n```\n{sample_rows}\n```"
        )
    else:
        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        total_rows = len(lines)
        sample = "\n".join(lines[:5])
        file_summary = (
            f"📄 **File `{filename}` (text):**\n"
            f"• Số dòng: **{total_rows}**\n\n"
            f"📝 **Mẫu 5 dòng đầu:**\n```\n{sample}\n```"
        )

    # ═══════════════════════════════════════════════════
    # 3. PHÁT HIỆN Ý ĐỊNH
    # ═══════════════════════════════════════════════════
    intent = _detect_upload_intent(user_message)
    
    # ═══════════════════════════════════════════════════
    # CHẾ ĐỘ ANALYZE: Chỉ phân tích, hỏi lại người dùng
    # ═══════════════════════════════════════════════════
    if intent == "analyze":
        # Gửi summary + user_message cho AI phân tích thông minh
        historical = _get_historical_context() if "uds-orders" not in filename.lower() else ""
        ai_prompt = (
            f"Người dùng upload file `{filename}` và hỏi: \"{user_message}\"\n\n"
            f"{file_summary}\n\n"
            f"Yêu cầu:\n"
            f"1. Trả lời trực tiếp câu hỏi của người dùng bằng tiếng Việt.\n"
            f"2. Nêu rõ những thông tin đang BỊ THIẾU trong file (các ô trống/null).\n"
            f"3. Đối với bài toán điều phối giao hàng (FLEX-VRP Logistics), chỉ rõ file này còn THIẾU những thông tin nghiệp vụ quan trọng nào "
            f"(ví dụ: tên người nhận, số điện thoại người nhận, thể tích/kích thước 3D kiện hàng, khung giờ nhận hàng chuẩn hóa [time window]).\n"
            f"4. Đề xuất giải pháp bổ sung (ví dụ: tự sinh đơn mẫu với thông số giả lập hợp lý, người dùng bổ sung, hoặc tự điền giá trị mặc định).\n"
            f"5. Hướng dẫn người dùng nhắn lệnh tiếp theo (ví dụ: 'tạo đơn từ file này', 'tạo đơn mẫu').\n"
            f"{historical}"
        )
        system = (
            "Bạn là Trợ lý AI Điều phối Logistics B2B FLEX-VRP. "
            "Phân tích chuyên sâu, rõ ràng, định dạng markdown đẹp mắt, dùng icon trực quan."
        )
        
        try:
            ai_reply, provider = call_llm(ai_prompt, system, preferred_provider="gemini")
        except Exception as e:
            print(f"[Upload] AI Analysis failed: {e}")
            ai_reply = file_summary
            provider = "Local"
        
        return {
            "success": True,
            "filename": filename,
            "total_created": 0,
            "reply": ai_reply,
            "provider": provider,
            "action": "file_analyzed",
            "file_info": {
                "total_rows": total_rows,
                "columns": columns if df is not None else [],
            }
        }
    
    # ═══════════════════════════════════════════════════
    # CHẾ ĐỘ CREATE: Tạo đơn hàng từ file
    # ═══════════════════════════════════════════════════
    created_orders = []
    
    # Chuẩn bị dữ liệu dòng
    if df is not None:
        work_df = df.head(50)  # Giới hạn 50 đơn/lần
        lines = work_df.apply(lambda row: ', '.join([str(val) for val in row if pd.notna(val)]), axis=1).tolist()
    else:
        lines = [l.strip() for l in raw_text.splitlines() if l.strip()][:50]

    # Gọi AI Batch Processing
    user_context = f"\nYêu cầu bổ sung của người dùng: {user_message}" if user_message else ""
    historical = _get_historical_context()
    prompt = (
        f"Dưới đây là {len(lines)} dòng dữ liệu từ file upload. Hãy phân tích và trích xuất từng dòng thành một đơn hàng. "
        "Nếu thiếu trọng lượng (weight_kg) hoặc kích thước, hãy TỰ ĐỘNG ƯỚC LƯỢNG dựa trên 'tên hàng' và 'số lượng'. "
        "Ví dụ: 1 thùng mì tôm ~ 2kg, 1 lốc sữa ~ 1.5kg, 1 tủ lạnh ~ 60kg (is_heavy=1). "
        "Nếu file có cột senderAddress/receiverAddress, lấy receiverAddress làm customer_address. "
        "Nếu file có cột package_name, lấy làm tên hàng. Nếu có cột weight, lấy làm weight_kg. "
        "Trả về định dạng JSON array chứa các object với keys: "
        "'customer_name', 'customer_address' (nếu không có mặc định TP.HCM), "
        "'items': [{'name', 'quantity', 'weight_kg', 'width_cm', 'depth_cm', 'height_cm', 'is_heavy', 'is_fragile', 'requires_cold'}].\n\n"
        f"Dữ liệu:\n" + "\n".join(lines) + user_context + historical
    )
    
    system_prompt = "Bạn là AI Logistics. Output phải là một JSON array hợp lệ. KHÔNG markdown, KHÔNG text giải thích."
    
    try:
        import re
        resp, _ = call_llm(prompt, system_prompt, preferred_provider="gemini")
        match = re.search(r'\[.*\]', resp, re.DOTALL)
        if match:
            orders_data = json.loads(match.group(0))
        else:
            orders_data = json.loads(resp)
    except Exception as e:
        print(f"[Upload] AI Batch Parsing Failed: {e}")
        orders_data = []
        for idx, line in enumerate(lines):
            parsed = _parse_fallback_local(line)
            if parsed:
                orders_data.append(parsed)

    for idx, parsed in enumerate(orders_data):
        cust_name = parsed.get("customer_name") or f"Khách hàng {idx+1}"
        addr = parsed.get("customer_address") or "TP. Hồ Chí Minh"
        
        items = parsed.get("items", [])
        if not items:
            continue
            
        item_data = items[0]
        qty = item_data.get("quantity")
        if qty is None: qty = 1
        item_name = item_data.get("name") or "Hàng hóa"
        
        weight_kg = item_data.get("weight_kg")
        if weight_kg is None: weight_kg = qty * 5.0
        
        is_heavy = item_data.get("is_heavy")
        if is_heavy is None: is_heavy = 1 if weight_kg > 30 else 0
        is_fragile = item_data.get("is_fragile") or 0
        requires_cold = item_data.get("requires_cold") or 0

        # Lưu customer
        cid = save_customer(cust_name, addr, 10.77 + (idx * 0.005), 106.69 + (idx * 0.005))
        code = _generate_order_code()
        ord_row = save_order(
            customer_id=cid,
            order_code=code,
            dataset_id=dataset_id,
            status="confirmed",
            total_quantity=qty,
            total_weight_kg=weight_kg,
            time_window_start="08:00",
            time_window_end="17:00",
            source="file_upload"
        )
        
        # Lưu items
        conn = _get_conn()
        try:
            conn.execute(
                "INSERT INTO order_items (order_id, product_name, quantity, weight_per_unit_kg, "
                "width_cm, depth_cm, height_cm, is_heavy, is_fragile, requires_cold) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ord_row["id"], item_name, qty, round(weight_kg / max(1, qty), 2),
                 item_data.get("width_cm") or 0, item_data.get("depth_cm") or 0, item_data.get("height_cm") or 0,
                 is_heavy, is_fragile, requires_cold)
            )
            conn.commit()
        finally:
            conn.close()
            
        created_orders.append({
            "order_code": code,
            "customer_name": cust_name,
            "address": addr,
            "quantity": qty
        })

    return {
        "success": True,
        "filename": filename,
        "total_created": len(created_orders),
        "orders": created_orders,
        "reply": f"📁 Đã xử lý file **`{filename}`** và tạo thành công **{len(created_orders)} đơn hàng** vào bảng dữ liệu hiện tại!"
    }


