# 📋 TODO — Danh Sách Vấn Đề Cần Xử Lý (Nháp)

> **Ngày tạo:** 2026-09-15  
> **Mục đích:** Liệt kê chi tiết từng vấn đề, root cause, file liên quan, và đề xuất cách sửa.  
> **Cách dùng:** Duyệt từng mục theo thứ tự. Chọn mục cần xử lý → lên plan chi tiết → thực hiện.

---

## Thứ tự xử lý đề xuất

| # | Vấn đề | Ưu tiên | Lý do xếp trước |
|---|--------|---------|-----------------|
| 1 | ✅ **[ĐÃ XỬ LÝ]** Bug chatbot: hiển thị ngày đặt thay vì ngày giao | 🔴 Critical | Bug hiển thị sai dữ liệu, ảnh hưởng UX trực tiếp |
| 2 | 🧹 Dọn UI: xóa "Nạp 10 Đơn Mẫu" và "Chu kỳ" | 🔴 High | Nhanh, dọn sạch UI trước khi chỉnh form |
| 3 | ✏️ Hoàn thiện form "Thêm Đơn Hàng" | 🔴 High | Phụ thuộc vào #2 (chỉ còn 1 nút) |
| 4 | 📊 Sửa số liệu dashboard không khớp DB | 🟡 Medium | Hiển thị sai thống kê |
| 5 | 🧪 Tạo data test 100 đơn | 🟡 Medium | Cần test trước khi chỉnh thuật toán |
| 6 | 📦 Nâng chiều cao xếp hàng tối đa lên 200cm | 🟡 Medium | Cần data test (#5) để kiểm chứng |
| 7 | 🤖 AI kiểm tra chất lượng câu trả lời chatbot | 🟢 Nice-to-have | Cải thiện chất lượng dần |
| 8 | 🚀 Tối ưu tốc độ thuật toán (quyết định ngày giao) | 🟢 Nice-to-have | Refactor lớn, cần ổn định trước |
| 9 | ✅ **[ĐÃ XỬ LÝ]** Chatbot: Hiển thị tình trạng lịch giao đầy đủ | 🟢 Nice-to-have | Đã code xong tính năng hiển thị xe, ETA, trạm |

---

## 1. 🐛 Bug Chatbot: Hiển thị ngày đặt hàng thay vì ngày giao

### Mô tả vấn đề
Khi người dùng hỏi chatbot "tra cứu tình trạng và ngày giao của Đại lý Thực phẩm Minh", chatbot trả về:
```
• Ngày giao: 2026-09-08 18:05
```
Nhưng giá trị này thực chất là **ngày đặt hàng** (`order_date`), không phải ngày giao thực tế.

### Root cause
**File:** `solver/db.py` — dòng 1339-1342

```python
date_expr = "COALESCE(o.order_date, o.delivery_date_preferred, substr(o.created_at, 1, 16))"
# ...
f"SELECT o.*, {date_expr} AS order_date, {date_expr} AS delivery_date_preferred, ..."
```

Hàm `get_orders()` dùng cùng một biểu thức `COALESCE` để gán **cả hai** cột `order_date` **lẫn** `delivery_date_preferred`. Kết quả là `delivery_date_preferred` luôn = `order_date`.

Sau đó trong chatbot (`solver/chatbot.py` dòng 509):
```python
f"• Ngày giao: {o.get('delivery_date_preferred', 'N/A')}\n"
```
→ Hiển thị ngày đặt thay vì ngày giao.

### Cách sửa
1. **`db.py`**: Tách riêng `order_date` và `delivery_date_preferred` trong query `get_orders()`:
   - `order_date` → `COALESCE(o.order_date, substr(o.created_at, 1, 16))`
   - `delivery_date_preferred` → giữ nguyên giá trị gốc từ cột DB, **không** ghi đè bằng `order_date`
2. **`chatbot.py`**: Khi tra cứu đơn, nếu đơn đã `scheduled` thì hiển thị ngày giao thực tế từ bảng `delivery_schedules` (nếu có). Nếu chưa lên lịch thì ghi "Chưa lên lịch".
3. **`chatbot.py` dòng 301-321**: Khi tra cứu bằng mã 6 ký tự, bổ sung hiển thị trạng thái lịch giao và ngày giao.

### Files cần sửa
- `solver/db.py` (dòng ~1339-1357)
- `solver/chatbot.py` (dòng ~502-518, dòng ~301-321)

### ✅ Trạng thái: Đã xử lý (2026-09-23)
**Cách xử lý thực tế:**
1. Phát hiện root cause bổ sung nằm ở lúc tạo đơn hàng (hàm `save_order` trong `solver/db.py` tự động chép `order_date` sang `delivery_date_preferred` nếu bị trống). Đã xóa bỏ logic ghi đè này.
2. Thêm một lớp lọc vào `solver/chatbot.py` (hàm `_format_delivery_info`): Nếu phát hiện dữ liệu cũ bị trùng lặp (`pref_date == order_date`), hệ thống sẽ tự xóa chuỗi bị sai và thay bằng hiển thị **"Chưa lên lịch"** kèm theo **"Ngày đặt hàng"** tách biệt rõ ràng.

---

## 2. 🧹 Dọn UI: Xóa "Nạp 10 Đơn Mẫu" và "Chu kỳ"

### Mô tả vấn đề
Trong action bar có 3 phần:
- 🌱 Nạp 10 Đơn Mẫu → **XÓA**
- ➕ Thêm Đơn Hàng → **GIỮ LẠI**
- 📅 Chu kỳ → **XÓA**

### Cách sửa
1. Xóa button `btn-b2b-seed` (dòng 2788-2790) trong HTML
2. Xóa div chứa select `b2bPlanningDays` (dòng 2794-2803) trong HTML
3. Xóa hoặc comment hàm JS `seedB2BData()` (nếu có)
4. Xử lý hàm `runB2BOptimization()` — hiện tại đọc `b2bPlanningDays.value` → set mặc định = 5 khi không có select
5. Cập nhật text hướng dẫn ở dòng 4227 (đoạn "Hãy bấm [🌱 Nạp 10 Đơn Mẫu]...")

### Files cần sửa
- `solver/static/index.html` (dòng ~2788-2803, ~4227)

---

## 3. ✏️ Hoàn Thiện Form "Thêm Đơn Hàng"

### Mô tả vấn đề
Form thêm đơn hàng hiện tại (`newOrderModal`, dòng 3419-3517) có nhiều vấn đề:

#### 3a. Xóa trường "Giờ bắt đầu" và "Giờ kết thúc"
- **Vị trí:** dòng 3489-3501 (2 input `moTimeStart`, `moTimeEnd`)
- **Cách sửa:** Xóa div chứa 2 input time. Trong JS `saveManualNewOrder()` (dòng 4495-4496), gán mặc định `time_window_start = "08:00"` và `time_window_end = "17:00"`.

#### 3b. Số lượng mặc định → trống (không phải 50)
- **Vị trí:** dòng 3479 `value="50"` và dòng 3485 `value="250"`
- **Cách sửa:** Xóa `value="50"` và `value="250"`, thay bằng `placeholder`. Khi lưu, nếu trống → cảnh báo bắt buộc nhập.

#### 3c. AI Ước Lượng: di chuyển xuống dưới "Số lượng" và bao gồm "Khối lượng"
- **Hiện tại:** Nút "✨ AI Ước Lượng" nằm trong khung kích thước kiện (dòng 3445-3447), chỉ ước lượng kích thước D×R×C.
- **Cách sửa:**
  1. Di chuyển nút AI Ước Lượng xuống **sau** input "Số lượng" và "Khối lượng"
  2. Khi bấm: AI ước lượng kích thước kiện **VÀ** khối lượng dựa trên tên sản phẩm + số lượng
  3. Logic: Người dùng nhập tên sản phẩm → nhập số lượng → bấm AI Ước Lượng → điền tự động kích thước + khối lượng
  4. Cập nhật API `/api/packing/dimensions/estimate` để trả thêm `estimated_weight_kg`

#### 3d. Gợi ý địa chỉ + chọn trên bản đồ (như form sửa đơn)
- **Hiện tại:** Input `moCustAddr` (dòng 3433) là text thuần, không có autocomplete/map
- **Tham khảo:** Form sửa đơn (`editOrderModal`, dòng 3532-3542) đã có autocomplete + map
- **Cách sửa:** Sao chép logic autocomplete + Leaflet map từ `editOrderModal` sang `newOrderModal`:
  1. Thêm div `moAutocompleteDropdown` cho danh sách gợi ý
  2. Thêm div `moMap` cho bản đồ Leaflet
  3. Thêm hidden input `moLat`, `moLon` lưu tọa độ
  4. Copy hàm `onEoSearchInput()` → tạo `onMoSearchInput()`
  5. Khi chọn địa chỉ gợi ý → gán tọa độ + hiển thị marker trên map

#### 3e. Validation trước khi nộp
- **Hiện tại:** Chỉ check `name` và `addr` (dòng 4499)
- **Cách sửa:** Bổ sung kiểm tra đầy đủ trước khi `POST`:
  - `customer_name` ≠ rỗng
  - `customer_address` ≠ rỗng VÀ có tọa độ (lat/lon)
  - `moItemName` ≠ rỗng
  - `moQty` > 0
  - `moWeight` > 0 (hoặc đã AI ước lượng)
  - Nếu thiếu → hiển thị lỗi cụ thể (không chỉ `alert`)

### Files cần sửa
- `solver/static/index.html` (modal form dòng ~3419-3517, JS dòng ~4456-4557)
- `solver/api.py` (endpoint `/api/packing/dimensions/estimate` — bổ sung trả weight)

---

## 4. 📊 Sửa Số Liệu Dashboard Không Khớp DB

### Mô tả vấn đề
Thanh summary bar hiển thị:
```
📦 861 đơn lên lịch  
⏳ 0 đơn lịch xa (>6 ngày)
```
Nhưng số 861 không khớp với số đơn thực tế trong DB.

### Root cause
**File:** `solver/static/index.html` dòng 4737:
```javascript
document.getElementById('sumOrders').textContent = kpis.total_orders || 0;
```
Giá trị `kpis.total_orders` đến từ kết quả optimization chạy lần cuối, **không phải** đếm trực tiếp từ DB hiện tại.

### Cách sửa
1. Khi load trang / load orders, đếm tổng số đơn từ API `/api/b2b/orders` và cập nhật `sumOrders`
2. `sumDistantOrders` — đếm đơn có `delivery_date_preferred` cách hôm nay >6 ngày
3. Cập nhật hàm `loadB2BOrders()` để tính đúng cả 2 giá trị
4. Nếu chưa chạy optimization → hiển thị "0 đơn lên lịch" (thay vì số cũ)

### Files cần sửa
- `solver/static/index.html` (hàm JS `loadB2BOrders()`, `renderB2BResult()`)
- Có thể cần thêm API endpoint trả count chính xác

---

## 5. 🧪 Tạo Data Test 100 Đơn

### Mô tả vấn đề
Hiện tại hệ thống có 1000 đơn trong DB (seed từ `solver/seed_1000_orders.py` → file `solver/1000_orders_hcm.json`). Cần test trước với 100 đơn.

### Các phương án

#### Phương án A: Giới hạn trong code (Nhanh nhất — **ĐỀ XUẤT**)
- Trong `pipeline.py` dòng ~178, sau khi lấy `orders_raw = get_orders()`, thêm:
  ```python
  orders_raw = orders_raw[:100]  # Giới hạn test 100 đơn
  ```
- **Ưu:** Không cần sửa DB, revert dễ (xóa 1 dòng)
- **Nhược:** Không clean, dễ quên xóa

#### Phương án B: Tạo script seed 100 đơn riêng
- Tạo file `solver/seed_100_orders.py` copy từ `seed_1000_orders.py`, đổi `range(1000)` → `range(100)`
- Hoặc thêm param `--count 100` vào script seed hiện tại
- **Ưu:** Clean, tách biệt
- **Nhược:** Cần reset DB trước khi seed lại

#### Phương án C: Query parameter trên API (Linh hoạt nhất)
- Thêm query param `?limit=100` vào endpoint `/api/b2b/optimize`:
  ```python
  @app.post("/api/b2b/optimize")
  async def optimize(req: Request):
      body = await req.json()
      limit = body.get("order_limit", None)
      # ...
      if limit:
          orders_raw = orders_raw[:limit]
  ```
- Frontend thêm input số lượng đơn test trước khi chạy optimize
- **Ưu:** Linh hoạt nhất, không cần sửa DB
- **Nhược:** Cần sửa cả frontend lẫn backend

### Đề xuất
Dùng **Phương án C** (API param) kết hợp **Phương án B** (seed riêng) để:
1. Seed 100 đơn sạch vào DB riêng hoặc reset DB
2. Trên UI thêm ô nhập số đơn tối đa khi chạy optimize

### Files liên quan
- `solver/pipeline.py` (dòng ~178)
- `solver/seed_1000_orders.py`
- `solver/api.py` (endpoint `/api/b2b/optimize`)

---

## 6. 📦 Nâng Chiều Cao Xếp Hàng Tối Đa Lên 200cm (2m)

### Mô tả vấn đề
Hiện tại bin packing xếp chưa đủ cao, muốn xếp tối đa 2m (200cm).

### Root cause
**File:** `solver/bin_packing.py`

Giá trị `cargo_height_cm` mặc định là `185.0` (dòng 759 — test, dòng 207 — fallback):
```python
# Dòng 207: PackingResult.to_dict()
th = self.vehicle.cargo_height_cm if self.vehicle else 185.0
```

**File:** `solver/pipeline.py` dòng 48:
```python
cargo_height_cm=float(v_spec.get("cargo_height_cm") or 185.0),
```

Ngoài ra, `max_layers=3` (dòng 59 của `bin_packing.py`) giới hạn số tầng xếp, nhưng không trực tiếp giới hạn chiều cao.

### Cách sửa
1. **`bin_packing.py`**: Đổi fallback height từ `185.0` → `200.0`
2. **`pipeline.py` dòng 48**: Đổi fallback từ `185.0` → `200.0`
3. **DB vehicle specs**: Cập nhật `cargo_height_cm` của các xe trong DB lên `200`
4. **Kiểm tra logic placement** (dòng 415-417):
   ```python
   az + h > vehicle.cargo_height_cm  # Constraint check
   ```
   Logic này đúng, chỉ cần tăng `cargo_height_cm` của vehicle.
5. **Cập nhật frontend** 3D viewer để hiển thị đúng thùng xe cao 200cm

### Files cần sửa
- `solver/bin_packing.py` (dòng 207, 759)
- `solver/pipeline.py` (dòng 48)
- DB records qua API update vehicle specs

---

## 7. 🤖 AI Kiểm Tra Chất Lượng Câu Trả Lời Chatbot

### Mô tả vấn đề
Cần 1 lớp AI kiểm tra xem câu trả lời của chatbot có khớp với câu hỏi không. Ví dụ: hỏi "ngày giao" nhưng chatbot trả lời "ngày đặt hàng".

### Cách làm
Tạo hàm `validate_chatbot_response()` trong `chatbot.py`:

```python
def validate_chatbot_response(user_question: str, bot_reply: str) -> dict:
    """
    Dùng LLM kiểm tra bot_reply có thực sự trả lời đúng user_question không.
    Trả về:
      - is_valid: bool
      - issues: list[str] — các vấn đề phát hiện
      - corrected_reply: str | None — câu trả lời đã sửa (nếu cần)
    """
    validation_prompt = f"""
    Câu hỏi: "{user_question}"
    Câu trả lời: "{bot_reply}"
    
    Kiểm tra:
    1. Câu trả lời có đúng nội dung câu hỏi không?
    2. Có trường nào hiển thị sai tên (VD: hiển thị "ngày đặt" khi hỏi "ngày giao")?
    3. Thông tin có nhất quán không?
    
    Trả về JSON: {{"is_valid": true/false, "issues": [...], "corrected_reply": "..."}}
    """
    # Gọi LLM validate
```

### Cách tích hợp
1. Sau khi chatbot tạo reply, chạy `validate_chatbot_response()` trước khi trả về user
2. Nếu `is_valid = false`, sử dụng `corrected_reply` hoặc thêm cảnh báo
3. Có thể bật/tắt qua config flag `ENABLE_RESPONSE_VALIDATION = True`

### Cân nhắc
- Mỗi câu trả lời cần 1 API call thêm → tăng latency + cost
- Có thể chỉ validate cho các intent `lookup_order` và `update_order` (không validate chat chung)
- Log kết quả validate để cải thiện prompt dần

### Files cần sửa
- `solver/chatbot.py` (thêm hàm mới + tích hợp vào `process_user_chat`)

---

## 8. 🚀 Tối Ưu Tốc Độ Thuật Toán (Quyết Định Ngày Giao Dựa Trên Scan)

### Mô tả vấn đề
Khi quét (scan) đơn hàng, muốn hệ thống tự động quyết định ngày giao dựa trên:
- Ngày giờ hiện tại khi scan
- Khung giờ giao (`time_window_start/end`) 
- Công suất xe còn trống
- Khoảng cách địa lý

### Cách làm
Tạo module `solver/delivery_scheduler.py`:

```python
def auto_assign_delivery_date(order_data: dict, current_datetime: datetime) -> str:
    """
    Dựa vào ngày giờ hiện tại + thông tin đơn hàng, trả về ngày giao tối ưu.
    
    Logic:
    1. Nếu scan trước 12:00 trưa → có thể giao trong ngày (nếu còn slot)
    2. Nếu scan sau 12:00 → giao ngày hôm sau
    3. Nếu đơn urgent → ưu tiên giao ngay
    4. Kiểm tra công suất xe còn trống cho ngày đó
    5. Nếu hết slot → dời sang ngày tiếp theo
    """
```

### Pipeline cải thiện tốc độ
1. **Pre-compute ngày giao** khi đơn vào DB (không chờ chạy optimize)
2. **Cache ma trận khoảng cách** giữa các điểm giao thường xuyên
3. **Incremental optimization**: Khi có đơn mới, chỉ tối ưu lại phần bị ảnh hưởng (không chạy lại toàn bộ 1000 đơn)
4. **Parallel processing**: Phân chia đơn theo khu vực, mỗi khu chạy optimizer riêng → gộp kết quả

### Files cần tạo/sửa
- `solver/delivery_scheduler.py` (MỚI)
- `solver/pipeline.py` (tích hợp auto-assign)
- `solver/api.py` (endpoint mới `/api/b2b/orders/scan`)

---

## 9. 🔍 Chatbot: Hiển Thị Tình Trạng Lịch Giao Đầy Đủ

### Mô tả vấn đề
Khi tra cứu đơn qua chatbot, cần cho người dùng biết:
- Đơn hàng đã lên lịch chưa?
- Nếu rồi: giao ngày nào, khoảng mấy giờ?
- Thông tin giống như hiển thị trong chi tiết khi chạy optimize

### Root cause
Hiện tại chatbot chỉ hiển thị các trường từ bảng `orders` (dòng 502-510). Không query bảng `delivery_schedules` hay `route_stops` để lấy ngày/giờ giao thực tế.

### Cách sửa
1. **`db.py`**: Tạo hàm `get_delivery_info_for_order(order_id)` trả về:
   - `is_scheduled: bool`
   - `delivery_date: str` (ngày giao thực tế)
   - `estimated_time: str` (giờ ETA)
   - `vehicle_name: str` (xe nào chở)
   - `route_code: str` (mã tuyến)
   - `stop_sequence: int` (điểm dừng thứ mấy)

2. **`chatbot.py`**: Bổ sung vào reply khi lookup:
   ```
   📦 Mã đơn: ABC123
   • Khách hàng: Đại lý Thực phẩm Minh
   • Số lượng: 230 thùng
   • Trạng thái: scheduled ✅
   • 📅 Lịch giao: Thứ 3, 2026-09-10
   • ⏰ Dự kiến: ~10:30 sáng
   • 🚛 Xe: Hyundai Porter 2.5T (BS: 51D-12345)
   • 📍 Điểm dừng thứ 3/7 trên tuyến R-001
   ```

### Files cần sửa
- `solver/db.py` (thêm hàm mới)
- `solver/chatbot.py` (dòng ~502-518 và ~301-321)

---

## Tóm Tắt Files Cần Sửa

| File | Vấn đề liên quan |
|------|-----------------|
| `solver/db.py` | #1, #4, #9 |
| `solver/chatbot.py` | #1, #7, #9 |
| `solver/static/index.html` | #2, #3, #4 |
| `solver/api.py` | #3, #5 |
| `solver/bin_packing.py` | #6 |
| `solver/pipeline.py` | #5, #6, #8 |
| `solver/seed_1000_orders.py` | #5 |
| `solver/delivery_scheduler.py` (MỚI) | #8 |

---

> **Ghi chú:** File này là nháp để trao đổi. Sau khi duyệt sẽ chọn từng mục để lên plan chi tiết và thực hiện.
