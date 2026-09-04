"""
╔══════════════════════════════════════════════════════════════════╗
║  FLEX-VRP — Route Optimization Engine (Prototype)               ║
║  Thuật toán tìm đường tối ưu dựa trên dữ liệu kẹt xe thực tế  ║
║  Dataset: Ho Chi Minh City Road Traffic (TomTom / Kaggle)       ║
╚══════════════════════════════════════════════════════════════════╝

Mô tả:
------
Chương trình này giải bài toán Vehicle Routing Problem (VRP) đơn giản hóa:
- 1 kho xuất phát (Warehouse/Depot)
- 8 điểm giao hàng (Delivery Points) phân bố trên các đường thực tế ở HCM
- Sử dụng dữ liệu giao thông thực tế từ TomTom để tính toán thời gian di chuyển
- Áp dụng hệ số thời tiết (Weather Factor) để điều chỉnh tốc độ

Thuật toán:
----------
1. Nearest Neighbor Heuristic  - Giải pháp ban đầu (greedy)
2. 2-Opt Local Search          - Cải thiện giải pháp bằng hoán đổi cạnh

Cách chạy:
----------
    python solver/vrp_engine.py

Tác giả: FLEX-VRP Team
"""

import math
import json
import os
import sys
from datetime import datetime
from typing import NamedTuple

# ============================================================
# PHẦN 1: CẤU TRÚC DỮ LIỆU (DATA STRUCTURES)
# ============================================================

class Location(NamedTuple):
    """
    Đại diện cho 1 điểm trên bản đồ.

    Attributes:
        id:   Mã định danh
        name: Tên địa điểm
        lat:  Vĩ độ (Latitude)
        lon:  Kinh độ (Longitude)
        type: "depot" (kho) hoặc "delivery" (điểm giao)
    """
    id: str
    name: str
    lat: float
    lon: float
    type: str  # "depot" hoặc "delivery"


class RoadSegment(NamedTuple):
    """
    Đại diện cho 1 đoạn đường với thông tin giao thông.

    Attributes:
        way_id:             Mã đường (từ OpenStreetMap)
        name:               Tên đường
        current_speed:      Tốc độ hiện tại (km/h) - có tính kẹt xe
        free_flow_speed:    Tốc độ khi thông thoáng (km/h)
        congestion_ratio:   Tỉ lệ kẹt xe = current / free_flow (0.0 → 1.0)
                            0.0 = kẹt cứng, 1.0 = thông thoáng hoàn toàn
    """
    way_id: int
    name: str
    current_speed: float
    free_flow_speed: float
    congestion_ratio: float


class TrafficLight(NamedTuple):
    """
    Đại diện cho 1 đèn giao thông.

    Attributes:
        lat:      Vĩ độ
        lon:      Kinh độ
        node_id:  Mã node OSM (0 nếu không có)
    """
    lat: float
    lon: float
    node_id: int = 0


class RouteResult(NamedTuple):
    """
    Kết quả tối ưu hóa tuyến đường.

    Attributes:
        route:          Danh sách Location theo thứ tự đi
        total_distance: Tổng quãng đường (km)
        total_time:     Tổng thời gian (phút)
        total_time_no_traffic: Thời gian nếu không kẹt xe (phút)
        time_saved_vs_naive:   Thời gian tiết kiệm so với đi theo thứ tự ban đầu (phút)
    """
    route: list
    total_distance: float
    total_time: float
    total_time_no_traffic: float
    time_saved_vs_naive: float


# ============================================================
# PHẦN 2: TÍNH KHOẢNG CÁCH (DISTANCE CALCULATION)
# ============================================================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Tính khoảng cách giữa 2 tọa độ GPS trên mặt cầu Trái Đất.

    Sử dụng công thức Haversine — chuẩn xác hơn khoảng cách Euclidean
    vì Trái Đất là hình cầu, không phải mặt phẳng.

    Công thức:
        a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlon/2)
        c = 2 × atan2(√a, √(1-a))
        d = R × c

    Với R = 6371 km (bán kính Trái Đất)

    Args:
        lat1, lon1: Tọa độ điểm A (độ)
        lat2, lon2: Tọa độ điểm B (độ)

    Returns:
        Khoảng cách tính bằng km
    """
    R = 6371  # Bán kính Trái Đất (km)

    # Chuyển từ độ (degrees) sang radian
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Công thức Haversine
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return round(distance, 4)


# ============================================================
# PHẦN 3: ĐỌC DỮ LIỆU GIAO THÔNG THỰC TẾ
# ============================================================

def load_traffic_data(parquet_path: str, target_hour: int = None) -> list[RoadSegment]:
    """
    Đọc dữ liệu giao thông từ file .parquet (Kaggle HCM Traffic Dataset).
    Nếu target_hour được cung cấp (0-23), lọc dữ liệu theo khung giờ đó (UTC+7).

    Dataset có các cột:
    - way_id: Mã đường (OSM)
    - name: Tên đường (vd: "Nguyễn Thị Minh Khai")
    - currentSpeed: Tốc độ hiện tại (km/h) — ĐÃ TÍNH KẸT XE
    - freeFlowSpeed: Tốc độ lý tưởng khi đường trống (km/h)

    Cách tính congestion_ratio (mức độ kẹt xe):
        congestion_ratio = currentSpeed / freeFlowSpeed
        - 1.0  = đường thông thoáng hoàn toàn
        - 0.5  = tốc độ giảm 50% do kẹt xe
        - 0.08 = gần như kẹt cứng (tốc độ chỉ còn 8%)

    Args:
        parquet_path: Đường dẫn tới file .parquet

    Returns:
        Danh sách RoadSegment đã tổng hợp (trung bình theo way_id)
    """
    try:
        import pandas as pd
        df = pd.read_parquet(parquet_path)
    except ImportError:
        print("[WARNING] pandas/pyarrow chua duoc cai dat. Su dung du lieu mau.")
        return _get_sample_traffic_data(target_hour)
    except FileNotFoundError:
        print(f"[WARNING] Khong tim thay file: {parquet_path}")
        print("[WARNING] Su dung du lieu mau thay the.")
        return _get_sample_traffic_data(target_hour)

    if target_hour is not None:
        try:
            # Lấy múi giờ Việt Nam (UTC+7)
            df['dt'] = pd.to_datetime(df['timestamp']).dt.tz_convert('Asia/Ho_Chi_Minh')
            df_filtered = df[df['dt'].dt.hour == target_hour]
            if not df_filtered.empty:
                df = df_filtered
            else:
                print(f"[WARNING] Khong co du lieu cho gio {target_hour}. Dung trung binh ngay.")
        except Exception as e:
            print(f"[WARNING] Loi loc theo gio: {e}")

    # Tổng hợp: lấy TRUNG BÌNH tốc độ cho mỗi đoạn đường
    agg = df.groupby('way_id').agg({
        'name': 'first',
        'currentSpeed': 'mean',
        'freeFlowSpeed': 'mean',
    }).reset_index()

    segments = []
    for _, row in agg.iterrows():
        free_flow = row['freeFlowSpeed']
        current = row['currentSpeed']
        ratio = current / free_flow if free_flow > 0 else 1.0

        segments.append(RoadSegment(
            way_id=int(row['way_id']),
            name=str(row['name']),
            current_speed=round(current, 1),
            free_flow_speed=round(free_flow, 1),
            congestion_ratio=round(ratio, 4),
        ))

    return segments


def _get_sample_traffic_data(target_hour: int = None) -> list[RoadSegment]:
    """Dữ liệu mẫu nếu không có file parquet. Giả lập kẹt xe theo giờ."""
    # Giả lập: giờ cao điểm (7,8,17,18) kẹt nặng, đêm thông thoáng
    factor = 1.0
    if target_hour in [7, 8, 17, 18]:
        factor = 0.7  # kẹt nặng
    elif target_hour in [0, 1, 2, 3, 4, 5]:
        factor = 1.2  # thông thoáng

    def adjust(speed): return max(5, int(speed * factor))

    return [
        RoadSegment(230935039, "Nguyen Thi Minh Khai", adjust(23), 28, adjust(23)/28),
        RoadSegment(1218900523, "Hai Ba Trung", adjust(17), 24, adjust(17)/24),
        RoadSegment(329878184, "Nam Ky Khoi Nghia", adjust(20), 26, adjust(20)/26),
        RoadSegment(599650678, "Xo Viet Nghe Tinh", adjust(16), 26, adjust(16)/26),
        RoadSegment(289968625, "Nguyen Trai", adjust(20), 27, adjust(20)/27),
        RoadSegment(408246393, "Dien Bien Phu", adjust(33), 41, adjust(33)/41),
        RoadSegment(470506018, "Duong 3 Thang 2", adjust(18), 29, adjust(18)/29),
        RoadSegment(35113033, "Nguyen Van Troi", adjust(28), 34, adjust(28)/34),
    ]


# ============================================================
# PHẦN 4: XÂY DỰNG MA TRẬN THỜI GIAN (TIME MATRIX)
# ============================================================

def compute_average_congestion(traffic_data: list[RoadSegment]) -> float:
    """
    Tính mức kẹt xe TRUNG BÌNH của toàn bộ thành phố.

    Dùng để ước lượng tốc độ di chuyển trên các đoạn đường
    mà ta không có dữ liệu trực tiếp.

    Returns:
        Giá trị trung bình congestion_ratio (0.0 → 1.0)
    """
    if not traffic_data:
        return 0.8  # Mặc định: kẹt nhẹ

    total = sum(seg.congestion_ratio for seg in traffic_data)
    return round(total / len(traffic_data), 4)


def find_nearest_road_congestion(
    lat: float, lon: float,
    traffic_data: list[RoadSegment],
    all_road_coords: dict,
    avg_congestion: float
) -> float:
    """
    Tìm đoạn đường GẦN NHẤT với 1 tọa độ và trả về mức kẹt xe của đường đó.

    Logic:
    1. Duyệt qua tất cả đường có dữ liệu giao thông
    2. Tính khoảng cách Haversine từ điểm giao hàng đến từng đường
    3. Chọn đường gần nhất → lấy congestion_ratio của đường đó

    Nếu đường gần nhất cách quá xa (> 2km) → dùng congestion trung bình.

    Args:
        lat, lon:         Tọa độ điểm cần tra cứu
        traffic_data:     Dữ liệu giao thông
        all_road_coords:  Dict {way_id: (lat, lon)} tọa độ các đường
        avg_congestion:   Congestion trung bình (fallback)

    Returns:
        congestion_ratio cho vị trí đó
    """
    best_dist = float('inf')
    best_congestion = avg_congestion

    for seg in traffic_data:
        if seg.way_id in all_road_coords:
            rlat, rlon = all_road_coords[seg.way_id]
            dist = haversine_distance(lat, lon, rlat, rlon)
            if dist < best_dist:
                best_dist = dist
                best_congestion = seg.congestion_ratio

    # Nếu đường gần nhất quá xa (> 2km), dùng trung bình
    if best_dist > 2.0:
        return avg_congestion

    return best_congestion


def count_traffic_lights_on_segment(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    traffic_lights: list,
    corridor_km: float = 0.3,
) -> tuple[int, list]:
    """
    Đếm số đèn giao thông nằm trong hành lang giữa 2 điểm.

    Logic: tạo bounding box mở rộng (corridor_km) quanh đường nối 2 điểm,
    đếm số đèn nằm trong box và kiểm tra khoảng cách tới đường nối.

    Args:
        lat1, lon1: Tọa độ điểm A
        lat2, lon2: Tọa độ điểm B
        traffic_lights: Danh sách TrafficLight
        corridor_km: Bề rộng hành lang (km) — mặc định 300m mỗi bên

    Returns:
        (count, list_of_lights_on_segment)
    """
    if not traffic_lights:
        return 0, []

    # Bounding box mở rộng
    deg_offset = corridor_km / 111.0  # ~1 degree ≈ 111km
    min_lat = min(lat1, lat2) - deg_offset
    max_lat = max(lat1, lat2) + deg_offset
    min_lon = min(lon1, lon2) - deg_offset
    max_lon = max(lon1, lon2) + deg_offset

    # Khoảng cách segment
    seg_len = haversine_distance(lat1, lon1, lat2, lon2)
    if seg_len < 0.01:  # Cùng vị trí
        return 0, []

    lights_on_seg = []
    for tl in traffic_lights:
        # Quick bounding box filter
        if not (min_lat <= tl.lat <= max_lat and min_lon <= tl.lon <= max_lon):
            continue

        # Kiểm tra khoảng cách tới đường nối (point-to-line distance)
        dist_a = haversine_distance(lat1, lon1, tl.lat, tl.lon)
        dist_b = haversine_distance(lat2, lon2, tl.lat, tl.lon)

        # Nếu đèn nằm trong phạm vi segment (không quá xa 2 đầu)
        if dist_a <= seg_len + corridor_km and dist_b <= seg_len + corridor_km:
            # Approximate perpendicular distance
            s = (dist_a + dist_b + seg_len) / 2
            area_sq = s * (s - dist_a) * (s - dist_b) * (s - seg_len)
            if area_sq > 0:
                perp_dist = 2 * math.sqrt(area_sq) / seg_len
            else:
                perp_dist = min(dist_a, dist_b)

            if perp_dist <= corridor_km:
                lights_on_seg.append({"lat": tl.lat, "lon": tl.lon})

    return len(lights_on_seg), lights_on_seg


def build_time_matrix(
    locations: list[Location],
    traffic_data: list[RoadSegment],
    road_coords: dict,
    weather_factor: float = 1.0,
    base_speed_kmh: float = 36.0,
    traffic_lights: list = None,
    traffic_light_penalty_sec: float = 30.0,
    high_density_red_probability: float = 0.70,
    low_density_red_probability: float = 0.50,
    time_calibration_factor: float = 1.8,
    ai_corrections: dict = None,
    target_hour: int = None,
) -> tuple[list[list[float]], list[list[float]], list[list[float]], list[list[int]], list]:
    """
    Xây dựng MA TRẬN THỜI GIAN di chuyển giữa tất cả các cặp điểm.
    Đã được chuẩn hóa sát với thực tế đường phố TP.HCM (tương đương Google Maps).

    Bao gồm:
    - Kẹt xe thực tế (TomTom data)
    - Hệ số thời tiết
    - Penalty đèn giao thông (deterministic expected value)
    - Hệ số hiệu chỉnh fine-tune
    - AI zone correction (từ trips trước)

    Công thức tính thời gian:
        distance = haversine(A, B)                    # km (đường chim bay)
        road_factor = 1.25                             # Hệ số đường quanh co đô thị HCM (~25%)
        actual_distance = distance × road_factor       # km (ước lượng đường thực)

        congestion = congestion_ratio tại khu vực A-B  # 0.0 → 1.0
        congestion_speed_factor = 0.65 + 0.35 * congestion
        effective_speed = (base_speed_kmh * congestion_speed_factor) / weather_factor
        effective_speed = max(effective_speed, 12.0)   # Tối thiểu 12 km/h

        base_time = actual_distance / effective_speed × 60  # phút

        # Penalty đèn giao thông (deterministic)
        prob = 0.70 nếu đường đông, 0.50 nếu đường vắng
        light_penalty = num_lights × penalty_sec × prob / 60  # phút

        # Tổng thời gian
        time = (base_time + light_penalty) × calibration_factor × ai_correction

    Args:
        locations:                  Danh sách tất cả điểm (depot + delivery)
        traffic_data:               Dữ liệu giao thông thực tế
        road_coords:                Dict tọa độ các đường
        weather_factor:             Hệ số thời tiết (>= 1.0)
        base_speed_kmh:             Tốc độ cơ bản khi đường thông thoáng (km/h)
        traffic_lights:             Danh sách TrafficLight
        traffic_light_penalty_sec:  Giây chờ đèn đỏ trung bình (mặc định 30s)
        high_density_red_probability: Xác suất gặp đèn đỏ đường đông (0.70)
        low_density_red_probability:  Xác suất gặp đèn đỏ đường vắng (0.50)
        time_calibration_factor:    Hệ số fine-tune tổng thời gian (1.0 = không đổi)
        ai_corrections:             Dict corrections từ AI learning (optional)
        target_hour:                Giờ khởi hành (để tra AI correction)

    Returns:
        Tuple gồm 5 phần tử:
        - time_matrix:              Thời gian THỰC TẾ (phút)
        - distance_matrix:          Khoảng cách (km)
        - ideal_time_matrix:        Thời gian LÝ TƯỞNG (phút)
        - traffic_light_count_matrix: Số đèn mỗi segment
        - all_segment_lights:       Danh sách tọa độ đèn trên từng segment
    """
    n = len(locations)
    time_matrix = [[0.0] * n for _ in range(n)]
    distance_matrix = [[0.0] * n for _ in range(n)]
    ideal_time_matrix = [[0.0] * n for _ in range(n)]
    light_count_matrix = [[0] * n for _ in range(n)]
    all_segment_lights = []  # Tất cả đèn trên tất cả segments (cho map rendering)

    avg_congestion = compute_average_congestion(traffic_data)
    road_factor = 1.25  # Đường thực tế dài hơn đường chim bay ~25%

    # Deduplicate traffic lights for map
    seen_lights = set()

    for i in range(n):
        for j in range(n):
            if i == j:
                continue

            # Bước 1: Khoảng cách đường chim bay → ước lượng đường thực tế
            raw_dist = haversine_distance(
                locations[i].lat, locations[i].lon,
                locations[j].lat, locations[j].lon
            )
            actual_dist = raw_dist * road_factor
            distance_matrix[i][j] = round(actual_dist, 2)

            # Bước 2: Tìm mức kẹt xe tại khu vực giữa 2 điểm
            mid_lat = (locations[i].lat + locations[j].lat) / 2
            mid_lon = (locations[i].lon + locations[j].lon) / 2

            congestion = find_nearest_road_congestion(
                mid_lat, mid_lon, traffic_data, road_coords, avg_congestion
            )

            # Bước 3: Tính tốc độ hiệu dụng (sát thực tế Google Maps)
            congestion_speed_factor = 0.65 + 0.35 * congestion
            effective_speed = (base_speed_kmh * congestion_speed_factor) / weather_factor
            effective_speed = max(effective_speed, 12.0)

            ideal_speed = base_speed_kmh  # Tốc độ lý tưởng đường thông thoáng

            # Bước 4: Thời gian cơ bản
            base_time_min = (actual_dist / effective_speed) * 60
            ideal_time_min = (actual_dist / ideal_speed) * 60

            # Bước 5: Penalty đèn giao thông (Deterministic Expected Value)
            num_lights = 0
            light_penalty_min = 0.0
            if traffic_lights:
                num_lights, lights_on_seg = count_traffic_lights_on_segment(
                    locations[i].lat, locations[i].lon,
                    locations[j].lat, locations[j].lon,
                    traffic_lights
                )
                light_count_matrix[i][j] = num_lights

                # Xác suất dựa trên mật độ giao thông (đông=0.70, vắng=0.50)
                red_prob = high_density_red_probability if congestion < 0.75 else low_density_red_probability
                light_penalty_min = (num_lights * traffic_light_penalty_sec * red_prob) / 60.0

                # Collect unique lights for map rendering
                for lt in lights_on_seg:
                    key = (round(lt['lat'], 5), round(lt['lon'], 5))
                    if key not in seen_lights:
                        seen_lights.add(key)
                        all_segment_lights.append(lt)

            # Bước 6: Áp dụng calibration factor + AI correction
            total_time_min = (base_time_min + light_penalty_min) * time_calibration_factor

            # AI Zone Correction (nếu có)
            if ai_corrections and target_hour is not None:
                zone_lat = round(mid_lat, 2)
                zone_lon = round(mid_lon, 2)
                zone_key = f"{zone_lat},{zone_lon},{target_hour}"
                ai_factor = ai_corrections.get(zone_key, 1.0)
                total_time_min *= ai_factor

            time_matrix[i][j] = round(total_time_min, 2)
            ideal_time_matrix[i][j] = round(ideal_time_min, 2)

    return time_matrix, distance_matrix, ideal_time_matrix, light_count_matrix, all_segment_lights


# ============================================================
# PHẦN 5: THUẬT TOÁN TỐI ƯU HÓA TUYẾN ĐƯỜNG
# ============================================================

def nearest_neighbor(
    time_matrix: list[list[float]],
    depot_index: int = 0,
    return_to_depot: bool = True
) -> list[int]:
    """
    THUẬT TOÁN 1: Nearest Neighbor (Láng giềng gần nhất)
    ====================================================

    Ý tưởng:
        Bắt đầu từ kho (depot), luôn chọn điểm CHƯA ĐẾN gần nhất
        (tốn ít thời gian nhất) để đi tiếp, cho đến khi thăm hết
        tất cả điểm. Nếu return_to_depot=True thì quay về kho.

    Args:
        time_matrix:      Ma trận thời gian [i][j] = phút từ i đến j
        depot_index:      Index của kho trong danh sách locations
        return_to_depot:  Có quay lại kho kết thúc hay không (True: khứ hồi, False: 1 chiều)

    Returns:
        Danh sách index theo thứ tự đi: [depot, ..., (depot nếu return_to_depot)]
    """
    n = len(time_matrix)
    visited = [False] * n
    route = [depot_index]
    visited[depot_index] = True

    current = depot_index
    for _ in range(n - 1):
        # Tìm điểm chưa thăm có thời gian đi ít nhất
        best_next = -1
        best_time = float('inf')

        for j in range(n):
            if not visited[j] and time_matrix[current][j] < best_time:
                best_time = time_matrix[current][j]
                best_next = j

        if best_next == -1:
            break

        route.append(best_next)
        visited[best_next] = True
        current = best_next

    # Quay về kho nếu được yêu cầu
    if return_to_depot:
        route.append(depot_index)
    return route


def two_opt_improve(
    route: list[int],
    time_matrix: list[list[float]],
    return_to_depot: bool = True,
    max_iterations: int = 1000
) -> list[int]:
    """
    THUẬT TOÁN 2: 2-Opt Local Search (Tối ưu cục bộ - Gỡ chéo đường)
    ==================================================================

    Hỗ trợ cả 2 chế độ:
    - Khứ hồi (return_to_depot=True): cố định điểm đầu và cuối là Depot.
    - Một chiều (return_to_depot=False): cố định điểm đầu là Depot, điểm cuối tự do tối ưu.

    Độ phức tạp: O(n² × iterations)

    Args:
        route:            Tuyến đường từ Nearest Neighbor
        time_matrix:      Ma trận thời gian
        return_to_depot:  Tùy chọn khứ hồi quay về kho
        max_iterations:   Số vòng lặp tối đa

    Returns:
        Tuyến đường đã cải thiện
    """
    best_route = list(route)
    improved = True
    iteration = 0
    n = len(best_route)

    if n <= 3:
        return best_route

    while improved and iteration < max_iterations:
        improved = False
        iteration += 1

        if return_to_depot:
            # Khứ hồi: điểm 0 và điểm n-1 đều là kho, chỉ đảo các điểm giao bên trong
            for i in range(1, n - 2):
                for j in range(i + 1, n - 1):
                    cost_current = (
                        time_matrix[best_route[i - 1]][best_route[i]] +
                        time_matrix[best_route[j]][best_route[j + 1]]
                    )
                    cost_new = (
                        time_matrix[best_route[i - 1]][best_route[j]] +
                        time_matrix[best_route[i]][best_route[j + 1]]
                    )
                    if cost_new < cost_current - 1e-6:
                        best_route[i:j + 1] = reversed(best_route[i:j + 1])
                        improved = True
        else:
            # Một chiều: điểm 0 là kho, điểm cuối cùng có thể thay đổi để tối ưu tổng thời gian
            # 1. Đảo các đoạn bên trong
            for i in range(1, n - 2):
                for j in range(i + 1, n - 1):
                    cost_current = (
                        time_matrix[best_route[i - 1]][best_route[i]] +
                        time_matrix[best_route[j]][best_route[j + 1]]
                    )
                    cost_new = (
                        time_matrix[best_route[i - 1]][best_route[j]] +
                        time_matrix[best_route[i]][best_route[j + 1]]
                    )
                    if cost_new < cost_current - 1e-6:
                        best_route[i:j + 1] = reversed(best_route[i:j + 1])
                        improved = True
            # 2. Đảo đoạn đuôi (thay đổi điểm kết thúc)
            for i in range(1, n - 1):
                j = n - 1
                cost_current = time_matrix[best_route[i - 1]][best_route[i]]
                cost_new = time_matrix[best_route[i - 1]][best_route[j]]
                if cost_new < cost_current - 1e-6:
                    best_route[i:j + 1] = reversed(best_route[i:j + 1])
                    improved = True

    return best_route


def calculate_route_cost(
    route: list[int],
    time_matrix: list[list[float]],
    distance_matrix: list[list[float]]
) -> tuple[float, float]:
    """
    Tính tổng thời gian và quãng đường của 1 tuyến.

    Args:
        route:           Danh sách index theo thứ tự đi
        time_matrix:     Ma trận thời gian (phút)
        distance_matrix: Ma trận khoảng cách (km)

    Returns:
        (total_time_min, total_distance_km)
    """
    total_time = 0.0
    total_distance = 0.0

    for k in range(len(route) - 1):
        i = route[k]
        j = route[k + 1]
        total_time += time_matrix[i][j]
        total_distance += distance_matrix[i][j]

    return round(total_time, 2), round(total_distance, 2)


# ============================================================
# PHẦN 6: CHƯƠNG TRÌNH CHÍNH (MAIN)
# ============================================================

def build_test_scenario() -> tuple[list[Location], dict]:
    """
    Tạo kịch bản test: 1 kho + 8 điểm giao hàng thực tế ở HCM.

    Returns:
        (locations, road_coords)
    """
    locations = [
        # INDEX 0: Kho xuất phát (Depot) — Quận 7
        Location("DEPOT", "Kho FLEX-VRP (Quan 7)", 10.7380, 106.7220, "depot"),

        # INDEX 1-8: 8 điểm giao hàng
        Location("D1", "Tap hoa Chi Lan (Q1)", 10.7760, 106.6990, "delivery"),
        Location("D2", "Shop My Pham (Q3)", 10.7825, 106.6925, "delivery"),
        Location("D3", "Dai ly Thuc Pham (Q5)", 10.7540, 106.6630, "delivery"),
        Location("D4", "Cua hang Tien Loi (Q10)", 10.7710, 106.6680, "delivery"),
        Location("D5", "Sieu thi Mini (Binh Thanh)", 10.8020, 106.7100, "delivery"),
        Location("D6", "Tap hoa Ba Hai (Phu Nhuan)", 10.7985, 106.6810, "delivery"),
        Location("D7", "Cua hang (Tan Binh)", 10.8020, 106.6530, "delivery"),
        Location("D8", "Tap hoa Ut (Go Vap)", 10.8190, 106.6870, "delivery"),
    ]

    # Tọa độ tham chiếu cho các đường (từ dataset)
    road_coords = {
        230935039:  (10.7735, 106.6893),   # Nguyen Thi Minh Khai
        1218900523: (10.7821, 106.6989),   # Hai Ba Trung
        329878184:  (10.7733, 106.7001),   # Nam Ky Khoi Nghia
        599650678:  (10.7955, 106.7100),   # Xo Viet Nghe Tinh
        289968625:  (10.7664, 106.6881),   # Nguyen Trai
        408246393:  (10.7784, 106.6854),   # Dien Bien Phu
        470506018:  (10.7686, 106.6744),   # Duong 3 Thang 2
        35113033:   (10.7930, 106.6800),   # Nguyen Van Troi
        32577828:   (10.7995, 106.6802),   # Nguyen Kiem
        289862908:  (10.7620, 106.6760),   # Nguyen Tri Phuong
        1267006216: (10.7870, 106.6930),   # Vo Thi Sau
        154823449:  (10.7876, 106.6783),   # Le Van Sy
        1163556205: (10.7704, 106.6581),   # Ly Thuong Kiet
        242307851:  (10.7729, 106.6670),   # Thanh Thai
        528264270:  (10.7410, 106.6960),   # Pham Hung
        1056903939: (10.7824, 106.6938),   # Pasteur
        828323704:  (10.7785, 106.7029),   # Le Thanh Ton
        35113963:   (10.7886, 106.7035),   # Nguyen Binh Khiem
        719043756:  (10.7713, 106.6948),   # Pham Hong Thai
        1162960449: (10.7659, 106.6967),   # Nguyen Thai Hoc
    }

    return locations, road_coords


def run_optimization(
    locations: list[Location],
    traffic_data: list[RoadSegment],
    road_coords: dict,
    weather_factor: float = 1.0,
    weather_desc: str = "Nang dep",
    return_to_depot: bool = True,
) -> RouteResult:
    """
    Chạy toàn bộ pipeline tối ưu hóa.

    Pipeline:
        1. Build time matrix (từ traffic + weather)
        2. Nearest Neighbor → giải pháp ban đầu
        3. 2-Opt → cải thiện
        4. Tính toán kết quả

    Args:
        locations:        Danh sách điểm
        traffic_data:     Dữ liệu kẹt xe
        road_coords:      Tọa độ các đường
        weather_factor:   Hệ số thời tiết
        weather_desc:     Mô tả thời tiết
        return_to_depot:  Tùy chọn khứ hồi (True: quay về kho, False: kết thúc tại điểm cuối)

    Returns:
        RouteResult chứa tuyến đường tối ưu và thống kê
    """
    route_type_desc = "Khu hoi (ve kho)" if return_to_depot else "1 chieu (khong ve kho)"
    print(f"\n{'='*60}")
    print(f"  FLEX-VRP Route Optimization Engine")
    print(f"  Che do: {route_type_desc}")
    print(f"  Thoi tiet: {weather_desc} (factor={weather_factor})")
    print(f"  So diem giao: {len(locations) - 1}")
    print(f"  Du lieu giao thong: {len(traffic_data)} doan duong")
    print(f"{'='*60}")

    # --- BƯỚC 1: Xây dựng ma trận ---
    print("\n[1/4] Xay dung ma tran thoi gian...")
    time_matrix, dist_matrix, ideal_time_matrix, light_matrix, _ = build_time_matrix(
        locations, traffic_data, road_coords,
        weather_factor=weather_factor
    )

    avg_cong = compute_average_congestion(traffic_data)
    print(f"  Muc ket xe trung binh: {avg_cong:.2%}")
    print(f"  He so thoi tiet: x{weather_factor}")

    # --- BƯỚC 2: Nearest Neighbor ---
    print("\n[2/4] Chay Nearest Neighbor...")
    nn_route = nearest_neighbor(time_matrix, depot_index=0, return_to_depot=return_to_depot)
    nn_time, nn_dist = calculate_route_cost(nn_route, time_matrix, dist_matrix)
    print(f"  Ket qua: {nn_time:.1f} phut | {nn_dist:.1f} km")

    # --- BƯỚC 3: 2-Opt Improvement ---
    print("\n[3/4] Chay 2-Opt Local Search...")
    optimized_route = two_opt_improve(nn_route, time_matrix, return_to_depot=return_to_depot)
    opt_time, opt_dist = calculate_route_cost(optimized_route, time_matrix, dist_matrix)
    improvement = nn_time - opt_time
    print(f"  Ket qua: {opt_time:.1f} phut | {opt_dist:.1f} km")
    if improvement > 0:
        print(f"  Cai thien: -{improvement:.1f} phut ({improvement/nn_time*100:.1f}%)")
    else:
        print(f"  Khong cai thien them (da tot roi).")

    # --- BƯỚC 4: So sánh ---
    print("\n[4/4] Tinh toan so sanh...")

    # Naive route: đi theo thứ tự gốc
    naive_route = list(range(len(locations))) + ([0] if return_to_depot else [])
    naive_time, naive_dist = calculate_route_cost(naive_route, time_matrix, dist_matrix)

    # Ideal time (không kẹt xe, không mưa)
    ideal_time, _ = calculate_route_cost(optimized_route, ideal_time_matrix, dist_matrix)

    time_saved = naive_time - opt_time

    # --- IN KẾT QUẢ ---
    print(f"\n{'='*60}")
    print(f"  KET QUA TOI UU HOA")
    print(f"{'='*60}")
    print(f"\n  Tuyen duong toi uu:")
    route_names = []
    for idx in optimized_route:
        loc = locations[idx]
        route_names.append(loc.name)

    for step, name in enumerate(route_names):
        if step == 0:
            print(f"    [START] {name}")
        elif step == len(route_names) - 1:
            print(f"    [END]   {name}")
        else:
            i_from = optimized_route[step - 1]
            i_to = optimized_route[step]
            seg_time = time_matrix[i_from][i_to]
            seg_dist = dist_matrix[i_from][i_to]
            print(f"    [{step}] {name}  ({seg_dist:.1f}km | {seg_time:.1f} phut)")

    print(f"\n  --- Thong ke ---")
    print(f"  Tong quang duong:      {opt_dist:.1f} km")
    print(f"  Tong thoi gian:        {opt_time:.1f} phut")
    print(f"  Thoi gian ly tuong:    {ideal_time:.1f} phut (khong ket xe)")
    print(f"  Thua ket xe + mua:     +{opt_time - ideal_time:.1f} phut")
    print(f"  Di theo thu tu ban dau:{naive_time:.1f} phut")
    print(f"  TIET KIEM:             {time_saved:.1f} phut ({time_saved/naive_time*100:.1f}%)")
    print(f"{'='*60}\n")

    return RouteResult(
        route=[locations[i] for i in optimized_route],
        total_distance=opt_dist,
        total_time=opt_time,
        total_time_no_traffic=ideal_time,
        time_saved_vs_naive=time_saved,
    )


# ============================================================
# PHẦN 7: CHẠY CÁC KỊCH BẢN TEST
# ============================================================

def main():
    """Entry point — chạy 3 kịch bản test với thời tiết khác nhau."""

    # Đường dẫn tới file dữ liệu
    # (tự động tìm từ cache kagglehub, hoặc dùng data mẫu)
    parquet_path = None
    cache_base = os.path.expanduser("~/.cache/kagglehub/datasets/evgenyarbatov/ho-chi-minh-city-road-traffic")
    # Tìm file parquet trong cả thư mục gốc và thư mục 'versions/'
    search_dirs = [cache_base]
    versions_dir = os.path.join(cache_base, "versions")
    if os.path.exists(versions_dir):
        search_dirs.append(versions_dir)
    for base in search_dirs:
        if not os.path.exists(base):
            continue
        for ver_dir in sorted(os.listdir(base), reverse=True):
            candidate = os.path.join(base, ver_dir, "vietnam-road-traffic-observations.parquet")
            if os.path.exists(candidate):
                parquet_path = candidate
                break
        if parquet_path:
            break

    if parquet_path:
        print(f"[INFO] Su dung du lieu giao thong: {parquet_path}")
    else:
        print("[INFO] Khong tim thay file parquet. Su dung du lieu mau.")

    # Đọc dữ liệu giao thông
    traffic_data = load_traffic_data(parquet_path) if parquet_path else _get_sample_traffic_data()

    # Tạo kịch bản test
    locations, road_coords = build_test_scenario()

    # ═══════════════════════════════════════════
    # KỊCH BẢN 1: Trời nắng đẹp
    # ═══════════════════════════════════════════
    result_sunny = run_optimization(
        locations, traffic_data, road_coords,
        weather_factor=1.0,
        weather_desc="Nang dep (binh thuong)"
    )

    # ═══════════════════════════════════════════
    # KỊCH BẢN 2: Mưa nhẹ
    # ═══════════════════════════════════════════
    result_light_rain = run_optimization(
        locations, traffic_data, road_coords,
        weather_factor=1.3,
        weather_desc="Mua nhe (cham hon 30%)"
    )

    # ═══════════════════════════════════════════
    # KỊCH BẢN 3: Mưa to
    # ═══════════════════════════════════════════
    result_heavy_rain = run_optimization(
        locations, traffic_data, road_coords,
        weather_factor=1.8,
        weather_desc="Mua to (cham hon 80%)"
    )

    # ═══════════════════════════════════════════
    # TỔNG HỢP SO SÁNH
    # ═══════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  TONG HOP SO SANH 3 KICH BAN")
    print("=" * 60)
    print(f"  {'Kich ban':<30} {'Thoi gian':>10} {'Quang duong':>12} {'Tiet kiem':>10}")
    print(f"  {'-'*30} {'-'*10} {'-'*12} {'-'*10}")
    print(f"  {'Nang dep':<30} {result_sunny.total_time:>8.1f}p {result_sunny.total_distance:>10.1f}km {result_sunny.time_saved_vs_naive:>8.1f}p")
    print(f"  {'Mua nhe (x1.3)':<30} {result_light_rain.total_time:>8.1f}p {result_light_rain.total_distance:>10.1f}km {result_light_rain.time_saved_vs_naive:>8.1f}p")
    print(f"  {'Mua to (x1.8)':<30} {result_heavy_rain.total_time:>8.1f}p {result_heavy_rain.total_distance:>10.1f}km {result_heavy_rain.time_saved_vs_naive:>8.1f}p")
    print(f"  {'-'*30} {'-'*10} {'-'*12} {'-'*10}")
    print(f"  Chenh lech mua to vs nang:   +{result_heavy_rain.total_time - result_sunny.total_time:.1f} phut")
    print("=" * 60)

    # Xuất kết quả JSON (để Laravel đọc sau này)
    output = {
        "generated_at": datetime.now().isoformat(),
        "scenarios": [
            {
                "weather": "sunny",
                "factor": 1.0,
                "total_time_min": result_sunny.total_time,
                "total_distance_km": result_sunny.total_distance,
                "time_saved_min": result_sunny.time_saved_vs_naive,
                "route": [{"id": loc.id, "name": loc.name, "lat": loc.lat, "lon": loc.lon}
                          for loc in result_sunny.route],
            },
            {
                "weather": "light_rain",
                "factor": 1.3,
                "total_time_min": result_light_rain.total_time,
                "total_distance_km": result_light_rain.total_distance,
                "time_saved_min": result_light_rain.time_saved_vs_naive,
                "route": [{"id": loc.id, "name": loc.name, "lat": loc.lat, "lon": loc.lon}
                          for loc in result_light_rain.route],
            },
            {
                "weather": "heavy_rain",
                "factor": 1.8,
                "total_time_min": result_heavy_rain.total_time,
                "total_distance_km": result_heavy_rain.total_distance,
                "time_saved_min": result_heavy_rain.time_saved_vs_naive,
                "route": [{"id": loc.id, "name": loc.name, "lat": loc.lat, "lon": loc.lon}
                          for loc in result_heavy_rain.route],
            },
        ]
    }

    output_path = os.path.join(os.path.dirname(__file__), "_result.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[OUTPUT] Ket qua da luu tai: {output_path}")


if __name__ == "__main__":
    main()
