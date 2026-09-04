"""
FLEX-VRP — Dinic's Maximum Flow Algorithm
Thuật toán phân chia đơn hàng (Split Delivery) & Gom đơn (Consolidation).

Xây dựng Flow Network:
    Source → Orders → TimeSlots (ngày × xe) → Sink

Mỗi edge có capacity [w_min, w_max] biểu thị lượng hàng
tối thiểu/tối đa có thể giao mỗi lần.

Thuật toán Dinic tìm Feasible Flow phân chia lượng hàng giao mỗi ngày
nằm gọn trong khoảng cho phép và khít với tải trọng xe.
"""

import math
from collections import deque
from typing import NamedTuple


# ============================================================
# PHẦN 1: CẤU TRÚC DỮ LIỆU FLOW NETWORK
# ============================================================

class Edge:
    """Cạnh trong Flow Network với capacity và flow."""
    __slots__ = ['to', 'cap', 'flow', 'rev_idx']

    def __init__(self, to: int, cap: float, rev_idx: int):
        self.to = to
        self.cap = cap
        self.flow = 0.0
        self.rev_idx = rev_idx  # Index của cạnh ngược trong adj[to]

    @property
    def residual(self) -> float:
        return self.cap - self.flow


class FlowNetwork:
    """
    Mạng lưới luồng (Flow Network) cho thuật toán Dinic.

    Nodes được đánh số 0..n-1.
    Mỗi cạnh (u, v, cap) có cạnh ngược (v, u, 0) để cho phép hủy luồng.
    """

    def __init__(self, n: int):
        self.n = n
        self.adj: list[list[Edge]] = [[] for _ in range(n)]
        self.level: list[int] = [0] * n
        self.iter_ptr: list[int] = [0] * n

    def add_edge(self, u: int, v: int, cap: float):
        """Thêm cạnh u→v với capacity cap (và cạnh ngược v→u với cap=0)."""
        rev_uv = len(self.adj[v])
        rev_vu = len(self.adj[u])
        self.adj[u].append(Edge(v, cap, rev_uv))
        self.adj[v].append(Edge(u, 0, rev_vu))

    def _bfs(self, s: int, t: int) -> bool:
        """BFS xây dựng level graph từ source s."""
        self.level = [-1] * self.n
        self.level[s] = 0
        queue = deque([s])
        while queue:
            u = queue.popleft()
            for edge in self.adj[u]:
                if edge.residual > 1e-9 and self.level[edge.to] < 0:
                    self.level[edge.to] = self.level[u] + 1
                    queue.append(edge.to)
        return self.level[t] >= 0

    def _dfs(self, u: int, t: int, pushed: float) -> float:
        """DFS tìm blocking flow trên level graph."""
        if u == t:
            return pushed
        while self.iter_ptr[u] < len(self.adj[u]):
            edge = self.adj[u][self.iter_ptr[u]]
            if edge.residual > 1e-9 and self.level[edge.to] == self.level[u] + 1:
                d = self._dfs(edge.to, t, min(pushed, edge.residual))
                if d > 1e-9:
                    edge.flow += d
                    self.adj[edge.to][edge.rev_idx].flow -= d
                    return d
            self.iter_ptr[u] += 1
        return 0

    def max_flow(self, s: int, t: int) -> float:
        """
        Thuật toán Dinic tìm luồng cực đại từ s đến t.

        Complexity: O(V²E) — rất nhanh cho mạng nhỏ.

        Returns:
            Giá trị luồng cực đại
        """
        total_flow = 0.0
        while self._bfs(s, t):
            self.iter_ptr = [0] * self.n
            while True:
                f = self._dfs(s, t, float('inf'))
                if f < 1e-9:
                    break
                total_flow += f
        return total_flow

    def get_flow_on_edge(self, u: int, edge_idx: int) -> float:
        """Lấy flow trên cạnh thứ edge_idx từ node u."""
        return self.adj[u][edge_idx].flow


# ============================================================
# PHẦN 2: XÂY DỰNG FLOW NETWORK CHO SPLIT DELIVERY
# ============================================================

class OrderInfo(NamedTuple):
    """Thông tin đơn hàng cho split delivery."""
    order_id: int
    order_code: str
    customer_id: int
    total_quantity: int
    total_weight_kg: float
    customer_lat: float
    customer_lon: float
    customer_name: str
    time_window_start: str
    time_window_end: str
    w_min: int  # Lượng tối thiểu mỗi lần giao
    w_max: int  # Lượng tối đa mỗi lần giao (thường = vehicle capacity)


class VehicleInfo(NamedTuple):
    """Thông tin xe cho split delivery."""
    vehicle_id: int
    vehicle_name: str
    capacity_kg: float
    capacity_cbm: float
    avg_speed_kmh: float
    cost_per_km: float


class DeliveryAssignment(NamedTuple):
    """Kết quả phân bổ: đơn nào, ngày nào, xe nào, bao nhiêu."""
    order_id: int
    order_code: str
    customer_name: str
    day_index: int
    delivery_date: str
    vehicle_id: int
    vehicle_name: str
    assigned_quantity: int
    assigned_weight_kg: float


def _haversine(lat1, lon1, lat2, lon2):
    """Khoảng cách giữa 2 tọa độ (km)."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def split_orders(
    orders: list[OrderInfo],
    vehicles: list[VehicleInfo],
    num_days: int = 5,
    delivery_dates: list[str] = None,
    w_min_ratio: float = 0.15,
) -> list[DeliveryAssignment]:
    """
    Phân chia đơn hàng lớn thành nhiều ngày giao bằng Flow Network.

    Xây dựng mạng lưới:
        Source(0) → Order nodes → TimeSlot nodes (day × vehicle) → Sink

    Mỗi TimeSlot = (ngày d, xe v) có capacity = capacity_kg của xe v.
    Mỗi Order → TimeSlot edge có capacity = [w_min, w_max].

    Args:
        orders: Danh sách đơn hàng
        vehicles: Danh sách xe
        num_days: Số ngày lập kế hoạch
        delivery_dates: Danh sách ngày giao (ISO format)
        w_min_ratio: Tỉ lệ tối thiểu mỗi lần giao (0.15 = 15% đơn)

    Returns:
        Danh sách DeliveryAssignment cho tất cả đơn
    """
    if not orders or not vehicles:
        return []

    n_orders = len(orders)
    n_vehicles = len(vehicles)
    n_slots = num_days * n_vehicles  # Mỗi slot = 1 ngày × 1 xe

    # Node mapping:
    # 0 = Source
    # 1..n_orders = Order nodes
    # n_orders+1..n_orders+n_slots = TimeSlot nodes
    # n_orders+n_slots+1 = Sink
    source = 0
    sink = n_orders + n_slots + 1
    total_nodes = sink + 1

    network = FlowNetwork(total_nodes)

    # Edge tracking cho decode kết quả
    # order_to_slot_edges[i] = [(edge_idx_in_adj[order_node], slot_idx, day, veh_idx)]
    order_to_slot_edges: list[list[tuple]] = [[] for _ in range(n_orders)]

    for i, order in enumerate(orders):
        order_node = i + 1

        # Tính w_min, w_max cho đơn này
        w_min = max(1, int(order.total_quantity * w_min_ratio))
        w_max = order.total_quantity  # Tối đa = toàn bộ đơn

        # Source → Order: capacity = total_quantity (tổng cần giao)
        network.add_edge(source, order_node, order.total_quantity)

        # Order → mỗi TimeSlot: capacity = min(w_max, vehicle_capacity_in_units)
        for d in range(num_days):
            for v_idx, vehicle in enumerate(vehicles):
                slot_idx = d * n_vehicles + v_idx
                slot_node = n_orders + 1 + slot_idx

                # Capacity = min(đơn hàng tối đa, xe chở được bao nhiêu unit)
                # Ước lượng: vehicle capacity / average weight per unit
                if order.total_weight_kg > 0 and order.total_quantity > 0:
                    weight_per_unit = order.total_weight_kg / order.total_quantity
                    max_units_by_weight = int(vehicle.capacity_kg / weight_per_unit) if weight_per_unit > 0 else w_max
                else:
                    max_units_by_weight = w_max

                edge_cap = min(w_max, max_units_by_weight)
                if edge_cap < w_min:
                    continue  # Xe không đủ tải cho lượng tối thiểu

                edge_idx = len(network.adj[order_node])
                network.add_edge(order_node, slot_node, edge_cap)
                order_to_slot_edges[i].append((edge_idx, slot_idx, d, v_idx))

    # TimeSlot → Sink: capacity = vehicle capacity (tính bằng units, ước lượng)
    for d in range(num_days):
        for v_idx, vehicle in enumerate(vehicles):
            slot_idx = d * n_vehicles + v_idx
            slot_node = n_orders + 1 + slot_idx

            # Ước lượng capacity slot = tổng units mà xe chở được
            # Dùng trọng lượng trung bình của tất cả đơn
            avg_weight = sum(o.total_weight_kg / max(o.total_quantity, 1) for o in orders) / len(orders)
            avg_weight = max(avg_weight, 0.5)  # Tối thiểu 0.5 kg/unit
            slot_cap = int(vehicle.capacity_kg / avg_weight)
            network.add_edge(slot_node, sink, slot_cap)

    # Chạy Dinic Max-Flow
    total_demand = sum(o.total_quantity for o in orders)
    max_flow_value = network.max_flow(source, sink)

    print(f"[Dinic] Tổng demand: {total_demand} units")
    print(f"[Dinic] Max flow: {max_flow_value:.0f} units")
    print(f"[Dinic] Coverage: {max_flow_value / total_demand * 100:.1f}%")

    # Decode kết quả
    assignments = []
    for i, order in enumerate(orders):
        order_node = i + 1
        for edge_idx, slot_idx, day, v_idx in order_to_slot_edges[i]:
            flow = network.get_flow_on_edge(order_node, edge_idx)
            if flow > 0.5:  # Threshold > 0 (tránh float noise)
                assigned_qty = int(round(flow))
                if assigned_qty <= 0:
                    continue
                vehicle = vehicles[v_idx]
                weight_per_unit = order.total_weight_kg / max(order.total_quantity, 1)

                date_str = delivery_dates[day] if delivery_dates and day < len(delivery_dates) else f"Day-{day + 1}"

                assignments.append(DeliveryAssignment(
                    order_id=order.order_id,
                    order_code=order.order_code,
                    customer_name=order.customer_name,
                    day_index=day,
                    delivery_date=date_str,
                    vehicle_id=vehicle.vehicle_id,
                    vehicle_name=vehicle.vehicle_name,
                    assigned_quantity=assigned_qty,
                    assigned_weight_kg=round(assigned_qty * weight_per_unit, 2),
                ))

    # Kiểm tra đơn chưa giao hết
    for i, order in enumerate(orders):
        assigned_total = sum(
            a.assigned_quantity for a in assignments if a.order_id == order.order_id
        )
        if assigned_total < order.total_quantity:
            remaining = order.total_quantity - assigned_total
            print(f"[Dinic] ⚠️ Đơn {order.order_code}: còn {remaining}/{order.total_quantity} "
                  f"units chưa phân bổ (thiếu xe/ngày)")

    return assignments


# ============================================================
# PHẦN 3: GOM ĐƠN NHỎ (CONSOLIDATION)
# ============================================================

def consolidate_small_orders(
    orders: list[OrderInfo],
    threshold_qty: int = 30,
    proximity_km: float = 3.0,
) -> list[list[int]]:
    """
    Gom các đơn hàng nhỏ gần nhau vào cùng 1 nhóm giao.

    Logic:
    1. Lọc đơn nhỏ (qty <= threshold_qty)
    2. Nhóm theo khoảng cách < proximity_km
    3. Trả về danh sách nhóm [group_1_order_ids, group_2_order_ids, ...]

    Args:
        orders: Danh sách đơn hàng
        threshold_qty: Ngưỡng đơn nhỏ (units)
        proximity_km: Khoảng cách tối đa để gom (km)

    Returns:
        Danh sách nhóm, mỗi nhóm là list order_ids
    """
    small_orders = [o for o in orders if o.total_quantity <= threshold_qty]
    if not small_orders:
        return []

    # Greedy clustering
    used = set()
    groups = []

    for i, o1 in enumerate(small_orders):
        if o1.order_id in used:
            continue
        group = [o1.order_id]
        used.add(o1.order_id)

        for j, o2 in enumerate(small_orders):
            if o2.order_id in used:
                continue
            dist = _haversine(
                o1.customer_lat, o1.customer_lon,
                o2.customer_lat, o2.customer_lon,
            )
            if dist <= proximity_km:
                # Kiểm tra time window overlap
                if _time_windows_overlap(
                    o1.time_window_start, o1.time_window_end,
                    o2.time_window_start, o2.time_window_end,
                ):
                    group.append(o2.order_id)
                    used.add(o2.order_id)

        if len(group) > 1:
            groups.append(group)
            print(f"[Consolidate] Gom {len(group)} đơn nhỏ: "
                  f"{[o.order_code for o in small_orders if o.order_id in group]}")

    return groups


def _time_windows_overlap(start1: str, end1: str, start2: str, end2: str) -> bool:
    """Kiểm tra 2 time windows có overlap không."""
    if not all([start1, end1, start2, end2]):
        return True  # Nếu thiếu data, coi như overlap
    return start1 < end2 and start2 < end1


# ============================================================
# PHẦN 4: HELPER — BUILD OrderInfo từ DB
# ============================================================

def build_order_infos_from_db(w_min_ratio: float = 0.15) -> list[OrderInfo]:
    """Đọc đơn hàng confirmed từ DB và build OrderInfo list."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from db import get_orders

    db_orders = get_orders(status="confirmed")
    infos = []
    for o in db_orders:
        qty = o.get('total_quantity', 0)
        if qty <= 0:
            continue
        w_min = max(1, int(qty * w_min_ratio))
        infos.append(OrderInfo(
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
    return infos


def build_vehicle_infos_from_db() -> list[VehicleInfo]:
    """Đọc xe từ DB và build VehicleInfo list."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from db import get_vehicles

    db_vehicles = get_vehicles()
    infos = []
    for v in db_vehicles:
        infos.append(VehicleInfo(
            vehicle_id=v['id'],
            vehicle_name=v['name'],
            capacity_kg=v.get('capacity_kg', 1000),
            capacity_cbm=v.get('capacity_cbm', 4.0),
            avg_speed_kmh=v.get('avg_city_speed_kmh', 25),
            cost_per_km=0,  # Sẽ tính sau
        ))
    return infos


# ============================================================
# PHẦN 5: STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  FLEX-VRP — Dinic Flow Test (Split Delivery)")
    print("=" * 60)

    # Test với dữ liệu mẫu
    orders = [
        OrderInfo(1, "A3K9X2", 1, 200, 1200.0, 10.754, 106.663, "Đại lý Minh (Q5)",
                  "07:00", "11:00", 30, 200),
        OrderInfo(2, "B7M2P4", 2, 150, 1350.0, 10.802, 106.710, "Siêu thị Thanh (BT)",
                  "08:00", "17:00", 20, 150),
        OrderInfo(3, "C1D5E8", 3, 25, 87.5, 10.776, 106.699, "Tạp hóa Lan (Q1)",
                  "08:00", "12:00", 5, 25),
        OrderInfo(4, "D4F6G7", 4, 15, 12.0, 10.783, 106.693, "Shop Hương (Q3)",
                  "09:00", "17:00", 3, 15),
    ]

    vehicles = [
        VehicleInfo(1, "Xe 1T", 1000, 4.0, 25, 0),
        VehicleInfo(2, "Xe 2.5T", 2500, 9.5, 22, 0),
        VehicleInfo(3, "Xe 5T", 5000, 20.0, 18, 0),
    ]

    dates = ["2026-09-07", "2026-09-08", "2026-09-09", "2026-09-10", "2026-09-11"]

    assignments = split_orders(orders, vehicles, num_days=5, delivery_dates=dates)

    print(f"\n{'─' * 60}")
    print(f"  KẾT QUẢ PHÂN BỔ ({len(assignments)} lần giao)")
    print(f"{'─' * 60}")
    for a in assignments:
        print(f"  Đơn {a.order_code} ({a.customer_name})")
        print(f"    → {a.delivery_date} | {a.vehicle_name} | "
              f"{a.assigned_quantity} units ({a.assigned_weight_kg:.1f} kg)")

    # Test consolidation
    print(f"\n{'─' * 60}")
    print("  TEST GOM ĐƠN NHỎ")
    print(f"{'─' * 60}")
    groups = consolidate_small_orders(orders, threshold_qty=30, proximity_km=3.0)
    for g in groups:
        codes = [o.order_code for o in orders if o.order_id in g]
        print(f"  Nhóm: {codes}")

    print("\n✅ Dinic Flow test hoàn tất!")
