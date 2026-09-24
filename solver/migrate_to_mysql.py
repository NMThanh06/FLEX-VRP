"""
FLEX-VRP — Migration Script: SQLite → MySQL
Tạo tất cả tables trong MySQL flexvrp database.
Nếu SQLite DB tồn tại, migrate data sang MySQL.

Chạy: python solver/migrate_to_mysql.py
"""

import sys
import os
from pathlib import Path

# Thêm solver vào path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import pymysql
import pymysql.cursors
import sqlite3
from datetime import datetime


def get_mysql_config() -> dict:
    """Đọc config MySQL từ .env"""
    env_file = Path(__file__).parent.parent / ".env"
    config = {
        "host": "127.0.0.1",
        "port": 3306,
        "user": "root",
        "password": "",
        "database": "flexvrp",
    }
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DB_HOST="): config["host"] = line.split("=", 1)[1].strip().strip('"\'')
            elif line.startswith("DB_PORT="):
                p = line.split("=", 1)[1].strip().strip('"\'')
                if p.isdigit(): config["port"] = int(p)
            elif line.startswith("DB_USERNAME="): config["user"] = line.split("=", 1)[1].strip().strip('"\'')
            elif line.startswith("DB_PASSWORD="): config["password"] = line.split("=", 1)[1].strip().strip('"\'')
            elif line.startswith("DB_DATABASE="): config["database"] = line.split("=", 1)[1].strip().strip('"\'')
    return config


def get_mysql_conn(config: dict):
    """Tạo kết nối MySQL."""
    return pymysql.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        database=config["database"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


# ═══════════════════════════════════════
# BƯỚC 1: TẠO TẤT CẢ TABLES TRONG MYSQL
# ═══════════════════════════════════════

MYSQL_TABLES_SQL = """

-- ═══════════════════════════════════════
-- CORE TABLES
-- ═══════════════════════════════════════

-- Vị trí (kho bãi + điểm giao)
CREATE TABLE IF NOT EXISTS locations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    lat DOUBLE NOT NULL,
    lon DOUBLE NOT NULL,
    type ENUM('depot', 'delivery') NOT NULL DEFAULT 'depot',
    address TEXT DEFAULT NULL,
    phone VARCHAR(20) DEFAULT '',
    operating_hours VARCHAR(50) DEFAULT '06:00-22:00',
    notes TEXT DEFAULT NULL,
    is_default TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Loại xe (MỚI: thêm status, license_plate, notes)
CREATE TABLE IF NOT EXISTS vehicles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL DEFAULT 'truck',
    max_speed_kmh DOUBLE NOT NULL DEFAULT 60,
    avg_city_speed_kmh DOUBLE NOT NULL DEFAULT 25,
    capacity_kg DOUBLE DEFAULT 0,
    capacity_cbm DOUBLE DEFAULT 0,
    fuel_type VARCHAR(50) DEFAULT 'gasoline',
    specs_source VARCHAR(50) DEFAULT 'manual',
    status ENUM('active', 'paused', 'maintenance') DEFAULT 'active',
    license_plate VARCHAR(20) DEFAULT '',
    notes TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Lịch sử chuyến đi
CREATE TABLE IF NOT EXISTS trip_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_id BIGINT(20) UNSIGNED DEFAULT NULL,
    route_json TEXT NOT NULL,
    estimated_time_min DOUBLE NOT NULL,
    actual_time_min DOUBLE DEFAULT NULL,
    departure_time VARCHAR(50) DEFAULT NULL,
    arrival_time VARCHAR(50) DEFAULT NULL,
    estimated_distance_km DOUBLE NOT NULL DEFAULT 0,
    weather_factor DOUBLE DEFAULT 1.0,
    target_hour INT DEFAULT NULL,
    num_stops INT DEFAULT NULL,
    num_traffic_lights INT DEFAULT 0,
    status VARCHAR(30) DEFAULT 'planned',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL DEFAULT NULL,
    completed_at TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Hiệu chỉnh AI theo khu vực
CREATE TABLE IF NOT EXISTS ai_corrections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    zone_lat DOUBLE NOT NULL,
    zone_lon DOUBLE NOT NULL,
    hour_bucket INT NOT NULL,
    correction_factor DOUBLE DEFAULT 1.0,
    sample_count INT DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_zone_hour (zone_lat, zone_lon, hour_bucket)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Sự kiện ảnh hưởng giao thông
CREATE TABLE IF NOT EXISTS traffic_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_name VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    start_date VARCHAR(30) NOT NULL,
    end_date VARCHAR(30) NOT NULL,
    traffic_impact_factor DOUBLE DEFAULT 1.0,
    description TEXT DEFAULT NULL,
    source VARCHAR(50) DEFAULT 'manual',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ═══════════════════════════════════════
-- PHASE II: B2B ORDER MANAGEMENT
-- ═══════════════════════════════════════

-- Bảng quản lý datasets (Bỏ qua vì Laravel có bảng khác)

-- Lịch giao hàng
CREATE TABLE IF NOT EXISTS delivery_schedule (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT(20) UNSIGNED NOT NULL,
    vehicle_id BIGINT(20) UNSIGNED DEFAULT NULL,
    delivery_date VARCHAR(30) NOT NULL,
    period_index INT DEFAULT 1,
    assigned_quantity INT NOT NULL,
    assigned_weight_kg DOUBLE DEFAULT 0,
    status ENUM('planned','in_progress','completed','cancelled') DEFAULT 'planned',
    route_id INT DEFAULT NULL,
    stop_sequence INT DEFAULT NULL,
    eta VARCHAR(30) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Route Pool
CREATE TABLE IF NOT EXISTS route_pool (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(100) NOT NULL,
    vehicle_id BIGINT(20) UNSIGNED DEFAULT NULL,
    delivery_date VARCHAR(30) DEFAULT NULL,
    period_index INT DEFAULT 1,
    route_json TEXT NOT NULL,
    stop_ids TEXT NOT NULL,
    total_distance_km DOUBLE DEFAULT 0,
    total_time_min DOUBLE DEFAULT 0,
    total_load_kg DOUBLE DEFAULT 0,
    total_load_cbm DOUBLE DEFAULT 0,
    cost DOUBLE DEFAULT 0,
    is_selected TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Chat sessions
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL UNIQUE,
    messages LONGTEXT DEFAULT NULL,
    pending_orders LONGTEXT DEFAULT NULL,
    status ENUM('active','completed','expired') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Optimization runs
CREATE TABLE IF NOT EXISTS optimization_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(100) NOT NULL UNIQUE,
    status ENUM('pending','running','completed','failed') DEFAULT 'pending',
    progress_pct INT DEFAULT 0,
    current_stage TEXT DEFAULT NULL,
    total_orders INT DEFAULT 0,
    total_vehicles INT DEFAULT 0,
    planning_days INT DEFAULT 5,
    result_json LONGTEXT DEFAULT NULL,
    error_message TEXT DEFAULT NULL,
    started_at TIMESTAMP NULL DEFAULT NULL,
    completed_at TIMESTAMP NULL DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Kích thước kiện hàng chuẩn
CREATE TABLE IF NOT EXISTS cargo_dimensions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_identifier VARCHAR(255) NOT NULL UNIQUE,
    width_cm DOUBLE NOT NULL DEFAULT 30,
    depth_cm DOUBLE NOT NULL DEFAULT 40,
    height_cm DOUBLE NOT NULL DEFAULT 30,
    weight_kg DOUBLE DEFAULT 10,
    is_fragile TINYINT(1) DEFAULT 0,
    is_heavy TINYINT(1) DEFAULT 0,
    requires_cold TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3D Loading Plans (đã có từ Phase 3)
CREATE TABLE IF NOT EXISTS loading_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    route_id VARCHAR(100) NOT NULL,
    vehicle_id BIGINT(20) UNSIGNED DEFAULT NULL,
    truck_width DOUBLE DEFAULT 0,
    truck_depth DOUBLE DEFAULT 0,
    truck_height DOUBLE DEFAULT 0,
    total_items INT DEFAULT 0,
    space_utilization DOUBLE DEFAULT 0,
    total_weight_kg DOUBLE DEFAULT 0,
    weight_balance_ratio DOUBLE DEFAULT 1.0,
    plan_json LONGTEXT DEFAULT NULL,
    warnings_json LONGTEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- AI Debate Logs (đã có từ Phase 3)
CREATE TABLE IF NOT EXISTS ai_debate_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    route_id VARCHAR(100) NOT NULL,
    vehicle_id BIGINT(20) UNSIGNED DEFAULT NULL,
    round_count INT DEFAULT 0,
    consensus_score DOUBLE DEFAULT 0,
    proposer_name VARCHAR(100) DEFAULT 'Proposer',
    opponent_name VARCHAR(100) DEFAULT 'Opponent',
    dialogue_json LONGTEXT DEFAULT NULL,
    final_verdict TEXT DEFAULT NULL,
    improvements_json LONGTEXT DEFAULT NULL,
    penalty_applied TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Algorithm Learning Weights (đã có từ Phase 3)
CREATE TABLE IF NOT EXISTS algorithm_learning_weights (
    id INT AUTO_INCREMENT PRIMARY KEY,
    weight_key VARCHAR(100) NOT NULL UNIQUE,
    weight_value DOUBLE DEFAULT 1.0,
    description TEXT DEFAULT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    id INT AUTO_INCREMENT PRIMARY KEY,
    weight_key VARCHAR(100) NOT NULL UNIQUE,
    weight_value DOUBLE DEFAULT 1.0,
    description TEXT DEFAULT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ═══════════════════════════════════════
-- MỚI: HUMAN FEEDBACK (AI Dashboard)
-- ═══════════════════════════════════════

CREATE TABLE IF NOT EXISTS human_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(100) DEFAULT NULL,
    feedback_type ENUM('approve','reject','adjust') NOT NULL DEFAULT 'approve',
    rating TINYINT DEFAULT NULL COMMENT '1-5 stars hoặc NULL',
    comment TEXT DEFAULT NULL,
    action_taken TEXT DEFAULT NULL COMMENT 'Mô tả hành động: dời đơn A,B sang ngày X',
    affected_order_ids TEXT DEFAULT NULL COMMENT 'JSON array of order IDs affected',
    reschedule_date VARCHAR(30) DEFAULT NULL,
    reason VARCHAR(255) DEFAULT NULL COMMENT 'Nhân viên nghỉ, xe hỏng, khách yêu cầu...',
    created_by VARCHAR(100) DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

"""


def create_mysql_tables(config: dict):
    """Tạo tất cả tables trong MySQL."""
    conn = get_mysql_conn(config)
    try:
        with conn.cursor() as cur:
            # Tách SQL thành từng câu lệnh riêng
            statements = [s.strip() for s in MYSQL_TABLES_SQL.split(';') if s.strip()]
            for stmt in statements:
                # Xóa các dòng comment
                lines = [l for l in stmt.split('\n') if l.strip() and not l.strip().startswith('--')]
                if not lines:
                    continue
                clean_stmt = '\n'.join(lines)
                try:
                    cur.execute(clean_stmt)
                    # Tìm tên bảng
                    for line in lines:
                        if 'CREATE TABLE' in line.upper():
                            tbl = line.split('`')[-1] if '`' in line else line.split()[-2].strip('(')
                            # Extract table name more reliably
                            import re
                            m = re.search(r'CREATE TABLE IF NOT EXISTS\s+(\w+)', line, re.IGNORECASE)
                            if m:
                                tbl = m.group(1)
                            print(f"  ✅ {tbl}")
                            break
                except Exception as e:
                    print(f"  ⚠️  Warning: {str(e)[:100]}")

        conn.commit()
        print(f"\n✅ Tất cả tables đã được tạo trong MySQL '{config['database']}'")
    finally:
        conn.close()


def migrate_column_adds(config: dict):
    """Thêm các cột mới cho bảng đã tồn tại (safe migration)."""
    conn = get_mysql_conn(config)
    try:
        with conn.cursor() as cur:
            # vehicles: thêm status, license_plate, notes, updated_at nếu chưa có
            migrations = [
                ("vehicles", "status", "ENUM('active','paused','maintenance') DEFAULT 'active' AFTER specs_source"),
                ("vehicles", "license_plate", "VARCHAR(20) DEFAULT '' AFTER status"),
                ("vehicles", "notes", "TEXT DEFAULT NULL AFTER license_plate"),
                ("vehicles", "updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                # locations: thêm address, phone, operating_hours, notes, is_default, updated_at
                ("locations", "address", "TEXT DEFAULT NULL AFTER type"),
                ("locations", "phone", "VARCHAR(20) DEFAULT '' AFTER address"),
                ("locations", "operating_hours", "VARCHAR(50) DEFAULT '06:00-22:00' AFTER phone"),
                ("locations", "notes", "TEXT DEFAULT NULL AFTER operating_hours"),
                ("locations", "is_default", "TINYINT(1) DEFAULT 0 AFTER notes"),
                ("locations", "updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            ]
            for table, col, col_def in migrations:
                try:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
                    print(f"  ✅ {table}.{col} added")
                except Exception as e:
                    if "Duplicate column" in str(e):
                        print(f"  ℹ️  {table}.{col} already exists")
                    else:
                        print(f"  ⚠️  {table}.{col}: {str(e)[:80]}")
        conn.commit()
    finally:
        conn.close()


def migrate_data_from_sqlite(config: dict):
    """Migrate data từ SQLite sang MySQL nếu SQLite DB tồn tại."""
    sqlite_path = Path(__file__).parent / "data" / "flex_vrp.db"
    if not sqlite_path.exists():
        print("\nℹ️  Không tìm thấy SQLite DB, bỏ qua data migration.")
        return

    print(f"\n📦 Bắt đầu migrate data từ SQLite: {sqlite_path}")
    
    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row
    
    mysql_conn = get_mysql_conn(config)
    
    # Thứ tự migrate (theo dependency)
    tables_to_migrate = [
        "locations",
        "vehicles",
        "trip_history",
        "ai_corrections",
        "traffic_events",
        "datasets",
        "customers",
        "orders",
        "order_items",
        "products",
        "delivery_schedule",
        "route_pool",
        "chat_sessions",
        "optimization_runs",
        "vehicle_cargo_specs",
        "cargo_dimensions",
    ]
    
    try:
        with mysql_conn.cursor() as cur:
            # Tạm tắt foreign key check
            cur.execute("SET FOREIGN_KEY_CHECKS=0")
            
            for table in tables_to_migrate:
                try:
                    # Đọc từ SQLite
                    sqlite_rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
                    if not sqlite_rows:
                        print(f"  ℹ️  {table}: trống (0 rows)")
                        continue
                    
                    # Kiểm tra MySQL đã có data chưa
                    cur.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                    mysql_count = cur.fetchone()["cnt"]
                    if mysql_count > 0:
                        print(f"  ⏭️  {table}: MySQL đã có {mysql_count} rows, bỏ qua")
                        continue
                    
                    # Lấy tên cột từ SQLite
                    cols = [desc[0] for desc in sqlite_rows[0].keys()] if hasattr(sqlite_rows[0], 'keys') else []
                    if not cols:
                        cols = [description[0] for description in sqlite_conn.execute(f"PRAGMA table_info({table})").fetchall()]
                        cols = [c[1] for c in sqlite_conn.execute(f"PRAGMA table_info({table})").fetchall()]
                    
                    # Lấy cột tồn tại trong MySQL
                    cur.execute(f"SHOW COLUMNS FROM {table}")
                    mysql_cols = {row["Field"] for row in cur.fetchall()}
                    
                    # Chỉ migrate cột có trong cả 2
                    valid_cols = [c for c in cols if c in mysql_cols]
                    if not valid_cols:
                        print(f"  ⚠️  {table}: không tìm thấy cột chung")
                        continue
                    
                    placeholders = ", ".join(["%s"] * len(valid_cols))
                    col_names = ", ".join(valid_cols)
                    insert_sql = f"INSERT IGNORE INTO {table} ({col_names}) VALUES ({placeholders})"
                    
                    count = 0
                    for row in sqlite_rows:
                        row_dict = dict(row)
                        values = tuple(row_dict.get(c) for c in valid_cols)
                        try:
                            cur.execute(insert_sql, values)
                            count += 1
                        except Exception as e:
                            pass  # Skip dups
                    
                    print(f"  ✅ {table}: migrated {count}/{len(sqlite_rows)} rows")
                    
                except Exception as e:
                    print(f"  ❌ {table}: {str(e)[:100]}")
            
            # Bật lại foreign key check
            cur.execute("SET FOREIGN_KEY_CHECKS=1")
        
        mysql_conn.commit()
        print("\n✅ Data migration hoàn tất!")
        
    finally:
        sqlite_conn.close()
        mysql_conn.close()


def seed_default_data(config: dict):
    """Seed dữ liệu mặc định nếu table trống."""
    conn = get_mysql_conn(config)
    try:
        with conn.cursor() as cur:
            # Seed dataset mặc định
            cur.execute("SELECT COUNT(*) as cnt FROM datasets")
            if cur.fetchone()["cnt"] == 0:
                cur.execute("INSERT INTO datasets (id, name, is_active) VALUES (1, 'Bảng mặc định', 1)")
                print("  ✅ Seeded default dataset")
            
            # Seed traffic events nếu trống
            cur.execute("SELECT COUNT(*) as cnt FROM traffic_events")
            if cur.fetchone()["cnt"] == 0:
                year = datetime.now().year
                events = [
                    (f"Tết Nguyên Đán {year}", "holiday", f"{year}-01-25", f"{year}-02-05", 0.5, "Dân về quê ăn Tết"),
                    (f"Nghỉ hè {year}", "school", f"{year}-06-15", f"{year}-08-31", 0.85, "Sinh viên về quê"),
                    (f"Nhập học {year}", "school", f"{year}-09-01", f"{year}-09-15", 1.15, "Sinh viên nhập học"),
                    (f"Quốc khánh 2/9 {year}", "holiday", f"{year}-09-02", f"{year}-09-02", 0.6, "Nghỉ lễ Quốc khánh"),
                    (f"30/4 - 1/5 {year}", "holiday", f"{year}-04-30", f"{year}-05-01", 0.55, "Nghỉ lễ dài ngày"),
                    (f"Noel - Tết Dương {year}", "holiday", f"{year}-12-24", f"{year}-12-31", 1.2, "Mua sắm Noel"),
                ]
                cur.executemany(
                    "INSERT INTO traffic_events (event_name, event_type, start_date, end_date, traffic_impact_factor, description, source) "
                    "VALUES (%s, %s, %s, %s, %s, %s, 'seed')",
                    events
                )
                print(f"  ✅ Seeded {len(events)} traffic events")
            
            # Seed cargo dimensions nếu trống
            cur.execute("SELECT COUNT(*) as cnt FROM cargo_dimensions")
            if cur.fetchone()["cnt"] == 0:
                items = [
                    ("Thùng mì gói Hảo Hảo", 38.0, 28.0, 22.0, 5.0, 0, 0, 0),
                    ("Thùng nước ngọt Coca", 40.0, 26.0, 14.0, 8.5, 0, 1, 0),
                    ("Thùng sữa Vinamilk", 36.0, 24.0, 15.0, 6.0, 1, 0, 0),
                    ("Thùng bia Tiger", 40.0, 27.0, 16.0, 9.0, 0, 1, 0),
                    ("Thùng dầu ăn Neptune", 34.0, 26.0, 28.0, 10.0, 0, 1, 0),
                    ("Thùng nước suối Lavie", 40.0, 26.0, 24.0, 6.0, 0, 0, 0),
                    ("Thùng bánh Oreo", 32.0, 22.0, 18.0, 3.0, 0, 0, 0),
                    ("Thùng bột giặt OMO", 42.0, 30.0, 25.0, 5.0, 0, 1, 0),
                    ("Thùng kem Merino / xúc xích lạnh", 40.0, 30.0, 25.0, 8.0, 0, 0, 1),
                    ("Thùng sữa chua / kem tươi", 36.0, 26.0, 20.0, 6.5, 1, 0, 1),
                ]
                cur.executemany(
                    "INSERT IGNORE INTO cargo_dimensions (item_identifier, width_cm, depth_cm, height_cm, weight_kg, is_fragile, is_heavy, requires_cold) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    items
                )
                print(f"  ✅ Seeded {len(items)} cargo dimensions")
            
            # Seed algorithm learning weights nếu trống
            cur.execute("SELECT COUNT(*) as cnt FROM algorithm_learning_weights")
            if cur.fetchone()["cnt"] == 0:
                weights = [
                    ("weight_heavy_bottom", 1.0, "Ưu tiên hàng nặng đặt đáy"),
                    ("weight_fragile_top", 1.0, "Ưu tiên hàng dễ vỡ trên cùng"),
                    ("weight_lifo_order", 1.0, "Tuân thủ LIFO (giao sau xếp trước)"),
                    ("weight_cold_cluster", 1.0, "Gom hàng lạnh vào 1 góc"),
                    ("weight_balance", 1.0, "Cân bằng trái-phải"),
                ]
                cur.executemany(
                    "INSERT IGNORE INTO algorithm_learning_weights (weight_key, weight_value, description) "
                    "VALUES (%s, %s, %s)",
                    weights
                )
                print(f"  ✅ Seeded {len(weights)} algorithm weights")
        
        conn.commit()
    finally:
        conn.close()


def main():
    print("=" * 60)
    print("  FLEX-VRP — SQLite → MySQL Migration")
    print("=" * 60)
    
    config = get_mysql_config()
    print(f"\n🔗 MySQL: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
    
    # Test connection
    try:
        test_conn = get_mysql_conn(config)
        test_conn.close()
        print("✅ Kết nối MySQL thành công!\n")
    except Exception as e:
        print(f"❌ Không thể kết nối MySQL: {e}")
        print("   Hãy chắc chắn MySQL đang chạy và database 'flexvrp' đã được tạo.")
        print(f"   CREATE DATABASE IF NOT EXISTS {config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        sys.exit(1)
    
    # Bước 1: Tạo tables
    print("📋 Bước 1: Tạo tables trong MySQL...")
    create_mysql_tables(config)
    
    # Bước 2: Thêm cột mới (safe migration)
    print("\n📋 Bước 2: Thêm cột mới (vehicles.status, locations.address...)...")
    migrate_column_adds(config)
    
    # Bước 3: Migrate data từ SQLite
    print("\n📋 Bước 3: Migrate data từ SQLite...")
    migrate_data_from_sqlite(config)
    
    # Bước 4: Seed dữ liệu mặc định
    print("\n📋 Bước 4: Seed dữ liệu mặc định...")
    seed_default_data(config)
    
    print("\n" + "=" * 60)
    print("  ✅ MIGRATION HOÀN TẤT!")
    print("=" * 60)
    print(f"\nDatabase: {config['database']}")
    print("Tiếp theo: Cập nhật db.py để sử dụng MySQL toàn bộ")


if __name__ == "__main__":
    main()
