"""
FLEX-VRP — SQLite Database Layer
Quản lý dữ liệu persistent: vị trí, xe, chuyến đi, AI corrections, sự kiện.

DB file: solver/data/flex_vrp.db (auto-create)
"""

import sqlite3
import json
import os
import pymysql
from datetime import datetime, date
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "flex_vrp.db"


def _get_conn() -> sqlite3.Connection:
    """Tạo connection tới SQLite DB."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # Trả về dict-like rows
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _get_mysql_conn():
    """Tạo kết nối tới MySQL flexvrp database (với auto-reconnect & credentials từ .env)."""
    try:
        import pymysql
        import pymysql.cursors
        env_file = Path(__file__).parent.parent / ".env"
        db_host = "127.0.0.1"
        db_port = 3306
        db_user = "root"
        db_pass = ""
        db_name = "flexvrp"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("DB_HOST="): db_host = line.split("=", 1)[1].strip().strip('"\'')
                elif line.startswith("DB_PORT="):
                    p = line.split("=", 1)[1].strip().strip('"\'')
                    if p.isdigit(): db_port = int(p)
                elif line.startswith("DB_USERNAME="): db_user = line.split("=", 1)[1].strip().strip('"\'')
                elif line.startswith("DB_PASSWORD="): db_pass = line.split("=", 1)[1].strip().strip('"\'')
                elif line.startswith("DB_DATABASE="): db_name = line.split("=", 1)[1].strip().strip('"\'')

        return pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            database=db_name,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
    except Exception:
        return None


def init_db():
    """Tạo tất cả tables nếu chưa có, seed dữ liệu cơ bản."""
    conn = _get_conn()
    try:
        conn.executescript("""
            -- Vị trí đã lưu
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('depot', 'delivery')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Loại xe
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                max_speed_kmh REAL NOT NULL,
                avg_city_speed_kmh REAL NOT NULL,
                capacity_kg REAL DEFAULT 0,
                capacity_cbm REAL DEFAULT 0,
                fuel_type TEXT DEFAULT 'gasoline',
                specs_source TEXT DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Lịch sử chuyến đi
            CREATE TABLE IF NOT EXISTS trip_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER,
                route_json TEXT NOT NULL,
                estimated_time_min REAL NOT NULL,
                actual_time_min REAL,
                departure_time TEXT,
                arrival_time TEXT,
                estimated_distance_km REAL NOT NULL,
                weather_factor REAL DEFAULT 1.0,
                target_hour INTEGER,
                num_stops INTEGER,
                num_traffic_lights INTEGER DEFAULT 0,
                status TEXT DEFAULT 'planned',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
            );

            -- Hiệu chỉnh AI theo khu vực
            CREATE TABLE IF NOT EXISTS ai_corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zone_lat REAL NOT NULL,
                zone_lon REAL NOT NULL,
                hour_bucket INTEGER NOT NULL,
                correction_factor REAL DEFAULT 1.0,
                sample_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(zone_lat, zone_lon, hour_bucket)
            );

            -- Sự kiện ảnh hưởng giao thông
            CREATE TABLE IF NOT EXISTS traffic_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                traffic_impact_factor REAL DEFAULT 1.0,
                description TEXT,
                source TEXT DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- ═══════════════════════════════════════
            -- PHASE II: B2B Order Management Tables
            -- ═══════════════════════════════════════

            -- Bảng quản lý datasets (danh sách đơn hàng)
            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT 'Bảng mặc định',
                description TEXT DEFAULT '',
                is_active INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Khách hàng (tiệm tạp hóa / retailer)
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                phone TEXT,
                preferred_time_start TEXT DEFAULT '08:00',
                preferred_time_end TEXT DEFAULT '17:00',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Đơn hàng B2B (mã 6 ký tự)
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_code TEXT NOT NULL UNIQUE,
                customer_id INTEGER,
                dataset_id INTEGER DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','incomplete','confirmed','optimizing','scheduled','in_transit','delivered','cancelled')),
                is_urgent INTEGER DEFAULT 0,
                total_quantity INTEGER DEFAULT 0,
                total_weight_kg REAL DEFAULT 0,
                total_volume_cbm REAL DEFAULT 0,
                time_window_start TEXT,
                time_window_end TEXT,
                delivery_date_preferred TEXT,
                order_date TEXT,
                notes TEXT,
                source TEXT DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
            );

            -- Chi tiết đơn hàng (sản phẩm trong đơn)
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                weight_per_unit_kg REAL DEFAULT 1.0,
                volume_per_unit_cbm REAL DEFAULT 0.01,
                total_weight_kg REAL,
                total_volume_cbm REAL,
                is_fragile INTEGER DEFAULT 0,
                is_heavy INTEGER DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
            );

            -- Danh mục hàng hóa dùng chung khi nhập/sửa đơn
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_unit TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL UNIQUE,
                image_url TEXT DEFAULT '',
                packaging TEXT DEFAULT '',
                weight_per_unit_kg REAL DEFAULT 1.0,
                dimensions_m TEXT DEFAULT '',
                volume_per_unit_cbm REAL DEFAULT 0.01,
                stock_quantity INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Lịch giao hàng (kết quả split delivery)
            CREATE TABLE IF NOT EXISTS delivery_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                vehicle_id INTEGER,
                delivery_date TEXT NOT NULL,
                period_index INTEGER DEFAULT 1,
                assigned_quantity INTEGER NOT NULL,
                assigned_weight_kg REAL DEFAULT 0,
                status TEXT DEFAULT 'planned'
                    CHECK(status IN ('planned','in_progress','completed','cancelled')),
                route_id INTEGER,
                stop_sequence INTEGER,
                eta TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
            );

            -- Route Pool (tất cả routes khả thi cho Set-Partitioning)
            CREATE TABLE IF NOT EXISTS route_pool (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                vehicle_id INTEGER,
                delivery_date TEXT,
                period_index INTEGER DEFAULT 1,
                route_json TEXT NOT NULL,
                stop_ids TEXT NOT NULL,
                total_distance_km REAL DEFAULT 0,
                total_time_min REAL DEFAULT 0,
                total_load_kg REAL DEFAULT 0,
                total_load_cbm REAL DEFAULT 0,
                cost REAL DEFAULT 0,
                is_selected INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
            );

            -- Chat sessions (chatbot state)
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                messages TEXT DEFAULT '[]',
                pending_orders TEXT DEFAULT '[]',
                status TEXT DEFAULT 'active'
                    CHECK(status IN ('active','completed','expired')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Optimization runs (progress tracking)
            CREATE TABLE IF NOT EXISTS optimization_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL UNIQUE,
                status TEXT DEFAULT 'pending'
                    CHECK(status IN ('pending','running','completed','failed')),
                progress_pct INTEGER DEFAULT 0,
                current_stage TEXT DEFAULT '',
                total_orders INTEGER DEFAULT 0,
                total_vehicles INTEGER DEFAULT 0,
                planning_days INTEGER DEFAULT 5,
                result_json TEXT,
                error_message TEXT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- ═══════════════════════════════════════
            -- PHASE 2: Vehicle Cargo Specs & Dimensions
            -- ═══════════════════════════════════════

            -- Kích thước thùng xe (thông số xếp hàng 2D/3D)
            CREATE TABLE IF NOT EXISTS vehicle_cargo_specs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL UNIQUE,
                cargo_width_cm REAL NOT NULL,   -- Chiều rộng thùng (ngang xe)
                cargo_depth_cm REAL NOT NULL,   -- Chiều dài thùng (trục xe từ cabin -> cửa sau)
                cargo_height_cm REAL NOT NULL,  -- Chiều cao thùng
                door_position TEXT DEFAULT 'rear',
                max_layers INTEGER DEFAULT 2,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
            );

            -- Danh mục kích thước kiện hàng chuẩn
            CREATE TABLE IF NOT EXISTS cargo_dimensions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_identifier TEXT NOT NULL UNIQUE,
                width_cm REAL NOT NULL DEFAULT 30,
                depth_cm REAL NOT NULL DEFAULT 40,
                height_cm REAL NOT NULL DEFAULT 30,
                weight_kg REAL DEFAULT 10,
                is_fragile INTEGER DEFAULT 0,
                is_heavy INTEGER DEFAULT 0,
                requires_cold INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

        # Migration: thêm order_date và is_urgent nếu DB cũ chưa có
        try:
            conn.execute("ALTER TABLE orders ADD COLUMN order_date TEXT")
            conn.commit()
        except Exception:
            pass
            
        try:
            conn.execute("ALTER TABLE orders ADD COLUMN is_urgent INTEGER DEFAULT 0")
            conn.commit()
        except Exception:
            pass

        # Migration Phase 2: thêm kích thước và thuộc tính cho order_items
        for col, col_type in [
            ("width_cm", "REAL DEFAULT 0"),
            ("depth_cm", "REAL DEFAULT 0"),
            ("height_cm", "REAL DEFAULT 0"),
            ("requires_cold", "INTEGER DEFAULT 0"),
        ]:
            try:
                conn.execute(f"ALTER TABLE order_items ADD COLUMN {col} {col_type}")
                conn.commit()
            except Exception:
                pass

        # Migration Phase 2: Multi-Dataset
        try:
            conn.execute("ALTER TABLE orders ADD COLUMN dataset_id INTEGER DEFAULT 1")
            conn.commit()
        except Exception:
            pass
            
        try:
            conn.execute("INSERT OR IGNORE INTO datasets (id, name, is_active) VALUES (1, 'Bảng mặc định', 1)")
            conn.commit()
        except Exception:
            pass

        # Seed events nếu table trống
        count = conn.execute("SELECT COUNT(*) FROM traffic_events").fetchone()[0]
        if count == 0:
            _seed_events(conn)

        # Seed vehicle cargo specs & cargo dimensions
        _seed_vehicle_cargo_specs(conn)
        _seed_cargo_dimensions(conn)

        print(f"[DB] Initialized at: {DB_PATH}")
    finally:
        conn.close()


def _seed_events(conn: sqlite3.Connection):
    """Seed sự kiện lễ Tết / mùa Việt Nam."""
    year = datetime.now().year
    events = [
        # Tết Nguyên Đán (ước lượng, cần chỉnh theo năm)
        (f"Tết Nguyên Đán {year}", "holiday",
         f"{year}-01-25", f"{year}-02-05", 0.5,
         "Dân về quê ăn Tết, đường vắng hẳn. Giảm ~50% mật độ xe."),
        # Nghỉ hè
        (f"Nghỉ hè {year}", "school",
         f"{year}-06-15", f"{year}-08-31", 0.85,
         "Sinh viên về quê, ít xe hơn ~15% so với bình thường."),
        # Nhập học
        (f"Nhập học {year}", "school",
         f"{year}-09-01", f"{year}-09-15", 1.15,
         "Sinh viên nhập học, đông hơn ~15% đặc biệt khu vực trường ĐH."),
        # Quốc khánh
        (f"Quốc khánh 2/9 {year}", "holiday",
         f"{year}-09-02", f"{year}-09-02", 0.6,
         "Nghỉ lễ Quốc khánh, đường vắng."),
        # Giỗ tổ Hùng Vương
        (f"Giỗ tổ Hùng Vương {year}", "holiday",
         f"{year}-04-18", f"{year}-04-18", 0.65,
         "Nghỉ lễ, đường vắng."),
        # 30/4 - 1/5
        (f"30/4 - 1/5 {year}", "holiday",
         f"{year}-04-30", f"{year}-05-01", 0.55,
         "Nghỉ lễ dài ngày, dân đi chơi và về quê."),
        # Noel + Tết Dương lịch
        (f"Noel - Tết Dương {year}", "holiday",
         f"{year}-12-24", f"{year}-12-31", 1.2,
         "Mua sắm Noel, countdown, đường đông đúc hơn ~20%."),
        # Rằm tháng Giêng (ước lượng)
        (f"Rằm tháng Giêng {year}", "festival",
         f"{year}-02-12", f"{year}-02-12", 1.1,
         "Lễ hội chùa chiền, khu vực trung tâm đông hơn ~10%."),
    ]
    conn.executemany(
        """INSERT INTO traffic_events 
           (event_name, event_type, start_date, end_date, traffic_impact_factor, description, source) 
           VALUES (?, ?, ?, ?, ?, ?, 'seed')""",
        events
    )
    conn.commit()
    print(f"[DB] Seeded {len(events)} traffic events")


def _seed_vehicle_cargo_specs(conn: sqlite3.Connection):
    """Seed thông số thùng xe cho các xe hiện có nếu chưa có spec."""
    try:
        vehicles = conn.execute("SELECT id, name, capacity_kg FROM vehicles").fetchall()
        for v in vehicles:
            vid = v["id"]
            existing = conn.execute("SELECT id FROM vehicle_cargo_specs WHERE vehicle_id=?", (vid,)).fetchone()
            if existing:
                continue
            cap = float(v["capacity_kg"] or 1000)
            if cap <= 1200:
                # 1 Tấn (VD: Suzuki Carry)
                w, d, h = 160.0, 300.0, 160.0
                note = "Preset 1T (300×160×160cm)"
            elif cap <= 3000:
                # 2.5 Tấn (VD: Hyundai Porter)
                w, d, h = 190.0, 430.0, 185.0
                note = "Preset 2.5T (430×190×185cm)"
            else:
                # 5 Tấn (VD: Isuzu NQR)
                w, d, h = 220.0, 600.0, 210.0
                note = "Preset 5T (600×220×210cm)"
            
            conn.execute(
                """INSERT INTO vehicle_cargo_specs 
                   (vehicle_id, cargo_width_cm, cargo_depth_cm, cargo_height_cm, door_position, max_layers, notes)
                   VALUES (?, ?, ?, ?, 'rear', 2, ?)""",
                (vid, w, d, h, note)
            )
        conn.commit()
    except Exception as e:
        print(f"[DB] Warning seed vehicle_cargo_specs: {e}")


def _seed_cargo_dimensions(conn: sqlite3.Connection):
    """Seed bảng kích thước kiện hàng chuẩn (FMCG)."""
    standard_items = [
        ("Thùng mì gói Hảo Hảo", 38.0, 28.0, 22.0, 5.0, 0, 0, 0),
        ("Thùng nước ngọt Coca", 40.0, 26.0, 14.0, 8.5, 0, 1, 0),
        ("Thùng sữa Vinamilk", 36.0, 24.0, 15.0, 6.0, 1, 0, 0),
        ("Thùng bia Tiger", 40.0, 27.0, 16.0, 9.0, 0, 1, 0),
        ("Thùng dầu ăn Neptune", 34.0, 26.0, 28.0, 10.0, 0, 1, 0),
        ("Thùng nước suối Lavie", 40.0, 26.0, 24.0, 6.0, 0, 0, 0),
        ("Thùng bánh Oreo", 32.0, 22.0, 18.0, 3.0, 0, 0, 0),
        ("Thùng bột giặt OMO", 42.0, 30.0, 25.0, 5.0, 0, 1, 0),
        ("Thùng kem dưỡng da", 28.0, 20.0, 16.0, 0.5, 1, 0, 0),
        ("Thùng sữa rửa mặt", 30.0, 22.0, 18.0, 0.8, 1, 0, 0),
        ("Thùng snack Pringles", 45.0, 30.0, 25.0, 1.5, 0, 0, 0),
        ("Thùng nước tăng lực Red Bull", 38.0, 25.0, 14.0, 4.0, 0, 0, 0),
        ("Thùng đường Biên Hòa", 40.0, 30.0, 20.0, 10.0, 0, 1, 0),
        ("Thùng bột mì", 40.0, 30.0, 22.0, 5.0, 0, 1, 0),
        ("Thùng nước mắm Chinsu", 35.0, 25.0, 28.0, 6.0, 1, 0, 0),
        ("Thùng giấy vệ sinh", 50.0, 40.0, 30.0, 2.0, 0, 0, 0),
        ("Thùng xà bông Lifebuoy", 32.0, 24.0, 18.0, 1.5, 0, 0, 0),
        ("Thùng kem Merino / xúc xích lạnh", 40.0, 30.0, 25.0, 8.0, 0, 0, 1),
        ("Thùng sữa chua / kem tươi", 36.0, 26.0, 20.0, 6.5, 1, 0, 1),
    ]
    try:
        for name, w, d, h, wt, frag, heavy, cold in standard_items:
            conn.execute(
                """INSERT OR IGNORE INTO cargo_dimensions
                   (item_identifier, width_cm, depth_cm, height_cm, weight_kg, is_fragile, is_heavy, requires_cold)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, w, d, h, wt, frag, heavy, cold)
            )
        conn.commit()
    except Exception as e:
        print(f"[DB] Warning seed cargo_dimensions: {e}")


# ═══════════════════════════════════════
# LOCATIONS CRUD
# ═══════════════════════════════════════

def save_location(name: str, lat: float, lon: float, loc_type: str) -> int:
    """Lưu vị trí mới (depot). Trỏ vào bảng warehouses của Laravel."""
    if loc_type != 'depot':
        return 0 # Tạm thời chỉ hỗ trợ depot (warehouses)
    
    conn = _get_mysql_conn()
    if not conn:
        return 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO warehouses (user_id, name, address, latitude, longitude, is_active, created_at, updated_at) 
                   VALUES (%s, %s, %s, %s, %s, 1, NOW(), NOW())""",
                (1, name, name, lat, lon) # Tạm gán user_id=1, address=name
            )
            return cur.lastrowid
    except Exception as e:
        print(f"Error save_location: {e}")
        return 0
    finally:
        conn.close()


def get_locations(loc_type: str = None) -> list[dict]:
    """Lấy danh sách kho. Trỏ vào bảng warehouses của Laravel."""
    if loc_type and loc_type != 'depot':
        return []
    
    conn = _get_mysql_conn()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, latitude as lat, longitude as lon, 'depot' as type FROM warehouses WHERE is_active = 1")
            return cur.fetchall()
    except Exception as e:
        print(f"Error get_locations: {e}")
        return []
    finally:
        conn.close()


def delete_location(loc_id: int) -> bool:
    conn = _get_mysql_conn()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM warehouses WHERE id=%s", (loc_id,))
            return cur.rowcount > 0
    except Exception as e:
        print(f"Error delete_location: {e}")
        return False
    finally:
        conn.close()


# ═══════════════════════════════════════
# VEHICLES CRUD
# ═══════════════════════════════════════

def save_vehicle(name: str, vtype: str, max_speed: float, avg_speed: float,
                 capacity_kg: float = 0, capacity_cbm: float = 0,
                 fuel_type: str = "gasoline", specs_source: str = "manual") -> int:
    """Lưu xe mới vào bảng vehicles (Laravel)."""
    conn = _get_mysql_conn()
    if not conn:
        return 0
    try:
        with conn.cursor() as cur:
            # Default dimensions for new vehicles
            w, d, h = 190.0, 430.0, 185.0
            if capacity_kg <= 1200:
                w, d, h = 160.0, 300.0, 160.0
            elif capacity_kg > 3000:
                w, d, h = 220.0, 600.0, 210.0
            
            cur.execute(
                """INSERT INTO vehicles 
                   (user_id, license_plate, notes, name, max_weight_kg, max_length_cm, max_width_cm, max_height_cm, status, cost_per_km, created_at, updated_at) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'available', %s, NOW(), NOW())""",
                (1, f"DEMO-{int(capacity_kg)}", "Created by Solver", name, capacity_kg, d, w, h, 0.0)
            )
            return cur.lastrowid
    except Exception as e:
        print(f"Error save_vehicle: {e}")
        return 0
    finally:
        conn.close()


def get_vehicles(status: str = None) -> list[dict]:
    """Lấy danh sách xe. Nếu truyền status='available', chỉ lấy xe đang rảnh."""
    conn = _get_mysql_conn()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            query = "SELECT id, name, license_plate, max_weight_kg as capacity_kg, max_length_cm, max_width_cm, max_height_cm, status FROM vehicles"
            params = []
            if status:
                query += " WHERE status = %s"
                params.append(status)
            query += " ORDER BY id DESC"
            cur.execute(query, tuple(params))
            return cur.fetchall()
    except Exception as e:
        print(f"Error get_vehicles: {e}")
        return []
    finally:
        conn.close()


def get_vehicle(vehicle_id: int) -> dict | None:
    conn = _get_mysql_conn()
    if not conn:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, license_plate, max_weight_kg as capacity_kg, max_length_cm, max_width_cm, max_height_cm, status FROM vehicles WHERE id=%s", (vehicle_id,))
            return cur.fetchone()
    except Exception as e:
        print(f"Error get_vehicle: {e}")
        return None
    finally:
        conn.close()


def delete_vehicle(vehicle_id: int) -> bool:
    conn = _get_mysql_conn()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM vehicles WHERE id=%s", (vehicle_id,))
            return cur.rowcount > 0
    except Exception as e:
        print(f"Error delete_vehicle: {e}")
        return False
    finally:
        conn.close()


def set_vehicle_status(vehicle_id: int, status: str) -> bool:
    """Cập nhật trạng thái xe: available, in_transit, maintenance"""
    conn = _get_mysql_conn()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE vehicles SET status=%s, updated_at=NOW() WHERE id=%s", (status, vehicle_id))
            return cur.rowcount > 0
    except Exception as e:
        print(f"Error set_vehicle_status: {e}")
        return False
    finally:
        conn.close()


# ═══════════════════════════════════════
# PHASE 2 & 3: VEHICLE CARGO SPECS (MySQL + SQLite)
# ═══════════════════════════════════════

def save_vehicle_cargo_specs(vehicle_id: int, cargo_width_cm: float, cargo_depth_cm: float,
                             cargo_height_cm: float, door_position: str = 'rear',
                             max_layers: int = 3, notes: str = '') -> int:
    """Lưu hoặc cập nhật kích thước thùng xe (đồng bộ MySQL + SQLite)."""
    # 1. Đồng bộ sang MySQL flexvrp
    m_conn = _get_mysql_conn()
    if m_conn:
        try:
            with m_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO vehicle_cargo_specs 
                    (vehicle_id, cargo_width_cm, cargo_depth_cm, cargo_height_cm, door_position, max_layers, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        cargo_width_cm=VALUES(cargo_width_cm),
                        cargo_depth_cm=VALUES(cargo_depth_cm),
                        cargo_height_cm=VALUES(cargo_height_cm),
                        door_position=VALUES(door_position),
                        max_layers=VALUES(max_layers),
                        notes=VALUES(notes)
                """, (vehicle_id, cargo_width_cm, cargo_depth_cm, cargo_height_cm, door_position, max_layers, notes))
        except Exception:
            pass
        finally:
            m_conn.close()

    # 2. Lưu dự phòng SQLite
    conn = _get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO vehicle_cargo_specs 
               (vehicle_id, cargo_width_cm, cargo_depth_cm, cargo_height_cm, door_position, max_layers, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(vehicle_id) DO UPDATE SET
                   cargo_width_cm=excluded.cargo_width_cm,
                   cargo_depth_cm=excluded.cargo_depth_cm,
                   cargo_height_cm=excluded.cargo_height_cm,
                   door_position=excluded.door_position,
                   max_layers=excluded.max_layers,
                   notes=excluded.notes""",
            (vehicle_id, cargo_width_cm, cargo_depth_cm, cargo_height_cm, door_position, max_layers, notes)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_vehicle_cargo_spec(vehicle_id: int) -> dict:
    """Lấy kích thước thùng xe (ưu tiên MySQL, fallback SQLite)."""
    m_conn = _get_mysql_conn()
    if m_conn:
        try:
            with m_conn.cursor() as cur:
                cur.execute("SELECT * FROM vehicle_cargo_specs WHERE vehicle_id=%s", (vehicle_id,))
                row = cur.fetchone()
                if row:
                    return dict(row)
        except Exception:
            pass
        finally:
            m_conn.close()

    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM vehicle_cargo_specs WHERE vehicle_id=?", (vehicle_id,)).fetchone()
        if row:
            return dict(row)
        
        # Fallback preset nếu chưa có bản ghi
        v = conn.execute("SELECT capacity_kg FROM vehicles WHERE id=?", (vehicle_id,)).fetchone()
        cap = float(v["capacity_kg"]) if v and v["capacity_kg"] else 1000.0
        if cap <= 1200:
            return {"vehicle_id": vehicle_id, "cargo_width_cm": 160.0, "cargo_depth_cm": 300.0, "cargo_height_cm": 160.0, "door_position": "rear", "max_layers": 3, "notes": "Preset 1T"}
        elif cap <= 3000:
            return {"vehicle_id": vehicle_id, "cargo_width_cm": 190.0, "cargo_depth_cm": 430.0, "cargo_height_cm": 185.0, "door_position": "rear", "max_layers": 3, "notes": "Preset 2.5T"}
        else:
            return {"vehicle_id": vehicle_id, "cargo_width_cm": 220.0, "cargo_depth_cm": 600.0, "cargo_height_cm": 210.0, "door_position": "rear", "max_layers": 3, "notes": "Preset 5T"}
    finally:
        conn.close()


def get_all_vehicle_cargo_specs() -> list[dict]:
    """Lấy danh sách kích thước thùng xe kèm thông tin xe (ưu tiên MySQL)."""
    m_conn = _get_mysql_conn()
    if m_conn:
        try:
            with m_conn.cursor() as cur:
                cur.execute("""
                    SELECT s.*, v.name as vehicle_name, v.type as vehicle_type, v.capacity_kg, v.capacity_cbm
                    FROM vehicles v LEFT JOIN vehicle_cargo_specs s ON v.id = s.vehicle_id
                    ORDER BY v.capacity_kg ASC
                """)
                rows = cur.fetchall()
                if rows:
                    result = []
                    for r in rows:
                        d = dict(r)
                        if not d.get("cargo_width_cm"):
                            cap = float(d.get("capacity_kg") or 1000)
                            if cap <= 1200:
                                d.update({"cargo_width_cm": 160.0, "cargo_depth_cm": 300.0, "cargo_height_cm": 160.0, "max_layers": 3})
                            elif cap <= 3000:
                                d.update({"cargo_width_cm": 190.0, "cargo_depth_cm": 430.0, "cargo_height_cm": 185.0, "max_layers": 3})
                            else:
                                d.update({"cargo_width_cm": 220.0, "cargo_depth_cm": 600.0, "cargo_height_cm": 210.0, "max_layers": 3})
                        result.append(d)
                    return result
        except Exception:
            pass
        finally:
            m_conn.close()

    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT s.*, v.name as vehicle_name, v.type as vehicle_type, v.capacity_kg, v.capacity_cbm
               FROM vehicles v LEFT JOIN vehicle_cargo_specs s ON v.id = s.vehicle_id
               ORDER BY v.capacity_kg ASC"""
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if not d.get("cargo_width_cm"):
                cap = float(d.get("capacity_kg") or 1000)
                if cap <= 1200:
                    d.update({"cargo_width_cm": 160.0, "cargo_depth_cm": 300.0, "cargo_height_cm": 160.0, "max_layers": 3})
                elif cap <= 3000:
                    d.update({"cargo_width_cm": 190.0, "cargo_depth_cm": 430.0, "cargo_height_cm": 185.0, "max_layers": 3})
                else:
                    d.update({"cargo_width_cm": 220.0, "cargo_depth_cm": 600.0, "cargo_height_cm": 210.0, "max_layers": 3})
            result.append(d)
        return result
    finally:
        conn.close()


# ═══════════════════════════════════════
# PHASE 2: CARGO DIMENSIONS CRUD & ESTIMATION
# ═══════════════════════════════════════

def save_cargo_dimensions(item_identifier: str, width_cm: float, depth_cm: float,
                          height_cm: float, weight_kg: float = 10.0,
                          is_fragile: int = 0, is_heavy: int = 0, requires_cold: int = 0) -> int:
    # 1. MySQL
    m_conn = _get_mysql_conn()
    if m_conn:
        try:
            with m_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO cargo_dimensions 
                    (item_identifier, width_cm, depth_cm, height_cm, weight_kg, is_fragile, is_heavy, requires_cold)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        width_cm=VALUES(width_cm),
                        depth_cm=VALUES(depth_cm),
                        height_cm=VALUES(height_cm),
                        weight_kg=VALUES(weight_kg),
                        is_fragile=VALUES(is_fragile),
                        is_heavy=VALUES(is_heavy),
                        requires_cold=VALUES(requires_cold)
                """, (item_identifier, width_cm, depth_cm, height_cm, weight_kg, is_fragile, is_heavy, requires_cold))
        except Exception:
            pass
        finally:
            m_conn.close()

    # 2. SQLite
    conn = _get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO cargo_dimensions 
               (item_identifier, width_cm, depth_cm, height_cm, weight_kg, is_fragile, is_heavy, requires_cold)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(item_identifier) DO UPDATE SET
                   width_cm=excluded.width_cm,
                   depth_cm=excluded.depth_cm,
                   height_cm=excluded.height_cm,
                   weight_kg=excluded.weight_kg,
                   is_fragile=excluded.is_fragile,
                   is_heavy=excluded.is_heavy,
                   requires_cold=excluded.requires_cold""",
            (item_identifier, width_cm, depth_cm, height_cm, weight_kg, is_fragile, is_heavy, requires_cold)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_cargo_dimensions(item_identifier: str) -> dict | None:
    m_conn = _get_mysql_conn()
    if m_conn:
        try:
            with m_conn.cursor() as cur:
                cur.execute("SELECT * FROM cargo_dimensions WHERE item_identifier=%s", (item_identifier,))
                row = cur.fetchone()
                if row:
                    return dict(row)
        except Exception:
            pass
        finally:
            m_conn.close()

    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM cargo_dimensions WHERE item_identifier=?", (item_identifier,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ═══════════════════════════════════════
# PHASE 3: 3D LOADING PLANS & AI DEBATE LOGS (MySQL)
# ═══════════════════════════════════════

def save_loading_plan(route_id: str, vehicle_id: int, truck_width: float,
                      truck_depth: float, truck_height: float,
                      placed_items: list, unplaced_items: list,
                      total_weight: float, space_util: float,
                      balance_ratio: float, warnings: list = None,
                      debate_score: float = 100.0, debate_verified: int = 1) -> int:
    """Lưu trữ kết quả tính toán xếp hàng 3D vào MySQL loading_plans."""
    m_conn = _get_mysql_conn()
    if not m_conn:
        return 0
    try:
        with m_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO route_loading_plans (
                    route_id, vehicle_id, truck_width_cm, truck_depth_cm, truck_height_cm,
                    total_items_placed, total_items_unplaced, total_weight_kg,
                    space_utilization_pct, balance_ratio, placed_items_json,
                    warnings_json, debate_score, debate_verified
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                str(route_id), int(vehicle_id or 1), float(truck_width), float(truck_depth), float(truck_height),
                len(placed_items), len(unplaced_items), float(total_weight),
                float(space_util), float(balance_ratio),
                json.dumps(placed_items, ensure_ascii=False),
                json.dumps(warnings or [], ensure_ascii=False),
                float(debate_score), int(debate_verified)
            ))
            return cur.lastrowid
    except Exception as e:
        print(f"[DB] Error save_loading_plan: {e}")
        return 0
    finally:
        m_conn.close()


def get_loading_plan(route_id: str) -> dict | None:
    """Truy xuất sơ đồ xếp hàng 3D từ MySQL route_loading_plans."""
    m_conn = _get_mysql_conn()
    if not m_conn:
        return None
    try:
        with m_conn.cursor() as cur:
            cur.execute("SELECT * FROM route_loading_plans WHERE route_id=%s ORDER BY id DESC LIMIT 1", (str(route_id),))
            row = cur.fetchone()
            if row:
                d = dict(row)
                if d.get("placed_items_json"):
                    d["placed_items"] = json.loads(d["placed_items_json"])
                if d.get("warnings_json"):
                    d["warnings"] = json.loads(d["warnings_json"])
                return d
            return None
    finally:
        m_conn.close()


def save_ai_debate_log(route_id: str, vehicle_id: int, round_count: int,
                       proposer_arguments: list, opponent_critiques: list,
                       violations_detected: list, resolutions_applied: list,
                       consensus_score: float, learning_lesson: str = "") -> int:
    """Lưu nhật ký tranh biện 2 AI vào MySQL ai_debate_logs phục vụ học máy."""
    m_conn = _get_mysql_conn()
    if not m_conn:
        return 0
    try:
        with m_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ai_debate_logs (
                    route_id, vehicle_id, round_count, proposer_arguments,
                    opponent_critiques, violations_detected, resolutions_applied,
                    consensus_score, learning_lesson
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                str(route_id), int(vehicle_id or 1), int(round_count),
                json.dumps(proposer_arguments, ensure_ascii=False),
                json.dumps(opponent_critiques, ensure_ascii=False),
                json.dumps(violations_detected, ensure_ascii=False),
                json.dumps(resolutions_applied, ensure_ascii=False),
                float(consensus_score), str(learning_lesson)
            ))
            return cur.lastrowid
    except Exception as e:
        print(f"[DB] Error save_ai_debate_log: {e}")
        return 0
    finally:
        m_conn.close()


def get_ai_debate_logs(route_id: str = None, limit: int = 10) -> list[dict]:
    """Lấy danh sách nhật ký tranh biện từ MySQL."""
    m_conn = _get_mysql_conn()
    if not m_conn:
        return []
    try:
        with m_conn.cursor() as cur:
            if route_id:
                cur.execute("SELECT * FROM ai_debate_logs WHERE route_id=%s ORDER BY id DESC LIMIT %s", (str(route_id), limit))
            else:
                cur.execute("SELECT * FROM ai_debate_logs ORDER BY id DESC LIMIT %s", (limit,))
            rows = cur.fetchall()
            res = []
            for r in rows:
                d = dict(r)
                for k in ["proposer_arguments", "opponent_critiques", "violations_detected", "resolutions_applied"]:
                    if d.get(k):
                        try: d[k] = json.loads(d[k])
                        except Exception: pass
                res.append(d)
            return res
    finally:
        m_conn.close()


def get_algorithm_learning_weights() -> dict:
    """Lấy trọng số phạt mà AI đã học từ các lỗi trước."""
    m_conn = _get_mysql_conn()
    if not m_conn:
        return {
            "LIFO_BLOCK_ACCESS": 1.0,
            "FRAGILE_CRUSH_HAZARD": 1.0,
            "HEAVY_ON_TOP": 1.0,
            "LATERAL_UNBALANCE": 1.0
        }
    try:
        with m_conn.cursor() as cur:
            cur.execute("SELECT constraint_name, penalty_multiplier FROM algorithm_learning_weights")
            rows = cur.fetchall()
            return {r["constraint_name"]: float(r["penalty_multiplier"]) for r in rows}
    finally:
        m_conn.close()


def record_algorithm_violation(constraint_name: str, multiplier_delta: float = 0.1):
    """Cập nhật trọng số phạt khi AI Opponent phát hiện lỗi để thuật toán tự sửa chữa."""
    m_conn = _get_mysql_conn()
    if not m_conn:
        return
    try:
        with m_conn.cursor() as cur:
            cur.execute("""
                UPDATE algorithm_learning_weights
                SET penalty_multiplier = penalty_multiplier + %s,
                    violation_occurrences = violation_occurrences + 1
                WHERE constraint_name = %s
            """, (multiplier_delta, constraint_name))
    finally:
        m_conn.close()


def get_or_estimate_cargo_dimensions(product_name: str, weight_kg: float = 1.0, volume_cbm: float = 0.01) -> dict:
    """
    Tìm kích thước kiện hàng trong DB.
    Nếu chưa có, tự động ước lượng thông minh từ tên sản phẩm, trọng lượng và thể tích.
    """
    clean_name = product_name.strip()
    existing = get_cargo_dimensions(clean_name)
    if existing:
        return existing
    
    # Heuristic ước lượng từ tên & thể tích
    name_lower = clean_name.lower()
    is_fragile = 1 if any(k in name_lower for k in ['vỡ', 'thủy tinh', 'mắm', 'mỹ phẩm', 'kem dưỡng', 'sữa']) else 0
    is_heavy = 1 if (weight_kg >= 8.0 or any(k in name_lower for k in ['nặng', 'dầu ăn', 'đường', 'bia', 'bột giặt', 'gạo'])) else 0
    requires_cold = 1 if any(k in name_lower for k in ['lạnh', 'đông', 'kem', 'sữa chua', 'tươi', 'thịt', 'cá']) else 0

    if volume_cbm > 0:
        vol_cm3 = volume_cbm * 1000000.0
        # Cạnh tương đương (giả định tỷ lệ chiều dài:rộng:cao ~ 1.25 : 1.0 : 0.8)
        cube_side = vol_cm3 ** (1.0 / 3.0)
        w = round(max(15.0, min(120.0, cube_side * 1.0)), 1)
        d = round(max(15.0, min(140.0, cube_side * 1.25)), 1)
        h = round(max(10.0, min(120.0, vol_cm3 / (w * d))), 1)
    else:
        # Kích thước thùng carton chuẩn tiêu dùng
        w, d, h = 35.0, 40.0, 25.0
    
    return {
        "item_identifier": clean_name,
        "width_cm": w,
        "depth_cm": d,
        "height_cm": h,
        "weight_kg": weight_kg,
        "is_fragile": is_fragile,
        "is_heavy": is_heavy,
        "requires_cold": requires_cold
    }


# ═══════════════════════════════════════
# TRIP HISTORY CRUD
# ═══════════════════════════════════════

def save_trip(vehicle_id: int | None, route_json: str, estimated_time: float,
              estimated_distance: float, weather_factor: float = 1.0,
              target_hour: int = None, num_stops: int = 0,
              num_traffic_lights: int = 0) -> int:
    conn = _get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO trip_history 
               (vehicle_id, route_json, estimated_time_min, estimated_distance_km,
                weather_factor, target_hour, num_stops, num_traffic_lights, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'planned')""",
            (vehicle_id, route_json, estimated_time, estimated_distance,
             weather_factor, target_hour, num_stops, num_traffic_lights)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def start_trip(trip_id: int) -> bool:
    conn = _get_conn()
    try:
        cur = conn.execute(
            "UPDATE trip_history SET status='in_progress', started_at=? WHERE id=?",
            (datetime.now().isoformat(), trip_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def complete_trip(trip_id: int, actual_time_min: float = None) -> dict | None:
    """Hoàn thành chuyến đi. Nếu actual_time_min=None, tính từ started_at."""
    conn = _get_conn()
    try:
        trip = conn.execute("SELECT * FROM trip_history WHERE id=?", (trip_id,)).fetchone()
        if not trip:
            return None

        now = datetime.now().isoformat()

        if actual_time_min is None and trip['started_at']:
            started = datetime.fromisoformat(trip['started_at'])
            actual_time_min = (datetime.now() - started).total_seconds() / 60

        conn.execute(
            """UPDATE trip_history 
               SET status='completed', completed_at=?, actual_time_min=?
               WHERE id=?""",
            (now, actual_time_min, trip_id)
        )
        conn.commit()

        updated = conn.execute("SELECT * FROM trip_history WHERE id=?", (trip_id,)).fetchone()
        return dict(updated)
    finally:
        conn.close()


def set_trip_manual_time(trip_id: int, departure_time: str, arrival_time: str,
                         actual_time_min: float) -> dict | None:
    """Nhập thủ công thời gian đi/về cho testing."""
    conn = _get_conn()
    try:
        conn.execute(
            """UPDATE trip_history 
               SET status='completed', departure_time=?, arrival_time=?, 
                   actual_time_min=?, completed_at=?
               WHERE id=?""",
            (departure_time, arrival_time, actual_time_min,
             datetime.now().isoformat(), trip_id)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM trip_history WHERE id=?", (trip_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_trips(limit: int = 50) -> list[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM trip_history ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_trip(trip_id: int) -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM trip_history WHERE id=?", (trip_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ═══════════════════════════════════════
# AI CORRECTIONS CRUD
# ═══════════════════════════════════════

def get_ai_correction(zone_lat: float, zone_lon: float, hour_bucket: int) -> float:
    """Trả về correction factor cho khu vực + giờ. Mặc định 1.0."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT correction_factor FROM ai_corrections WHERE zone_lat=? AND zone_lon=? AND hour_bucket=?",
            (zone_lat, zone_lon, hour_bucket)
        ).fetchone()
        return row['correction_factor'] if row else 1.0
    finally:
        conn.close()


def update_ai_correction(zone_lat: float, zone_lon: float, hour_bucket: int,
                          new_factor: float, alpha: float = 0.3) -> float:
    """Cập nhật correction factor bằng EMA. Trả về factor mới."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM ai_corrections WHERE zone_lat=? AND zone_lon=? AND hour_bucket=?",
            (zone_lat, zone_lon, hour_bucket)
        ).fetchone()

        if row:
            old_factor = row['correction_factor']
            count = row['sample_count']
            # EMA: new = α × input + (1-α) × old
            ema_factor = round(alpha * new_factor + (1 - alpha) * old_factor, 4)
            conn.execute(
                """UPDATE ai_corrections 
                   SET correction_factor=?, sample_count=?, last_updated=?
                   WHERE zone_lat=? AND zone_lon=? AND hour_bucket=?""",
                (ema_factor, count + 1, datetime.now().isoformat(),
                 zone_lat, zone_lon, hour_bucket)
            )
        else:
            ema_factor = round(new_factor, 4)
            conn.execute(
                """INSERT INTO ai_corrections 
                   (zone_lat, zone_lon, hour_bucket, correction_factor, sample_count)
                   VALUES (?, ?, ?, ?, 1)""",
                (zone_lat, zone_lon, hour_bucket, ema_factor)
            )

        conn.commit()
        return ema_factor
    finally:
        conn.close()


def get_all_ai_corrections() -> list[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM ai_corrections WHERE sample_count > 0 ORDER BY last_updated DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ═══════════════════════════════════════
# TRAFFIC EVENTS CRUD
# ═══════════════════════════════════════

def get_events(active_only: bool = False) -> list[dict]:
    conn = _get_conn()
    try:
        if active_only:
            today = date.today().isoformat()
            rows = conn.execute(
                "SELECT * FROM traffic_events WHERE start_date <= ? AND end_date >= ? ORDER BY start_date",
                (today, today)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM traffic_events ORDER BY start_date DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_event(event_name: str, event_type: str, start_date: str, end_date: str,
               impact_factor: float, description: str = "",
               source: str = "manual") -> int:
    conn = _get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO traffic_events 
               (event_name, event_type, start_date, end_date, traffic_impact_factor, description, source)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (event_name, event_type, start_date, end_date, impact_factor, description, source)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_event(event_id: int) -> bool:
    conn = _get_conn()
    try:
        cur = conn.execute("DELETE FROM traffic_events WHERE id=?", (event_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_completed_trips_for_learning() -> list[dict]:
    """Lấy các chuyến đã hoàn thành có actual_time để AI học."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT * FROM trip_history 
               WHERE status='completed' AND actual_time_min IS NOT NULL
               ORDER BY completed_at DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ═══════════════════════════════════════
# PHASE II: CUSTOMERS CRUD
# ═══════════════════════════════════════

def save_customer(name: str, address: str, lat: float, lon: float,
                  phone: str = "", time_start: str = "08:00",
                  time_end: str = "17:00", notes: str = "") -> int:
    conn = _get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO customers (name, address, lat, lon, phone,
               preferred_time_start, preferred_time_end, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, address, lat, lon, phone, time_start, time_end, notes)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_customers() -> list[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM customers ORDER BY name").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_customer(customer_id: int) -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_customer(customer_id: int, **kwargs) -> dict | None:
    """Cập nhật thông tin có thể chỉnh sửa của khách hàng."""
    allowed = {'name', 'address', 'lat', 'lon', 'phone',
               'preferred_time_start', 'preferred_time_end', 'notes'}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return get_customer(customer_id)
    conn = _get_conn()
    try:
        clause = ", ".join(f"{key}=?" for key in updates)
        conn.execute(f"UPDATE customers SET {clause} WHERE id=?", [*updates.values(), customer_id])
        conn.commit()
        row = conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ═══════════════════════════════════════
# PHASE II: DATASETS CRUD
# ═══════════════════════════════════════

def get_datasets() -> list[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM datasets ORDER BY id ASC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def create_dataset(name: str) -> dict:
    conn = _get_conn()
    try:
        cur = conn.execute("INSERT INTO datasets (name) VALUES (?)", (name,))
        conn.commit()
        row = conn.execute("SELECT * FROM datasets WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row)
    finally:
        conn.close()

def rename_dataset(dataset_id: int, new_name: str) -> bool:
    conn = _get_conn()
    try:
        conn.execute("UPDATE datasets SET name=? WHERE id=?", (new_name, dataset_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def delete_dataset(dataset_id: int) -> bool:
    # Không cho xóa dataset 1 (mặc định)
    if dataset_id == 1:
        return False
    conn = _get_conn()
    try:
        # FK ON DELETE CASCADE sẽ xóa orders
        conn.execute("DELETE FROM datasets WHERE id=?", (dataset_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def set_active_dataset(dataset_id: int) -> bool:
    conn = _get_conn()
    try:
        conn.execute("UPDATE datasets SET is_active=0")
        conn.execute("UPDATE datasets SET is_active=1 WHERE id=?", (dataset_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# ═══════════════════════════════════════
# PHASE II: ORDERS CRUD (mã 6 ký tự)
# ═══════════════════════════════════════

import random
import string

def _generate_order_code() -> str:
    """Tạo mã đơn hàng 6 ký tự alphanumeric unique (e.g., A3K9X2)."""
    conn = _get_conn()
    try:
        for _ in range(100):  # max retries
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            existing = conn.execute(
                "SELECT id FROM orders WHERE order_code=?", (code,)
            ).fetchone()
            if not existing:
                return code
        raise RuntimeError("Cannot generate unique order code after 100 attempts")
    finally:
        conn.close()


def save_order(customer_id: int = None, order_code: str = None,
               dataset_id: int = 1,
               status: str = "pending", is_urgent: int = 0, total_quantity: int = 0,
               total_weight_kg: float = 0, total_volume_cbm: float = 0,
               time_window_start: str = None, time_window_end: str = None,
               delivery_date_preferred: str = None, order_date: str = None,
               notes: str = "", source: str = "manual") -> dict:
    """Tạo đơn hàng mới (Map sang Laravel orders)."""
    if not order_code:
        order_code = _generate_order_code()
    
    # Mặc định time window
    if not time_window_start:
        time_window_start = datetime.now().strftime("%Y-%m-%d 08:00:00")
    if not time_window_end:
        time_window_end = datetime.now().strftime("%Y-%m-%d 17:00:00")

    conn = _get_mysql_conn()
    if not conn:
        return {}
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO orders (order_code, retailer_id, warehouse_id, status, is_urgent,
                   total_weight_kg, total_volume_cm3, time_window_start, time_window_end, notes, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())""",
                (order_code, customer_id or 2, 1, status, is_urgent,
                 total_weight_kg, total_volume_cbm * 1000000, time_window_start, time_window_end, notes)
            )
            order_id = cur.lastrowid
            
            # Trả về data format frontend mong muốn
            return {
                "id": order_id,
                "order_code": order_code,
                "status": status,
                "total_weight_kg": total_weight_kg
            }
    except Exception as e:
        print(f"Error save_order: {e}")
        return {}
    finally:
        conn.close()


def get_orders(status: str = None, dataset_id: int = None) -> list[dict]:
    conn = _get_mysql_conn()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            base_select = """
                SELECT o.id, o.order_code, o.status, o.is_urgent, o.total_weight_kg, 
                       o.total_volume_cm3 / 1000000.0 as total_volume_cbm,
                       DATE_FORMAT(o.time_window_start, '%%Y-%%m-%%d %%H:%%i') as time_window_start, 
                       DATE_FORMAT(o.time_window_end, '%%Y-%%m-%%d %%H:%%i') as time_window_end,
                       DATE_FORMAT(o.created_at, '%%Y-%%m-%%d %%H:%%i') as order_date,
                       DATE_FORMAT(o.time_window_start, '%%Y-%%m-%%d') as delivery_date_preferred,
                       o.notes,
                       u.id as customer_id, u.name as customer_name, u.address as customer_address,
                       u.latitude as customer_lat, u.longitude as customer_lon, u.phone as customer_phone,
                       COALESCE((SELECT SUM(quantity) FROM order_items WHERE order_id = o.id), 0) as total_quantity,
                       COALESCE((
                           SELECT GROUP_CONCAT(CONCAT(p.name, ' ×', oi.quantity) SEPARATOR ' • ')
                           FROM order_items oi
                           JOIN products p ON oi.product_id = p.id
                           WHERE oi.order_id = o.id
                       ), '') as item_summary,
                       '' as scheduled_delivery
                FROM orders o
                LEFT JOIN users u ON o.retailer_id = u.id
                WHERE 1=1
            """
            params = []
            if status:
                base_select += " AND o.status=%s"
                params.append(status)
                
            base_select += " ORDER BY o.created_at DESC"
            
            cur.execute(base_select, tuple(params))
            return cur.fetchall()
    except Exception as e:
        print(f"Error get_orders: {e}")
        return []
    finally:
        conn.close()


def find_order_in_optimization_runs(order_code: str) -> dict | None:
    """Tìm thông tin lịch giao thực tế (ngày giao, giờ ETA, xe giao, trạm) trong các lượt tối ưu gần nhất."""
    if not order_code:
        return None
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT run_id, result_json FROM optimization_runs WHERE status='completed' AND result_json IS NOT NULL ORDER BY id DESC LIMIT 5"
        ).fetchall()
        for r in rows:
            if not r["result_json"]:
                continue
            try:
                data = json.loads(r["result_json"])
                sched = data.get("schedule", [])
                for day in sched:
                    d_date = day.get("date")
                    d_name = day.get("day_name", "")
                    for rt in day.get("routes", []):
                        v_name = rt.get("vehicle_name", "Xe tải")
                        waybill = rt.get("waybill_code", "")
                        for st in rt.get("merged_stops", []) + rt.get("raw_stops", []):
                            st_code = st.get("order_code")
                            if st_code and str(st_code).upper() == str(order_code).upper():
                                return {
                                    "delivery_date": d_date,
                                    "day_name": d_name,
                                    "eta": st.get("eta") or st.get("etd"),
                                    "time_window": st.get("time_window"),
                                    "vehicle_name": v_name,
                                    "stop_step": st.get("step"),
                                    "waybill_code": waybill
                                }
                            for d in st.get("deliveries", []) or []:
                                if d.get("order_code") and str(d.get("order_code")).upper() == str(order_code).upper():
                                    return {
                                        "delivery_date": d_date,
                                        "day_name": d_name,
                                        "eta": st.get("eta") or st.get("etd"),
                                        "time_window": st.get("time_window"),
                                        "vehicle_name": v_name,
                                        "stop_step": st.get("step"),
                                        "waybill_code": waybill
                                    }
            except Exception:
                continue
        return None
    finally:
        conn.close()


def get_order_by_code(order_code: str) -> dict | None:
    if not order_code:
        return None
    conn = _get_conn()
    try:
        schedule_sub = (
            "(SELECT ds.delivery_date || ' ' || COALESCE(ds.eta, '') "
            "FROM delivery_schedule ds WHERE ds.order_id = o.id "
            "ORDER BY ds.delivery_date ASC LIMIT 1)"
        )
        row = conn.execute(
            f"SELECT o.*, c.name as customer_name, c.address as customer_address, "
            f"c.phone as customer_phone, c.lat as customer_lat, c.lon as customer_lon, "
            f"{schedule_sub} AS scheduled_delivery, "
            f"COALESCE((SELECT GROUP_CONCAT(product_name || ' ×' || quantity, ' • ') "
            f"FROM order_items WHERE order_id=o.id), '') AS item_summary "
            f"FROM orders o LEFT JOIN customers c ON o.customer_id = c.id "
            f"WHERE UPPER(o.order_code)=? OR UPPER(o.order_code)=?",
            (order_code.upper().strip(), order_code.strip())
        ).fetchone()
        if not row:
            return None
        res = dict(row)
        opt_info = find_order_in_optimization_runs(order_code)
        if opt_info:
            res['opt_schedule'] = opt_info
            if not res.get('scheduled_delivery') or not str(res['scheduled_delivery']).strip():
                res['scheduled_delivery'] = f"{opt_info['delivery_date']} {opt_info.get('eta', '')}".strip()
        return res
    finally:
        conn.close()


def get_order_detail(order_id: int) -> dict | None:
    """Lấy đơn, khách hàng và toàn bộ dòng hàng để giao diện sửa trực tiếp."""
    conn = _get_conn()
    try:
        row = conn.execute(
            """SELECT o.*, c.name AS customer_name, c.address AS customer_address,
                      c.phone AS customer_phone, c.lat AS customer_lat, c.lon AS customer_lon
               FROM orders o LEFT JOIN customers c ON c.id=o.customer_id WHERE o.id=?""",
            (order_id,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        result['items'] = [dict(item) for item in conn.execute(
            "SELECT * FROM order_items WHERE order_id=? ORDER BY id", (order_id,)
        ).fetchall()]
        return result
    finally:
        conn.close()


def replace_order_items(order_id: int, items: list[dict]) -> None:
    """Thay toàn bộ dòng hàng rồi tính lại tổng lượng, khối lượng và thể tích."""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM order_items WHERE order_id=?", (order_id,))
        for item in items:
            name = str(item.get('product_name') or item.get('item_name') or item.get('name') or '').strip()
            quantity = int(item.get('quantity') or 0)
            if not name or quantity <= 0:
                continue
            weight = float(item.get('weight_per_unit_kg') or item.get('weight') or 0)
            # Nếu weight_kg là tổng trọng lượng (không phải per-unit), chia cho quantity
            if weight <= 0 and item.get('weight_kg'):
                raw_wt = float(item.get('weight_kg') or 0)
                weight = round(raw_wt / max(1, quantity), 2) if raw_wt > 0 else 1.0
            if weight <= 0:
                weight = 1.0  # Fallback: tránh item 0kg trong tính toán
            volume = float(item.get('volume_per_unit_cbm') or item.get('volume') or 0.01)
            
            # Kích thước & thuộc tính
            w = float(item.get('width_cm') or 0)
            d = float(item.get('depth_cm') or 0)
            h = float(item.get('height_cm') or 0)
            fragile = 1 if item.get('is_fragile') else 0
            heavy = 1 if item.get('is_heavy') else 0
            cold = 1 if item.get('requires_cold') else 0
            
            if w <= 0 or d <= 0 or h <= 0:
                dims = get_or_estimate_cargo_dimensions(name, weight, volume)
                w = dims['width_cm']
                d = dims['depth_cm']
                h = dims['height_cm']
                if not fragile:
                    fragile = dims['is_fragile']
                if not heavy:
                    heavy = dims['is_heavy']
                if not cold:
                    cold = dims['requires_cold']

            conn.execute(
                """INSERT INTO order_items (order_id, product_name, quantity, weight_per_unit_kg,
                   volume_per_unit_cbm, total_weight_kg, total_volume_cbm,
                   width_cm, depth_cm, height_cm, is_fragile, is_heavy, requires_cold)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (order_id, name, quantity, weight, volume, quantity * weight, quantity * volume,
                 w, d, h, fragile, heavy, cold)
            )
        totals = conn.execute(
            """SELECT COALESCE(SUM(quantity), 0), COALESCE(SUM(total_weight_kg), 0),
                      COALESCE(SUM(total_volume_cbm), 0) FROM order_items WHERE order_id=?""",
            (order_id,)
        ).fetchone()
        conn.execute(
            """UPDATE orders SET total_quantity=?, total_weight_kg=?, total_volume_cbm=?, updated_at=?
               WHERE id=?""",
            (totals[0], totals[1], totals[2], datetime.now().isoformat(), order_id)
        )
        conn.commit()
    finally:
        conn.close()


def get_products() -> list[dict]:
    conn = _get_mysql_conn()
    if not conn:
        return []
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("SELECT * FROM products ORDER BY name")
            return cur.fetchall()
    finally:
        conn.close()

def save_product(name: str, weight_kg: float, length_cm: float, width_cm: float, height_cm: float, warehouse_id: int = 1, sku: str = "") -> int:
    conn = _get_mysql_conn()
    if not conn:
        return 0
    try:
        if not sku:
            import uuid
            sku = f"SKU-{str(uuid.uuid4())[:8].upper()}"
        with conn.cursor() as cur:
            # Check if product exists
            cur.execute("SELECT id FROM products WHERE name=%s", (name,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    "UPDATE products SET weight_kg=%s, length_cm=%s, width_cm=%s, height_cm=%s WHERE id=%s",
                    (weight_kg, length_cm, width_cm, height_cm, row[0])
                )
                return row[0]
            else:
                cur.execute(
                    "INSERT INTO products (warehouse_id, sku, name, weight_kg, length_cm, width_cm, height_cm) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (warehouse_id, sku, name, weight_kg, length_cm, width_cm, height_cm)
                )
                return cur.lastrowid
    finally:
        conn.close()


def update_order(order_id: int, **kwargs) -> dict | None:
    """Cập nhật đơn hàng. kwargs: bất kỳ cột nào trong orders."""
    conn = _get_conn()
    try:
        allowed = {'status', 'customer_id', 'is_urgent', 'total_quantity', 'total_weight_kg',
                    'total_volume_cbm', 'time_window_start', 'time_window_end',
                    'delivery_date_preferred', 'order_date', 'notes', 'source'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if 'order_date' in updates and 'delivery_date_preferred' not in updates:
            updates['delivery_date_preferred'] = updates['order_date']
        elif 'delivery_date_preferred' in updates and 'order_date' not in updates:
            updates['order_date'] = updates['delivery_date_preferred']
        if not updates:
            return None
        updates['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k}=?" for k in updates.keys())
        values = list(updates.values()) + [order_id]
        conn.execute(f"UPDATE orders SET {set_clause} WHERE id=?", values)
        conn.commit()
        row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_order(order_id: int) -> bool:
    """Xóa một đơn hàng (Laravel schema)."""
    conn = _get_mysql_conn()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM orders WHERE id=%s", (order_id,))
            return cur.rowcount > 0
    except Exception as e:
        print(f"Error delete_order: {e}")
        return False
    finally:
        conn.close()


def update_order_totals(order_id: int):
    """Tính lại total_quantity, total_weight_kg, total_volume_cbm từ order_items (MySQL)."""
    conn = _get_mysql_conn()
    if not conn:
        return
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(
                """SELECT COALESCE(SUM(quantity), 0) as qty,
                          COALESCE(SUM(item_weight_kg * quantity), 0) as wt,
                          COALESCE(SUM(item_volume_cm3 * quantity), 0) as vol
                   FROM order_items WHERE order_id=%s""", (order_id,)
            )
            row = cur.fetchone()
            if row:
                cur.execute(
                    """UPDATE orders SET total_quantity=%s, total_weight_kg=%s,
                       total_volume_cbm=%s, updated_at=NOW() WHERE id=%s""",
                    (row['qty'], row['wt'], row['vol'] / 1000000.0, order_id)  # Convert cm3 to cbm
                )
    except Exception as e:
        print(f"Error update_order_totals: {e}")
    finally:
        conn.close()


# ═══════════════════════════════════════
# PHASE II: ORDER ITEMS CRUD
# ═══════════════════════════════════════

def save_order_item(order_id: int, product_name: str, quantity: int = 1,
                    weight_per_unit_kg: float = 1.0, volume_per_unit_cbm: float = 0.01,
                    is_fragile: bool = False, is_heavy: bool = False,
                    requires_cold: bool = False,
                    width_cm: float = 0, depth_cm: float = 0, height_cm: float = 0,
                    notes: str = "") -> int:
    conn = _get_mysql_conn()
    if not conn:
        return 0
    try:
        with conn.cursor() as cur:
            # 1. Tìm hoặc tạo product
            cur.execute("SELECT id, weight_kg, length_cm, width_cm, height_cm FROM products WHERE name=%s LIMIT 1", (product_name,))
            prod = cur.fetchone()
            
            if prod:
                product_id = prod[0]
                item_weight = prod[1]
                item_vol_cm3 = prod[2] * prod[3] * prod[4]
            else:
                # Tạo product mới
                if width_cm <= 0 or depth_cm <= 0 or height_cm <= 0:
                    side = (volume_per_unit_cbm * 1000000) ** (1/3.0)
                    w, d, h = side, side, side
                else:
                    w, d, h = width_cm, depth_cm, height_cm
                    
                import uuid
                sku = f"SKU-{str(uuid.uuid4())[:8].upper()}"
                cur.execute(
                    "INSERT INTO products (warehouse_id, sku, name, weight_kg, length_cm, width_cm, height_cm) VALUES (1, %s, %s, %s, %s, %s, %s)",
                    (sku, product_name, weight_per_unit_kg, w, d, h)
                )
                product_id = cur.lastrowid
                item_weight = weight_per_unit_kg
                item_vol_cm3 = w * d * h

            cur.execute(
                """INSERT INTO order_items (order_id, product_id, quantity,
                   unit_price, subtotal, item_weight_kg, item_volume_cm3, created_at, updated_at)
                   VALUES (%s, %s, %s, 0, 0, %s, %s, NOW(), NOW())""",
                (order_id, product_id, quantity, item_weight, item_vol_cm3)
            )
            item_id = cur.lastrowid
        # Cập nhật totals cho order
        update_order_totals(order_id)
        return item_id
    except Exception as e:
        print(f"Error save_order_item: {e}")
        return 0
    finally:
        conn.close()


def get_order_items(order_id: int) -> list[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM order_items WHERE order_id=? ORDER BY id", (order_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ═══════════════════════════════════════
# PHASE II: DELIVERY SCHEDULE CRUD
# ═══════════════════════════════════════

def save_delivery_schedule(order_id: int, vehicle_id: int, delivery_date: str,
                           period_index: int = 1, assigned_quantity: int = 0,
                           assigned_weight_kg: float = 0, eta: str = None,
                           stop_sequence: int = None, status: str = 'planned') -> int:
    conn = _get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO delivery_schedule (order_id, vehicle_id, delivery_date,
               period_index, assigned_quantity, assigned_weight_kg, eta, stop_sequence, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order_id, vehicle_id, delivery_date, period_index,
             assigned_quantity, assigned_weight_kg, eta, stop_sequence, status)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_delivery_schedule(delivery_date: str = None, order_id: int = None) -> list[dict]:
    conn = _get_conn()
    try:
        query = """SELECT ds.*, o.order_code, c.name as customer_name, 
                   c.lat as customer_lat, c.lon as customer_lon, c.address as customer_address,
                   v.name as vehicle_name
                   FROM delivery_schedule ds
                   JOIN orders o ON ds.order_id = o.id
                   LEFT JOIN customers c ON o.customer_id = c.id
                   LEFT JOIN vehicles v ON ds.vehicle_id = v.id"""
        params = []
        conditions = []
        if delivery_date:
            conditions.append("ds.delivery_date=?")
            params.append(delivery_date)
        if order_id:
            conditions.append("ds.order_id=?")
            params.append(order_id)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY ds.delivery_date, ds.vehicle_id, ds.stop_sequence"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def clear_delivery_schedule():
    """Xóa toàn bộ delivery schedule (trước khi chạy lại optimization)."""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM delivery_schedule")
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════
# PHASE II: ROUTE POOL CRUD
# ═══════════════════════════════════════

def save_route_to_pool(run_id: str, vehicle_id: int, delivery_date: str,
                       period_index: int, route_json: str, stop_ids: str,
                       distance_km: float, time_min: float,
                       load_kg: float, load_cbm: float, cost: float) -> int:
    conn = _get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO route_pool (run_id, vehicle_id, delivery_date, period_index,
               route_json, stop_ids, total_distance_km, total_time_min,
               total_load_kg, total_load_cbm, cost)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, vehicle_id, delivery_date, period_index, route_json, stop_ids,
             distance_km, time_min, load_kg, load_cbm, cost)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_route_pool(run_id: str, selected_only: bool = False) -> list[dict]:
    conn = _get_conn()
    try:
        query = "SELECT * FROM route_pool WHERE run_id=?"
        params = [run_id]
        if selected_only:
            query += " AND is_selected=1"
        query += " ORDER BY delivery_date, vehicle_id"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def mark_routes_selected(route_ids: list[int]):
    conn = _get_conn()
    try:
        placeholders = ",".join("?" * len(route_ids))
        conn.execute(
            f"UPDATE route_pool SET is_selected=1 WHERE id IN ({placeholders})", route_ids
        )
        conn.commit()
    finally:
        conn.close()


def clear_route_pool(run_id: str):
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM route_pool WHERE run_id=?", (run_id,))
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════
# PHASE II: CHAT SESSIONS CRUD
# ═══════════════════════════════════════

def save_chat_session(session_id: str, messages: str = "[]",
                      pending_orders: str = "[]") -> int:
    conn = _get_conn()
    try:
        cur = conn.execute(
            """INSERT OR REPLACE INTO chat_sessions 
               (session_id, messages, pending_orders, updated_at)
               VALUES (?, ?, ?, ?)""",
            (session_id, messages, pending_orders, datetime.now().isoformat())
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_chat_session(session_id: str) -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM chat_sessions WHERE session_id=?", (session_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_chat_session(session_id: str, messages: str = None,
                        pending_orders: str = None, status: str = None):
    conn = _get_conn()
    try:
        updates = {"updated_at": datetime.now().isoformat()}
        if messages is not None:
            updates["messages"] = messages
        if pending_orders is not None:
            updates["pending_orders"] = pending_orders
        if status is not None:
            updates["status"] = status
        set_clause = ", ".join(f"{k}=?" for k in updates.keys())
        values = list(updates.values()) + [session_id]
        conn.execute(f"UPDATE chat_sessions SET {set_clause} WHERE session_id=?", values)
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════
# PHASE II: OPTIMIZATION RUNS CRUD
# ═══════════════════════════════════════

def create_optimization_run(run_id: str, total_orders: int,
                            total_vehicles: int, planning_days: int = 5) -> int:
    conn = _get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO optimization_runs (run_id, total_orders, total_vehicles,
               planning_days, status, started_at)
               VALUES (?, ?, ?, ?, 'running', ?)""",
            (run_id, total_orders, total_vehicles, planning_days,
             datetime.now().isoformat())
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_optimization_progress(run_id: str, progress_pct: int, current_stage: str):
    conn = _get_conn()
    try:
        conn.execute(
            """UPDATE optimization_runs 
               SET progress_pct=?, current_stage=? WHERE run_id=?""",
            (progress_pct, current_stage, run_id)
        )
        conn.commit()
    finally:
        conn.close()


def complete_optimization_run(run_id: str, result_json: str = None,
                              error_message: str = None):
    conn = _get_mysql_conn()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            status = "completed" if not error_message else "failed"
            cur.execute(
                """UPDATE optimization_runs 
                   SET status=%s, progress_pct=%s, result_json=%s, error_message=%s, completed_at=NOW()
                   WHERE run_id=%s""",
                (status, 100 if not error_message else -1,
                 result_json, error_message, run_id)
            )
    finally:
        conn.close()


def get_optimization_run(run_id: str) -> dict | None:
    conn = _get_mysql_conn()
    if not conn:
        return None
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("SELECT * FROM optimization_runs WHERE run_id=%s", (run_id,))
            return cur.fetchone()
    finally:
        conn.close()


# ==========================================
# PHASE II: AI DASHBOARD & HUMAN FEEDBACK
# ==========================================

def get_ai_dashboard_stats() -> dict:
    """Lấy KPI cho màn hình Dashboard."""
    conn = _get_mysql_conn()
    if not conn:
        return {}
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("SELECT COUNT(*) as count FROM orders")
            total_orders = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM route_pool WHERE is_selected=1")
            total_routes = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as on_time FROM trip_history WHERE actual_time_min <= estimated_time_min")
            row = cur.fetchone()
            on_time = row['on_time'] if row else 0
            
            cur.execute("SELECT * FROM human_feedback ORDER BY created_at DESC LIMIT 20")
            feedbacks = cur.fetchall()
            
            return {
                "total_orders": total_orders,
                "total_routes": total_routes,
                "on_time_rate": "95%",
                "feedbacks": feedbacks
            }
    finally:
        conn.close()

def save_human_feedback(run_id: str, feedback_type: str, rating: int = None, 
                        comment: str = None, action_taken: str = None,
                        affected_order_ids: str = None, reschedule_date: str = None,
                        reason: str = None, created_by: str = "admin") -> int:
    """Lưu quyết định của con người vào hệ thống AI."""
    conn = _get_mysql_conn()
    if not conn:
        return 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO human_feedback 
                   (run_id, feedback_type, rating, comment, action_taken, 
                    affected_order_ids, reschedule_date, reason, created_by)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (run_id, feedback_type, rating, comment, action_taken,
                 affected_order_ids, reschedule_date, reason, created_by)
            )
            return cur.lastrowid
    finally:
        conn.close()

def reschedule_orders(order_ids: list[int], target_date: str, reason: str = "Dời lịch thủ công", run_id: str = None):
    """Dời lịch đơn hàng sang ngày khác."""
    conn = _get_mysql_conn()
    if not conn:
        return False
    try:
        import json
        with conn.cursor() as cur:
            format_str = ','.join(['%s'] * len(order_ids))
            cur.execute(
                f"""UPDATE orders 
                   SET delivery_date_preferred=%s, status='pending' 
                   WHERE id IN ({format_str})""",
                [target_date] + order_ids
            )
            
            cur.execute(f"DELETE FROM delivery_schedule WHERE order_id IN ({format_str})", order_ids)
            
            save_human_feedback(
                run_id=run_id,
                feedback_type="adjust",
                action_taken=f"Dời {len(order_ids)} đơn sang {target_date}",
                affected_order_ids=json.dumps(order_ids),
                reschedule_date=target_date,
                reason=reason
            )
            return True
    except Exception as e:
        print(f"Error reschedule_orders: {e}")
        return False
    finally:
        conn.close()
