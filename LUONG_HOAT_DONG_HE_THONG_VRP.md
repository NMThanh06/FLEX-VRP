# KIẾN TRÚC & LUỒNG HOẠT ĐỘNG TOÀN DIỆN HỆ THỐNG FLEX-VRP
## Matheuristics for Flexible Multi-Period Vehicle Routing with Time Windows, 3D Bin Packing & AI Logistics Assistant

---

## 1. TỔNG QUAN HỆ THỐNG (SYSTEM OVERVIEW)

### 1.1. Bối cảnh và Bài toán
Hệ thống **FLEX-VRP** được thiết kế để giải quyết bài toán vận tải phân phối chặng cuối đô thị phức hợp: **Flexible Multi-Period Vehicle Routing Problem with Time Windows (FMP-VRPTW)** tích hợp **Xếp hàng không gian ba chiều (3D Bin Packing)** và **Trí tuệ nhân tạo (AI Logistics Assistant)**.

Trong môi trường giao vận thực tế tại các đô thị lớn (như TP. Hồ Chí Minh):
- Khách hàng có khung giờ nhận hàng khắt khe (Time Windows).
- Đơn hàng phát sinh đa dạng về khối lượng, kích thước, đặc tính bảo quản (dễ vỡ, cần lạnh, quá khổ).
- Đội xe vận tải hỗn hợp (nhiều chủng loại tải trọng và thể tích).
- Giao thông đô thị có độ trễ lớn do đèn tín hiệu và mật độ phương tiện.
- Quy trình bốc dỡ đòi hỏi tính tuần tự nghiêm ngặt (LIFO - Last In First Out) để tài xế không phải bốc dỡ lại hàng khi tới từng điểm giao.

### 1.2. Kiến trúc 4 tầng (4-Tier Architecture)
Hệ thống được tổ chức thành 4 phân tầng đồng bộ:
1. **Data Layer (Tầng dữ liệu)**: Cơ sở dữ liệu SQLite (`flex_vrp.db`), các tệp cấu hình JSON, module xác thực và làm sạch dữ liệu tự động.
2. **Algorithmic Solver Layer (Tầng thuật toán tối ưu)**:
   - **Pha 1**: Phân bổ luồng mạng đa chu kỳ bằng thuật toán luồng cực đại Dinic (Dinic's Maximum Flow).
   - **Pha 2**: Lập lộ trình chi tiết bằng Matheuristic lai ghép (GRASP + VND + VNS).
3. **3D Cargo Packing Layer (Tầng xếp dỡ không gian 3D)**: Thuật toán xếp kiện hàng theo thứ tự ngược của lộ trình giao (LIFO), kiểm soát tâm tải trọng và ma sát lật.
4. **AI & Presentation Layer (Tầng AI & Giao diện người dùng)**:
   - Kiến trúc Dual-Engine AI (Google Gemini 2.0 Flash + OpenRouter Llama 3.1) phục vụ Chatbot và suy luận tham số hàng hóa.
   - Giao diện Dashboard tương tác trực tiếp với bản đồ Leaflet và đồ họa 3D Three.js.

```
       ┌────────────────────────────────────────────────────────┐
       │                   DATA INGESTION                       │
       │    - B2B Orders / 1000 HCM Orders Dataset              │
       │    - Auto-Validation & Sanitization (Clean DB)          │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │     PHASE 1: DINIC MAX-FLOW (Period & Fleet Match)     │
       │    - Residual Graph (Source -> Orders -> Days -> Sink) │
       │    - Demand Consolidation & Order Splitting            │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │     PHASE 2: MATHEURISTIC VRP (Routing Engine)         │
       │    - GRASP: Restricted Candidate List (RCL)            │
       │    - VND: 2-opt, Or-opt, Relocate, Swap, Cross-Ex      │
       │    - VNS: Shaking & Perturbation (Escape Local Optima) │
       │    - Traffic Light & Time Window Penalty Tuning        │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │     PHASE 3: 3D BIN PACKING & LOADING PLAN             │
       │    - Strict LIFO Sequence (Reverse Route Drop)         │
       │    - 6-DOF Orientation, Heavy-Bottom, CoG Stability    │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │     AI ASSISTANT & REAL-TIME DASHBOARD (FastAPI)       │
       │    - Dual-Engine LLM: Auto Estimate Dimensions & Chat   │
       │    - Interactive Map (Leaflet) & 3D Viewer (Three.js)  │
       └────────────────────────────────────────────────────────┘
```

---

## 2. DÒNG DỮ LIỆU & TIỀN XỬ LÝ (DATA FLOW & SANITIZATION)

### 2.1. Cấu trúc thực thể Đơn hàng (Order Data Schema)
Mỗi đơn hàng trong hệ thống mang các trường thông tin chuẩn hóa:
- `order_code`: Định danh 6 ký tự duy nhất (ví dụ: `HN8K21`).
- `lat`, `lng`: Tọa độ địa lý điểm giao hàng.
- `demand_weight` / `demand_volume`: Khối lượng (kg) và thể tích ($m^3$).
- `time_window_start`, `time_window_end`: Khung giờ nhận hàng bắt buộc (tính bằng phút kể từ đầu ngày).
- `service_time`: Thời gian dừng đỗ bốc dỡ hàng tại điểm (thường từ 10 - 20 phút).
- `delivery_deadline_days`: Khung thời gian hạn chót cho phép giao trong chu kỳ lập kế hoạch (Multi-period, từ thứ Hai đến thứ Sáu).
- `cargo_properties`: `is_fragile` (dễ vỡ), `is_heavy` (nặng), `requires_cold` (bảo quản lạnh).

### 2.2. Cơ chế Tự động Xác thực & Làm sạch Dữ liệu (Auto-Sanitization)
Trước khi bất kỳ thuật toán tối ưu nào được kích hoạt, dữ liệu thô phải trải qua bước tiền xử lý tại `solver/pipeline.py`:
1. **Phát hiện dữ liệu sai hỏng**:
   - Tọa độ thiếu hoặc nằm ngoài biên độ hợp lệ của khu vực hoạt động (TP.HCM).
   - Nhu cầu giao hàng không dương ($\le 0$).
   - Khung giờ giao hàng mâu thuẫn ($TW_{start} \ge TW_{end}$).
2. **Cơ chế Hard-Delete**:
   - Khi chạy pipeline với tham số chọn tập đơn (ví dụ chọn 100 đơn), hệ thống tự động quét toàn bộ cơ sở dữ liệu SQLite, gọi `delete_order()` để loại bỏ hoàn toàn các đơn bị lỗi, đảm bảo 100% dữ liệu nạp vào ma trận khoảng cách là dữ liệu khả thi (Feasible Data).

---

## 3. PHA 1: PHÂN BỔ ĐA CHU KỲ VỚI LUỒNG CỰC ĐẠI DINIC (DINIC MAX-FLOW)

### 3.1. Mô hình Mạng luồng (Flow Network Construction)
Để giải quyết bài toán giao hàng đa ngày (Multi-Period Planning), hệ thống mô hình hóa bài toán gán đơn thành đồ thị luồng mạng $G = (V, E)$:
- **Source ($S$)**: Nguồn phát tổng nhu cầu vận tải.
- **Tầng Đơn hàng ($U$)**: Mỗi nút đại diện cho một đơn hàng cần giao. Cung $(S, u)$ có dung lượng bằng nhu cầu $Demand(u)$.
- **Tầng Chu kỳ/Ngày ($D$)**: Các nút đại diện cho ngày giao khả dĩ (Thứ 2, Thứ 3, ..., Thứ 6). Cung nối từ đơn hàng $u$ sang ngày $d$ chỉ tồn tại nếu ngày $d \le Deadline(u)$.
- **Tầng Đội xe ($K$)**: Mỗi ngày kết nối với các xe khả dụng, dung lượng cung giới hạn bởi tải trọng xe $Cap(k)$.
- **Sink ($T$)**: Nút thu nhận luồng.

### 3.2. Thuật toán Dinic
Thuật toán Dinic được cài đặt trong `solver/dinic_flow.py`:
1. **Xây dựng Đồ thị Phân tầng (Level Graph)** thông qua duyệt theo chiều rộng (BFS) từ $S$ đến $T$. Nếu không tới được $T$, thuật toán dừng.
2. **Tìm Luồng Chặn (Blocking Flow)** thông qua duyệt theo chiều sâu (DFS) trên đồ thị phân tầng kết hợp kỹ thuật con trỏ trượt (*Current Arc Optimization*).
3. **Độ phức tạp**: $O(V^2 E)$, vượt trội so với Edmonds-Karp $O(V E^2)$, đặc biệt hiệu quả khi số lượng đơn hàng lên tới hàng nghìn.

### 3.3. Gom đơn (Consolidation) & Tách đơn (Splitting)
- **Gom đơn**: Các đơn hàng cực nhỏ có tọa độ gần nhau và cùng khung giờ được gom thành cụm (Cluster) nhằm giảm bớt số chiều bài toán.
- **Tách đơn**: Nếu một đơn hàng lớn vượt quá sức chở của một xe đơn lẻ, thuật toán sẽ tự động phân tách thành các phần nhỏ hơn và gán vào các chu kỳ/xe khác nhau mà vẫn đảm bảo tổng luồng đạt 100%.

---

## 4. PHA 2: LẬP LỘ TRÌNH CHI TIẾT BẰNG THUẬT TOÁN MATHEURISTIC

Sau khi Dinic phân bổ tập đơn hàng vào từng ngày và từng đội xe, bài toán tại mỗi chu kỳ trở thành **Vehicle Routing Problem with Time Windows (VRPTW)**. Thuật toán được cài đặt tại `solver/matheuristic.py` và `solver/vrp_engine.py`.

### 4.1. Hàm Mục Tiêu Đa Tiêu Chí (Multi-Objective Evaluation)
Mỗi phương án lộ trình $S$ được đánh giá thông qua hàm chi phí tổng thể:
$$f(S) = w_1 \sum C_{distance}(r) + w_2 \sum C_{duration}(r) + w_3 \sum Cost_{vehicle}(k) + P_{TW}(S) + P_{Cap}(S)$$

Trong đó:
- $C_{distance}$: Chi phí nhiên liệu tính trên tổng quãng đường (áp dụng ma trận khoảng cách Haversine/OSRM).
- $C_{duration}$: Chi phí thời gian chạy, bao gồm thời gian di chuyển, thời gian phục vụ tại điểm và thời gian chờ đèn tín hiệu giao thông.
- $P_{TW}$: Hình phạt vi phạm khung giờ giao hàng (Time Window Violation Penalty).
- $P_{Cap}$: Hình phạt nếu tải trọng hoặc thể tích vượt ngưỡng an toàn.

### 4.2. Giai đoạn Khởi tạo: GRASP (Greedy Randomized Adaptive Search)
- Hệ thống xây dựng lộ trình ban đầu bằng thuật toán tham lam ngẫu nhiên có kiểm soát.
- Tại mỗi bước chọn điểm dừng kế tiếp, một danh sách ứng viên thu gọn (**RCL - Restricted Candidate List**) được tạo ra dựa trên khoảng cách địa lý và độ tương thích về thời gian đến dự kiến. Một điểm trong RCL được chọn ngẫu nhiên để đa dạng hóa nghiệm ban đầu.

### 4.3. Giai đoạn Tối ưu Cục bộ: VND (Variable Neighborhood Descent)
VND duyệt tuần tự qua 5 cấu trúc lân cận kinh điển theo thứ tự từ nhẹ đến sâu:
1. **2-opt (Intra-route)**: Đảo ngược thứ tự các điểm dừng liên tiếp trên cùng một tuyến để khử các đoạn đường bị bắt chéo.
2. **Or-opt (Intra-route)**: Di chuyển một chuỗi gồm 1, 2 hoặc 3 khách hàng liên tiếp sang vị trí khác trên cùng tuyến xe.
3. **Relocate (Inter-route)**: Lấy một đơn hàng từ tuyến xe $A$ chuyển sang vị trí tối ưu trên tuyến xe $B$.
4. **Swap (Inter-route)**: Hoán đổi vị trí của một đơn hàng trên xe $A$ với một đơn hàng trên xe $B$.
5. **Cross-Exchange (Inter-route)**: Cắt và tráo đổi hai đoạn hành trình giữa hai xe khác nhau.

VND chỉ chuyển sang cấu trúc lân cận tiếp theo khi lân cận hiện tại không còn khả năng cải thiện nghiệm (First-Improvement hoặc Best-Improvement).

### 4.4. Cơ chế Thoát Cực tiểu Địa phương: VNS (Variable Neighborhood Search)
Khi VND hội tụ về một nghiệm cực tiểu cục bộ (Local Optimum), cơ chế **Shaking (Rung chuyển)** của VNS được kích hoạt:
- Ngẫu nhiên tháo gỡ (Ruin) từ 15% - 30% số điểm dừng trên các tuyến đường.
- Tái chèn (Recreate) các điểm dừng này bằng heuristic tham lam có điều kiện.
- Đưa nghiệm mới qua lại bộ lọc VND để tìm kiếm nghiệm tốt hơn trên diện rộng.

---

## 5. PHA 3: TỐI ƯU HÓA XẾP HÀNG THÙNG XE 3D (3D BIN PACKING)

Được cài đặt tại `solver/bin_packing.py`, module này đóng vai trò cầu nối vật lý giữa lộ trình di chuyển và thực tế xếp dỡ kho vận.

### 5.1. Ràng buộc LIFO Tuyệt đối (Last-In First-Out)
- Kiện hàng của điểm dừng **giao sau cùng** sẽ được xếp vào **sâu nhất trong thùng xe**.
- Kiện hàng của điểm dừng **giao đầu tiên** sẽ nằm ngay sát **cửa sau thùng xe**.
- Ràng buộc này loại bỏ hoàn toàn tình trạng tài xế phải dỡ hàng hóa của khách hàng khác ra ngoài vỉa hè để lấy kiện hàng cần giao.

### 5.2. Các Ràng buộc Không gian và Động học
1. **6 Hướng xoay không gian (6-DOF Orientations)**: Mỗi kiện hàng hình hộp chữ nhật có thể được thử nghiệm ở 6 tư thế xoay khác nhau, trừ trường hợp kiện hàng có cờ cảnh báo *"Không lật úp"*.
2. **Nguyên lý Đáy nặng (Heavy-Bottom Principle)**: Các kiện hàng có tỷ trọng lớn bắt buộc phải nằm trên sàn xe hoặc trên các kiện hàng chịu lực tốt hơn; tuyệt đối không đặt hàng nặng đè lên hàng nhẹ hoặc hàng dán nhãn `is_fragile`.
3. **Cân bằng Trọng tâm (Center of Gravity - CoG)**: Tọa độ trọng tâm toàn bộ khối hàng trong thùng xe phải nằm trong dải dung sai an toàn ($\pm 10\%$ quanh trục giữa), ngăn ngừa hiện tượng lật xe khi vào cua hoặc mất phanh do phân bổ tải trọng lệch trục.

---

## 6. PHA 4: HỆ THỐNG TRỢ LÝ LOGISTICS THÔNG MINH (DUAL AI ENGINE)

Được cài đặt tại `solver/chatbot.py`, `solver/ai_debate.py` và `solver/vehicle_intelligence.py`.

### 6.1. Kiến trúc Dual AI Fallback
Hệ thống sử dụng cơ chế bảo vệ hai lớp để đảm bảo tính sẵn sàng 24/7:
- **Primary Engine**: Google Gemini 2.0 Flash (Tốc độ xử lý dưới 1s, context window lớn, hỗ trợ phân tích hình ảnh chứng từ).
- **Secondary Engine**: OpenRouter API kết nối Meta Llama 3.1 8B Instruct (Kích hoạt tự động khi Gemini chạm ngưỡng hạn mức hoặc gặp sự cố mạng).

### 6.2. Tính năng AI Ước lượng Kích thước Kiện hàng (`/api/packing/dimensions/estimate`)
Khi người dùng nhập đơn hàng thủ công chỉ với tên gọi tự nhiên (ví dụ: *"10 thùng mì Hảo Hảo"* hoặc *"1 máy giặt Electrolux 9kg"*):
- Hệ thống gửi prompt đặc thù về tri thức logistics cho LLM.
- LLM trả về cấu trúc JSON chuẩn:
  ```json
  {
    "width_cm": 40.0,
    "depth_cm": 30.0,
    "height_cm": 25.0,
    "weight_kg": 8.5,
    "is_fragile": false,
    "is_heavy": false,
    "requires_cold": false
  }
  ```
- Dữ liệu này lập tức được đưa vào mô phỏng 3D Bin Packing mà không bắt người dùng phải đo đạc thủ công.

### 6.3. Chatbot Logistics & AI Trích xuất Đơn hàng
- Cho phép điều phối viên giao tiếp bằng ngôn ngữ tự nhiên: Tra cứu thông tin xe, tiến độ giao hàng, phân tích chi phí.
- Tự động bóc tách thông tin địa chỉ, số điện thoại, mặt hàng từ email hoặc tin nhắn của khách hàng để tạo đơn hàng trực tiếp vào CSDL.

---

## 7. KIẾN TRÚC GIAO TIẾP & GIAO DIỆN ĐIỀU HÀNH (API & WEB UI)

### 7.1. Cấu trúc REST API (`solver/api.py`)
- `POST /api/pipeline/run`: Kích hoạt toàn bộ quy trình từ làm sạch dữ liệu, phân bổ Dinic đến giải thuật VRP.
- `GET /api/orders`: Truy vấn danh sách đơn hàng và trạng thái giao.
- `POST /api/packing/3d`: Nhận danh sách mã đơn trên một chuyến xe, trả về ma trận tọa độ $(x, y, z)$ và kích thước hiển thị 3D.
- `POST /api/packing/dimensions/estimate`: Endpoint suy luận thông số hàng hóa bằng AI.
- `POST /api/chat`: Endpoint xử lý hội thoại với trợ lý AI.

### 7.2. Giao diện Người dùng Tương tác (Interactive Dashboard)
- **Bản đồ số (Leaflet.js)**: Hiển thị trực quan toàn bộ kho tổng (Depot), các trạm trung chuyển (Cross-docking) và hệ thống tuyến đường với các mã màu riêng biệt cho từng xe.
- **Không gian 3D tương tác (Three.js)**: Giúp thủ kho và tài xế xem trước mô hình thùng xe, xoay góc nhìn, kiểm tra thứ tự bốc dỡ từng kiện hàng theo thời gian thực.
