"""
FLEX-VRP — SQLite Database Layer
Quản lý dữ liệu persistent: vị trí, xe, chuyến đi, AI corrections, sự kiện.

DB file: solver/data/flex_vrp.db (auto-create)
"""

import sqlite3
import json
import os
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
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','incomplete','confirmed','optimizing','scheduled','in_transit','delivered','cancelled')),
                total_quantity INTEGER DEFAULT 0,
                total_weight_kg REAL DEFAULT 0,
                total_volume_cbm REAL DEFAULT 0,
                time_window_start TEXT,
                time_window_end TEXT,
                delivery_date_preferred TEXT,
                notes TEXT,
                source TEXT DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
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
        """)
        conn.commit()

        # Seed events nếu table trống
        count = conn.execute("SELECT COUNT(*) FROM traffic_events").fetchone()[0]
        if count == 0:
            _seed_events(conn)

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


# ═══════════════════════════════════════
# LOCATIONS CRUD
# ═══════════════════════════════════════

def save_location(name: str, lat: float, lon: float, loc_type: str) -> int:
    """Lưu vị trí mới. Trả về id."""
    conn = _get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO locations (name, lat, lon, type) VALUES (?, ?, ?, ?)",
            (name, lat, lon, loc_type)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_locations(loc_type: str = None) -> list[dict]:
    """Lấy danh sách locations. loc_type=None → tất cả."""
    conn = _get_conn()
    try:
        if loc_type:
            rows = conn.execute(
                "SELECT * FROM locations WHERE type=? ORDER BY created_at DESC", (loc_type,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM locations ORDER BY type, created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_location(loc_id: int) -> bool:
    conn = _get_conn()
    try:
        cur = conn.execute("DELETE FROM locations WHERE id=?", (loc_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ═══════════════════════════════════════
# VEHICLES CRUD
# ═══════════════════════════════════════

def save_vehicle(name: str, vtype: str, max_speed: float, avg_speed: float,
                 capacity_kg: float = 0, capacity_cbm: float = 0,
                 fuel_type: str = "gasoline", specs_source: str = "manual") -> int:
    conn = _get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO vehicles 
               (name, type, max_speed_kmh, avg_city_speed_kmh, capacity_kg, capacity_cbm, fuel_type, specs_source) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, vtype, max_speed, avg_speed, capacity_kg, capacity_cbm, fuel_type, specs_source)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_vehicles() -> list[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM vehicles ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_vehicle(vehicle_id: int) -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM vehicles WHERE id=?", (vehicle_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_vehicle(vehicle_id: int) -> bool:
    conn = _get_conn()
    try:
        cur = conn.execute("DELETE FROM vehicles WHERE id=?", (vehicle_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


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
               status: str = "pending", total_quantity: int = 0,
               total_weight_kg: float = 0, total_volume_cbm: float = 0,
               time_window_start: str = None, time_window_end: str = None,
               delivery_date_preferred: str = None, notes: str = "",
               source: str = "manual") -> dict:
    """Tạo đơn hàng mới. Tự sinh mã 6 ký tự nếu không cung cấp."""
    if not order_code:
        order_code = _generate_order_code()
    conn = _get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO orders (order_code, customer_id, status, total_quantity,
               total_weight_kg, total_volume_cbm, time_window_start, time_window_end,
               delivery_date_preferred, notes, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order_code, customer_id, status, total_quantity,
             total_weight_kg, total_volume_cbm, time_window_start, time_window_end,
             delivery_date_preferred, notes, source)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM orders WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def get_orders(status: str = None) -> list[dict]:
    conn = _get_conn()
    try:
        if status:
            rows = conn.execute(
                "SELECT o.*, c.name as customer_name, c.address as customer_address, "
                "c.lat as customer_lat, c.lon as customer_lon, "
                "COALESCE((SELECT GROUP_CONCAT(product_name || ' ×' || quantity, ' • ') FROM order_items WHERE order_id=o.id), '') AS item_summary "
                "FROM orders o LEFT JOIN customers c ON o.customer_id = c.id "
                "WHERE o.status=? ORDER BY o.created_at DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT o.*, c.name as customer_name, c.address as customer_address, "
                "c.lat as customer_lat, c.lon as customer_lon, "
                "COALESCE((SELECT GROUP_CONCAT(product_name || ' ×' || quantity, ' • ') FROM order_items WHERE order_id=o.id), '') AS item_summary "
                "FROM orders o LEFT JOIN customers c ON o.customer_id = c.id "
                "ORDER BY o.created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_order_by_code(order_code: str) -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT o.*, c.name as customer_name, c.address as customer_address, "
            "c.lat as customer_lat, c.lon as customer_lon "
            "FROM orders o LEFT JOIN customers c ON o.customer_id = c.id "
            "WHERE o.order_code=?", (order_code.upper(),)
        ).fetchone()
        return dict(row) if row else None
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
            name = str(item.get('product_name') or item.get('name') or '').strip()
            quantity = int(item.get('quantity') or 0)
            if not name or quantity <= 0:
                continue
            weight = float(item.get('weight_per_unit_kg') or 1.0)
            volume = float(item.get('volume_per_unit_cbm') or 0.01)
            conn.execute(
                """INSERT INTO order_items (order_id, product_name, quantity, weight_per_unit_kg,
                   volume_per_unit_cbm, total_weight_kg, total_volume_cbm)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (order_id, name, quantity, weight, volume, quantity * weight, quantity * volume)
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
    conn = _get_conn()
    try:
        return [dict(row) for row in conn.execute("SELECT * FROM products ORDER BY name").fetchall()]
    finally:
        conn.close()


def update_order(order_id: int, **kwargs) -> dict | None:
    """Cập nhật đơn hàng. kwargs: bất kỳ cột nào trong orders."""
    conn = _get_conn()
    try:
        allowed = {'status', 'customer_id', 'total_quantity', 'total_weight_kg',
                    'total_volume_cbm', 'time_window_start', 'time_window_end',
                    'delivery_date_preferred', 'notes', 'source'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
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


def update_order_totals(order_id: int):
    """Tính lại total_quantity, total_weight_kg, total_volume_cbm từ order_items."""
    conn = _get_conn()
    try:
        row = conn.execute(
            """SELECT COALESCE(SUM(quantity), 0) as qty,
                      COALESCE(SUM(total_weight_kg), 0) as wt,
                      COALESCE(SUM(total_volume_cbm), 0) as vol
               FROM order_items WHERE order_id=?""", (order_id,)
        ).fetchone()
        conn.execute(
            """UPDATE orders SET total_quantity=?, total_weight_kg=?,
               total_volume_cbm=?, updated_at=? WHERE id=?""",
            (row['qty'], row['wt'], row['vol'], datetime.now().isoformat(), order_id)
        )
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════
# PHASE II: ORDER ITEMS CRUD
# ═══════════════════════════════════════

def save_order_item(order_id: int, product_name: str, quantity: int = 1,
                    weight_per_unit_kg: float = 1.0, volume_per_unit_cbm: float = 0.01,
                    is_fragile: bool = False, is_heavy: bool = False,
                    notes: str = "") -> int:
    conn = _get_conn()
    try:
        total_weight = quantity * weight_per_unit_kg
        total_volume = quantity * volume_per_unit_cbm
        cur = conn.execute(
            """INSERT INTO order_items (order_id, product_name, quantity,
               weight_per_unit_kg, volume_per_unit_cbm,
               total_weight_kg, total_volume_cbm, is_fragile, is_heavy, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order_id, product_name, quantity, weight_per_unit_kg, volume_per_unit_cbm,
             total_weight, total_volume, int(is_fragile), int(is_heavy), notes)
        )
        conn.commit()
        # Cập nhật totals cho order
        update_order_totals(order_id)
        return cur.lastrowid
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
                           period_index: int, assigned_quantity: int,
                           assigned_weight_kg: float = 0) -> int:
    conn = _get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO delivery_schedule (order_id, vehicle_id, delivery_date,
               period_index, assigned_quantity, assigned_weight_kg)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (order_id, vehicle_id, delivery_date, period_index,
             assigned_quantity, assigned_weight_kg)
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
    conn = _get_conn()
    try:
        status = "completed" if not error_message else "failed"
        conn.execute(
            """UPDATE optimization_runs 
               SET status=?, progress_pct=?, result_json=?, error_message=?, completed_at=?
               WHERE run_id=?""",
            (status, 100 if not error_message else -1,
             result_json, error_message, datetime.now().isoformat(), run_id)
        )
        conn.commit()
    finally:
        conn.close()


def get_optimization_run(run_id: str) -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM optimization_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
