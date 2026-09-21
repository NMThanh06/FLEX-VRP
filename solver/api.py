"""
FLEX-VRP — Web API Server v2
Kết nối giao diện web với thuật toán VRP Engine.
Tích hợp: đèn giao thông, persistent DB, AI learning, vehicle management.

Chạy:
    python solver/api.py

Mở trình duyệt:
    http://localhost:5000
"""

import os
import sys
import json
import asyncio
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Thêm thư mục cha vào path để import modules
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from vrp_engine import (
    Location, RoadSegment, TrafficLight,
    load_traffic_data, _get_sample_traffic_data,
    build_time_matrix, compute_average_congestion,
    nearest_neighbor, two_opt_improve, calculate_route_cost,
    find_nearest_road_congestion, count_traffic_lights_on_segment,
)
from db import (
    init_db, save_location, get_locations, delete_location,
    save_vehicle, get_vehicles, get_vehicle, delete_vehicle,
    save_trip, start_trip, complete_trip, set_trip_manual_time,
    get_trips, get_trip, get_events, save_event, delete_event,
    get_all_ai_corrections,
    get_orders, save_order, save_customer, get_customers, get_optimization_run,
    get_order_detail, update_order, delete_order, update_customer, replace_order_items, get_products,
    save_vehicle_cargo_specs, get_vehicle_cargo_spec, get_all_vehicle_cargo_specs,
    save_cargo_dimensions, get_cargo_dimensions, get_or_estimate_cargo_dimensions,
    save_loading_plan, get_loading_plan, save_ai_debate_log, get_ai_debate_logs,
)
from bin_packing import BinPacker2D, BinPacker3D, CargoItem, VehicleCargo
from ai_debate import ai_debate_council
from ai_learner import (
    AILearner, EventsAnalyzer, lookup_vehicle_specs,
    suggest_alternative_routes,
)
from test_data import seed_b2b_test_data
from pipeline import run_full_pipeline, start_async_pipeline
from chatbot import process_user_chat, process_uploaded_file

app = FastAPI(title="FLEX-VRP Route Optimizer v2")

# Serve static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ── Global State ──
import urllib.request
from datetime import datetime, date

PARQUET_PATH = None
POLY_PATH = None
ROAD_COORDS: dict = {}
ROAD_POLYLINES: dict = {}
_DF_CACHE = None
TRAFFIC_LIGHTS: list = []  # List of TrafficLight
GEMINI_API_KEY: str = None
_TRAFFIC_DATA_CACHE = {}


def get_traffic_data_for_hour(hour: int):
    global _TRAFFIC_DATA_CACHE
    if hour not in _TRAFFIC_DATA_CACHE:
        _TRAFFIC_DATA_CACHE[hour] = load_traffic_data(PARQUET_PATH, hour) if PARQUET_PATH else _get_sample_traffic_data(hour)
    return _TRAFFIC_DATA_CACHE[hour]


def _load_env():
    """Load .env file for GEMINI_API_KEY."""
    global GEMINI_API_KEY
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line.startswith('GEMINI_API_KEY=') and not line.startswith('#'):
                val = line.split('=', 1)[1].strip().strip('"').strip("'")
                if val and val != 'your_gemini_api_key_here':
                    GEMINI_API_KEY = val
                    print(f"[API] Gemini API key loaded (***{val[-4:]})")
                    return
    print("[API] No Gemini API key found. Vehicle lookup & events scan will use fallback.")


def _decode_polyline(polyline_str: str) -> list[list[float]]:
    """Decode chuỗi Google/TomTom encoded polyline thành danh sách tọa độ [[lat, lon], ...]."""
    if not polyline_str or not isinstance(polyline_str, str):
        return []
    index, lat, lng = 0, 0, 0
    coordinates = []
    length = len(polyline_str)
    while index < length:
        b, shift, result = 0, 0, 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat

        shift, result = 0, 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += dlng

        coordinates.append([lat / 1e5, lng / 1e5])
    return coordinates


def _fetch_traffic_lights_from_osm():
    """Fetch vị trí đèn giao thông TP.HCM từ Overpass API (OpenStreetMap)."""
    global TRAFFIC_LIGHTS

    # Bounding box HCM
    bbox = "10.7,106.6,10.85,106.8"
    query = f"""
    [out:json][timeout:10];
    node["highway"="traffic_signals"]({bbox});
    out body;
    """

    try:
        url = "https://overpass-api.de/api/interpreter"
        data = f"data={urllib.request.quote(query)}".encode('utf-8')
        req = urllib.request.Request(url, data=data, method="POST",
                                     headers={"User-Agent": "FLEX-VRP/2.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            elements = result.get('elements', [])

            TRAFFIC_LIGHTS = [
                TrafficLight(lat=el['lat'], lon=el['lon'], node_id=el.get('id', 0))
                for el in elements
                if 'lat' in el and 'lon' in el
            ]
            print(f"[API] Loaded {len(TRAFFIC_LIGHTS)} traffic lights from OSM Overpass")
            return

    except Exception as e:
        print(f"[API] Overpass API failed: {e}. Using fallback traffic lights.")

    # Fallback: hardcode ~40 vị trí đèn phổ biến TP.HCM
    TRAFFIC_LIGHTS = [
        TrafficLight(10.7760, 106.7005, 0),   # Ngã tư Nguyễn Huệ - Lê Lợi
        TrafficLight(10.7735, 106.6893, 0),   # Nguyễn Thị Minh Khai - CMT8
        TrafficLight(10.7821, 106.6989, 0),   # Hai Bà Trưng - Điện Biên Phủ
        TrafficLight(10.7733, 106.7001, 0),   # Nam Kỳ Khởi Nghĩa - Lê Lợi
        TrafficLight(10.7664, 106.6881, 0),   # Nguyễn Trãi - Cống Quỳnh
        TrafficLight(10.7784, 106.6854, 0),   # Điện Biên Phủ - Nguyễn Bỉnh Khiêm
        TrafficLight(10.7686, 106.6744, 0),   # 3 Tháng 2 - Sư Vạn Hạnh
        TrafficLight(10.7930, 106.6800, 0),   # Nguyễn Văn Trỗi - Hoàng Văn Thụ
        TrafficLight(10.7955, 106.7100, 0),   # Xô Viết Nghệ Tĩnh - Đinh Bộ Lĩnh
        TrafficLight(10.7876, 106.6783, 0),   # Lê Văn Sỹ - Trần Huy Liệu
        TrafficLight(10.7704, 106.6581, 0),   # Lý Thường Kiệt - Tô Hiến Thành
        TrafficLight(10.7729, 106.6670, 0),   # Thành Thái - 3/2
        TrafficLight(10.7410, 106.6960, 0),   # Phạm Hùng - Nguyễn Văn Linh
        TrafficLight(10.7824, 106.6938, 0),   # Pasteur - Điện Biên Phủ
        TrafficLight(10.7785, 106.7029, 0),   # Lê Thánh Tôn - Đồng Khởi
        TrafficLight(10.7886, 106.7035, 0),   # Nguyễn Bỉnh Khiêm - Nguyễn Thị Minh Khai
        TrafficLight(10.7713, 106.6948, 0),   # Phạm Hồng Thái - Trần Hưng Đạo
        TrafficLight(10.7659, 106.6967, 0),   # Nguyễn Thái Học - Trần Hưng Đạo
        TrafficLight(10.7620, 106.6760, 0),   # Nguyễn Tri Phương - 3/2
        TrafficLight(10.7870, 106.6930, 0),   # Võ Thị Sáu - Pasteur
        TrafficLight(10.7995, 106.6802, 0),   # Nguyễn Kiệm - Phạm Văn Đồng
        TrafficLight(10.7800, 106.6950, 0),   # Ngã 6 Phù Đổng
        TrafficLight(10.7750, 106.6900, 0),   # Vòng xoay Dân Chủ
        TrafficLight(10.7700, 106.6820, 0),   # Ngã tư Bảy Hiền
        TrafficLight(10.8020, 106.7100, 0),   # Bình Thạnh - Xô Viết Nghệ Tĩnh
        TrafficLight(10.8020, 106.6530, 0),   # Tân Bình - Cộng Hòa
        TrafficLight(10.8190, 106.6870, 0),   # Gò Vấp - Nguyễn Oanh
        TrafficLight(10.7540, 106.6630, 0),   # Q5 - Trần Hưng Đạo
        TrafficLight(10.7710, 106.6680, 0),   # Q10 - 3/2
        TrafficLight(10.7985, 106.6810, 0),   # Phú Nhuận - Nguyễn Văn Trỗi
        TrafficLight(10.7750, 106.7050, 0),   # Q1 - Tôn Đức Thắng
        TrafficLight(10.7680, 106.6950, 0),   # Q1 - Trần Hưng Đạo - Nguyễn Cư Trinh
        TrafficLight(10.7770, 106.6980, 0),   # Q1 - Lê Lai - Nguyễn Trung Trực
        TrafficLight(10.7830, 106.6870, 0),   # Q3 - Võ Văn Tần
        TrafficLight(10.7810, 106.6920, 0),   # Q3 - Pasteur - Nguyễn Đình Chiểu
        TrafficLight(10.7900, 106.6750, 0),   # Phú Nhuận - Phan Đình Phùng
        TrafficLight(10.7650, 106.6700, 0),   # Q5/Q10 - Hùng Vương
        TrafficLight(10.7600, 106.6850, 0),   # Q5 - An Dương Vương
        TrafficLight(10.8100, 106.6700, 0),   # Tân Bình - Trường Chinh
        TrafficLight(10.8050, 106.6600, 0),   # Tân Bình - Cách Mạng Tháng 8
    ]
    print(f"[API] Loaded {len(TRAFFIC_LIGHTS)} fallback traffic lights")


def _init_traffic_data():
    """Tìm file parquet khi server khởi động và trích xuất tọa độ & đường đa tuyến."""
    global PARQUET_PATH, POLY_PATH, ROAD_COORDS, ROAD_POLYLINES, _DF_CACHE

    parquet_path = None
    cache_base = os.path.expanduser("~/.cache/kagglehub/datasets/evgenyarbatov/ho-chi-minh-city-road-traffic")
    search_dirs = [cache_base]
    versions_dir = os.path.join(cache_base, "versions")
    if os.path.exists(versions_dir):
        search_dirs.append(versions_dir)
    for base in search_dirs:
        if not os.path.exists(base):
            continue
        for ver_dir in sorted(os.listdir(base), reverse=True):
            cand_obs = os.path.join(base, ver_dir, "vietnam-road-traffic-observations.parquet")
            cand_poly = os.path.join(base, ver_dir, "vietnam-road-traffic-polylines.parquet")
            if os.path.exists(cand_obs):
                PARQUET_PATH = cand_obs
            if os.path.exists(cand_poly):
                POLY_PATH = cand_poly
            if PARQUET_PATH and POLY_PATH:
                break
        if PARQUET_PATH:
            break

    # Default fallback road coordinates
    ROAD_COORDS.update({
        230935039:  (10.7735, 106.6893), 1218900523: (10.7821, 106.6989),
        329878184:  (10.7733, 106.7001), 599650678:  (10.7955, 106.7100),
        289968625:  (10.7664, 106.6881), 408246393:  (10.7784, 106.6854),
        470506018:  (10.7686, 106.6744), 35113033:   (10.7930, 106.6800),
        32577828:   (10.7995, 106.6802), 289862908:  (10.7620, 106.6760),
        1267006216: (10.7870, 106.6930), 154823449:  (10.7876, 106.6783),
        1163556205: (10.7704, 106.6581), 242307851:  (10.7729, 106.6670),
        528264270:  (10.7410, 106.6960), 1056903939: (10.7824, 106.6938),
        828323704:  (10.7785, 106.7029), 35113963:   (10.7886, 106.7035),
        719043756:  (10.7713, 106.6948), 1162960449: (10.7659, 106.6967),
    })

    if PARQUET_PATH:
        print(f"[API] Found parquet at: {PARQUET_PATH}")
        try:
            import pandas as pd
            df = pd.read_parquet(PARQUET_PATH)
            df['dt'] = pd.to_datetime(df['timestamp']).dt.tz_convert('Asia/Ho_Chi_Minh')
            df['hour'] = df['dt'].dt.hour
            df['congestion_ratio'] = df['currentSpeed'] / df['freeFlowSpeed']
            _DF_CACHE = df
            
            if 'lat' in df.columns and 'lon' in df.columns:
                coords_df = df[['way_id', 'lat', 'lon']].drop_duplicates('way_id')
                for _, row in coords_df.iterrows():
                    ROAD_COORDS[int(row['way_id'])] = (float(row['lat']), float(row['lon']))
                print(f"[API] Loaded {len(ROAD_COORDS)} road coordinates from dataset.")
        except Exception as e:
            print(f"[API] Error pre-loading dataframe: {e}")
    else:
        print("[API] No parquet found, using sample data.")

    # Load polylines
    if POLY_PATH:
        try:
            import pandas as pd
            df_poly = pd.read_parquet(POLY_PATH)
            for _, row in df_poly.iterrows():
                coords = _decode_polyline(row['polyline'])
                if coords:
                    ROAD_POLYLINES[int(row['way_id'])] = coords
            print(f"[API] Loaded {len(ROAD_POLYLINES)} road polylines from dataset.")
        except Exception as e:
            print(f"[API] Error loading polylines: {e}")

    # Fetch traffic lights
    _fetch_traffic_lights_from_osm()


def _interpret_wmo_code(code: int) -> tuple[str, str, float]:
    """Chuyển mã thời tiết WMO của Open-Meteo thành (mô tả, emoji, hệ số weather_factor)."""
    mapping = {
        0: ("Trời quang đãng, nắng đẹp", "☀️", 1.0),
        1: ("Trời quang, ít mây", "🌤️", 1.0),
        2: ("Mây rải rác", "⛅", 1.0),
        3: ("Nhiều mây, u ám", "☁️", 1.05),
        45: ("Có sương mù", "🌫️", 1.05),
        48: ("Sương mù dày", "🌫️", 1.1),
        51: ("Mưa phùn nhẹ rải rác", "🌦️", 1.1),
        53: ("Mưa phùn vừa", "🌦️", 1.15),
        55: ("Mưa phùn dầm", "🌧️", 1.15),
        61: ("Mưa rào nhẹ", "🌧️", 1.15),
        63: ("Mưa vừa", "🌧️", 1.25),
        65: ("Mưa to", "🌧️", 1.35),
        80: ("Mưa rào thoáng qua", "🌦️", 1.15),
        81: ("Mưa rào nặng hạt", "🌧️", 1.25),
        82: ("Mưa rất to", "⛈️", 1.35),
        95: ("Dông bão, sấm chớp", "⛈️", 1.35),
        96: ("Dông bão kèm mưa đá nhẹ", "⛈️", 1.4),
        99: ("Dông bão kèm mưa đá to", "⛈️", 1.4),
    }
    return mapping.get(code, ("Thời tiết bình thường", "🌤️", 1.0))


def _get_ai_corrections_dict(hour: int) -> dict:
    """Build dict corrections cho engine từ DB."""
    corrections = get_all_ai_corrections()
    d = {}
    for c in corrections:
        key = f"{c['zone_lat']},{c['zone_lon']},{c['hour_bucket']}"
        d[key] = c['correction_factor']
    return d


# ── Initialize ──
_load_env()
init_db()
_init_traffic_data()


# ═══════════════════════════════════════
# API ROUTES — Core Pages
# ═══════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve trang chính."""
    html_path = static_dir / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


# ═══════════════════════════════════════
# API ROUTES — Weather
# ═══════════════════════════════════════

@app.get("/api/weather-forecast")
async def get_weather_forecast():
    """Lấy dữ liệu thời tiết thực tế TP.HCM từ Open-Meteo API."""
    now_str = datetime.now().strftime("%H:%M - %d/%m/%Y")
    
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        "latitude=10.8231&longitude=106.6297"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code,wind_speed_10m"
        "&hourly=temperature_2m,precipitation_probability,rain,weather_code"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max"
        "&timezone=Asia%2FBangkok"
    )
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FLEX-VRP/2.0"})
        with urllib.request.urlopen(req, timeout=4) as response:
            raw = json.loads(response.read().decode("utf-8"))
            
            cur = raw.get("current", {})
            code = cur.get("weather_code", 0)
            desc, icon, factor = _interpret_wmo_code(code)
            
            # Next 24 hours
            hourly_raw = raw.get("hourly", {})
            times = hourly_raw.get("time", [])
            temps = hourly_raw.get("temperature_2m", [])
            rain_probs = hourly_raw.get("precipitation_probability", [])
            rains = hourly_raw.get("rain", [])
            codes = hourly_raw.get("weather_code", [])
            
            current_iso_hour = datetime.now().strftime("%Y-%m-%dT%H:00")
            start_idx = 0
            for idx, t in enumerate(times):
                if t >= current_iso_hour:
                    start_idx = idx
                    break
            
            hourly_24h = []
            for i in range(start_idx, min(start_idx + 24, len(times))):
                h_code = codes[i] if i < len(codes) else 0
                h_desc, h_icon, _ = _interpret_wmo_code(h_code)
                h_time_obj = datetime.fromisoformat(times[i])
                hourly_24h.append({
                    "time": h_time_obj.strftime("%H:00"),
                    "full_time": times[i],
                    "temperature": round(temps[i], 1) if i < len(temps) else 30.0,
                    "rain_prob": int(rain_probs[i]) if i < len(rain_probs) else 0,
                    "rain_mm": float(rains[i]) if i < len(rains) else 0.0,
                    "description": h_desc,
                    "icon": h_icon,
                })
            
            # 7-day daily forecast
            daily_raw = raw.get("daily", {})
            d_times = daily_raw.get("time", [])
            d_max = daily_raw.get("temperature_2m_max", [])
            d_min = daily_raw.get("temperature_2m_min", [])
            d_prob = daily_raw.get("precipitation_probability_max", [])
            d_rain = daily_raw.get("precipitation_sum", [])
            d_codes = daily_raw.get("weather_code", [])
            
            daily_7d = []
            for i in range(min(7, len(d_times))):
                d_code = d_codes[i] if i < len(d_codes) else 0
                d_desc, d_icon, _ = _interpret_wmo_code(d_code)
                daily_7d.append({
                    "date": d_times[i],
                    "temp_max": round(d_max[i], 1) if i < len(d_max) else 33.0,
                    "temp_min": round(d_min[i], 1) if i < len(d_min) else 25.0,
                    "rain_prob_max": int(d_prob[i]) if i < len(d_prob) else 30,
                    "rain_sum_mm": float(d_rain[i]) if i < len(d_rain) else 0.0,
                    "description": d_desc,
                    "icon": d_icon,
                })
            
            return {
                "success": True,
                "city": "TP. Hồ Chí Minh",
                "last_updated": now_str,
                "current": {
                    "temperature": round(cur.get("temperature_2m", 30.0), 1),
                    "apparent_temperature": round(cur.get("apparent_temperature", 33.0), 1),
                    "humidity": cur.get("relative_humidity_2m", 75),
                    "wind_speed_kmh": round(cur.get("wind_speed_10m", 10.0), 1),
                    "rain_mm": cur.get("rain", 0.0),
                    "weather_code": code,
                    "description": desc,
                    "icon": icon,
                    "recommended_weather_factor": factor,
                },
                "hourly_24h": hourly_24h,
                "daily_7d": daily_7d,
            }
    except Exception as e:
        print(f"[API] Weather API error: {e}. Using fallback.")
        current_hour = datetime.now().hour
        is_day = 6 <= current_hour <= 18
        fallback_temp = 32.0 if is_day else 27.0
        return {
            "success": True,
            "city": "TP. Hồ Chí Minh (Offline)",
            "last_updated": now_str,
            "current": {
                "temperature": fallback_temp,
                "apparent_temperature": fallback_temp + 3.0,
                "humidity": 78,
                "wind_speed_kmh": 12.0,
                "rain_mm": 0.0,
                "weather_code": 1,
                "description": "Trời nắng ráo, nhiều mây",
                "icon": "🌤️",
                "recommended_weather_factor": 1.0,
            },
            "hourly_24h": [
                {
                    "time": f"{(current_hour + i) % 24:02d}:00",
                    "temperature": round(fallback_temp + (2.0 if (7 <= (current_hour + i) % 24 <= 15) else -2.0), 1),
                    "rain_prob": 20 if (14 <= (current_hour + i) % 24 <= 18) else 5,
                    "rain_mm": 0.0,
                    "description": "Nhiều mây",
                    "icon": "⛅",
                } for i in range(24)
            ],
            "daily_7d": [],
        }


# ═══════════════════════════════════════
# API ROUTES — Traffic Analytics
# ═══════════════════════════════════════

@app.get("/api/traffic-analytics")
async def traffic_analytics(hour: int = None):
    """Trả về phân tích toàn diện 24 giờ & chi tiết khung giờ được chọn."""
    global _DF_CACHE
    now = datetime.now()
    if hour is None or hour < 0 or hour > 23:
        hour = now.hour

    now_str = now.strftime("%H:%M:%S - %d/%m/%Y")
    
    # 1. Thống kê 24 giờ
    hourly_stats = []
    
    if _DF_CACHE is not None:
        try:
            agg_24h = _DF_CACHE.groupby('hour').agg({
                'currentSpeed': 'mean',
                'freeFlowSpeed': 'mean',
                'congestion_ratio': 'mean',
                'way_id': 'nunique'
            }).reset_index()
            
            for _, row in agg_24h.iterrows():
                h = int(row['hour'])
                cr = float(row['congestion_ratio'])
                cs = float(row['currentSpeed'])
                ff = float(row['freeFlowSpeed'])
                is_peak = h in [7, 8, 17, 18]
                hourly_stats.append({
                    "hour": h,
                    "label": f"{h:02d}:00",
                    "congestion_pct": round(cr * 100, 1),
                    "congestion_ratio": round(cr, 4),
                    "current_speed": round(cs, 1),
                    "free_flow_speed": round(ff, 1),
                    "is_peak": is_peak,
                })
        except Exception as e:
            print(f"[API] Error in 24h aggregation: {e}")

    if not hourly_stats:
        for h in range(24):
            if h in [7, 8, 17, 18]:
                cr, cs, ff = 0.68, 21.0, 30.8
            elif h in [11, 12, 13, 14]:
                cr, cs, ff = 0.77, 23.8, 30.8
            elif 0 <= h <= 5:
                cr, cs, ff = 0.98, 30.4, 30.9
            else:
                cr, cs, ff = 0.82, 25.5, 30.8
            hourly_stats.append({
                "hour": h, "label": f"{h:02d}:00",
                "congestion_pct": round(cr * 100, 1),
                "congestion_ratio": round(cr, 4),
                "current_speed": round(cs, 1),
                "free_flow_speed": round(ff, 1),
                "is_peak": h in [7, 8, 17, 18],
            })

    # 2. Chi tiết khung giờ
    selected_traffic_data = load_traffic_data(PARQUET_PATH, hour) if PARQUET_PATH else _get_sample_traffic_data(hour)
    avg_congestion = compute_average_congestion(selected_traffic_data)
    
    roads_list = []
    heavy_congestion_roads = []
    
    for seg in selected_traffic_data:
        coords = ROAD_COORDS.get(seg.way_id, (10.775, 106.695))
        poly = ROAD_POLYLINES.get(int(seg.way_id), [])
        road_item = {
            "way_id": seg.way_id,
            "name": seg.name,
            "current_speed": seg.current_speed,
            "free_flow_speed": seg.free_flow_speed,
            "congestion_ratio": seg.congestion_ratio,
            "congestion_pct": f"{seg.congestion_ratio:.1%}",
            "speed_loss_pct": round((1 - seg.congestion_ratio) * 100, 1),
            "lat": coords[0],
            "lon": coords[1],
            "polyline": poly,
            "status": "heavy" if seg.congestion_ratio < 0.6 else ("medium" if seg.congestion_ratio < 0.75 else "good")
        }
        roads_list.append(road_item)
        if seg.congestion_ratio < 0.6:
            heavy_congestion_roads.append(road_item)

    top_congested = sorted(roads_list, key=lambda x: x["congestion_ratio"])[:15]
    top_smooth = sorted(roads_list, key=lambda x: x["congestion_ratio"], reverse=True)[:15]

    avg_cs = round(sum(r["current_speed"] for r in roads_list) / len(roads_list), 1) if roads_list else 24.0
    avg_ff = round(sum(r["free_flow_speed"] for r in roads_list) / len(roads_list), 1) if roads_list else 31.0
    speed_drop_pct = round((1 - avg_cs / avg_ff) * 100, 1) if avg_ff > 0 else 0.0

    if hour in [7, 8]:
        rec = "⚠️ Giờ cao điểm sáng: Mật độ xe tăng mạnh khu vực trung tâm."
    elif hour in [17, 18]:
        rec = "🛑 Giờ cao điểm chiều: Kẹt xe nghiêm trọng nhất trong ngày."
    elif hour in [11, 12, 13]:
        rec = "✅ Khung giờ trưa: Giao thông tương đối ổn định."
    elif 0 <= hour <= 5:
        rec = "🌙 Khung giờ đêm khuya: Đường hoàn toàn thông thoáng."
    else:
        rec = "🚗 Tình trạng giao thông ở mức bình thường."

    return {
        "success": True,
        "selected_hour": hour,
        "selected_hour_label": f"{hour:02d}:00",
        "last_updated": now_str,
        "summary": {
            "total_roads": len(roads_list),
            "average_congestion": round(avg_congestion, 4),
            "average_congestion_pct": f"{avg_congestion * 100:.1f}%",
            "average_current_speed": avg_cs,
            "average_free_flow_speed": avg_ff,
            "speed_drop_pct": speed_drop_pct,
            "heavy_congestion_count": len(heavy_congestion_roads),
            "peak_hours_text": "08:00 và 17:00",
            "best_hours_text": "12:00 - 14:00 và sau 21:00",
            "recommendation": rec,
        },
        "hourly_24h_chart": hourly_stats,
        "top_congested_roads": top_congested,
        "top_smooth_roads": top_smooth,
        "all_roads": roads_list,
    }


@app.get("/api/traffic-summary")
async def traffic_summary():
    """Trả về tóm tắt tình hình giao thông hiện tại."""
    current_hour = datetime.now().hour
    traffic_data = load_traffic_data(PARQUET_PATH, current_hour) if PARQUET_PATH else _get_sample_traffic_data(current_hour)
    
    if not traffic_data:
        return JSONResponse({"error": "No traffic data"}, status_code=500)

    avg = compute_average_congestion(traffic_data)
    segments_info = []
    heavy_congestion = []
    for seg in traffic_data:
        info = {
            "name": seg.name,
            "current_speed": seg.current_speed,
            "free_flow_speed": seg.free_flow_speed,
            "congestion_ratio": seg.congestion_ratio,
        }
        segments_info.append(info)
        if seg.congestion_ratio < 0.6:
            heavy_congestion.append(info)

    return {
        "hour": current_hour,
        "total_roads": len(traffic_data),
        "average_congestion": round(avg, 4),
        "average_congestion_pct": f"{avg:.1%}",
        "heavy_congestion_count": len(heavy_congestion),
        "heavy_congestion_roads": heavy_congestion[:10],
        "all_roads": sorted(segments_info, key=lambda x: x["congestion_ratio"])[:20],
    }


# ═══════════════════════════════════════
# API ROUTES — Route Optimization (Enhanced)
# ═══════════════════════════════════════

@app.post("/api/optimize")
async def optimize(request: Request):
    """
    Nhận danh sách điểm giao hàng, chạy VRP, trả kết quả.
    Enhanced: traffic lights, vehicle speed, AI correction, alternative routes.
    """
    body = await request.json()
    depots = body.get("depots", [])
    depot = body.get("depot")
    if not depot and depots:
        depot = depots[0]
    deliveries = body.get("deliveries", [])
    weather_factor = float(body.get("weather_factor", 1.0))
    target_hour = body.get("target_hour")
    return_to_depot = bool(body.get("return_to_depot", True))
    vehicle_id = body.get("vehicle_id")
    time_calibration_factor = float(body.get("time_calibration_factor", 1.8))
    
    if target_hour is None or target_hour == "":
        target_hour = datetime.now().hour
    else:
        target_hour = int(target_hour)

    if not depot or not deliveries:
        return JSONResponse({"error": "Cần ít nhất 1 kho và 1 điểm giao."}, status_code=400)

    if len(deliveries) > 20:
        return JSONResponse({"error": "Tối đa 20 điểm giao hàng."}, status_code=400)

    # Vehicle speed
    base_speed = 36.0
    vehicle_info = None
    if vehicle_id:
        vehicle_info = get_vehicle(int(vehicle_id))
        if vehicle_info:
            base_speed = vehicle_info['avg_city_speed_kmh']

    # Build locations
    locations = [
        Location("DEPOT", depot["name"], float(depot["lat"]), float(depot["lon"]), "depot")
    ]
    for i, d in enumerate(deliveries):
        locations.append(
            Location(f"D{i+1}", d["name"], float(d["lat"]), float(d["lon"]), "delivery")
        )

    # Traffic data
    traffic_data = load_traffic_data(PARQUET_PATH, target_hour) if PARQUET_PATH else _get_sample_traffic_data(target_hour)

    # AI corrections
    ai_corrections = _get_ai_corrections_dict(target_hour)

    # Events impact
    events_info = EventsAnalyzer.get_active_events()
    event_factor = events_info['combined_traffic_factor']

    # Apply event factor to weather (compound)
    effective_weather = weather_factor * event_factor

    # Build matrices (enhanced)
    time_matrix, dist_matrix, ideal_time_matrix, light_count_matrix, route_lights = build_time_matrix(
        locations, traffic_data, ROAD_COORDS,
        weather_factor=effective_weather,
        base_speed_kmh=base_speed,
        traffic_lights=TRAFFIC_LIGHTS,
        traffic_light_penalty_sec=30.0,
        high_density_red_probability=0.70,
        low_density_red_probability=0.50,
        time_calibration_factor=time_calibration_factor,
        ai_corrections=ai_corrections if ai_corrections else None,
        target_hour=target_hour,
    )

    # Optimize
    nn_route = nearest_neighbor(time_matrix, depot_index=0, return_to_depot=return_to_depot)
    optimized_route = two_opt_improve(nn_route, time_matrix, return_to_depot=return_to_depot)

    opt_time, opt_dist = calculate_route_cost(optimized_route, time_matrix, dist_matrix)
    ideal_time, _ = calculate_route_cost(optimized_route, ideal_time_matrix, dist_matrix)

    # Naive comparison
    naive_route = list(range(len(locations))) + ([0] if return_to_depot else [])
    naive_time, naive_dist = calculate_route_cost(naive_route, time_matrix, dist_matrix)

    nn_time, _ = calculate_route_cost(nn_route, time_matrix, dist_matrix)
    time_saved = naive_time - opt_time
    avg_congestion = compute_average_congestion(traffic_data)

    # Count total traffic lights on route
    total_lights = 0
    for k in range(len(optimized_route) - 1):
        total_lights += light_count_matrix[optimized_route[k]][optimized_route[k + 1]]

    # Build route details
    route_steps = []
    for step_idx in range(len(optimized_route)):
        loc_idx = optimized_route[step_idx]
        loc = locations[loc_idx]
        step = {
            "index": step_idx,
            "id": loc.id,
            "name": loc.name,
            "lat": loc.lat,
            "lon": loc.lon,
            "type": loc.type,
        }
        if step_idx > 0:
            prev_idx = optimized_route[step_idx - 1]
            step["distance_km"] = dist_matrix[prev_idx][loc_idx]
            step["time_min"] = time_matrix[prev_idx][loc_idx]
            step["ideal_time_min"] = ideal_time_matrix[prev_idx][loc_idx]
            step["traffic_lights"] = light_count_matrix[prev_idx][loc_idx]

            mid_lat = (locations[prev_idx].lat + loc.lat) / 2
            mid_lon = (locations[prev_idx].lon + loc.lon) / 2
            seg_congestion = find_nearest_road_congestion(
                mid_lat, mid_lon, traffic_data, ROAD_COORDS, avg_congestion
            )
            step["congestion_ratio"] = round(seg_congestion, 4)
        route_steps.append(step)

    # Warnings
    warnings = []
    for step in route_steps:
        if "congestion_ratio" in step and step["congestion_ratio"] < 0.6:
            warnings.append({
                "type": "traffic", "severity": "high",
                "message": f"Khu vuc {step['name']}: ket xe nang ({step['congestion_ratio']:.0%})"
            })
        if "congestion_ratio" in step and 0.6 <= step["congestion_ratio"] < 0.75:
            warnings.append({
                "type": "traffic", "severity": "medium",
                "message": f"Khu vuc {step['name']}: ket xe vua ({step['congestion_ratio']:.0%})"
            })

    if weather_factor >= 1.3:
        warnings.insert(0, {
            "type": "weather", "severity": "high",
            "message": f"Thoi tiet xau (x{weather_factor}) — +{opt_time - ideal_time:.0f} phut"
        })
    elif weather_factor >= 1.1:
        warnings.insert(0, {
            "type": "weather", "severity": "medium",
            "message": f"Mua nhe (x{weather_factor}) — +{opt_time - ideal_time:.0f} phut"
        })

    if events_info['has_events']:
        warnings.insert(0, {
            "type": "event", "severity": "info",
            "message": f"🎆 {events_info['summary']} (factor: {event_factor:.2f})"
        })

    # Alternative routes
    alternatives = suggest_alternative_routes(
        locations, time_matrix, dist_matrix,
        traffic_light_matrix=light_count_matrix,
        return_to_depot=return_to_depot,
    )
    # Build full route details for each alternative
    for alt in alternatives:
        alt_steps = []
        for si in range(len(alt['route_indices'])):
            li = alt['route_indices'][si]
            loc = locations[li]
            s = {"index": si, "id": loc.id, "name": loc.name, "lat": loc.lat, "lon": loc.lon, "type": loc.type}
            if si > 0:
                pi = alt['route_indices'][si - 1]
                s["distance_km"] = dist_matrix[pi][li]
                s["time_min"] = time_matrix[pi][li]
                s["traffic_lights"] = light_count_matrix[pi][li]
                mid_lat = (locations[pi].lat + loc.lat) / 2
                mid_lon = (locations[pi].lon + loc.lon) / 2
                s["congestion_ratio"] = round(find_nearest_road_congestion(
                    mid_lat, mid_lon, traffic_data, ROAD_COORDS, avg_congestion
                ), 4)
            alt_steps.append(s)
        alt['route'] = alt_steps
        del alt['route_indices']

    # AI learning stats
    ai_stats = AILearner.get_learning_stats()

    # Save trip to DB
    trip_id = save_trip(
        vehicle_id=int(vehicle_id) if vehicle_id else None,
        route_json=json.dumps(route_steps),
        estimated_time=opt_time,
        estimated_distance=opt_dist,
        weather_factor=weather_factor,
        target_hour=target_hour,
        num_stops=len(deliveries),
        num_traffic_lights=total_lights,
    )

    return {
        "success": True,
        "trip_id": trip_id,
        "route": route_steps,
        "return_to_depot": return_to_depot,
        "traffic_lights_on_route": route_lights,
        "stats": {
            "total_distance_km": opt_dist,
            "total_time_min": opt_time,
            "ideal_time_min": ideal_time,
            "naive_time_min": naive_time,
            "time_saved_min": round(time_saved, 1),
            "time_saved_pct": round(time_saved / naive_time * 100, 1) if naive_time > 0 else 0,
            "nn_time_min": nn_time,
            "improvement_vs_nn": round(nn_time - opt_time, 1),
            "traffic_delay_min": round(opt_time - ideal_time, 1),
            "weather_factor": weather_factor,
            "avg_congestion": round(avg_congestion, 4),
            "num_roads_analyzed": len(traffic_data),
            "return_to_depot": return_to_depot,
            "total_traffic_lights": total_lights,
            "traffic_light_delay_min": round(total_lights * 30 * 0.7 / 60, 1),
            "time_calibration_factor": time_calibration_factor,
            "event_factor": event_factor,
            "vehicle_speed_kmh": base_speed,
        },
        "warnings": warnings,
        "alternatives": alternatives,
        "events": events_info,
        "ai_stats": ai_stats,
    }


# ═══════════════════════════════════════
# API ROUTES — Locations (Persistent)
# ═══════════════════════════════════════

@app.get("/api/locations")
async def api_get_locations(type: str = None):
    return {"success": True, "locations": get_locations(type)}


@app.post("/api/locations")
async def api_save_location(request: Request):
    body = await request.json()
    loc_id = save_location(body["name"], body["lat"], body["lon"], body["type"])
    return {"success": True, "id": loc_id}


@app.delete("/api/locations/{loc_id}")
async def api_delete_location(loc_id: int):
    ok = delete_location(loc_id)
    return {"success": ok}


# ═══════════════════════════════════════
# API ROUTES — Vehicles
# ═══════════════════════════════════════

@app.get("/api/vehicles")
async def api_get_vehicles():
    return {"success": True, "vehicles": get_vehicles()}


@app.post("/api/vehicles")
async def api_save_vehicle(request: Request):
    body = await request.json()
    vid = save_vehicle(
        name=body["name"], vtype=body["type"],
        max_speed=body["max_speed_kmh"], avg_speed=body["avg_city_speed_kmh"],
        capacity_kg=body.get("capacity_kg", 0),
        capacity_cbm=body.get("capacity_cbm", 0),
        fuel_type=body.get("fuel_type", "gasoline"),
        specs_source=body.get("specs_source", "manual"),
    )
    return {"success": True, "id": vid}


@app.delete("/api/vehicles/{vid}")
async def api_delete_vehicle(vid: int):
    ok = delete_vehicle(vid)
    return {"success": ok}


@app.post("/api/vehicles/lookup")
async def api_vehicle_lookup(request: Request):
    """Tra cứu thông số xe qua Gemini API."""
    body = await request.json()
    vehicle_name = body.get("name", "")
    if not vehicle_name:
        return JSONResponse({"error": "Cần nhập tên xe"}, status_code=400)
    
    specs = lookup_vehicle_specs(vehicle_name, GEMINI_API_KEY)
    return {"success": True, "specs": specs}


# ═══════════════════════════════════════
# API ROUTES — Trips & AI Learning
# ═══════════════════════════════════════

@app.get("/api/trips")
async def api_get_trips():
    return {"success": True, "trips": get_trips(50)}


@app.post("/api/trips/{trip_id}/start")
async def api_start_trip(trip_id: int):
    ok = start_trip(trip_id)
    return {"success": ok}


@app.post("/api/trips/{trip_id}/complete")
async def api_complete_trip(trip_id: int, request: Request):
    body = await request.json()
    actual_time = body.get("actual_time_min")
    
    trip = complete_trip(trip_id, actual_time)
    if not trip:
        return JSONResponse({"error": "Trip not found"}, status_code=404)
    
    # Trigger AI learning
    learn_result = AILearner.learn_from_trip(trip)
    
    return {"success": True, "trip": trip, "ai_learning": learn_result}


@app.post("/api/trips/{trip_id}/manual-time")
async def api_manual_time(trip_id: int, request: Request):
    """Nhập thủ công thời gian đi/về cho testing."""
    body = await request.json()
    departure = body.get("departure_time", "")
    arrival = body.get("arrival_time", "")
    actual_time = float(body.get("actual_time_min", 0))
    
    if not actual_time and departure and arrival:
        # Parse HH:MM
        try:
            dep = datetime.strptime(departure, "%H:%M")
            arr = datetime.strptime(arrival, "%H:%M")
            diff = (arr - dep).total_seconds() / 60
            if diff < 0:
                diff += 1440  # Next day
            actual_time = diff
        except Exception:
            pass
    
    if actual_time <= 0:
        return JSONResponse({"error": "Cần nhập thời gian hợp lệ"}, status_code=400)
    
    trip = set_trip_manual_time(trip_id, departure, arrival, actual_time)
    if not trip:
        return JSONResponse({"error": "Trip not found"}, status_code=404)
    
    # Trigger AI learning
    learn_result = AILearner.learn_from_trip(trip)
    
    return {"success": True, "trip": trip, "ai_learning": learn_result}


# ═══════════════════════════════════════
# API ROUTES — AI Stats & Events
# ═══════════════════════════════════════

@app.get("/api/ai/stats")
async def api_ai_stats():
    stats = AILearner.get_learning_stats()
    events = EventsAnalyzer.get_active_events()
    return {"success": True, "stats": stats, "events": events}


@app.get("/api/events")
async def api_get_events(active_only: bool = False):
    return {"success": True, "events": get_events(active_only)}


@app.post("/api/events")
async def api_save_event(request: Request):
    body = await request.json()
    eid = save_event(
        event_name=body["event_name"], event_type=body["event_type"],
        start_date=body["start_date"], end_date=body["end_date"],
        impact_factor=float(body.get("traffic_impact_factor", 1.0)),
        description=body.get("description", ""),
        source=body.get("source", "manual"),
    )
    return {"success": True, "id": eid}


@app.delete("/api/events/{eid}")
async def api_delete_event(eid: int):
    ok = delete_event(eid)
    return {"success": ok}


@app.post("/api/events/scan")
async def api_scan_events():
    """Trigger Gemini scan tin tức → tạo events mới."""
    if not GEMINI_API_KEY:
        return JSONResponse({"error": "Cần Gemini API key trong .env"}, status_code=400)
    
    created = EventsAnalyzer.scan_news_for_events(GEMINI_API_KEY)
    return {"success": True, "events_created": len(created), "events": created}


# ═══════════════════════════════════════
# API ROUTES — Traffic Lights Info
# ═══════════════════════════════════════

@app.get("/api/traffic-lights")
async def api_traffic_lights():
    """Trả về danh sách đèn giao thông đã load."""
    return {
        "success": True,
        "count": len(TRAFFIC_LIGHTS),
        "lights": [{"lat": tl.lat, "lon": tl.lon} for tl in TRAFFIC_LIGHTS[:200]],
    }


@app.post("/api/route-geometry")
async def api_route_geometry(request: Request):
    """
    Nhận danh sách waypoints [{lat, lon}], trả về:
    - segments: mỗi segment có geometry thực tế từ OSRM + traffic lights gần tuyến
    - congestion info cho mỗi đoạn
    """
    body = await request.json()
    waypoints = body.get("waypoints", [])
    target_hour = body.get("target_hour")

    if target_hour is None:
        target_hour = datetime.now().hour
    else:
        target_hour = int(target_hour)

    if len(waypoints) < 2:
        return JSONResponse({"error": "Cần ít nhất 2 waypoints"}, status_code=400)

    # Khung giờ mặc định nếu waypoint không có ETA
    default_hour = target_hour

    segments = []
    all_route_lights = []

    for i in range(len(waypoints) - 1):
        wp_from = waypoints[i]
        wp_to = waypoints[i + 1]
        lat1, lon1 = float(wp_from["lat"]), float(wp_from["lon"])
        lat2, lon2 = float(wp_to["lat"]), float(wp_to["lon"])

        # Trích xuất thời điểm giao hàng / ETA của đoạn này
        seg_hour = default_hour
        eta_str = wp_from.get("eta") or wp_from.get("time") or wp_from.get("etd")
        if eta_str and isinstance(eta_str, str) and ":" in eta_str:
            try:
                seg_hour = int(eta_str.split(":")[0].strip())
            except Exception:
                pass

        # Lấy dữ liệu 77 tuyến đường Kaggle tại đúng khung giờ xe lăn bánh
        traffic_data = get_traffic_data_for_hour(seg_hour)
        avg_congestion = compute_average_congestion(traffic_data)

        # Gọi OSRM để lấy geometry thực tế
        osrm_coords = f"{lon1},{lat1};{lon2},{lat2}"
        osrm_url = f"https://router.project-osrm.org/route/v1/driving/{osrm_coords}?overview=full&geometries=geojson&steps=true"
        geometry = [[lat1, lon1], [lat2, lon2]]  # Fallback: đường thẳng
        osrm_distance = None
        osrm_duration = None

        try:
            req = urllib.request.Request(osrm_url, headers={"User-Agent": "FLEX-VRP/2.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                osrm_data = json.loads(resp.read().decode('utf-8'))
                if osrm_data.get("code") == "Ok" and osrm_data.get("routes"):
                    route = osrm_data["routes"][0]
                    coords = route["geometry"]["coordinates"]
                    geometry = [[c[1], c[0]] for c in coords]  # GeoJSON [lon,lat] → [lat,lon]
                    osrm_distance = round(route.get("distance", 0) / 1000, 2)  # m → km
                    osrm_duration = round(route.get("duration", 0) / 60, 1)    # s → min
        except Exception as e:
            print(f"[API] OSRM error for segment {i}: {e}")

        # Tìm congestion gần nhất cho đoạn này tại đúng thời điểm seg_hour
        mid_lat = (lat1 + lat2) / 2
        mid_lon = (lon1 + lon2) / 2
        seg_congestion = find_nearest_road_congestion(
            mid_lat, mid_lon, traffic_data, ROAD_COORDS, avg_congestion
        )

        # Tìm đèn giao thông gần tuyến (< 200m từ bất kỳ điểm nào trên geometry)
        seg_lights = []
        from vrp_engine import haversine_distance as _hd
        # Sample mỗi 5 điểm trên geometry để tối ưu performance
        sample_points = geometry[::max(1, len(geometry)//10)]
        for tl in TRAFFIC_LIGHTS:
            for pt in sample_points:
                d = _hd(tl.lat, tl.lon, pt[0], pt[1])
                if d < 0.2:  # < 200m
                    seg_lights.append({"lat": tl.lat, "lon": tl.lon})
                    all_route_lights.append({"lat": tl.lat, "lon": tl.lon})
                    break

        # Xác định trạng thái ùn tắc chuẩn:
        # 🔴 Kẹt nặng: < 60%
        # 🟡 Kẹt vừa: 60% - 75%
        # 🟢 Thông thoáng: >= 75%
        if seg_congestion < 0.60:
            status = "heavy"
            color = "#ef4444"
        elif seg_congestion < 0.75:
            status = "medium"
            color = "#f59e0b"
        else:
            status = "good"
            color = "#22c55e"

        segments.append({
            "index": i,
            "geometry": geometry,
            "congestion_ratio": round(seg_congestion, 4),
            "status": status,
            "color": color,
            "hour": seg_hour,
            "eta": eta_str,
            "distance_km": osrm_distance,
            "duration_min": osrm_duration,
            "traffic_lights": seg_lights,
            "traffic_light_count": len(seg_lights),
        })

    # Deduplicate traffic lights
    seen = set()
    unique_lights = []
    for tl in all_route_lights:
        key = (round(tl["lat"], 5), round(tl["lon"], 5))
        if key not in seen:
            seen.add(key)
            unique_lights.append(tl)

    return {
        "success": True,
        "segments": segments,
        "total_traffic_lights": len(unique_lights),
        "all_traffic_lights": unique_lights,
        "hour": target_hour,
        "avg_congestion": round(avg_congestion, 4),
    }


# ═══════════════════════════════════════
# PHASE II: Datasets API
# ═══════════════════════════════════════

from db import (
    get_datasets, create_dataset, rename_dataset, delete_dataset, set_active_dataset
)

@app.get("/api/datasets")
async def api_get_datasets():
    return {"success": True, "datasets": get_datasets()}

@app.post("/api/datasets")
async def api_create_dataset(request: Request):
    body = await request.json()
    name = body.get("name", "Bảng mới")
    dataset = create_dataset(name)
    return {"success": True, "dataset": dataset}

@app.put("/api/datasets/{dataset_id}")
async def api_rename_dataset(dataset_id: int, request: Request):
    body = await request.json()
    name = body.get("name")
    if not name:
        return JSONResponse({"error": "Tên không hợp lệ"}, status_code=400)
    success = rename_dataset(dataset_id, name)
    return {"success": success}

@app.delete("/api/datasets/{dataset_id}")
async def api_delete_dataset(dataset_id: int):
    success = delete_dataset(dataset_id)
    if not success:
        return JSONResponse({"error": "Không thể xóa bảng này (có thể là bảng mặc định)"}, status_code=400)
    return {"success": True}

@app.post("/api/datasets/{dataset_id}/activate")
async def api_activate_dataset(dataset_id: int):
    success = set_active_dataset(dataset_id)
    return {"success": success}


# ═══════════════════════════════════════
# PHASE II: B2B Order Management & Optimization
# ═══════════════════════════════════════

@app.get("/api/b2b/orders")
async def api_b2b_orders(status: str = None, dataset_id: int = None):
    """Lấy danh sách đơn hàng B2B."""
    return {"success": True, "orders": get_orders(status, dataset_id)}


@app.get("/api/b2b/products")
async def api_b2b_products():
    """Danh mục hàng hóa để chọn khi tạo/sửa đơn."""
    return {"success": True, "products": get_products()}


@app.get("/api/b2b/orders/{order_id}")
async def api_b2b_order_detail(order_id: int):
    order = get_order_detail(order_id)
    if not order:
        return JSONResponse({"error": "Không tìm thấy đơn hàng"}, status_code=404)
    return {"success": True, "order": order}


@app.put("/api/b2b/orders/{order_id}")
async def api_b2b_update_order(order_id: int, request: Request):
    """Lưu trực tiếp tên, địa chỉ, ngày, nguồn và các dòng hàng của một đơn."""
    body = await request.json()
    existing = get_order_detail(order_id)
    if not existing:
        return JSONResponse({"error": "Không tìm thấy đơn hàng"}, status_code=404)
    customer_id = existing.get("customer_id")
    if customer_id:
        update_args = {
            "name": str(body.get("customer_name", existing.get("customer_name") or "")).strip(),
            "address": str(body.get("customer_address", existing.get("customer_address") or "")).strip(),
            "phone": str(body.get("customer_phone", existing.get("customer_phone") or "")).strip(),
        }
        if "lat" in body and body["lat"] is not None:
            update_args["lat"] = float(body["lat"])
        if "lon" in body and body["lon"] is not None:
            update_args["lon"] = float(body["lon"])
        update_customer(customer_id, **update_args)
    update_order(order_id,
        order_date=body.get("order_date") or body.get("delivery_date_preferred"),
        delivery_date_preferred=body.get("delivery_date_preferred") or body.get("order_date"),
        source=body.get("source", existing.get("source") or "manual"),
        notes=body.get("notes", existing.get("notes") or ""),
        is_urgent=int(body.get("is_urgent", existing.get("is_urgent", 0)))
    )
    if isinstance(body.get("items"), list):
        replace_order_items(order_id, body["items"])
    return {"success": True, "order": get_order_detail(order_id)}


@app.delete("/api/b2b/orders/{order_id}")
async def api_b2b_delete_order(order_id: int):
    """Xóa một đơn hàng B2B."""
    success = delete_order(order_id)
    if not success:
        return JSONResponse({"error": "Không tìm thấy đơn hàng"}, status_code=404)
    return {"success": True, "message": f"Đã xóa đơn hàng #{order_id}"}


@app.post("/api/b2b/orders")
async def api_b2b_save_order(request: Request):
    """Tạo hoặc cập nhật đơn hàng B2B."""
    body = await request.json()
    cust_id = body.get("customer_id")
    if not cust_id and body.get("customer_name"):
        cust_id = save_customer(
            body["customer_name"],
            body.get("customer_address", "TP. Hồ Chí Minh"),
            float(body.get("lat", 10.776)),
            float(body.get("lon", 106.699))
        )
    qty = int(body.get("total_quantity") or 0)
    wt = float(body.get("total_weight_kg") or 0)
    dataset_id = int(body.get("dataset_id") or 1)
    
    order = save_order(
        customer_id=cust_id,
        order_code=body.get("order_code"),
        dataset_id=dataset_id,
        status=body.get("status", "confirmed"),
        is_urgent=int(body.get("is_urgent", 0)),
        total_quantity=qty,
        total_weight_kg=wt,
        time_window_start=body.get("time_window_start", "08:00"),
        time_window_end=body.get("time_window_end", "17:00"),
        order_date=body.get("order_date") or body.get("delivery_date_preferred"),
        delivery_date_preferred=body.get("delivery_date_preferred") or body.get("order_date"),
        notes=body.get("notes", ""),
        source=body.get("source", "manual")
    )
    if isinstance(body.get("items"), list) and body["items"]:
        replace_order_items(order["id"], body["items"])
    elif body.get("item_name"):
        weight_per = round(wt / max(1, qty), 1) if qty > 0 else 0
        replace_order_items(order["id"], [{
            "product_name": body.get("item_name"),
            "quantity": qty,
            "weight_per_unit_kg": weight_per,
            "width_cm": float(body.get("width_cm", 35)),
            "depth_cm": float(body.get("depth_cm", 40)),
            "height_cm": float(body.get("height_cm", 25)),
            "is_heavy": int(body.get("is_heavy", 0)),
            "is_fragile": int(body.get("is_fragile", 0)),
            "requires_cold": int(body.get("requires_cold", 0))
        }])

    # Logic xử lý đơn gấp và hàng đợi 50 đơn
    run_id = None
    is_urgent = int(body.get("is_urgent", 0))
    if is_urgent == 1:
        # Nếu là đơn gấp, kích hoạt tối ưu ngay
        run_id = start_async_pipeline(planning_days=1)
    else:
        # Kiểm tra số lượng đơn chờ không gấp
        pending_orders = get_orders(status="pending")
        non_urgent_pending = [o for o in pending_orders if o.get("is_urgent", 0) == 0]
        if len(non_urgent_pending) >= 50:
            run_id = start_async_pipeline(planning_days=5)

    res = {"success": True, "order": order}
    if run_id:
        res["run_id"] = run_id
        res["message"] = "Đã kích hoạt quá trình tối ưu tự động."
    return res


@app.post("/api/b2b/seed")
async def api_b2b_seed():
    """Nạp nhanh bộ dữ liệu test B2B MVP (1 kho Q7, 6 tiệm tạp hóa, 3 xe, 10 đơn)."""
    stats = seed_b2b_test_data()
    return {"success": True, "stats": stats, "orders": get_orders()}


@app.post("/api/b2b/optimize")
async def api_b2b_optimize(request: Request):
    """Khởi chạy pipeline tối ưu đa xe đa ngày (bất đồng bộ)."""
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    days = int(body.get("planning_days", 5))
    limit = body.get("order_limit")
    if limit is not None:
        limit = int(limit)
    run_id = start_async_pipeline(planning_days=days, order_limit=limit)
    return {"success": True, "run_id": run_id}


@app.get("/api/b2b/optimize-status/{run_id}")
async def api_b2b_optimize_status(run_id: str):
    """Kiểm tra tiến trình tối ưu theo thời gian thực."""
    run_info = get_optimization_run(run_id)
    if not run_info:
        return JSONResponse({"error": "Không tìm thấy phiên tối ưu"}, status_code=404)
    return {"success": True, "run": run_info}


@app.get("/api/b2b/optimize-result/{run_id}")
async def api_b2b_optimize_result(run_id: str):
    """Lấy toàn bộ kết quả phân bổ chi phí, so sánh và lộ trình xe."""
    run_info = get_optimization_run(run_id)
    if not run_info:
        return JSONResponse({"error": "Không tìm thấy phiên tối ưu"}, status_code=404)
    res_data = {}
    if run_info.get("result_json"):
        try:
            res_data = json.loads(run_info["result_json"])
        except Exception:
            pass
    return {"success": True, "run": run_info, "result": res_data}


@app.post("/api/chat")
async def api_chat(request: Request):
    """Nhận tin nhắn Chatbot, bóc tách đơn hàng bằng AI."""
    body = await request.json()
    message = body.get("message", "")
    session_id = body.get("session_id", "default")
    provider = body.get("provider", "gemini")
    res = await asyncio.to_thread(process_user_chat, message, session_id=session_id, preferred_provider=provider)
    return res


@app.post("/api/chat/upload")
async def api_chat_upload(request: Request):
    """Upload file đơn hàng (CSV/Text/Excel) để AI đọc."""
    form = await request.form()
    file_obj = form.get("file")
    dataset_id = form.get("dataset_id", "1")
    message = form.get("message", "")
    if not file_obj:
        return JSONResponse({"error": "Chưa chọn file để tải lên"}, status_code=400)
    contents = await file_obj.read()
    try:
        res = await asyncio.to_thread(process_uploaded_file, contents, file_obj.filename, int(dataset_id), message)
        return res
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"success": False, "reply": f"⚠️ Lỗi xử lý file: {str(e)}"}, status_code=200)

# ═══════════════════════════════════════
# FLOOD RISK & HOLIDAY ENDPOINTS
# ═══════════════════════════════════════

# Danh sách tuyến đường thường xuyên ngập tại TPHCM (nguồn: báo chí, dữ liệu công khai)
FLOOD_PRONE_ROADS = [
    {"name": "Nguyễn Hữu Cảnh", "district": "Bình Thạnh", "severity": 0.95, "lat": 10.7892, "lng": 106.7127},
    {"name": "Phan Huy Ích", "district": "Gò Vấp", "severity": 0.75, "lat": 10.8364, "lng": 106.6535},
    {"name": "Lê Đức Thọ", "district": "Gò Vấp", "severity": 0.70, "lat": 10.8320, "lng": 106.6378},
    {"name": "Huỳnh Tấn Phát", "district": "Quận 7", "severity": 0.85, "lat": 10.7389, "lng": 106.7261},
    {"name": "Quốc lộ 13", "district": "Thủ Đức", "severity": 0.65, "lat": 10.8618, "lng": 106.7190},
    {"name": "Tô Ngọc Vân", "district": "Thủ Đức", "severity": 0.60, "lat": 10.8565, "lng": 106.7518},
    {"name": "Đỗ Xuân Hợp", "district": "Quận 9", "severity": 0.70, "lat": 10.8335, "lng": 106.7817},
    {"name": "An Dương Vương", "district": "Quận 5/8", "severity": 0.80, "lat": 10.7517, "lng": 106.6560},
    {"name": "Hồ Học Lãm", "district": "Bình Tân", "severity": 0.75, "lat": 10.7279, "lng": 106.6072},
    {"name": "Kinh Dương Vương", "district": "Bình Tân/Q6", "severity": 0.80, "lat": 10.7429, "lng": 106.6230},
    {"name": "Nguyễn Văn Quá", "district": "Quận 12", "severity": 0.65, "lat": 10.8552, "lng": 106.6305},
    {"name": "Lê Văn Khương", "district": "Quận 12", "severity": 0.60, "lat": 10.8477, "lng": 106.6464},
    {"name": "Trần Xuân Soạn", "district": "Quận 7", "severity": 0.75, "lat": 10.7445, "lng": 106.7199},
    {"name": "Bùi Hữu Nghĩa", "district": "Bình Thạnh", "severity": 0.55, "lat": 10.7958, "lng": 106.6988},
    {"name": "Ung Văn Khiêm", "district": "Bình Thạnh", "severity": 0.70, "lat": 10.8013, "lng": 106.7073},
    {"name": "Phan Xích Long", "district": "Phú Nhuận", "severity": 0.50, "lat": 10.7984, "lng": 106.6813},
    {"name": "Võ Văn Ngân", "district": "Thủ Đức", "severity": 0.65, "lat": 10.8498, "lng": 106.7685},
    {"name": "Nguyễn Xí", "district": "Bình Thạnh", "severity": 0.60, "lat": 10.8054, "lng": 106.7000},
    {"name": "Thành Thái", "district": "Quận 10", "severity": 0.55, "lat": 10.7730, "lng": 106.6673},
    {"name": "Lý Thường Kiệt", "district": "Quận 10/11", "severity": 0.50, "lat": 10.7746, "lng": 106.6579},
    {"name": "Cách Mạng Tháng 8", "district": "Quận 10/3", "severity": 0.55, "lat": 10.7832, "lng": 106.6659},
    {"name": "Ba Tháng Hai", "district": "Quận 10", "severity": 0.50, "lat": 10.7730, "lng": 106.6676},
    {"name": "Hậu Giang", "district": "Quận 6", "severity": 0.70, "lat": 10.7486, "lng": 106.6302},
    {"name": "Trường Chinh", "district": "Tân Bình/Q12", "severity": 0.55, "lat": 10.8182, "lng": 106.6312},
]

# Danh sách ngày lễ ảnh hưởng giao thông & logistics tại VN
VN_HOLIDAYS = [
    {"name": "Tết Dương lịch", "date": "01-01", "duration": 1, "impact": "high"},
    {"name": "Tết Nguyên đán (ước tính)", "date": "01-28", "duration": 7, "impact": "critical"},
    {"name": "Giỗ Tổ Hùng Vương", "date": "04-07", "duration": 1, "impact": "high"},
    {"name": "Ngày Giải phóng miền Nam", "date": "04-30", "duration": 1, "impact": "critical"},
    {"name": "Quốc tế Lao động", "date": "05-01", "duration": 1, "impact": "critical"},
    {"name": "Quốc khánh", "date": "09-02", "duration": 2, "impact": "critical"},
    {"name": "Trung thu", "date": "09-17", "duration": 1, "impact": "high"},
    {"name": "Noel", "date": "12-25", "duration": 1, "impact": "high"},
]


@app.get("/api/flood-risk")
async def api_flood_risk():
    """Tính toán nguy cơ ngập dựa trên dự báo mưa từ Open-Meteo + lịch sử ngập."""
    import urllib.request
    import urllib.error
    
    # Lấy dự báo mưa 48h từ Open-Meteo (TPHCM: 10.8231, 106.6297)
    rain_data = {"hourly_max_mm": 0, "total_24h_mm": 0, "rain_hours": []}
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast?"
            "latitude=10.8231&longitude=106.6297"
            "&hourly=precipitation,rain"
            "&timezone=Asia/Ho_Chi_Minh"
            "&forecast_days=2"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "FLEX-VRP/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            meteo = json.loads(resp.read().decode('utf-8'))
            hourly = meteo.get("hourly", {})
            precip = hourly.get("precipitation", [])
            times = hourly.get("time", [])
            
            if precip:
                rain_data["hourly_max_mm"] = max(precip)
                rain_data["total_24h_mm"] = sum(precip[:24])
                # Tìm giờ mưa nặng
                for i, (t, p) in enumerate(zip(times, precip)):
                    if p > 5:  # > 5mm/h = mưa đáng kể
                        rain_data["rain_hours"].append({"time": t, "mm": p})
    except Exception as e:
        print(f"[API] Open-Meteo error: {e}")
    
    # Tính nguy cơ ngập cho từng tuyến đường
    max_rain = rain_data["hourly_max_mm"]
    total_rain = rain_data["total_24h_mm"]
    
    flood_roads = []
    for road in FLOOD_PRONE_ROADS:
        # Công thức nguy cơ: severity_history * rain_factor
        if max_rain > 50:
            rain_factor = 1.0  # Mưa rất lớn
        elif max_rain > 30:
            rain_factor = 0.75
        elif max_rain > 15:
            rain_factor = 0.45
        elif max_rain > 5:
            rain_factor = 0.20
        else:
            rain_factor = 0.05
        
        risk_score = round(road["severity"] * rain_factor * 100, 1)
        
        status = "safe"
        if risk_score > 60:
            status = "danger"
        elif risk_score > 30:
            status = "warning"
        
        flood_roads.append({
            "name": road["name"],
            "district": road["district"],
            "risk_score": risk_score,
            "status": status,
            "lat": road["lat"],
            "lng": road["lng"],
        })
    
    # Sắp xếp theo risk_score giảm dần
    flood_roads.sort(key=lambda x: x["risk_score"], reverse=True)
    
    # Tổng quan
    danger_count = sum(1 for r in flood_roads if r["status"] == "danger")
    warning_count = sum(1 for r in flood_roads if r["status"] == "warning")
    
    overall = "safe"
    if danger_count > 3:
        overall = "danger"
    elif danger_count > 0 or warning_count > 3:
        overall = "warning"
    
    return {
        "success": True,
        "overall_status": overall,
        "danger_count": danger_count,
        "warning_count": warning_count,
        "rain_forecast": {
            "max_hourly_mm": rain_data["hourly_max_mm"],
            "total_24h_mm": round(total_rain, 1),
            "heavy_rain_hours": rain_data["rain_hours"][:6],
        },
        "roads": flood_roads,
    }


@app.get("/api/holidays")
async def api_holidays():
    """Trả về danh sách ngày lễ VN + countdown."""
    from datetime import datetime, timedelta
    
    today = datetime.now()
    current_year = today.year
    
    holidays = []
    for h in VN_HOLIDAYS:
        month, day = h["date"].split("-")
        
        # Thử năm nay, nếu đã qua thì lấy năm sau
        try:
            hdate = datetime(current_year, int(month), int(day))
        except ValueError:
            continue
        
        if hdate.date() < today.date():
            hdate = datetime(current_year + 1, int(month), int(day))
        
        days_until = (hdate.date() - today.date()).days
        
        holidays.append({
            "name": h["name"],
            "date": hdate.strftime("%Y-%m-%d"),
            "days_until": days_until,
            "duration": h["duration"],
            "impact": h["impact"],
            "display_date": hdate.strftime("%d/%m/%Y"),
        })
    
    # Sắp xếp theo ngày gần nhất
    holidays.sort(key=lambda x: x["days_until"])
    
    # Ngày lễ sắp tới (trong 30 ngày)
    upcoming = [h for h in holidays if h["days_until"] <= 30]
    
    return {
        "success": True,
        "upcoming": upcoming,
        "all_holidays": holidays[:8],  # 8 ngày lễ gần nhất
        "next_holiday": holidays[0] if holidays else None,
    }


# ═══════════════════════════════════════
# PHASE 2: BIN PACKING 2D API ENDPOINTS
# ═══════════════════════════════════════

@app.get("/api/packing/specs")
async def api_packing_get_specs():
    """Lấy danh sách thông số kích thước thùng xe của toàn bộ đội xe."""
    specs = get_all_vehicle_cargo_specs()
    return {"success": True, "specs": specs}


@app.put("/api/packing/specs/{vehicle_id}")
async def api_packing_update_specs(vehicle_id: int, request: Request):
    """Cập nhật kích thước thùng xe (chiều rộng, dài, cao, cửa, số lớp)."""
    body = await request.json()
    w = float(body.get("cargo_width_cm") or 190.0)
    d = float(body.get("cargo_depth_cm") or 430.0)
    h = float(body.get("cargo_height_cm") or 185.0)
    door = body.get("door_position", "rear")
    layers = int(body.get("max_layers", 2))
    notes = body.get("notes", "")
    save_vehicle_cargo_specs(vehicle_id, w, d, h, door, layers, notes)
    spec = get_vehicle_cargo_spec(vehicle_id)
    return {"success": True, "spec": spec}


@app.post("/api/packing/dimensions/estimate")
async def api_packing_estimate_dimensions(request: Request):
    """Ước lượng kích thước và đặc tính kiện hàng từ tên sản phẩm, cân nặng, thể tích bằng AI."""
    body = await request.json()
    name = str(body.get("item_name") or body.get("name") or body.get("product_name") or "Hàng hóa").strip()
    wt = float(body.get("weight_kg") or 1.0)
    vol = float(body.get("volume_cbm") or 0.01)
    
    try:
        from chatbot import call_gemini
        import json
        prompt = f"""
Bạn là chuyên gia logistics. Hãy ước lượng kích thước 3 chiều (width_cm, depth_cm, height_cm) và 
đặc tính (is_fragile, is_heavy, requires_cold) cho loại hàng hóa sau:
Tên: {name}
Trọng lượng: {wt} kg
Thể tích (tùy chọn): {vol} CBM

Lưu ý:
- Trọng lượng >= 8kg thường là hàng nặng (is_heavy=1)
- Các mặt hàng đông lạnh, sữa, kem cần lạnh (requires_cold=1)
- Các mặt hàng thủy tinh, gốm sứ dễ vỡ (is_fragile=1)

Chỉ trả về ĐÚNG JSON với format sau, không kèm bất kỳ giải thích nào:
{{
  "width_cm": 35.0,
  "depth_cm": 40.0,
  "height_cm": 25.0,
  "is_fragile": 0,
  "is_heavy": 0,
  "requires_cold": 0
}}
"""
        res_text = call_gemini(prompt)
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0]
        elif "```" in res_text:
            res_text = res_text.split("```")[1].split("```")[0]
            
        ai_data = json.loads(res_text.strip())
        dims = {
            "item_identifier": name,
            "width_cm": float(ai_data.get("width_cm", 35.0)),
            "depth_cm": float(ai_data.get("depth_cm", 40.0)),
            "height_cm": float(ai_data.get("height_cm", 25.0)),
            "weight_kg": wt,
            "is_fragile": int(ai_data.get("is_fragile", 0)),
            "is_heavy": int(ai_data.get("is_heavy", 0)),
            "requires_cold": int(ai_data.get("requires_cold", 0))
        }
    except Exception as e:
        print("AI estimation error:", e)
        # Fallback to heuristics
        dims = get_or_estimate_cargo_dimensions(name, wt, vol)
        
    return {"success": True, "dimensions": dims}


@app.post("/api/packing/compute")
async def api_packing_compute(request: Request):
    """
    Tính toán sơ đồ xếp hàng 2D cho một chuyến xe.
    Nhận payload:
      - Cách 1: { run_id: "...", day_idx: 0, route_idx: 0 }
      - Cách 2: { vehicle: {...}, items: [...] }
      - Cách 3: { vehicle_id: ..., stops: [...], total_load_kg: ... }
    """
    body = await request.json()

    # Cách 1: Truy xuất từ kết quả optimization_run
    if "run_id" in body:
        run_id = body["run_id"]
        day_idx = int(body.get("day_idx", 0))
        route_idx = int(body.get("route_idx", 0))

        run_info = get_optimization_run(run_id)
        if not run_info or not run_info.get("result_json"):
            return JSONResponse({"error": "Không tìm thấy kết quả tối ưu"}, status_code=404)

        try:
            res_json = json.loads(run_info["result_json"])
            schedule = res_json.get("schedule", [])
            if day_idx < len(schedule):
                day = schedule[day_idx]
                routes = day.get("routes", [])
                if route_idx < len(routes):
                    rt = routes[route_idx]
                    if "packing_plan" in rt:
                        return {"success": True, "packing_plan": rt["packing_plan"]}
        except Exception as e:
            return JSONResponse({"error": f"Lỗi đọc dữ liệu: {str(e)}"}, status_code=500)

    # Cách 3: Tính toán trực tiếp từ stops & vehicle_id
    if "stops" in body:
        vid = body.get("vehicle_id") or 1
        # Chuyển đổi tên xe nếu truyền chuỗi
        spec = None
        if isinstance(vid, int) or (isinstance(vid, str) and vid.isdigit()):
            spec = get_vehicle_cargo_spec(int(vid))
        if not spec:
            all_specs = get_all_vehicle_cargo_specs()
            for s in all_specs:
                if str(vid).lower() in str(s.get("vehicle_name", "")).lower():
                    spec = s
                    break
            if not spec and all_specs:
                spec = all_specs[0]
        if not spec:
            spec = {"cargo_width_cm": 190.0, "cargo_depth_cm": 430.0, "cargo_height_cm": 185.0, "max_weight_kg": 2500.0}

        vehicle_cargo = VehicleCargo(
            vehicle_id=int(spec.get("vehicle_id") or 1),
            vehicle_name=str(spec.get("vehicle_name") or "Xe tải"),
            cargo_width_cm=float(spec.get("cargo_width_cm") or 190.0),
            cargo_depth_cm=float(spec.get("cargo_depth_cm") or 430.0),
            cargo_height_cm=float(spec.get("cargo_height_cm") or 185.0),
            max_weight_kg=float(spec.get("max_weight_kg") or 2500.0),
            door_position=str(spec.get("door_position") or "rear"),
            max_layers=int(spec.get("max_layers") or 2)
        )

        cargo_items = []
        item_counter = 1
        for stop in body.get("stops", []):
            st_type = stop.get("type", "customer")
            if st_type == "depot":
                continue
            step = int(stop.get("step") or 1)
            order_code = str(stop.get("order_code") or "")
            cust_name = str(stop.get("name") or stop.get("customer_name") or "")
            qty = int(stop.get("quantity") or 1)
            total_wt = float(stop.get("weight_kg") or 20.0)
            wt_per_unit = max(0.5, total_wt / max(1, qty))

            dims = get_or_estimate_cargo_dimensions(cust_name or order_code, wt_per_unit, 0.01)

            pack_count = min(qty, 20)
            adj_wt = total_wt / max(1, pack_count)
            for k in range(pack_count):
                cargo_items.append(CargoItem(
                    item_id=f"ITEM_{item_counter:03d}",
                    name=f"Kiện {item_counter} ({order_code or cust_name[:12]})",
                    width_cm=dims.get("width_cm", 35.0),
                    depth_cm=dims.get("depth_cm", 40.0),
                    height_cm=dims.get("height_cm", 25.0),
                    weight_kg=round(adj_wt, 1),
                    is_fragile=bool(dims.get("is_fragile", 0)),
                    is_heavy=bool(dims.get("is_heavy", 0)),
                    requires_cold=bool(dims.get("requires_cold", 0)),
                    delivery_order=step,
                    order_code=order_code,
                    customer_name=cust_name,
                    quantity_index=k + 1
                ))
                item_counter += 1

        packer = BinPacker3D()
        packing_result = packer.pack(cargo_items, vehicle_cargo)
        
        # Chạy Hội Đồng 2 AI Tranh Biện (Proposer vs Opponent)
        route_label = f"ROUTE_{vid}_{len(body.get('stops', []))}"
        debate_summary = ai_debate_council.debate_loading_plan(packing_result, vehicle_cargo, route_id=route_label)
        
        packing_dict = packing_result.to_dict()
        packing_dict["debate_summary"] = debate_summary.to_dict()
        packing_dict["debate_verified"] = debate_summary.consensus_reached

        # Tự động lưu trữ vào MySQL loading_plans
        try:
            save_loading_plan(
                route_id=route_label,
                vehicle_id=vehicle_cargo.vehicle_id,
                truck_width=vehicle_cargo.cargo_width_cm,
                truck_depth=vehicle_cargo.cargo_depth_cm,
                truck_height=vehicle_cargo.cargo_height_cm,
                placed_items=packing_dict.get("placed_items", []),
                unplaced_items=packing_dict.get("unplaced_items", []),
                total_weight=packing_result.total_packed_weight_kg,
                space_util=packing_result.space_utilization_pct,
                balance_ratio=packing_result.balance_ratio,
                warnings=packing_result.warnings,
                debate_score=debate_summary.consensus_score,
                debate_verified=1 if debate_summary.consensus_reached else 0
            )
        except Exception as e:
            print(f"[API] Error saving plan to MySQL: {e}")

        return {
            "success": True,
            "packing_plan": packing_dict,
            "debate_summary": debate_summary.to_dict()
        }

    # Cách 2: Tính toán từ custom vehicle & items
    v_data = body.get("vehicle", {})
    items_data = body.get("items", [])

    if not v_data and not items_data:
        return JSONResponse({"error": "Thiếu dữ liệu vehicle hoặc items"}, status_code=400)

    vehicle_cargo = VehicleCargo(
        vehicle_id=int(v_data.get("vehicle_id") or 1),
        vehicle_name=str(v_data.get("vehicle_name") or "Xe tải"),
        cargo_width_cm=float(v_data.get("cargo_width_cm") or 190.0),
        cargo_depth_cm=float(v_data.get("cargo_depth_cm") or 430.0),
        cargo_height_cm=float(v_data.get("cargo_height_cm") or 185.0),
        max_weight_kg=float(v_data.get("max_weight_kg") or 2500.0),
        door_position=str(v_data.get("door_position") or "rear"),
        max_layers=int(v_data.get("max_layers") or 3)
    )

    cargo_items = []
    for idx, it in enumerate(items_data, 1):
        cargo_items.append(CargoItem(
            item_id=str(it.get("item_id") or f"ITM_{idx:03d}"),
            name=str(it.get("name") or f"Kiện hàng {idx}"),
            width_cm=float(it.get("width_cm") or 35.0),
            depth_cm=float(it.get("depth_cm") or 40.0),
            height_cm=float(it.get("height_cm") or 25.0),
            weight_kg=float(it.get("weight_kg") or 5.0),
            is_fragile=bool(it.get("is_fragile")),
            is_heavy=bool(it.get("is_heavy")),
            requires_cold=bool(it.get("requires_cold")),
            delivery_order=int(it.get("delivery_order") or 1),
            order_code=str(it.get("order_code") or ""),
            customer_name=str(it.get("customer_name") or ""),
            eta=str(it.get("eta") or "")
        ))

    packer = BinPacker3D()
    packing_result = packer.pack(cargo_items, vehicle_cargo)
    debate_summary = ai_debate_council.debate_loading_plan(packing_result, vehicle_cargo, route_id="CUSTOM_ROUTE")
    packing_dict = packing_result.to_dict()
    packing_dict["debate_summary"] = debate_summary.to_dict()
    packing_dict["debate_verified"] = debate_summary.consensus_reached

    return {
        "success": True,
        "packing_plan": packing_dict,
        "debate_summary": debate_summary.to_dict()
    }


@app.post("/api/packing/debate")
async def api_packing_debate(request: Request):
    """
    Endpoint Hội Đồng 2 AI Tranh Biện (Proposer vs Opponent):
    Chạy phản biện đa vòng, soi lỗi theo từng khách và lưu trữ vào MySQL.
    """
    body = await request.json()
    route_id = str(body.get("route_id") or "ROUTE_DEBATE")
    vid = body.get("vehicle_id") or 1
    spec = get_vehicle_cargo_spec(int(vid) if str(vid).isdigit() else 1)
    
    vehicle_cargo = VehicleCargo(
        vehicle_id=int(spec.get("vehicle_id") or 1),
        vehicle_name=str(spec.get("vehicle_name") or "Xe tải"),
        cargo_width_cm=float(spec.get("cargo_width_cm") or 190.0),
        cargo_depth_cm=float(spec.get("cargo_depth_cm") or 430.0),
        cargo_height_cm=float(spec.get("cargo_height_cm") or 185.0),
        max_weight_kg=float(spec.get("max_weight_kg") or 2500.0),
        door_position=str(spec.get("door_position") or "rear"),
        max_layers=int(spec.get("max_layers") or 3)
    )

    cargo_items = []
    for idx, it in enumerate(body.get("items", []), 1):
        cargo_items.append(CargoItem(
            item_id=str(it.get("item_id") or f"ITM_{idx:03d}"),
            name=str(it.get("name") or f"Kiện {idx}"),
            width_cm=float(it.get("width_cm") or 35.0),
            depth_cm=float(it.get("depth_cm") or 40.0),
            height_cm=float(it.get("height_cm") or 25.0),
            weight_kg=float(it.get("weight_kg") or 5.0),
            is_fragile=bool(it.get("is_fragile")),
            is_heavy=bool(it.get("is_heavy")),
            requires_cold=bool(it.get("requires_cold")),
            delivery_order=int(it.get("delivery_order") or 1),
            order_code=str(it.get("order_code") or ""),
            customer_name=str(it.get("customer_name") or "Khách hàng"),
            eta=str(it.get("eta") or "")
        ))

    packer = BinPacker3D()
    packing_result = packer.pack(cargo_items, vehicle_cargo)
    debate_summary = ai_debate_council.debate_loading_plan(packing_result, vehicle_cargo, route_id=route_id)

    return {
        "success": True,
        "debate_summary": debate_summary.to_dict(),
        "packing_plan": packing_result.to_dict()
    }


@app.get("/api/packing/debate/logs")
async def api_get_debate_logs(limit: int = 10):
    """Lấy danh sách nhật ký tranh biện đã lưu trong MySQL flexvrp."""
    logs = get_ai_debate_logs(limit=limit)
    return {"success": True, "logs": logs}


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  FLEX-VRP Web Interface v2")
    print("  Open: http://localhost:5000")
    print(f"  Traffic lights: {len(TRAFFIC_LIGHTS)}")
    print(f"  Gemini API: {'✅ Ready' if GEMINI_API_KEY else '❌ Not configured'}")
    print("=" * 50 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=5000)
