"""
FLEX-VRP — Phase II Optimization Pipeline
Điều phối luồng giải thuật: Dinic Flow -> Matheuristic (GRASP + VND + VNS) -> Dashboard Analytics.
Hỗ trợ chạy đồng bộ hoặc bất đồng bộ với cập nhật tiến trình theo thời gian thực vào SQLite DB.
"""

import sys
import json
import time
import math
import uuid
import threading
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))
from db import (
    get_orders, get_order_by_code, get_customers, get_customer,
    get_vehicles, get_locations, save_delivery_schedule,
    create_optimization_run, update_optimization_progress,
    complete_optimization_run, get_optimization_run,
)
from dinic_flow import (
    split_orders, consolidate_small_orders,
    build_order_infos_from_db, build_vehicle_infos_from_db,
    OrderInfo, VehicleInfo,
)
from matheuristic import (
    Stop, Route, Solution, run_matheuristic,
)
from vrp_engine import haversine_distance


def run_full_pipeline(planning_days: int = 5, start_date: str = None, run_id: str = None) -> dict:
    """
    Chạy toàn bộ pipeline giải thuật Phase II:
    1. Đọc dữ liệu từ DB (Orders, Customers, Vehicles)
    2. Dinic Max-Flow phân chia đơn hàng lớn (Split Delivery)
    3. Gom đơn hàng nhỏ lân cận (Consolidation)
    4. Matheuristic (GRASP + VND MAB + LA-VNS) tối ưu tuyến đa xe, đa ngày
    5. So sánh đối sánh với phương án thủ công (Naive)
    6. Lưu lịch vận chuyển và trả về dashboard kết quả
    """
    if not run_id:
        run_id = f"opt_{uuid.uuid4().hex[:8]}"
    
    # Ngày bắt đầu (mặc định Thứ Hai tuần tới hoặc hôm nay)
    today = datetime.now().date()
    # Tìm thứ Hai kế tiếp hoặc hôm nay nếu là ngày trong tuần
    days_ahead = (0 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    start_dt = today + timedelta(days=days_ahead)
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        except Exception:
            pass

    date_list = [(start_dt + timedelta(days=i)).isoformat() for i in range(planning_days)]

    # 1. Nạp dữ liệu
    orders_raw = get_orders()
    customers_raw = get_customers()
    vehicles_raw = get_vehicles()
    locations_raw = get_locations("depot")

    depot_lat, depot_lon = 10.7380, 106.7220
    depot_name = "Kho Trung Tâm Q7"
    if locations_raw:
        depot_lat = locations_raw[0]["lat"]
        depot_lon = locations_raw[0]["lon"]
        depot_name = locations_raw[0]["name"]

    if not get_optimization_run(run_id):
        create_optimization_run(run_id, len(orders_raw), len(vehicles_raw), planning_days)
    update_optimization_progress(run_id, 8, "📋 Đang đọc dữ liệu đơn hàng...")
    time.sleep(0.2)
    update_optimization_progress(run_id, 12, "📋 Đang nạp danh sách phương tiện...")

    if not orders_raw or not vehicles_raw:
        msg = "Chưa có đủ đơn hàng hoặc phương tiện trong hệ thống để tối ưu."
        complete_optimization_run(run_id, error_message=msg)
        return {"success": False, "run_id": run_id, "error": msg}

    update_optimization_progress(run_id, 15, f"📋 Đã nạp {len(orders_raw)} đơn hàng, {len(vehicles_raw)} phương tiện")
    time.sleep(0.2)

    # 2. Chuẩn bị dữ liệu cho Dinic Flow
    update_optimization_progress(run_id, 18, "✂️ Chuẩn bị dữ liệu cho Dinic Flow...")
    time.sleep(0.15)
    update_optimization_progress(run_id, 22, "✂️ Phân chia đơn hàng lớn (Dinic's Maximum Flow)...")
    orders_info = build_order_infos_from_db()
    if not orders_info:
        for o in orders_raw:
            qty = o.get('total_quantity', 0)
            if qty <= 0:
                continue
            w_min = max(1, int(qty * 0.15))
            orders_info.append(OrderInfo(
                order_id=o['id'],
                order_code=o['order_code'],
                customer_id=o.get('customer_id', 0),
                total_quantity=qty,
                total_weight_kg=o.get('total_weight_kg', 0),
                customer_lat=o.get('customer_lat', 10.78),
                customer_lon=o.get('customer_lon', 106.70),
                customer_name=o.get('customer_name', 'Unknown'),
                time_window_start=o.get('time_window_start', '08:00'),
                time_window_end=o.get('time_window_end', '17:00'),
                w_min=w_min,
                w_max=qty,
            ))
    vehicles_info = build_vehicle_infos_from_db()

    # Chạy Dinic Flow
    update_optimization_progress(run_id, 28, f"✂️ Đang phân chia {len(orders_info)} đơn cho {len(vehicles_info)} xe...")
    assignments = split_orders(
        orders_info, vehicles_info,
        num_days=planning_days,
        delivery_dates=date_list
    )
    update_optimization_progress(run_id, 35, f"✂️ Hoàn tất phân chia: {len(assignments)} lượt giao")
    time.sleep(0.2)

    # 3. Gom đơn hàng nhỏ
    update_optimization_progress(run_id, 38, "📦 Gom cụm các đơn hàng nhỏ cùng khu vực (<3km)...")
    consolidated_groups = consolidate_small_orders(orders_info, threshold_qty=30, proximity_km=3.0)
    update_optimization_progress(run_id, 42, f"📦 Đã gom {len([g for g in consolidated_groups if len(g)>1])} cụm đơn hàng")
    time.sleep(0.15)

    # 4. Chuẩn bị Stops cho Matheuristic dựa trên kết quả phân chia
    update_optimization_progress(run_id, 45, "📍 Chuẩn bị điểm dừng cho thuật toán tối ưu...")
    
    # Tạo các stops từ assignments
    stops = []
    cust_map = {c["id"]: c for c in customers_raw}
    for idx, a in enumerate(assignments):
        # Lấy thông tin khách hàng
        c_lat, c_lon = 10.776, 106.699
        t_start, t_end = "08:00", "17:00"
        for o in orders_info:
            if o.order_id == a.order_id:
                c_lat = o.customer_lat
                c_lon = o.customer_lon
                t_start = o.time_window_start
                t_end = o.time_window_end
                break

        stops.append(Stop(
            order_id=a.order_id,
            order_code=a.order_code,
            customer_name=a.customer_name,
            lat=c_lat,
            lon=c_lon,
            quantity=a.assigned_quantity,
            weight_kg=a.assigned_weight_kg,
            time_start=t_start,
            time_end=t_end
        ))

    # Phương tiện cho matheuristic
    math_vehicles = []
    for v in vehicles_raw:
        math_vehicles.append({
            "id": v["id"],
            "name": v["name"],
            "capacity_kg": v.get("capacity_kg", 1000) or 1000,
            "avg_city_speed_kmh": v.get("avg_city_speed_kmh", 25) or 25,
            "fuel_type": v.get("fuel_type", "diesel"),
        })

    # 5. Chạy Matheuristic Framework
    update_optimization_progress(run_id, 50, f"🔄 Khởi tạo GRASP với {len(stops)} điểm giao...")
    time.sleep(0.15)
    update_optimization_progress(run_id, 55, "🔄 Tối ưu tuyến đường (Reactive GRASP + VND Multi-Armed Bandit)...")
    time.sleep(0.15)
    update_optimization_progress(run_id, 62, "⚡ Đang chạy VND Multi-Armed Bandit...")
    time.sleep(0.15)
    update_optimization_progress(run_id, 68, "⚡ Mở rộng không gian nghiệm (LA-VNS Strategic Oscillation)...")
    best_sol, route_pool, math_stats = run_matheuristic(
        stops=stops,
        vehicles=math_vehicles,
        num_days=planning_days,
        grasp_iterations=8,
        vnd_iterations=16,
        vns_iterations=10,
        depot_lat=depot_lat,
        depot_lon=depot_lon
    )
    update_optimization_progress(run_id, 78, "✅ Thuật toán hội tụ! Đang tính toán chi phí...")
    time.sleep(0.2)

    # 6. Tính toán kết quả & Đối sánh Naive (Thủ công)
    update_optimization_progress(run_id, 82, "📊 Tính toán chi phí phương án thủ công...")
    time.sleep(0.15)
    update_optimization_progress(run_id, 86, "📊 Đối sánh hiệu quả tối ưu vs thủ công...")

    opt_distance_km = round(best_sol.total_distance(), 1)
    opt_time_min = round(sum(r.total_time() for r in best_sol.routes), 1)
    opt_cost_vnd = round(best_sol.total_cost(), 0)
    opt_vehicles_used = best_sol.total_vehicles_used()

    # Tính chi phí Naive (giao đơn lẻ từng chuyến khứ hồi từ kho)
    naive_distance_km = 0.0
    for s in stops:
        d = haversine_distance(depot_lat, depot_lon, s.lat, s.lon) * 1.25 * 2.0  # Đi và về
        naive_distance_km += d
    naive_distance_km = round(naive_distance_km, 1)
    naive_time_min = round((naive_distance_km / 25.0) * 60.0, 1)
    naive_cost_vnd = round(naive_distance_km * 4500.0, 0)  # ~4,500đ/km nhiên liệu & hao mòn
    naive_vehicles_count = len(stops)  # Mỗi lần 1 chuyến đơn lẻ

    distance_saved_km = max(0.0, round(naive_distance_km - opt_distance_km, 1))
    cost_saved_vnd = max(0.0, round(naive_cost_vnd - opt_cost_vnd, 0))
    time_saved_min = max(0.0, round(naive_time_min - opt_time_min, 1))
    saved_pct = round((distance_saved_km / naive_distance_km) * 100, 1) if naive_distance_km > 0 else 0.0

    # Phân tích đơn tách (Split Delivery analysis)
    order_splits = {}
    for a in assignments:
        if a.order_code not in order_splits:
            order_splits[a.order_code] = {
                "order_code": a.order_code,
                "customer_name": a.customer_name,
                "splits": []
            }
        order_splits[a.order_code]["splits"].append({
            "date": a.delivery_date,
            "vehicle": a.vehicle_name,
            "quantity": a.assigned_quantity,
            "weight_kg": round(a.assigned_weight_kg, 1)
        })

    split_summary = []
    for code, data in order_splits.items():
        is_split = len(data["splits"]) > 1
        split_summary.append({
            "order_code": code,
            "customer_name": data["customer_name"],
            "is_split": is_split,
            "split_count": len(data["splits"]),
            "deliveries": data["splits"]
        })

    # Lịch giao hàng theo ngày (Gantt schedule)
    day_labels = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
    schedule_by_day = []

    for d_idx in range(planning_days):
        d_date = date_list[d_idx]
        dt_obj = datetime.strptime(d_date, "%Y-%m-%d")
        day_name = day_labels[dt_obj.weekday()]

        routes_for_day = []
        for r in best_sol.routes:
            if r.day_index == d_idx and r.num_stops > 0:
                stops_detail = []
                # Trạm xuất phát kho
                stops_detail.append({
                    "step": 0,
                    "name": depot_name,
                    "lat": depot_lat,
                    "lon": depot_lon,
                    "type": "depot",
                    "action": "Xuất phát",
                    "eta": "07:30"
                })
                current_time_dt = datetime.strptime(f"{d_date} 07:30", "%Y-%m-%d %H:%M")
                prev_lat, prev_lon = depot_lat, depot_lon

                for s_idx, st in enumerate(r.stops):
                    seg_dist = haversine_distance(prev_lat, prev_lon, st.lat, st.lon) * 1.25
                    seg_time_min = (seg_dist / 25.0) * 60.0
                    current_time_dt += timedelta(minutes=int(seg_time_min))
                    arr_str = current_time_dt.strftime("%H:%M")
                    # Giao hàng 15 phút
                    current_time_dt += timedelta(minutes=15)
                    dep_str = current_time_dt.strftime("%H:%M")

                    stops_detail.append({
                        "step": s_idx + 1,
                        "name": st.customer_name,
                        "order_code": st.order_code,
                        "lat": st.lat,
                        "lon": st.lon,
                        "type": "customer",
                        "quantity": st.quantity,
                        "weight_kg": round(st.weight_kg, 1),
                        "eta": arr_str,
                        "etd": dep_str,
                        "time_window": f"{st.time_start} - {st.time_end}"
                    })
                    prev_lat, prev_lon = st.lat, st.lon

                # Về kho
                return_dist = haversine_distance(prev_lat, prev_lon, depot_lat, depot_lon) * 1.25
                current_time_dt += timedelta(minutes=int((return_dist / 25.0) * 60.0))
                stops_detail.append({
                    "step": len(r.stops) + 1,
                    "name": f"Về {depot_name}",
                    "lat": depot_lat,
                    "lon": depot_lon,
                    "type": "depot",
                    "action": "Kết thúc hành trình",
                    "eta": current_time_dt.strftime("%H:%M")
                })

                routes_for_day.append({
                    "vehicle_id": r.vehicle_id,
                    "vehicle_name": r.vehicle_name,
                    "capacity_kg": r.capacity_kg,
                    "total_load_kg": round(r.total_load_kg, 1),
                    "load_percentage": round((r.total_load_kg / r.capacity_kg) * 100, 1) if r.capacity_kg > 0 else 0,
                    "stops_count": r.num_stops,
                    "distance_km": round(r.total_distance(), 1),
                    "time_min": round(r.total_time(), 1),
                    "cost_vnd": round(r.cost(), 0),
                    "stops": stops_detail
                })

        schedule_by_day.append({
            "day_index": d_idx,
            "date": d_date,
            "day_name": day_name,
            "routes": routes_for_day,
            "total_trips": len(routes_for_day),
            "total_day_load_kg": round(sum(rt["total_load_kg"] for rt in routes_for_day), 1),
            "total_day_dist_km": round(sum(rt["distance_km"] for rt in routes_for_day), 1)
        })

    # Kết quả đóng gói
    result = {
        "success": True,
        "run_id": run_id,
        "planning_days": planning_days,
        "depot": {"name": depot_name, "lat": depot_lat, "lon": depot_lon},
        "kpis": {
            "total_orders": len(orders_raw),
            "total_deliveries": len(assignments),
            "vehicles_used": opt_vehicles_used,
            "total_distance_km": opt_distance_km,
            "total_time_hours": round(opt_time_min / 60.0, 1),
            "total_cost_vnd": opt_cost_vnd,
            "saved_percentage": saved_pct,
            "saved_distance_km": distance_saved_km,
            "saved_cost_vnd": cost_saved_vnd,
            "saved_time_hours": round(time_saved_min / 60.0, 1),
            "avg_load_pct": round(sum(r.total_load_kg / r.capacity_kg for r in best_sol.routes if r.num_stops > 0) / max(1, opt_vehicles_used) * 100, 1)
        },
        "comparison": {
            "naive": {
                "label": "Giao Thủ Công (Từng chuyến)",
                "distance_km": naive_distance_km,
                "time_hours": round(naive_time_min / 60.0, 1),
                "cost_vnd": naive_cost_vnd,
                "trips": naive_vehicles_count
            },
            "optimized": {
                "label": "Tối Ưu Hóa (FLEX-VRP)",
                "distance_km": opt_distance_km,
                "time_hours": round(opt_time_min / 60.0, 1),
                "cost_vnd": opt_cost_vnd,
                "trips": opt_vehicles_used
            },
            "savings": {
                "pct": saved_pct,
                "km": distance_saved_km,
                "cost_vnd": cost_saved_vnd,
                "hours": round(time_saved_min / 60.0, 1)
            }
        },
        "split_delivery": split_summary,
        "consolidations": [
            {"group_id": i + 1, "order_codes": [o.order_code for o in orders_info if o.order_id in g]}
            for i, g in enumerate(consolidated_groups) if len(g) > 1
        ],
        "schedule": schedule_by_day,
        "completed_at": datetime.now().isoformat()
    }

    update_optimization_progress(run_id, 90, "💾 Đang lưu lịch vận chuyển vào cơ sở dữ liệu...")
    time.sleep(0.15)
    result_json = json.dumps(result, ensure_ascii=False)
    update_optimization_progress(run_id, 95, "📋 Hoàn thiện báo cáo kết quả...")
    time.sleep(0.15)
    complete_optimization_run(run_id, result_json=result_json)
    update_optimization_progress(run_id, 100, "✅ Hoàn tất tối ưu hóa!")

    return result


def start_async_pipeline(planning_days: int = 5) -> str:
    """Khởi động pipeline trong thread riêng để không block FastAPI server."""
    run_id = f"opt_{uuid.uuid4().hex[:8]}"
    
    # Tạo trước run trong DB
    orders_raw = get_orders()
    vehicles_raw = get_vehicles()
    create_optimization_run(run_id, len(orders_raw), len(vehicles_raw), planning_days)
    update_optimization_progress(run_id, 5, "Khởi động tiến trình tối ưu...")

    def _worker():
        try:
            run_full_pipeline(planning_days=planning_days, run_id=run_id)
        except Exception as e:
            print(f"[Pipeline] Error in run {run_id}: {e}")
            complete_optimization_run(run_id, error_message=str(e))

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return run_id
