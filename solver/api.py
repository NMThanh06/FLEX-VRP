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
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Thêm thư mục cha vào path để import modules
sys.path.insert(0, str(Path(__file__).parent))
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
)
from ai_learner import (
    AILearner, EventsAnalyzer, lookup_vehicle_specs,
    suggest_alternative_routes,
)

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


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  FLEX-VRP Web Interface v2")
    print("  Open: http://localhost:5000")
    print(f"  Traffic lights: {len(TRAFFIC_LIGHTS)}")
    print(f"  Gemini API: {'✅ Ready' if GEMINI_API_KEY else '❌ Not configured'}")
    print("=" * 50 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=5000)
