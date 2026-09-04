"""
FLEX-VRP — B2B Test Data Seeder
Tạo dữ liệu test thực tế cho Phase II: customers, orders, vehicles.

Kịch bản MVP:
- 1 kho nhà máy (Q7, HCM)
- 6 tiệm tạp hóa (Q1, Q3, Q5, Q10, Bình Thạnh, Phú Nhuận)
- 3 xe tải (1T, 2.5T, 5T)
- 10 đơn hàng (có split delivery + consolidation)
- Horizon: 5 ngày (T2-T6)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))
from db import (
    init_db, save_customer, save_vehicle, save_order, save_order_item,
    save_location, get_customers, get_orders, get_vehicles,
)


def seed_b2b_test_data():
    """
    Seed toàn bộ dữ liệu test cho Phase II.
    Trả về dict thống kê số lượng đã tạo.
    """
    print("\n" + "=" * 60)
    print("  FLEX-VRP — Seeding B2B Test Data")
    print("=" * 60)

    stats = {"customers": 0, "vehicles": 0, "orders": 0, "order_items": 0}

    # ═══════════════════════════════════════
    # 1. DEPOT (Kho nhà máy)
    # ═══════════════════════════════════════
    print("\n[1/4] Tạo kho xuất phát (Depot)...")
    save_location("Kho FLEX-VRP (Quận 7)", 10.7380, 106.7220, "depot")
    print("  ✅ Kho: Quận 7, HCM (10.7380, 106.7220)")

    # ═══════════════════════════════════════
    # 2. CUSTOMERS (6 tiệm tạp hóa)
    # ═══════════════════════════════════════
    print("\n[2/4] Tạo 6 khách hàng...")
    customers_data = [
        {
            "name": "Tạp hóa Chị Lan",
            "address": "45 Nguyễn Huệ, Quận 1, HCM",
            "lat": 10.7760, "lon": 106.6990,
            "phone": "0901234001",
            "time_start": "08:00", "time_end": "12:00",
            "notes": "Giao cửa trước, có bãi đỗ xe tải nhỏ"
        },
        {
            "name": "Shop Mỹ Phẩm Hương",
            "address": "120 Võ Văn Tần, Quận 3, HCM",
            "lat": 10.7825, "lon": 106.6925,
            "phone": "0901234002",
            "time_start": "09:00", "time_end": "17:00",
            "notes": "Hàng dễ vỡ cần xếp cẩn thận"
        },
        {
            "name": "Đại lý Thực phẩm Minh",
            "address": "78 Trần Hưng Đạo, Quận 5, HCM",
            "lat": 10.7540, "lon": 106.6630,
            "phone": "0901234003",
            "time_start": "07:00", "time_end": "11:00",
            "notes": "Đơn lớn, cần chia nhiều ngày"
        },
        {
            "name": "Cửa hàng Tiện Lợi 24h",
            "address": "200 Sư Vạn Hạnh, Quận 10, HCM",
            "lat": 10.7710, "lon": 106.6680,
            "phone": "0901234004",
            "time_start": "08:00", "time_end": "22:00",
            "notes": "Mở cửa cả ngày, giao giờ nào cũng được"
        },
        {
            "name": "Siêu thị Mini Thanh",
            "address": "55 Xô Viết Nghệ Tĩnh, Bình Thạnh, HCM",
            "lat": 10.8020, "lon": 106.7100,
            "phone": "0901234005",
            "time_start": "08:00", "time_end": "17:00",
            "notes": "Kho lạnh có sẵn, nhận hàng nặng"
        },
        {
            "name": "Tạp hóa Bà Hai",
            "address": "30 Nguyễn Văn Trỗi, Phú Nhuận, HCM",
            "lat": 10.7985, "lon": 106.6810,
            "phone": "0901234006",
            "time_start": "07:30", "time_end": "12:00",
            "notes": "Hẻm nhỏ, chỉ xe 1T vào được"
        },
    ]

    customer_ids = []
    for c in customers_data:
        cid = save_customer(
            name=c["name"], address=c["address"],
            lat=c["lat"], lon=c["lon"], phone=c["phone"],
            time_start=c["time_start"], time_end=c["time_end"],
            notes=c["notes"]
        )
        customer_ids.append(cid)
        stats["customers"] += 1
        print(f"  ✅ KH#{cid}: {c['name']} ({c['address'][:30]}...)")

    # ═══════════════════════════════════════
    # 3. VEHICLES (3 xe tải)
    # ═══════════════════════════════════════
    print("\n[3/4] Tạo 3 xe tải...")
    vehicles_data = [
        {
            "name": "Xe tải nhỏ 1T (Suzuki Carry)",
            "type": "xe_tai_nhe",
            "max_speed": 70, "avg_speed": 25,
            "capacity_kg": 1000, "capacity_cbm": 4.0,
            "fuel_type": "gasoline",
            "notes": "Thùng: 300×160×160cm, vào hẻm nhỏ được"
        },
        {
            "name": "Xe tải trung 2.5T (Hyundai Porter)",
            "type": "xe_tai_nhe",
            "max_speed": 80, "avg_speed": 22,
            "capacity_kg": 2500, "capacity_cbm": 9.5,
            "fuel_type": "diesel",
            "notes": "Thùng: 430×190×185cm, phổ biến nhất"
        },
        {
            "name": "Xe tải lớn 5T (Isuzu NQR)",
            "type": "xe_tai_nang",
            "max_speed": 60, "avg_speed": 18,
            "capacity_kg": 5000, "capacity_cbm": 20.0,
            "fuel_type": "diesel",
            "notes": "Thùng: 600×220×210cm, không vào hẻm"
        },
    ]

    vehicle_ids = []
    for v in vehicles_data:
        vid = save_vehicle(
            name=v["name"], vtype=v["type"],
            max_speed=v["max_speed"], avg_speed=v["avg_speed"],
            capacity_kg=v["capacity_kg"], capacity_cbm=v["capacity_cbm"],
            fuel_type=v["fuel_type"], specs_source="test_data"
        )
        vehicle_ids.append(vid)
        stats["vehicles"] += 1
        print(f"  ✅ Xe#{vid}: {v['name']} ({v['capacity_kg']}kg, {v['capacity_cbm']}m³)")

    # ═══════════════════════════════════════
    # 4. ORDERS (10 đơn hàng)
    # ═══════════════════════════════════════
    print("\n[4/4] Tạo 10 đơn hàng...")

    # Ngày bắt đầu = thứ Hai tuần tới
    today = datetime.now().date()
    days_ahead = 7 - today.weekday()  # Thứ Hai tuần tới
    if days_ahead <= 0:
        days_ahead += 7
    start_date = today + timedelta(days=days_ahead)
    date_strs = [(start_date + timedelta(days=i)).isoformat() for i in range(5)]
    print(f"  📅 Horizon: {date_strs[0]} (T2) → {date_strs[4]} (T6)")

    orders_config = [
        # ── ĐƠN LỚN (cần Split Delivery) ──
        {
            "customer_idx": 2,  # Đại lý Thực phẩm Minh (Q5)
            "time_start": "07:00", "time_end": "11:00",
            "preferred_date": date_strs[0],
            "notes": "Đơn lớn - cần chia 3 ngày giao",
            "items": [
                {"name": "Thùng mì gói Hảo Hảo", "qty": 100, "wt": 5.0, "vol": 0.04, "heavy": True},
                {"name": "Thùng nước ngọt Coca", "qty": 80, "wt": 8.5, "vol": 0.05, "heavy": True},
                {"name": "Thùng sữa Vinamilk", "qty": 50, "wt": 6.0, "vol": 0.035, "fragile": True},
            ]
        },
        {
            "customer_idx": 4,  # Siêu thị Mini Thanh (Bình Thạnh)
            "time_start": "08:00", "time_end": "17:00",
            "preferred_date": date_strs[0],
            "notes": "Đơn lớn - cần chia 2 ngày giao",
            "items": [
                {"name": "Thùng bia Tiger", "qty": 120, "wt": 9.0, "vol": 0.06, "heavy": True},
                {"name": "Thùng dầu ăn Neptune", "qty": 60, "wt": 10.0, "vol": 0.04, "heavy": True},
            ]
        },

        # ── ĐƠN VỪA ──
        {
            "customer_idx": 0,  # Tạp hóa Chị Lan (Q1)
            "time_start": "08:00", "time_end": "12:00",
            "preferred_date": date_strs[0],
            "notes": "Giao buổi sáng",
            "items": [
                {"name": "Thùng nước suối Lavie", "qty": 30, "wt": 6.0, "vol": 0.03},
                {"name": "Thùng bánh Oreo", "qty": 20, "wt": 3.0, "vol": 0.025},
                {"name": "Thùng bột giặt OMO", "qty": 15, "wt": 5.0, "vol": 0.03, "heavy": True},
            ]
        },
        {
            "customer_idx": 1,  # Shop Mỹ Phẩm Hương (Q3)
            "time_start": "09:00", "time_end": "17:00",
            "preferred_date": date_strs[1],
            "notes": "Hàng dễ vỡ, xếp cẩn thận",
            "items": [
                {"name": "Thùng kem dưỡng da", "qty": 40, "wt": 0.5, "vol": 0.008, "fragile": True},
                {"name": "Thùng sữa rửa mặt", "qty": 30, "wt": 0.8, "vol": 0.01, "fragile": True},
            ]
        },
        {
            "customer_idx": 3,  # Cửa hàng Tiện Lợi 24h (Q10)
            "time_start": "08:00", "time_end": "22:00",
            "preferred_date": date_strs[1],
            "notes": "Giao giờ nào cũng được",
            "items": [
                {"name": "Thùng snack Pringles", "qty": 50, "wt": 1.5, "vol": 0.015},
                {"name": "Thùng nước tăng lực Red Bull", "qty": 40, "wt": 4.0, "vol": 0.02},
            ]
        },
        {
            "customer_idx": 5,  # Tạp hóa Bà Hai (Phú Nhuận)
            "time_start": "07:30", "time_end": "12:00",
            "preferred_date": date_strs[2],
            "notes": "Hẻm nhỏ, chỉ xe 1T",
            "items": [
                {"name": "Thùng đường Biên Hòa", "qty": 25, "wt": 10.0, "vol": 0.03, "heavy": True},
                {"name": "Thùng bột mì", "qty": 20, "wt": 5.0, "vol": 0.025, "heavy": True},
                {"name": "Thùng nước mắm Chinsu", "qty": 30, "wt": 6.0, "vol": 0.02, "fragile": True},
            ]
        },

        # ── ĐƠN NHỎ (gom đơn cùng tuyến) ──
        {
            "customer_idx": 0,  # Tạp hóa Chị Lan (Q1) — đơn bổ sung
            "time_start": "08:00", "time_end": "12:00",
            "preferred_date": date_strs[2],
            "notes": "Đơn bổ sung, gom chung xe",
            "items": [
                {"name": "Thùng giấy vệ sinh", "qty": 10, "wt": 2.0, "vol": 0.05},
                {"name": "Thùng xà bông Lifebuoy", "qty": 8, "wt": 1.5, "vol": 0.01},
            ]
        },
        {
            "customer_idx": 1,  # Shop Mỹ Phẩm Hương (Q3) — đơn nhỏ
            "time_start": "09:00", "time_end": "17:00",
            "preferred_date": date_strs[3],
            "notes": "Đơn nhỏ, gom chung",
            "items": [
                {"name": "Thùng son môi", "qty": 15, "wt": 0.3, "vol": 0.005, "fragile": True},
            ]
        },
        {
            "customer_idx": 3,  # Cửa hàng Tiện Lợi 24h (Q10) — đơn nhỏ
            "time_start": "08:00", "time_end": "22:00",
            "preferred_date": date_strs[3],
            "notes": "Gom chung xe",
            "items": [
                {"name": "Thùng khăn giấy", "qty": 12, "wt": 1.0, "vol": 0.02},
                {"name": "Thùng kẹo cao su", "qty": 10, "wt": 0.5, "vol": 0.008},
            ]
        },
        {
            "customer_idx": 5,  # Tạp hóa Bà Hai (Phú Nhuận) — đơn nhỏ
            "time_start": "07:30", "time_end": "12:00",
            "preferred_date": date_strs[4],
            "notes": "Đơn nhỏ cuối tuần",
            "items": [
                {"name": "Thùng muối I-ốt", "qty": 10, "wt": 5.0, "vol": 0.01},
            ]
        },
    ]

    for oc in orders_config:
        cust = customers_data[oc["customer_idx"]]
        cust_id = customer_ids[oc["customer_idx"]]

        order = save_order(
            customer_id=cust_id,
            status="confirmed",
            time_window_start=oc["time_start"],
            time_window_end=oc["time_end"],
            delivery_date_preferred=oc["preferred_date"],
            notes=oc["notes"],
            source="test_data"
        )
        stats["orders"] += 1

        total_qty = 0
        for item in oc["items"]:
            save_order_item(
                order_id=order["id"],
                product_name=item["name"],
                quantity=item["qty"],
                weight_per_unit_kg=item["wt"],
                volume_per_unit_cbm=item["vol"],
                is_fragile=item.get("fragile", False),
                is_heavy=item.get("heavy", False),
            )
            total_qty += item["qty"]
            stats["order_items"] += 1

        print(f"  ✅ Đơn {order['order_code']}: {cust['name'][:20]} — "
              f"{total_qty} thùng, {len(oc['items'])} SP, "
              f"giao {oc['preferred_date']}")

    # ═══════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════
    print(f"\n{'=' * 60}")
    print(f"  ✅ HOÀN TẤT SEED DATA")
    print(f"  • Khách hàng: {stats['customers']}")
    print(f"  • Xe tải:     {stats['vehicles']}")
    print(f"  • Đơn hàng:   {stats['orders']} ({stats['order_items']} sản phẩm)")
    print(f"  • Horizon:    {date_strs[0]} → {date_strs[4]} (5 ngày)")
    print(f"{'=' * 60}\n")

    return stats


if __name__ == "__main__":
    init_db()
    seed_b2b_test_data()
