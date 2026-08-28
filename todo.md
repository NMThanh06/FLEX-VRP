# FLEX-VRP — Sprint Checklist (TODO)

> **Project:** SmartLog B2B — MVP  
> **Methodology:** Agile Scrum (2-week sprints)  
> **Last Updated:** 2026-08-28  
> **Reference:** [architecture.md](./architecture.md)

---

## Legend

| Symbol | Meaning |
|---|---|
| `- [ ]` | Chưa bắt đầu |
| `- [/]` | Đang thực hiện |
| `- [x]` | Hoàn thành |
| 🔴 | Blocker / Critical |
| 🟡 | Medium Priority |
| 🟢 | Nice-to-have |

---

## Phase 1: Database & Core Models Setup (Laravel)

> **Sprint:** 1–2 | **Estimated:** 1.5 weeks  
> **Goal:** Thiết lập nền tảng database, models, relationships và seed data mẫu.

### 1.1 Database Migrations

- [ ] 🔴 Tạo migration `create_users_table` — Thêm cột `role` (enum: admin, carrier, retailer), `phone`, `address`, `latitude`, `longitude`
- [ ] 🔴 Tạo migration `create_warehouses_table` — FK `user_id` (carrier), tọa độ, `is_active`
- [ ] 🔴 Tạo migration `create_products_table` — FK `warehouse_id`, SKU unique, kích thước (D×R×C), `weight_kg`, `is_heavy`, `is_fragile`, `stock_quantity`
- [ ] 🔴 Tạo migration `create_vehicles_table` — FK `user_id` (carrier), `license_plate` unique, kích thước lòng thùng, `max_weight_kg`, computed `max_volume_cm3`, `status`, `cost_per_km`
- [ ] 🔴 Tạo migration `create_orders_table` — FK `retailer_id`, `warehouse_id`, `order_code` unique, `status` enum (7 trạng thái), `time_window_start/end`, tổng weight/volume/amount
- [ ] 🔴 Tạo migration `create_order_items_table` — FK `order_id`, `product_id`, `quantity`, `unit_price`, `subtotal`, `item_weight_kg`, `item_volume_cm3`
- [ ] 🔴 Tạo migration `create_routes_table` — FK `carrier_id`, `vehicle_id`, `route_code` unique, `delivery_date`, `period_index`, `status`, `solver_metadata` (JSON)
- [ ] 🔴 Tạo migration `create_route_stops_table` — FK `route_id`, `order_id`, `stop_sequence`, tọa độ, ETA/ETD, `distance_from_prev_km`, `duration_from_prev_min`, unique constraint `[route_id, stop_sequence]`
- [ ] 🔴 Tạo migration `create_loading_plans_table` — FK `route_id`, `order_item_id`, `vehicle_id`, tọa độ `pos_x/y/z_cm`, kích thước xếp, `rotation_axis`, `loading_sequence`

### 1.2 Eloquent Models & Relationships

- [ ] 🔴 Tạo Model `User` — Relationships: `hasMany(Warehouse)`, `hasMany(Vehicle)`, `hasMany(Order)` (as retailer), `hasMany(Route)` (as carrier)
- [ ] 🔴 Tạo Model `Warehouse` — Relationships: `belongsTo(User)`, `hasMany(Product)`, `hasMany(Order)`
- [ ] 🔴 Tạo Model `Product` — Relationships: `belongsTo(Warehouse)`, `hasMany(OrderItem)`. Accessors: `volume_cm3` (computed)
- [ ] 🔴 Tạo Model `Vehicle` — Relationships: `belongsTo(User)`, `hasMany(Route)`, `hasMany(LoadingPlan)`
- [ ] 🔴 Tạo Model `Order` — Relationships: `belongsTo(User)` (retailer), `belongsTo(Warehouse)`, `hasMany(OrderItem)`, `hasMany(RouteStop)`
- [ ] 🔴 Tạo Model `OrderItem` — Relationships: `belongsTo(Order)`, `belongsTo(Product)`, `hasMany(LoadingPlan)`
- [ ] 🔴 Tạo Model `Route` — Relationships: `belongsTo(User)` (carrier), `belongsTo(Vehicle)`, `hasMany(RouteStop)`, `hasMany(LoadingPlan)`
- [ ] 🔴 Tạo Model `RouteStop` — Relationships: `belongsTo(Route)`, `belongsTo(Order)`
- [ ] 🔴 Tạo Model `LoadingPlan` — Relationships: `belongsTo(Route)`, `belongsTo(OrderItem)`, `belongsTo(Vehicle)`

### 1.3 Seeders & Factories

- [ ] 🟡 Tạo `UserSeeder` — Seed 1 Admin, 1 Carrier, 4 Retailers (tạp hóa HCM)
- [ ] 🟡 Tạo `WarehouseSeeder` — Seed 1 kho nhà máy (với tọa độ thực tế HCM)
- [ ] 🟡 Tạo `ProductSeeder` — Seed 20–30 mặt hàng mẫu (thực phẩm, mỹ phẩm, nước giải khát) với kích thước D×R×C, khối lượng, thuộc tính heavy/fragile
- [ ] 🟡 Tạo `VehicleSeeder` — Seed 2–3 xe tải mẫu (xe nhỏ 1T, xe trung 2.5T, xe lớn 5T) với kích thước lòng thùng
- [ ] 🟡 Tạo `OrderSeeder` — Seed 4–6 đơn hàng mẫu cho kịch bản MVP (4 tiệm tạp hóa)
- [ ] 🟡 Viết `DatabaseSeeder` tổng hợp — Gọi tất cả seeders theo đúng thứ tự dependency

### 1.4 Testing & Validation

- [ ] 🟡 Chạy `php artisan migrate:fresh --seed` thành công trên local
- [ ] 🟡 Viết Unit Test cho Model relationships (ít nhất 1 test/model)
- [ ] 🟢 Viết Feature Test cho database constraints (FK, unique, enum)

---

## Phase 2: Authentication & Order Management API

> **Sprint:** 2–3 | **Estimated:** 2 weeks  
> **Goal:** Xây dựng API RESTful cho Auth, quản lý sản phẩm, đơn hàng, xe cộ và kho bãi.

### 2.1 Authentication & Authorization

- [ ] 🔴 Cài đặt & cấu hình Laravel Sanctum (SPA token authentication)
- [ ] 🔴 Tạo `AuthController` — `POST /api/v1/auth/register` (phân role)
- [ ] 🔴 Tạo `AuthController` — `POST /api/v1/auth/login` (trả về token + user info)
- [ ] 🔴 Tạo `AuthController` — `POST /api/v1/auth/logout` (revoke token)
- [ ] 🔴 Tạo `AuthController` — `GET /api/v1/auth/me` (thông tin user hiện tại)
- [ ] 🔴 Tạo Middleware `CheckRole` — Phân quyền `role:admin`, `role:carrier`, `role:retailer`
- [ ] 🔴 Đăng ký middleware trong `bootstrap/app.php` và áp dụng vào route groups
- [ ] 🟡 Cấu hình Rate Limiting — 60 req/min (general), 10 req/min (optimize endpoint)

### 2.2 Product & Warehouse API (Carrier)

- [ ] 🔴 Tạo `WarehouseController@index` — `GET /api/v1/carrier/warehouses` (list kho của carrier)
- [ ] 🔴 Tạo `WarehouseController@store` — `POST /api/v1/carrier/warehouses` (tạo kho mới)
- [ ] 🔴 Tạo `WarehouseController@update` — `PUT /api/v1/carrier/warehouses/{id}` (cập nhật kho)
- [ ] 🔴 Tạo `ProductController@index` — `GET /api/v1/carrier/warehouses/{id}/products` (list sản phẩm)
- [ ] 🔴 Tạo `ProductController@store` — `POST /api/v1/carrier/products` (thêm sản phẩm mới)
- [ ] 🔴 Tạo `ProductController@update` — `PUT /api/v1/carrier/products/{id}` (cập nhật sản phẩm)
- [ ] 🔴 Tạo `ProductController@destroy` — `DELETE /api/v1/carrier/products/{id}` (xóa mềm sản phẩm)
- [ ] 🟡 Tạo `StoreProductRequest` — Validation rules: required fields, kích thước > 0, weight > 0
- [ ] 🟡 Tạo `StoreWarehouseRequest` — Validation rules: tọa độ hợp lệ, tên required

### 2.3 Vehicle Fleet API (Carrier)

- [ ] 🔴 Tạo `VehicleController@index` — `GET /api/v1/carrier/vehicles` (list xe của carrier)
- [ ] 🔴 Tạo `VehicleController@store` — `POST /api/v1/carrier/vehicles` (thêm xe)
- [ ] 🔴 Tạo `VehicleController@update` — `PUT /api/v1/carrier/vehicles/{id}` (cập nhật thông số xe)
- [ ] 🔴 Tạo `VehicleController@destroy` — `DELETE /api/v1/carrier/vehicles/{id}` (xóa xe)
- [ ] 🟡 Tạo `StoreVehicleRequest` — Validation: `license_plate` unique, kích thước > 0, `max_weight_kg` > 0

### 2.4 Product Catalog & Order API (Retailer)

- [ ] 🔴 Tạo `CatalogController@index` — `GET /api/v1/retailer/catalog` (tìm kiếm sản phẩm trong kho, filter by warehouse, search by name/SKU)
- [ ] 🔴 Tạo `CatalogController@show` — `GET /api/v1/retailer/catalog/{id}` (chi tiết sản phẩm)
- [ ] 🔴 Tạo `OrderController@store` — `POST /api/v1/retailer/orders` (tạo đơn hàng mới)
  - [ ] Validate `time_window_start` > now, `time_window_end` > `time_window_start`, khoảng cách ≥ 2h
  - [ ] Validate stock availability cho mỗi item
  - [ ] Auto-calculate `total_weight_kg`, `total_volume_cm3`, `total_amount`
  - [ ] Generate unique `order_code` (format: `ORD-YYYYMMDD-XXXX`)
- [ ] 🔴 Tạo `OrderController@index` — `GET /api/v1/retailer/orders` (danh sách đơn hàng của retailer)
- [ ] 🔴 Tạo `OrderController@show` — `GET /api/v1/retailer/orders/{id}` (chi tiết đơn + items)
- [ ] 🟡 Tạo `OrderController@cancel` — `PUT /api/v1/retailer/orders/{id}/cancel` (hủy đơn, chỉ khi status = pending)
- [ ] 🟡 Tạo `CreateOrderRequest` — Form Request với đầy đủ Poka-yoke validation rules

### 2.5 Order Management API (Carrier)

- [ ] 🔴 Tạo `CarrierOrderController@index` — `GET /api/v1/carrier/orders` (danh sách đơn hàng cần xử lý)
- [ ] 🔴 Tạo `CarrierOrderController@confirm` — `PUT /api/v1/carrier/orders/{id}/confirm` (xác nhận đơn: pending → confirmed)
- [ ] 🔴 Tạo `CarrierOrderController@reject` — `PUT /api/v1/carrier/orders/{id}/reject` (từ chối đơn: pending → cancelled)
- [ ] 🟡 Implement State Machine validation — Chỉ cho phép chuyển trạng thái hợp lệ theo sơ đồ

### 2.6 API Resource & Response Format

- [ ] 🟡 Tạo API Resources: `UserResource`, `WarehouseResource`, `ProductResource`, `VehicleResource`, `OrderResource`, `OrderItemResource`
- [ ] 🟡 Standardize API response format: `{ success: bool, data: {}, message: string, errors: {} }`
- [ ] 🟡 Tạo `ApiResponseTrait` helper cho consistent response
- [ ] 🟢 Viết API documentation (Postman collection hoặc OpenAPI/Swagger)

### 2.7 Testing

- [ ] 🟡 Viết Feature Tests cho Auth flow (register, login, logout, me)
- [ ] 🟡 Viết Feature Tests cho Order CRUD (create, list, show, cancel)
- [ ] 🟡 Viết Feature Tests cho phân quyền (Carrier không tạo được đơn, Retailer không quản lý xe)
- [ ] 🟢 Viết Feature Tests cho validation rules (Poka-yoke: time window, stock check, geocoding)

---

## Phase 3: Integration with Python Solver & n8n Workflow

> **Sprint:** 3–4 | **Estimated:** 2 weeks  
> **Goal:** Kết nối Laravel với Python Optimization Engine và thiết lập n8n tự động hóa.

### 3.1 Python Solver Service Setup

- [ ] 🔴 Tạo thư mục `solver/` chứa Python project (FastAPI + Celery)
- [ ] 🔴 Cấu hình `solver/requirements.txt` — FastAPI, Celery, Redis, OR-Tools/PuLP, numpy, scipy
- [ ] 🔴 Tạo `solver/app/main.py` — FastAPI entry point với endpoint `POST /solve`
- [ ] 🔴 Tạo `solver/app/vrp_solver.py` — VRP Solver module (FMPMD-CVRP-TW Matheuristic)
- [ ] 🔴 Tạo `solver/app/bin_packing.py` — 3D Bin Packing module (LIFO + Stacking constraints)
- [ ] 🔴 Tạo `solver/app/validation.py` — Input validation (Poka-yoke) trước khi chạy solver
- [ ] 🟡 Tạo `solver/Dockerfile` — Docker image cho Python service
- [ ] 🟡 Viết unit tests cho VRP solver với test case nhỏ (3 orders, 1 vehicle)
- [ ] 🟡 Viết unit tests cho 3D Bin Packing (kiểm tra LIFO order, stacking rules)

### 3.2 Laravel ↔ Python Integration

- [ ] 🔴 Tạo `App\Services\SolverService` — Service class gọi Python FastAPI endpoint
- [ ] 🔴 Tạo `App\Jobs\OptimizeRoutesJob` — Queue Job dispatch qua Redis
  - [ ] Compile payload (orders, vehicles, warehouse) theo API contract
  - [ ] Gọi Python service qua HTTP (Guzzle/Http facade)
  - [ ] Handle timeout & retry logic (max 3 retries, timeout 300s)
- [ ] 🔴 Tạo `POST /api/v1/carrier/optimize` — Endpoint Carrier kích hoạt tối ưu hóa
  - [ ] Validate: ít nhất 1 order confirmed, ít nhất 1 vehicle available
  - [ ] Đánh dấu selected orders → status `optimizing`
  - [ ] Dispatch `OptimizeRoutesJob` to queue
- [ ] 🔴 Tạo `POST /api/internal/solver-callback` — Endpoint nhận kết quả từ Python
  - [ ] Validate `task_id` (idempotent check)
  - [ ] Parse & lưu `routes`, `route_stops`, `loading_plans` vào database
  - [ ] Cập nhật orders → status `scheduled`
  - [ ] Broadcast kết quả qua Laravel Reverb
- [ ] 🟡 Tạo `App\Events\OptimizationCompleted` — Broadcastable event
- [ ] 🟡 Tạo `App\Events\OptimizationFailed` — Broadcastable event
- [ ] 🟡 Implement retry mechanism — Nếu solver fail, auto-retry hoặc notify carrier

### 3.3 n8n Workflow Automation

- [ ] 🔴 Cài đặt n8n (Docker self-hosted) trong Docker Compose stack
- [ ] 🔴 Tạo Workflow 1: **Order Confirmation Flow**
  - Trigger: Webhook khi order được tạo (Laravel gửi)
  - Action: Gửi email/notification xác nhận cho Retailer
  - Action: Gửi notification cho Carrier có đơn mới cần xác nhận
- [ ] 🔴 Tạo Workflow 2: **Optimization Result Flow**
  - Trigger: Webhook khi solver hoàn tất
  - Action: Gửi notification kết quả cho Carrier
  - Action: Gửi notification lịch giao hàng cho Retailer
- [ ] 🟡 Tạo Workflow 3: **Delivery Status Update Flow**
  - Trigger: Webhook khi route_stop status thay đổi
  - Action: Gửi notification realtime cho Retailer (đang giao / đã giao)
- [ ] 🟡 Tạo `App\Services\N8nWebhookService` — Service gửi event đến n8n webhooks

### 3.4 Docker Compose Configuration

- [ ] 🔴 Tạo/cập nhật `docker-compose.yml` với services: `app` (Laravel), `mysql`, `redis`, `reverb`, `solver` (Python), `n8n`
- [ ] 🟡 Cấu hình `.env` variables cho tất cả services
- [ ] 🟡 Tạo `Makefile` hoặc script `setup.sh` cho one-command setup
- [ ] 🟡 Viết `docker-compose.override.yml` cho môi trường development

### 3.5 Testing

- [ ] 🟡 Viết Integration Test: Laravel dispatch job → Mock Python response → Verify database state
- [ ] 🟡 Viết Integration Test: Solver callback endpoint → Verify routes & loading_plans created
- [ ] 🟢 End-to-end test: Full flow từ order creation → optimization → result broadcast

---

## Phase 4: Realtime Dashboard & Frontend Visualizer (React + Reverb)

> **Sprint:** 4–6 | **Estimated:** 3 weeks  
> **Goal:** Xây dựng Dashboard React với bản đồ tuyến đường và mô hình 3D thùng xe.

### 4.1 Laravel Reverb WebSocket Configuration

- [ ] 🔴 Cài đặt & cấu hình Laravel Reverb (`php artisan reverb:install`)
- [ ] 🔴 Cấu hình channels: `private-carrier.{id}`, `private-order.{id}`
- [ ] 🔴 Tạo `BroadcastServiceProvider` — Định nghĩa channel authorization rules
- [ ] 🔴 Test broadcast event thủ công với `php artisan tinker`
- [ ] 🟡 Cấu hình Reverb cho production (SSL, custom domain)

### 4.2 React Project Setup

- [ ] 🔴 Khởi tạo React project (Vite) trong thư mục `frontend/`
- [ ] 🔴 Cấu hình routing: React Router v6+ (Login, Dashboard, Orders, Vehicles, Warehouse)
- [ ] 🔴 Cài đặt dependencies: `axios`, `laravel-echo`, `pusher-js`, `react-query`/`@tanstack/react-query`
- [ ] 🔴 Tạo API client service (`frontend/src/services/api.js`) — Axios instance với token interceptor
- [ ] 🔴 Tạo Auth context & hooks (`useAuth`, `useUser`)
- [ ] 🟡 Cấu hình Laravel Echo client kết nối Reverb WebSocket

### 4.3 Authentication UI

- [ ] 🔴 Tạo trang Login (`/login`) — Form đăng nhập, role indicator
- [ ] 🔴 Tạo trang Register (`/register`) — Form đăng ký, chọn role (Retailer / Carrier)
- [ ] 🔴 Implement Protected Route — Redirect về login nếu chưa auth
- [ ] 🟡 Implement role-based routing — Carrier → Carrier Dashboard, Retailer → Retailer Dashboard

### 4.4 Retailer Interface

- [ ] 🔴 Tạo trang **Product Catalog** (`/retailer/catalog`) — Grid/List sản phẩm, search, filter by category
- [ ] 🔴 Tạo trang **Create Order** (`/retailer/orders/create`) — Chọn sản phẩm, số lượng, time window picker
- [ ] 🔴 Tạo trang **My Orders** (`/retailer/orders`) — Danh sách đơn hàng, status badges, chi tiết đơn
- [ ] 🟡 Tạo component **Order Status Tracker** — Realtime status updates qua WebSocket
- [ ] 🟡 Tạo component **Time Window Picker** — Date/Time range picker UX-friendly

### 4.5 Carrier Dashboard

- [ ] 🔴 Tạo trang **Carrier Dashboard** (`/carrier/dashboard`) — Overview: tổng xe, tổng đơn, đơn chờ xử lý
- [ ] 🔴 Tạo trang **Pending Orders** (`/carrier/orders`) — Danh sách đơn hàng cần confirm/reject
- [ ] 🔴 Tạo trang **Vehicle Management** (`/carrier/vehicles`) — CRUD xe tải, hiển thị trạng thái
- [ ] 🔴 Tạo trang **Warehouse & Products** (`/carrier/warehouse`) — CRUD kho & sản phẩm
- [ ] 🔴 Tạo nút **"Tối ưu hóa"** — Gọi `POST /optimize`, hiển thị loading state
- [ ] 🔴 Tạo trang **Routes Result** (`/carrier/routes`) — Danh sách tuyến đường tối ưu, chi tiết từng route

### 4.6 Map Visualization (Mapbox / Leaflet)

- [ ] 🔴 Cài đặt Mapbox GL JS hoặc Leaflet + React wrapper
- [ ] 🔴 Tạo component **RouteMap** — Render tuyến đường trên bản đồ
  - [ ] Hiển thị warehouse marker (điểm xuất phát)
  - [ ] Hiển thị route stops markers (đánh số thứ tự)
  - [ ] Vẽ polyline nối các điểm theo thứ tự giao hàng
  - [ ] Popup thông tin: tên cửa hàng, ETA, khối lượng giao
- [ ] 🟡 Hỗ trợ hiển thị nhiều routes cùng lúc (phân biệt theo màu xe)
- [ ] 🟡 Animation: Vẽ tuyến đường theo thứ tự (progressive drawing)
- [ ] 🟢 Toggle layers: hiển thị/ẩn từng tuyến đường

### 4.7 3D Loading Plan Viewer (Three.js)

- [ ] 🔴 Cài đặt Three.js + React Three Fiber (`@react-three/fiber`, `@react-three/drei`)
- [ ] 🔴 Tạo component **TruckContainer3D** — Render hình hộp thùng xe (wireframe)
- [ ] 🔴 Tạo component **CargoItem3D** — Render từng kiện hàng theo tọa độ `(x, y, z)` từ `loading_plans`
  - [ ] Màu sắc phân biệt: 🔴 Hàng nặng (đỏ), 🔵 Hàng thường (xanh), 🟡 Hàng dễ vỡ (vàng)
  - [ ] Label hiển thị tên sản phẩm + số thứ tự bốc hàng
- [ ] 🔴 Tạo controls: Xoay (orbit), Zoom, Pan cho camera 3D
- [ ] 🟡 Thêm tooltip hover: hiển thị chi tiết sản phẩm, order, kích thước
- [ ] 🟡 Thêm animation: render từng kiện hàng theo `loading_sequence` (step-by-step)
- [ ] 🟢 Export screenshot 3D view (png) để in hướng dẫn xếp hàng

### 4.8 Realtime Integration

- [ ] 🔴 Kết nối Laravel Echo lắng nghe channel `private-carrier.{id}`
- [ ] 🔴 Handle event `optimization.started` — Show loading spinner, progress bar
- [ ] 🔴 Handle event `optimization.completed` — Fetch & render routes + loading plans
- [ ] 🔴 Handle event `optimization.failed` — Show error notification, retry button
- [ ] 🟡 Handle event `order.status.updated` — Update order status badge realtime

### 4.9 UI/UX Polish

- [ ] 🟡 Responsive design — Desktop-first, mobile-friendly
- [ ] 🟡 Dark mode toggle
- [ ] 🟡 Skeleton loading states cho tất cả data-fetching pages
- [ ] 🟡 Toast notification system (success, error, warning)
- [ ] 🟢 Onboarding tour cho Carrier Dashboard (first-time user)

### 4.10 Testing

- [ ] 🟡 Viết Component tests cho Map + 3D viewer (render đúng dữ liệu)
- [ ] 🟡 Viết Integration tests cho WebSocket event handling
- [ ] 🟢 Cross-browser testing (Chrome, Firefox, Safari)

---

## Phase 5: Weather/Traffic Integration & Backtesting (MVP Finalization)

> **Sprint:** 6–7 | **Estimated:** 2 weeks  
> **Goal:** Tích hợp dữ liệu thời tiết/giao thông, chạy kịch bản MVP, và hoàn thiện tài liệu.

### 5.1 OpenWeatherMap API Integration

- [ ] 🔴 Đăng ký API Key OpenWeatherMap
- [ ] 🔴 Tạo `App\Services\WeatherService` — Gọi API lấy dữ liệu thời tiết theo tọa độ
- [ ] 🔴 Truyền weather data vào solver payload (`config.use_weather_adjustment = true`)
- [ ] 🟡 Tạo `solver/app/weather_factor.py` — Module tính hệ số điều chỉnh thời gian do mưa/ngập
- [ ] 🟡 Cache weather data (Redis, TTL 30 phút) để giảm API calls

### 5.2 Traffic Data Integration

- [ ] 🔴 Kết nối API giao thông thực tế (Google Maps Distance Matrix API hoặc OSRM)
- [ ] 🔴 Tạo `App\Services\TrafficMatrixService` — Build ma trận thời gian di chuyển giữa các điểm
- [ ] 🔴 Truyền traffic matrix vào solver payload
- [ ] 🟡 Tạo `solver/app/traffic_matrix.py` — Module xử lý & chuẩn hóa ma trận giao thông
- [ ] 🟡 Implement time-dependent travel times (ma trận khác nhau theo khung giờ: sáng, trưa, chiều)

### 5.3 AI Agent / LLM Integration (OpenRouter)

- [ ] 🟡 Tạo `App\Services\AIAgentService` — Wrapper gọi OpenRouter API
- [ ] 🟡 Implement LLM Router logic:
  - Tác vụ phức tạp (phân tích đơn hàng bất thường) → Claude 3.5 / GPT-4o
  - Tra cứu nhanh (tra cứu sản phẩm, FAQ) → Gemini 1.5 Flash / Llama 3
- [ ] 🟡 Implement State Machine cho AI Agent (trạng thái hội thoại)
- [ ] 🟢 Implement HITL triggers — AI gợi ý, Carrier xác nhận

### 5.4 MVP Backtesting Scenario

- [ ] 🔴 Chuẩn bị dữ liệu kịch bản MVP:
  - 1 kho nhà máy (Quận 7, HCM)
  - 4 tiệm tạp hóa (Quận 1, Quận 3, Quận 5, Quận 10)
  - 2 xe tải (1 tấn + 2.5 tấn)
  - 20 mặt hàng (đa dạng kích thước & thuộc tính)
  - 4 đơn hàng với time windows khác nhau
- [ ] 🔴 Chạy full flow: Retailer đặt hàng → Carrier xác nhận → Tối ưu hóa → Xem kết quả
- [ ] 🔴 Verify kết quả:
  - [ ] Routes hợp lý (không vi phạm time windows)
  - [ ] Loading plans hợp lệ (không vượt kích thước thùng xe, LIFO đúng thứ tự)
  - [ ] Hàng nặng phía dưới, hàng dễ vỡ phía trên
  - [ ] Tổng tải trọng ≤ max_weight_kg từng xe
- [ ] 🟡 So sánh kết quả tối ưu vs sắp xếp thủ công (tiết kiệm bao nhiêu % quãng đường)
- [ ] 🟡 Ghi nhận performance metrics: thời gian solver chạy, số lần retry

### 5.5 Documentation & Operations Guide

- [ ] 🔴 Cập nhật `README.md` — Hướng dẫn cài đặt, cấu hình, chạy dự án
- [ ] 🔴 Viết `DEPLOYMENT.md` — Hướng dẫn deploy Docker Compose lên server
- [ ] 🔴 Viết `API_DOCS.md` — API Reference cho tất cả endpoints
- [ ] 🟡 Viết `OPERATIONS.md` — Hướng dẫn vận hành: monitoring, backup, troubleshooting
- [ ] 🟡 Cập nhật `architecture.md` — Bổ sung các thay đổi phát sinh trong quá trình phát triển
- [ ] 🟡 Viết `CHANGELOG.md` — Ghi lại các thay đổi theo phiên bản

### 5.6 Performance & Security Hardening

- [ ] 🟡 Database indexing review — Kiểm tra query performance với `EXPLAIN`
- [ ] 🟡 API response caching — Cache danh sách sản phẩm, thông tin kho (Redis)
- [ ] 🟡 Rate limiting fine-tuning — Điều chỉnh theo tải thực tế
- [ ] 🟡 Input sanitization review — XSS, SQL Injection, CSRF
- [ ] 🟢 Load testing — JMeter/k6 cho 50 concurrent users
- [ ] 🟢 Security audit — Dependency vulnerability scan (`composer audit`, `npm audit`)

### 5.7 Final Review & Handoff

- [ ] 🔴 Code review toàn bộ codebase — Clean code, naming conventions, dead code removal
- [ ] 🔴 UAT (User Acceptance Testing) — Carrier & Retailer flow hoàn chỉnh
- [ ] 🟡 Demo recording — Quay video demo MVP flow cho stakeholders
- [ ] 🟡 Retrospective — Ghi nhận bài học kinh nghiệm, backlog cho version 2.0

---

## Backlog (Post-MVP)

> Các tính năng dự kiến cho phiên bản tiếp theo, **không** nằm trong scope MVP.

- [ ] Multi-tenant support (nhiều Carrier trên cùng hệ thống)
- [ ] Mobile App (React Native) cho Retailer đặt hàng
- [ ] Driver App — Ứng dụng cho tài xế với navigation turn-by-turn
- [ ] Advanced Analytics Dashboard — Báo cáo hiệu suất vận tải, chi phí
- [ ] Automatic re-routing — Tự động tối ưu lại khi có đơn hàng mới phát sinh
- [ ] Dynamic pricing — Tính phí vận chuyển động dựa trên khoảng cách & tải trọng
- [ ] Integration với ERP/POS hệ thống kho bãi bên thứ ba
- [ ] Chatbot AI hỗ trợ Retailer đặt hàng bằng ngôn ngữ tự nhiên

---

> **Document Status:** ✅ Living Document — Cập nhật theo từng Sprint.  
> **Tracking Tool:** Chuyển sang Jira/Linear khi team mở rộng.
