"""
FLEX-VRP — AI Learning System
Học từ chuyến đi thực tế, tự hiệu chỉnh thời gian dự kiến.
Nhận biết sự kiện / lễ Tết / mùa ảnh hưởng giao thông.

Không cần API key cho core learning (EMA).
Gemini API key cho: tra cứu xe, phân tích sự kiện tin tức.
"""

import json
import os
import math
from datetime import datetime, date
from pathlib import Path


# ═══════════════════════════════════════
# AI LEARNER — EMA Zone Correction
# ═══════════════════════════════════════

class AILearner:
    """
    Học từ chuyến đi thực tế bằng Exponential Moving Average (EMA).
    
    Mỗi khu vực (~1km grid) + khung giờ có một correction_factor.
    Khi có dữ liệu thực tế mới:
        new_factor = α × error_ratio + (1-α) × old_factor
    Với α = 0.3 (trọng số dữ liệu mới)
    """
    
    ALPHA = 0.3  # Trọng số cho dữ liệu mới (EMA)
    GRID_PRECISION = 2  # Round lat/lon tới 0.01 → grid ~1.1km

    @staticmethod
    def _zone_key(lat: float, lon: float) -> tuple[float, float]:
        """Chuyển tọa độ thành zone key (grid ~1.1km)."""
        return (round(lat, AILearner.GRID_PRECISION),
                round(lon, AILearner.GRID_PRECISION))

    @staticmethod
    def learn_from_trip(trip: dict) -> dict:
        """
        Học từ 1 chuyến đi đã hoàn thành.
        
        Args:
            trip: dict từ DB (phải có estimated_time_min, actual_time_min, route_json, target_hour)
        
        Returns:
            dict với thông tin học: zones updated, corrections applied
        """
        from db import update_ai_correction

        estimated = trip.get('estimated_time_min', 0)
        actual = trip.get('actual_time_min', 0)
        
        if not estimated or not actual or estimated <= 0:
            return {"learned": False, "reason": "Missing time data"}

        error_ratio = actual / estimated  # >1 = underestimate, <1 = overestimate
        hour = trip.get('target_hour', datetime.now().hour)
        
        # Parse route để lấy zones
        try:
            route = json.loads(trip.get('route_json', '[]'))
        except (json.JSONDecodeError, TypeError):
            route = []
        
        zones_updated = []
        
        for stop in route:
            lat = stop.get('lat', 0)
            lon = stop.get('lon', 0)
            if lat == 0 and lon == 0:
                continue
                
            zone_lat, zone_lon = AILearner._zone_key(lat, lon)
            new_factor = update_ai_correction(
                zone_lat, zone_lon, hour, error_ratio, AILearner.ALPHA
            )
            zones_updated.append({
                "zone": f"{zone_lat},{zone_lon}",
                "hour": hour,
                "correction_factor": new_factor,
            })

        return {
            "learned": True,
            "error_ratio": round(error_ratio, 3),
            "interpretation": (
                f"Hệ thống đánh giá {'thấp' if error_ratio > 1.05 else 'cao' if error_ratio < 0.95 else 'đúng'} "
                f"({error_ratio:.0%} so với thực tế)"
            ),
            "zones_updated": len(zones_updated),
            "details": zones_updated[:5],  # Top 5
        }

    @staticmethod
    def get_zone_correction(lat: float, lon: float, hour: int) -> float:
        """
        Trả về correction factor cho khu vực + giờ.
        1.0 = không điều chỉnh, >1.0 = tăng thời gian, <1.0 = giảm.
        """
        from db import get_ai_correction
        zone_lat, zone_lon = AILearner._zone_key(lat, lon)
        return get_ai_correction(zone_lat, zone_lon, hour)

    @staticmethod
    def get_learning_stats() -> dict:
        """Thống kê AI learning: tổng trips, accuracy, top zones."""
        from db import get_completed_trips_for_learning, get_all_ai_corrections

        trips = get_completed_trips_for_learning()
        corrections = get_all_ai_corrections()
        
        total_trips = len(trips)
        
        # Tính accuracy
        accuracies = []
        for t in trips:
            est = t.get('estimated_time_min', 0)
            act = t.get('actual_time_min', 0)
            if est > 0 and act > 0:
                accuracy = 1 - abs(act - est) / act
                accuracies.append(max(0, accuracy))
        
        avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0.0
        
        # Top zones cần hiệu chỉnh nhiều nhất
        top_zones = sorted(
            corrections,
            key=lambda c: abs(c['correction_factor'] - 1.0),
            reverse=True
        )[:10]

        return {
            "total_trips_learned": total_trips,
            "average_accuracy": round(avg_accuracy * 100, 1),
            "total_zones_with_corrections": len(corrections),
            "total_samples": sum(c['sample_count'] for c in corrections),
            "top_corrections": [
                {
                    "zone": f"{c['zone_lat']},{c['zone_lon']}",
                    "hour": c['hour_bucket'],
                    "factor": c['correction_factor'],
                    "samples": c['sample_count'],
                }
                for c in top_zones
            ],
        }


# ═══════════════════════════════════════
# EVENTS ANALYZER — Holiday & Event Awareness
# ═══════════════════════════════════════

class EventsAnalyzer:
    """
    Nhận biết sự kiện (lễ Tết, hè, bóng đá...) ảnh hưởng giao thông.
    
    Seed data: Tết, hè, nhập học, Quốc khánh, Noel...
    Gemini API: Scan tin tức để tạo events mới (optional).
    """

    @staticmethod
    def get_active_events(target_date: date = None) -> dict:
        """
        Kiểm tra ngày hiện tại có event nào đang active không.
        
        Returns:
            dict với events list và combined_factor
        """
        from db import get_events
        
        if target_date is None:
            target_date = date.today()
        
        target_str = target_date.isoformat()
        
        all_events = get_events(active_only=False)
        active = []
        
        for ev in all_events:
            if ev['start_date'] <= target_str <= ev['end_date']:
                active.append(ev)
        
        # Combined impact: nhân tất cả factors
        combined_factor = 1.0
        for ev in active:
            combined_factor *= ev['traffic_impact_factor']
        
        return {
            "date": target_str,
            "active_events": active,
            "combined_traffic_factor": round(combined_factor, 3),
            "has_events": len(active) > 0,
            "summary": (
                " + ".join(ev['event_name'] for ev in active) if active
                else "Không có sự kiện đặc biệt"
            ),
        }

    @staticmethod
    def scan_news_for_events(gemini_api_key: str = None) -> list[dict]:
        """
        Dùng Gemini API phân tích sự kiện TP.HCM ảnh hưởng giao thông.
        
        Returns:
            Danh sách events mới được tạo
        """
        if not gemini_api_key:
            return []
        
        try:
            import urllib.request
            
            today = date.today().isoformat()
            prompt = (
                f"Ngày hôm nay là {today}. Hãy liệt kê các sự kiện tại TP.HCM "
                f"trong 14 ngày tới có thể ảnh hưởng giao thông đường bộ. "
                f"Bao gồm: lễ hội, bóng đá, sự kiện lớn, sửa đường, "
                f"thiên tai dự báo, kỳ nghỉ, nhập học, v.v.\n\n"
                f"Trả về JSON array, mỗi item có:\n"
                f'{{"event_name": "...", "event_type": "holiday|school|sport|festival|construction|weather_extreme", '
                f'"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", '
                f'"traffic_impact_factor": 0.5-1.5, "description": "..."}}\n\n'
                f"CHỈ trả về JSON array, không giải thích thêm."
            )
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_api_key}"
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048}
            }).encode('utf-8')
            
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                text = result['candidates'][0]['content']['parts'][0]['text']
                
                # Parse JSON từ response
                text = text.strip()
                if text.startswith('```'):
                    text = text.split('\n', 1)[1].rsplit('```', 1)[0]
                
                events_data = json.loads(text)
                
                from db import save_event
                created = []
                for ev in events_data:
                    try:
                        eid = save_event(
                            event_name=ev['event_name'],
                            event_type=ev.get('event_type', 'festival'),
                            start_date=ev['start_date'],
                            end_date=ev['end_date'],
                            impact_factor=float(ev.get('traffic_impact_factor', 1.0)),
                            description=ev.get('description', ''),
                            source='gemini_api'
                        )
                        ev['id'] = eid
                        created.append(ev)
                    except Exception as e:
                        print(f"[AI] Error saving event: {e}")
                
                print(f"[AI] Created {len(created)} events from Gemini scan")
                return created
                
        except Exception as e:
            print(f"[AI] Gemini events scan failed: {e}")
            return []


# ═══════════════════════════════════════
# VEHICLE LOOKUP via Gemini
# ═══════════════════════════════════════

# Preset fallback khi không có Gemini API
VEHICLE_PRESETS = {
    "xe_may": {
        "type": "xe_may", "max_speed_kmh": 60,
        "avg_city_speed_kmh": 25, "capacity_kg": 20,
        "capacity_cbm": 0.05, "fuel_type": "gasoline"
    },
    "xe_van": {
        "type": "xe_van", "max_speed_kmh": 80,
        "avg_city_speed_kmh": 30, "capacity_kg": 800,
        "capacity_cbm": 4.0, "fuel_type": "gasoline"
    },
    "xe_tai_nhe": {
        "type": "xe_tai_nhe", "max_speed_kmh": 70,
        "avg_city_speed_kmh": 22, "capacity_kg": 3000,
        "capacity_cbm": 12.0, "fuel_type": "diesel"
    },
    "xe_tai_nang": {
        "type": "xe_tai_nang", "max_speed_kmh": 60,
        "avg_city_speed_kmh": 18, "capacity_kg": 8000,
        "capacity_cbm": 30.0, "fuel_type": "diesel"
    },
}


def lookup_vehicle_specs(vehicle_name: str, gemini_api_key: str = None) -> dict:
    """
    Tra cứu thông số xe qua Gemini API.
    Fallback: dùng preset nếu không có API key.
    """
    if gemini_api_key:
        try:
            import urllib.request
            
            prompt = (
                f'Tra cứu thông số kỹ thuật xe "{vehicle_name}" tại Việt Nam.\n'
                f"Trả về JSON duy nhất:\n"
                f'{{"type": "xe_may"|"xe_van"|"xe_tai_nhe"|"xe_tai_nang", '
                f'"max_speed_kmh": number, "avg_city_speed_kmh": number, '
                f'"capacity_kg": number, "capacity_cbm": number, '
                f'"fuel_type": "gasoline"|"diesel"|"electric"}}\n\n'
                f"avg_city_speed_kmh = tốc độ trung bình nội thành TP.HCM, "
                f"tính cả dừng đèn đỏ và kẹt xe nhẹ.\n"
                f"CHỈ trả về JSON, không giải thích."
            )

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_api_key}"
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 512}
            }).encode('utf-8')

            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                text = result['candidates'][0]['content']['parts'][0]['text']
                text = text.strip()
                if text.startswith('```'):
                    text = text.split('\n', 1)[1].rsplit('```', 1)[0]

                specs = json.loads(text)
                specs['source'] = 'gemini_api'
                specs['vehicle_name'] = vehicle_name
                print(f"[AI] Vehicle lookup OK: {vehicle_name} → {specs.get('type')}")
                return specs

        except Exception as e:
            print(f"[AI] Gemini vehicle lookup failed for '{vehicle_name}': {e}")

    # Fallback: guess type from name
    name_lower = vehicle_name.lower()
    if any(kw in name_lower for kw in ['wave', 'vision', 'dream', 'air blade', 'xe máy', 'xe_may', 'exciter', 'winner', 'sirius', 'yamaha', 'honda']):
        preset = VEHICLE_PRESETS['xe_may'].copy()
    elif any(kw in name_lower for kw in ['van', 'starex', 'transit', 'daily', 'solati']):
        preset = VEHICLE_PRESETS['xe_van'].copy()
    elif any(kw in name_lower for kw in ['tải nặng', 'xe_tai_nang', '5 tấn', '7 tấn', '10 tấn', 'hino', 'hyundai hd']):
        preset = VEHICLE_PRESETS['xe_tai_nang'].copy()
    elif any(kw in name_lower for kw in ['tải', 'xe_tai', 'porter', 'mighty', 'kia k', 'isuzu', 'thaco']):
        preset = VEHICLE_PRESETS['xe_tai_nhe'].copy()
    else:
        preset = VEHICLE_PRESETS['xe_van'].copy()

    preset['source'] = 'preset_fallback'
    preset['vehicle_name'] = vehicle_name
    return preset


# ═══════════════════════════════════════
# ALTERNATIVE ROUTES
# ═══════════════════════════════════════

def suggest_alternative_routes(
    locations: list,
    time_matrix: list[list[float]],
    dist_matrix: list[list[float]],
    traffic_light_matrix: list[list[int]] = None,
    return_to_depot: bool = True,
) -> list[dict]:
    """
    Tạo 3 route khác nhau:
    Route A: Nhanh nhất (2-Opt chuẩn — time)
    Route B: Ngắn nhất (2-Opt tối ưu distance)
    Route C: Ít đèn đỏ nhất (2-Opt tối ưu traffic lights)
    """
    from vrp_engine import nearest_neighbor, two_opt_improve, calculate_route_cost
    
    n = len(time_matrix)
    
    # Route A: Nhanh nhất (time-optimized) — đây là route chính
    nn_a = nearest_neighbor(time_matrix, 0, return_to_depot)
    route_a = two_opt_improve(nn_a, time_matrix, return_to_depot)
    time_a, dist_a = calculate_route_cost(route_a, time_matrix, dist_matrix)
    lights_a = _count_route_lights(route_a, traffic_light_matrix) if traffic_light_matrix else 0

    # Route B: Ngắn nhất (distance-optimized)
    nn_b = nearest_neighbor(dist_matrix, 0, return_to_depot)
    route_b = two_opt_improve(nn_b, dist_matrix, return_to_depot)
    time_b, dist_b = calculate_route_cost(route_b, time_matrix, dist_matrix)
    lights_b = _count_route_lights(route_b, traffic_light_matrix) if traffic_light_matrix else 0

    # Route C: Ít đèn đỏ nhất
    if traffic_light_matrix and any(any(c > 0 for c in row) for row in traffic_light_matrix):
        # Tạo ma trận penalty: time + đèn đỏ weighted heavily
        light_penalty_matrix = [
            [time_matrix[i][j] + traffic_light_matrix[i][j] * 2.0 for j in range(n)]
            for i in range(n)
        ]
        nn_c = nearest_neighbor(light_penalty_matrix, 0, return_to_depot)
        route_c = two_opt_improve(nn_c, light_penalty_matrix, return_to_depot)
        time_c, dist_c = calculate_route_cost(route_c, time_matrix, dist_matrix)
        lights_c = _count_route_lights(route_c, traffic_light_matrix)
    else:
        # Fallback: random permutation variant
        import random
        best_route_c = route_a
        best_time_c = time_a
        for _ in range(20):
            perm = [0] + random.sample(range(1, n), n - 1)
            if return_to_depot:
                perm.append(0)
            opt = two_opt_improve(perm, time_matrix, return_to_depot)
            t, _ = calculate_route_cost(opt, time_matrix, dist_matrix)
            if t < best_time_c and opt != route_a:
                best_route_c = opt
                best_time_c = t
        route_c = best_route_c
        time_c, dist_c = calculate_route_cost(route_c, time_matrix, dist_matrix)
        lights_c = _count_route_lights(route_c, traffic_light_matrix) if traffic_light_matrix else 0

    return [
        {
            "label": "Route A",
            "tag": "⚡ Nhanh nhất",
            "route_indices": route_a,
            "total_time_min": time_a,
            "total_distance_km": dist_a,
            "traffic_lights": lights_a,
        },
        {
            "label": "Route B",
            "tag": "📏 Ngắn nhất",
            "route_indices": route_b,
            "total_time_min": time_b,
            "total_distance_km": dist_b,
            "traffic_lights": lights_b,
        },
        {
            "label": "Route C",
            "tag": "🚦 Ít đèn đỏ",
            "route_indices": route_c,
            "total_time_min": time_c,
            "total_distance_km": dist_c,
            "traffic_lights": lights_c,
        },
    ]


def _count_route_lights(route: list[int], light_matrix: list[list[int]]) -> int:
    """Đếm tổng đèn giao thông trên route."""
    if not light_matrix:
        return 0
    total = 0
    for k in range(len(route) - 1):
        total += light_matrix[route[k]][route[k + 1]]
    return total
