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
    _generate_order_code,
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

    resp = requests.post(url, json=payload, timeout=8)
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
    """Gọi OpenRouter API (Claude, Llama, v.v.)."""
    key = api_key or OPENROUTER_API_KEY
    if not key:
        raise ValueError("Chưa có OPENROUTER_API_KEY")

    model_name = model or "meta-llama/llama-3.1-8b-instruct:free"
    url = "https://openrouter.ai/api/v1/chat/completions"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

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

    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        return data['choices'][0]['message']['content']


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

KHI NGƯỜI DÙNG MUỐN TRA CỨU ĐƠN HÀNG (VD: Tìm đơn MT, tra cứu đơn 6K4U00):
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


def process_user_chat(message: str, session_id: str = "default",
                      preferred_provider: str = "gemini",
                      gemini_key: str = None, openrouter_key: str = None) -> dict:
    """
    Xử lý tin nhắn của người dùng trong Chatbot.
    Tự động lưu lịch sử hội thoại, tạo đơn vào DB khi đủ thông tin.
    """
    # 1. Tra cứu xem tin nhắn có chứa mã đơn 6 ký tự để tra cứu không (VD: tra cứu đơn A3K9X2)
    words = [w.strip(".,;:?!'\"") for w in message.split()]
    for w in words:
        if len(w) == 6 and w.isalnum():
            order_found = get_order_by_code(w)
            if order_found:
                resp_text = (
                    f"📦 **Thông tin đơn hàng `{order_found['order_code']}`**:\n"
                    f"• **Khách hàng:** {order_found.get('customer_name') or 'N/A'}\n"
                    f"• **Địa chỉ:** {order_found.get('customer_address') or 'N/A'}\n"
                    f"• **Số lượng:** {order_found.get('total_quantity', 0)} kiện/thùng\n"
                    f"• **Khung giờ:** {order_found.get('time_window_start', '08:00')} - {order_found.get('time_window_end', '17:00')}\n"
                    f"• **Trạng thái:** {order_found.get('status', 'pending')}"
                )
                return {
                    "success": True,
                    "reply": resp_text,
                    "provider": "Local DB",
                    "action": "order_lookup",
                    "order": order_found
                }

    # 2. Gọi AI phân tích
    raw_reply = None
    parsed = {}
    provider_used = "Local Parser"
    try:
        raw_reply, provider_used = call_llm(
            prompt=f"Tin nhắn người dùng: \"{message}\"",
            system_prompt=SYSTEM_ORDER_PROMPT,
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
        
        all_orders = get_orders()
        found = []
        for o in all_orders:
            if query.lower() in o.get("order_code", "").lower() or query.lower() in o.get("customer_name", "").lower():
                found.append(o)
        
        if not found:
            return {"success": True, "reply": f"Không tìm thấy đơn hàng nào khớp với '{query}'.", "provider": provider_used, "action": "chat"}
        
        reply = f"🔍 **Đã tìm thấy {len(found)} đơn hàng khớp với '{query}':**\n"
        for o in found[:5]: # Chỉ hiện 5 đơn gần nhất
            reply += (
                f"\n📦 **Mã đơn: `{o['order_code']}`**\n"
                f"• Khách hàng: {o.get('customer_name', 'N/A')}\n"
                f"• Số lượng: {o.get('total_quantity', 0)} thùng\n"
                f"• Trạng thái: {o.get('status', 'pending')}\n"
                f"• Ngày giao: {o.get('delivery_date_preferred', 'N/A')}\n"
            )
        
        return {
            "success": True,
            "reply": reply,
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


def process_uploaded_file(content_bytes: bytes, filename: str) -> dict:
    """Đọc file Excel/CSV/Text upload, bóc tách và tạo danh sách đơn hàng."""
    created_orders = []
    lines = []
    
    # Thử decode text/csv
    try:
        text = content_bytes.decode('utf-8', errors='ignore')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
    except Exception:
        pass

    if not lines:
        return {"success": False, "error": "Không thể đọc nội dung file."}

    # Bỏ dòng header nếu có
    if len(lines) > 1 and any(h in lines[0].lower() for h in ["tên", "khách", "địa chỉ", "name", "address"]):
        data_lines = lines[1:]
    else:
        data_lines = lines

    for idx, line in enumerate(data_lines[:20]):  # Tối đa 20 dòng mỗi file
        parsed = _parse_fallback_local(line)
        if parsed:
            cust_name = parsed["customer_name"]
            addr = parsed["customer_address"]
            qty = parsed["items"][0]["quantity"]

            # Lưu customer
            cid = save_customer(cust_name, addr, 10.77 + (idx * 0.005), 106.69 + (idx * 0.005))
            code = _generate_order_code()
            ord_row = save_order(
                customer_id=cid,
                order_code=code,
                status="confirmed",
                total_quantity=qty,
                total_weight_kg=qty * 5.0,
                time_window_start="08:00",
                time_window_end="17:00",
                source="file_upload"
            )
            save_order_item(ord_row["id"], parsed["items"][0]["name"], qty, 5.0, 0.04)
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
        "reply": f"📁 Đã xử lý file **`{filename}`** và tạo thành công **{len(created_orders)} đơn hàng** mới vào hệ thống!"
    }

