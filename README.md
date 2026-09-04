<p align="center">
  <h1 align="center">🚛 FLEX-VRP</h1>
  <p align="center">
    <strong>SmartLog B2B — Tối ưu Định tuyến & Xếp hàng 3D cho Vận tải B2B</strong>
  </p>
  <p align="center">
    <a href="#-cài-đặt-nhanh-với-docker">Cài đặt</a> •
    <a href="#-kiến-trúc-hệ-thống">Kiến trúc</a> •
    <a href="#-tech-stack">Tech Stack</a> •
    <a href="#-lệnh-thường-dùng">Lệnh thường dùng</a> •
    <a href="#-tài-liệu-kỹ-thuật">Tài liệu</a>
  </p>
</p>

---

## 📋 Giới thiệu

**FLEX-VRP** là hệ thống Web App B2B giải quyết bài toán **Tối ưu Định tuyến Giao hàng Đa kỳ (Multi-Period VRP)** kết hợp **Tính toán Sơ đồ Bốc xếp 3D** cho chuỗi cung ứng vận tải:

- 🏭 **Kho nhà máy (Carrier):** Quản lý đội xe, danh mục hàng hóa → Kích hoạt thuật toán → Xem lịch trình tối ưu + sơ đồ xếp hàng 3D trên Dashboard.
- 🛒 **Tạp hóa / Shop (Retailer):** Duyệt danh mục kho → Đặt hàng → Chọn khung giờ nhận hàng mong muốn.

### Hai Động cơ Thuật toán Cốt lõi

| Thuật toán | Mô tả |
|---|---|
| **VRP Solver** (FMPMD-CVRP-TW) | Tự động gom/chia đơn, tính lộ trình đa kỳ né kẹt xe, kết hợp dữ liệu giao thông & thời tiết thực tế |
| **3D Bin Packing** | Tính toán tọa độ xếp hàng (LIFO theo thứ tự giao + hàng nặng dưới / dễ vỡ trên) → Render 3D trên Dashboard |

---

## 🛠 Tech Stack

| Layer | Công nghệ | Version |
|---|---|---|
| **Backend** | Laravel (PHP) | 12.x (PHP 8.2) |
| **Database** | MySQL | 8.0 |
| **Cache & Queue** | Redis | 7.4 |
| **Realtime** | Laravel Reverb | WebSocket |
| **Frontend** | React + Vite | 18+ / 7.x |
| **Map** | Mapbox GL / Leaflet | — |
| **3D Viewer** | Three.js | — |
| **Optimization Engine** | Python (FastAPI + Celery) | 3.11+ |
| **Automation** | n8n | Self-hosted |
| **AI Agent** | OpenRouter API | Claude / GPT-4o |
| **Container** | Docker + Docker Compose | 29.x / 5.x |

---

## 🚀 Cài đặt nhanh với Docker

### Yêu cầu

Chỉ cần cài **2 thứ** trên máy:

| Phần mềm | Download |
|---|---|
| **Git** | [git-scm.com](https://git-scm.com/downloads) |
| **Docker Desktop** | [docker.com](https://www.docker.com/products/docker-desktop/) |

> ⚠️ **Windows:** Sau khi cài Docker Desktop, mở app và đảm bảo Docker Engine đang chạy (icon 🐳 trên taskbar).

### Bước 1 — Clone dự án

```bash
git clone https://github.com/NMThanh06/FLEX-VRP.git
cd FLEX-VRP
```

### Bước 2 — Khởi chạy Docker

```bash
docker compose up -d
```

> ⏳ Lần đầu chạy sẽ mất **3–5 phút** để tải image và build. Các lần sau chỉ mất vài giây.

Docker sẽ tự động thực hiện:
- ✅ Dựng container: PHP 8.2, Nginx, MySQL 8.0, Redis 7.4
- ✅ Cài `composer install` & `npm install`
- ✅ Copy `.env.example` → `.env` và generate `APP_KEY`
- ✅ Chạy `php artisan migrate` tạo bảng database
- ✅ Khởi động Vite dev server (Hot Reload)

### Bước 3 — Mở trình duyệt

| Service | URL | Mô tả |
|---|---|---|
| 🌐 **App** | [http://localhost:8000](http://localhost:8000) | Trang web chính |
| 🗄️ **phpMyAdmin** | [http://localhost:8080](http://localhost:8080) | Quản lý database (GUI) |
| ⚡ **Vite** | [http://localhost:5173](http://localhost:5173) | Frontend dev server |

**Xong! 🎉** Dự án đã chạy.

---

## 💻 Lệnh thường dùng

### Quản lý Docker

```bash
# Khởi chạy tất cả services
docker compose up -d

# Tắt tất cả services
docker compose down

# Xem logs (tất cả hoặc từng service)
docker compose logs -f
docker compose logs -f app

# Restart 1 service
docker compose restart app

# Reset toàn bộ (xóa database, làm lại từ đầu)
docker compose down -v
docker compose up -d
```

### Laravel Artisan

Tất cả lệnh `php artisan` chạy qua Docker:

```bash
# Chạy migration
docker compose exec app php artisan migrate

# Chạy migration + seed data mẫu
docker compose exec app php artisan migrate:fresh --seed

# Tạo migration mới
docker compose exec app php artisan make:migration create_example_table

# Tạo Model
docker compose exec app php artisan make:model Example -mfs

# Tạo Controller
docker compose exec app php artisan make:controller ExampleController --api

# Xóa cache
docker compose exec app php artisan optimize:clear

# Chạy queue worker
docker compose exec app php artisan queue:work

# Mở Tinker (Laravel REPL)
docker compose exec app php artisan tinker

# Chạy tests
docker compose exec app php artisan test
```

### Composer & NPM

```bash
# Cài thêm package PHP
docker compose exec app composer require package/name

# Cài thêm package NPM
docker compose exec app npm install package-name

# Build frontend cho production
docker compose exec app npm run build
```

### Database

```bash
# Truy cập MySQL CLI
docker compose exec mysql mysql -u flexvrp -pflexvrp_secret flexvrp

# Backup database
docker compose exec mysql mysqldump -u flexvrp -pflexvrp_secret flexvrp > backup.sql

# Restore database
docker compose exec -T mysql mysql -u flexvrp -pflexvrp_secret flexvrp < backup.sql
```

---

## 📁 Cấu trúc dự án

```
FLEX-VRP/
├── app/                    # Laravel Application (Models, Controllers, Services)
│   ├── Http/Controllers/   # API Controllers
│   ├── Models/             # Eloquent Models
│   ├── Services/           # Business Logic Services
│   └── Jobs/               # Queue Jobs
├── config/                 # Laravel Configuration
├── database/
│   ├── migrations/         # Database Migrations
│   ├── seeders/            # Data Seeders
│   └── factories/          # Model Factories
├── docker/                 # 🐳 Docker Configuration
│   ├── php/
│   │   ├── Dockerfile      # PHP 8.2-FPM image
│   │   └── php.ini         # PHP settings
│   ├── nginx/
│   │   └── default.conf    # Nginx config
│   ├── mysql/
│   │   ├── Dockerfile      # MySQL 8.0 image
│   │   └── my.cnf          # MySQL settings
│   ├── supervisor/
│   │   └── supervisord.conf # Queue worker config
│   └── entrypoint.sh       # Auto-setup script
├── public/                 # Public assets
├── resources/              # Views, CSS, JS
├── routes/                 # API & Web routes
├── storage/                # Logs, cache, uploads
├── tests/                  # PHPUnit Tests
├── architecture.md         # 📐 Tài liệu kiến trúc hệ thống
├── todo.md                 # ✅ Sprint checklist
├── docker-compose.yml      # 🐳 Docker Compose config
├── .env.example            # Template biến môi trường
├── composer.json           # PHP dependencies
└── package.json            # Node.js dependencies
```

---

## 🏗 Kiến trúc Hệ thống

```
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                         │
│                                                                 │
│  ┌──────────┐   ┌──────────┐  ┌──────────┐   ┌──────────┐       │
│  │  Nginx   │   │ Laravel  │  │  Vite    │   │phpMyAdmin│       │
│  │  :8000   │   │ PHP-FPM  │  │  :5173   │   │  :8080   │       │
│  └────┬─────┘   └────┬─────┘  └──────────┘   └────┬─────┘       │
│       │              │                            |             │
│  ┌────┴──────────────┴────────────────────────────┴─────┐       │
│  │                  Internal Network                    │       │
│  └────┬──────────────┬──────────────────────────────────┘       │
│       │              │                                          │
│  ┌────┴─────┐  ┌─────┴────┐                                     │
│  │  MySQL   │  │  Redis   │                                     │
│  │  :3306   │  │  :6379   │                                     │
│  └──────────┘  └──────────┘                                     │
└─────────────────────────────────────────────────────────────────┘
```

> 📐 Xem chi tiết kiến trúc đầy đủ tại [architecture.md](./architecture.md)

---

## 🔐 Thông tin kết nối (Development)

| Service | Host | Port | Username | Password |
|---|---|---|---|---|
| **MySQL** | `localhost` | `3306` | `flexvrp` | `flexvrp_secret` |
| **MySQL Root** | `localhost` | `3306` | `root` | `root_secret` |
| **Redis** | `localhost` | `6379` | — | — |
| **phpMyAdmin** | `localhost` | `8080` | `flexvrp` | `flexvrp_secret` |

> ⚠️ Đây là credentials cho môi trường **development** local. **KHÔNG** sử dụng cho production.

---

## 📝 Quy trình phát triển (Developer Workflow)

### Khi bạn muốn code tính năng mới

```bash
# 1. Tạo branch mới
git checkout -b feature/ten-tinh-nang

# 2. Đảm bảo Docker đang chạy
docker compose up -d

# 3. Code bình thường trên VS Code
#    (sửa file → save → tự động cập nhật trong container)

# 4. Nếu cần tạo migration
docker compose exec app php artisan make:migration create_xxx_table

# 5. Chạy migration
docker compose exec app php artisan migrate

# 6. Chạy tests
docker compose exec app php artisan test

# 7. Commit & Push
git add .
git commit -m "feat: mô tả tính năng"
git push origin feature/ten-tinh-nang
```

### Khi pull code mới từ Git

```bash
git pull origin main

# Cài lại dependencies nếu composer.json thay đổi
docker compose exec app composer install

# Chạy migration nếu có migration mới
docker compose exec app php artisan migrate
```

---

## 🐛 Xử lý lỗi thường gặp

<details>
<summary><strong>❌ Port 8000 đã được sử dụng</strong></summary>

Đổi port trong `docker-compose.yml`:
```yaml
nginx:
  ports:
    - "8001:80"   # Đổi 8000 thành 8001
```
Sau đó: `docker compose up -d`
</details>

<details>
<summary><strong>❌ MySQL không khởi động được</strong></summary>

```bash
# Xóa data cũ và tạo lại
docker compose down -v
docker compose up -d
```
</details>

<details>
<summary><strong>❌ Permission denied trên storage/</strong></summary>

```bash
docker compose exec app chmod -R 775 storage bootstrap/cache
```
</details>

<details>
<summary><strong>❌ Composer/NPM install bị lỗi</strong></summary>

```bash
# Xóa cache và cài lại
docker compose exec app composer clear-cache
docker compose exec app composer install

docker compose exec app npm cache clean --force
docker compose exec app npm install
```
</details>

---

## 📚 Tài liệu kỹ thuật

| File | Mô tả |
|---|---|
| [architecture.md](./architecture.md) | Kiến trúc hệ thống, ERD, Database Schema, Data Flow, Security |
| [todo.md](./todo.md) | Sprint checklist — Tiến độ phát triển theo từng Phase |

---

## 📄 License

Dự án được phân phối dưới giấy phép [Apache License 2.0](./LICENSE).

---

<p align="center">
  <sub>Built with ❤️ by <strong>FLEX-VRP Team</strong></sub>
</p>
