# HƯỚNG DẪN CÀI ĐẶT & CHẠY DỰ ÁN — NHÁNH `ThanhTimDuong`

Tài liệu này hướng dẫn chi tiết cách tải, thiết lập môi trường và chạy dự án **FLEX-VRP** trên nhánh `ThanhTimDuong` cho thành viên nhóm hoặc máy tính mới.

---

## 1. Tổng quan nhánh `ThanhTimDuong`
Nhánh này tích hợp toàn bộ hệ sinh thái tối ưu vận tải và kho vận thông minh:
- **Thuật toán VRP Pipeline 2 pha**: Luồng cực đại Dinic (Dinic Max-Flow) + Matheuristic (GRASP + VND + VNS).
- **Mô phỏng Xếp hàng 3D (3D Bin Packing)**: Ràng buộc LIFO (dỡ hàng không bị cản trở), phân bổ tầng trọng tải, kiểm soát trọng tâm xe.
- **AI Logistics Assistant (Dual-Engine)**:
  - Tích hợp **Google Gemini 2.0** & **OpenRouter (Llama 3.1)** dự phòng.
  - Chatbot tự động bóc tách đơn hàng từ ngôn ngữ tự nhiên.
  - **AI ước lượng kích thước & đặc tính kiện hàng (Dài, Rộng, Cao, Dễ vỡ, Cần lạnh, Nặng)** khi tạo đơn hàng B2B.
- **Giao diện Web trực quan (Full Dashboard)**: Tích hợp sẵn tại cổng `5000` (FastAPI).

---

## 2. Yêu cầu hệ thống
- **Python**: Phiên bản 3.10 trở lên (khuyến nghị 3.11 hoặc 3.12).
- **Git** đã cài đặt trên máy.
- *(Tùy chọn nếu dùng phần Laravel)*: PHP 8.2+, Composer, Node.js 18+.

---

## 3. Các bước cài đặt & Khởi chạy (Dành cho người kéo code)

### Bước 1: Chuyển sang nhánh và cập nhật code mới nhất
Mở terminal tại thư mục dự án và chạy:
```bash
git fetch origin
git checkout ThanhTimDuong
git pull origin ThanhTimDuong
```

---

### Bước 2: Tạo môi trường ảo Python (Khuyến nghị)
Nên tạo virtual environment để tránh xung đột thư viện:

- **Trên Windows (PowerShell/CMD):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\activate
  ```
- **Trên macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

---

### Bước 3: Cài đặt các thư viện phụ thuộc
Chạy lệnh cài đặt từ file `requirements.txt`:
```bash
pip install -r requirements.txt
```

Các thư viện chính bao gồm:
- `fastapi`, `uvicorn`: Web API framework tốc độ cao.
- `requests`, `python-dotenv`: Xử lý HTTP request và đọc cấu hình môi trường.
- `pandas`, `pymysql`: Phân tích và kết nối dữ liệu.
- `pydantic`: Ràng buộc và xác thực dữ liệu API.

---

### Bước 4: Cấu hình file môi trường `.env`
1. Tạo file `.env` ở thư mục gốc của dự án (nếu chưa có, có thể copy từ `.env.example`):
   ```bash
   cp .env.example .env
   ```
2. Mở file `.env` và cấu hình API Key để sử dụng các tính năng AI (Chatbot, Ước lượng hàng hóa):
   ```env
   # API Key cho Google Gemini (Khuyến nghị)
   GEMINI_API_KEY=your_gemini_api_key_here

   # API Key dự phòng OpenRouter (Tùy chọn)
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```
   > **Lưu ý:** Nếu không có API Key, hệ thống vẫn giải được bài toán định tuyến VRP và xếp hàng 3D, nhưng phần Chatbot và AI Ước lượng kích thước sẽ dùng thuật toán heuristic cơ bản thay vì mô hình ngôn ngữ lớn.

---

### Bước 5: Khởi động Server
Chạy lệnh khởi động máy chủ API & Web Dashboard:
```bash
python solver/api.py
```

Khi terminal hiển thị:
```text
INFO:     Uvicorn running on http://0.0.0.0:5000 (Press CTRL+C to quit)
```
Mở trình duyệt web và truy cập địa chỉ:
👉 **[http://localhost:5000](http://localhost:5000)**

---

## 4. Hướng dẫn trải nghiệm các tính năng chính

### 1. Tab "Lập lộ trình VRP" (Routing & Pipeline)
- Chọn số lượng đơn hàng (ví dụ: `50`, `100`, `200` đơn hoặc `Toàn bộ`).
- Chọn các ràng buộc mong muốn: **Khung giờ giao (Time Windows)**, **Trọng tải xe**, **Phân tầng xe tải**.
- Bấm **"Giải lộ trình (Pipeline Dinic + VRP)"**.
- Bản đồ tương tác hiển thị lộ trình chi tiết từng xe, màu sắc phân biệt từng tuyến, kèm bảng thống kê chi phí, số km và thời gian.

### 2. Tab "Mô phỏng xếp hàng 3D" (3D Cargo Packing)
- Chọn lộ trình hoặc xe cụ thể để xem không gian thùng xe 3 chiều.
- Quan sát thứ tự xếp dỡ LIFO (hàng giao trước xếp gần cửa sau, hàng nặng xếp dưới sàn).
- Xoay 360 độ và kiểm tra trọng tâm xe (Center of Gravity).

### 3. Tab "Quản lý đơn hàng & AI Ước tính" (B2B Order Form)
- Thêm đơn hàng mới: Điền tên mặt hàng (ví dụ: *"20 két bia Heineken"* hoặc *"5 màn hình máy tính Dell 27 inch"*).
- Bấm nút **"✨ AI Ước tính kích thước"**: Hệ thống sẽ tự động gọi AI để suy luận chiều dài, rộng, cao, cân nặng và gắn nhãn (Dễ vỡ / Cần bảo quản lạnh / Hàng nặng).

### 4. Tab "AI Logistics Chatbot"
- Trò chuyện tự nhiên: Hỏi đáp về tiến độ giao hàng, kiểm tra đơn hàng hoặc yêu cầu tạo nhanh đơn hàng mới qua đoạn chat.

---

## 5. (Tùy chọn) Chạy phần giao diện quản trị Laravel
Nếu bạn muốn sử dụng cả hệ thống quản trị bằng PHP Laravel:
1. Cài đặt các gói PHP:
   ```bash
   composer install
   ```
2. Tạo application key:
   ```bash
   php artisan key:generate
   ```
3. Cài đặt các gói giao diện frontend:
   ```bash
   npm install
   npm run build
   ```
4. Chạy server Laravel:
   ```bash
   php artisan serve
   ```
   Giao diện Laravel sẽ chạy tại: `http://localhost:8000`.

---

## 6. Xử lý sự cố thường gặp (Troubleshooting)

- **Lỗi `ModuleNotFoundError: No module named '...'`:**
  - Kiểm tra xem đã kích hoạt đúng môi trường ảo Python chưa và chạy lại `pip install -r requirements.txt`.
- **Lỗi cổng 5000 đã bị chiếm dụng (Port already in use):**
  - Đóng tiến trình đang chạy cổng 5000 hoặc kiểm tra terminal khác có đang mở `python solver/api.py`.
- **Cơ sở dữ liệu SQLite:**
  - Dữ liệu đơn hàng và lộ trình được lưu cục bộ trong `solver/data/flex_vrp.db`. Nếu muốn khôi phục lại dữ liệu mẫu 1000 đơn ban đầu, có thể chạy:
    ```bash
    python solver/seed_1000_orders.py
    ```
