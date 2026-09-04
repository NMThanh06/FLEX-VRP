"""
FLEX-VRP — Matheuristic Framework
Bộ khung lai Reactive GRASP + VND (Multi-Armed Bandit) + LA-VNS
cho tối ưu hóa tuyến đường multi-vehicle, multi-period.

Thuật toán:
1. Reactive GRASP: Khởi tạo phương án ban đầu (random + greedy)
2. VND + MAB: Cải thiện bằng local search, AI chọn neighborhood tốt nhất
3. LA-VNS: Thoát khỏi optima cục bộ bằng shaking + strategic oscillation
4. Route Pool: Lưu tất cả routes khả thi cho Set-Partitioning
"""

import math
import random
import copy
from typing import NamedTuple
from collections import defaultdict


# ============================================================
# PHẦN 1: CẤU TRÚC DỮ LIỆU
# ============================================================

class Stop:
    """Một điểm dừng giao hàng trên route."""
    __slots__ = ['order_id', 'order_code', 'customer_name', 'lat', 'lon',
                 'quantity', 'weight_kg', 'time_start', 'time_end']

    def __init__(self, order_id, order_code, customer_name,
                 lat, lon, quantity, weight_kg,
                 time_start='08:00', time_end='17:00'):
        self.order_id = order_id
        self.order_code = order_code
        self.customer_name = customer_name
        self.lat = lat
        self.lon = lon
        self.quantity = quantity
        self.weight_kg = weight_kg
        self.time_start = time_start
        self.time_end = time_end


class Route:
    """Một tuyến đường cho 1 xe trong 1 ngày."""

    def __init__(self, vehicle_id: int, vehicle_name: str,
                 capacity_kg: float, day_index: int,
                 depot_lat: float = 10.738, depot_lon: float = 106.722):
        self.vehicle_id = vehicle_id
        self.vehicle_name = vehicle_name
        self.capacity_kg = capacity_kg
        self.day_index = day_index
        self.depot_lat = depot_lat
        self.depot_lon = depot_lon
        self.stops: list[Stop] = []

    @property
    def total_load_kg(self) -> float:
        return sum(s.weight_kg for s in self.stops)

    @property
    def total_quantity(self) -> int:
        return sum(s.quantity for s in self.stops)

    @property
    def remaining_capacity_kg(self) -> float:
        return self.capacity_kg - self.total_load_kg

    @property
    def is_overloaded(self) -> bool:
        return self.total_load_kg > self.capacity_kg * 1.01  # 1% tolerance

    @property
    def num_stops(self) -> int:
        return len(self.stops)

    def total_distance(self) -> float:
        """Tổng khoảng cách route (km), bao gồm depot → stops → depot."""
        if not self.stops:
            return 0.0
        dist = _haversine(self.depot_lat, self.depot_lon,
                          self.stops[0].lat, self.stops[0].lon)
        for i in range(len(self.stops) - 1):
            dist += _haversine(self.stops[i].lat, self.stops[i].lon,
                               self.stops[i + 1].lat, self.stops[i + 1].lon)
        dist += _haversine(self.stops[-1].lat, self.stops[-1].lon,
                           self.depot_lat, self.depot_lon)
        return dist * 1.25  # Road factor

    def total_time(self, avg_speed_kmh: float = 25.0) -> float:
        """Tổng thời gian (phút) bao gồm di chuyển + service time."""
        dist = self.total_distance()
        travel_time = (dist / avg_speed_kmh) * 60 if avg_speed_kmh > 0 else 0
        service_time = len(self.stops) * 10  # 10 phút/trạm dỡ hàng
        return travel_time + service_time

    def cost(self, cost_per_km: float = 5000.0) -> float:
        """Chi phí route (VND): distance × cost_per_km + penalty."""
        base_cost = self.total_distance() * cost_per_km
        # Penalty nếu quá tải
        if self.is_overloaded:
            overload_ratio = self.total_load_kg / self.capacity_kg
            base_cost *= (1 + (overload_ratio - 1) * 10)  # Heavy penalty
        return base_cost

    def order_ids(self) -> list[int]:
        return [s.order_id for s in self.stops]

    def clone(self) -> 'Route':
        r = Route(self.vehicle_id, self.vehicle_name, self.capacity_kg,
                  self.day_index, self.depot_lat, self.depot_lon)
        r.stops = [copy.copy(s) for s in self.stops]
        return r


class Solution:
    """Một phương án hoàn chỉnh: tất cả routes cho tất cả xe × ngày."""

    def __init__(self):
        self.routes: list[Route] = []

    def total_cost(self) -> float:
        return sum(r.cost() for r in self.routes)

    def total_distance(self) -> float:
        return sum(r.total_distance() for r in self.routes)

    def total_vehicles_used(self) -> int:
        return len([r for r in self.routes if r.num_stops > 0])

    def is_feasible(self) -> bool:
        return all(not r.is_overloaded for r in self.routes)

    def get_routes_for_day(self, day_index: int) -> list[Route]:
        return [r for r in self.routes if r.day_index == day_index]

    def get_all_served_order_ids(self) -> set[int]:
        ids = set()
        for r in self.routes:
            ids.update(r.order_ids())
        return ids

    def clone(self) -> 'Solution':
        s = Solution()
        s.routes = [r.clone() for r in self.routes]
        return s


# ============================================================
# PHẦN 2: HELPER FUNCTIONS
# ============================================================

def _haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _insertion_cost(route: Route, stop: Stop, position: int) -> float:
    """Tính chi phí chèn stop vào route tại vị trí position."""
    stops = route.stops
    if not stops:
        # Route trống: depot → stop → depot
        return (_haversine(route.depot_lat, route.depot_lon, stop.lat, stop.lon) +
                _haversine(stop.lat, stop.lon, route.depot_lat, route.depot_lon)) * 1.25

    if position == 0:
        prev_lat, prev_lon = route.depot_lat, route.depot_lon
    else:
        prev_lat, prev_lon = stops[position - 1].lat, stops[position - 1].lon

    if position < len(stops):
        next_lat, next_lon = stops[position].lat, stops[position].lon
    else:
        next_lat, next_lon = route.depot_lat, route.depot_lon

    # Chi phí thêm = dist(prev → new) + dist(new → next) - dist(prev → next)
    cost_add = (_haversine(prev_lat, prev_lon, stop.lat, stop.lon) +
                _haversine(stop.lat, stop.lon, next_lat, next_lon) -
                _haversine(prev_lat, prev_lon, next_lat, next_lon)) * 1.25
    return cost_add


# ============================================================
# PHẦN 3: REACTIVE GRASP
# ============================================================

class ReactiveGRASP:
    """
    Greedy Randomized Adaptive Search Procedure.
    Khởi tạo phương án ban đầu bằng cách kết hợp greedy + random.

    Alpha controls randomness:
    - alpha=0: pure greedy (luôn chọn tốt nhất)
    - alpha=1: pure random
    - Reactive: tự động điều chỉnh alpha dựa trên chất lượng solution
    """

    def __init__(self, alpha_list=None):
        self.alpha_list = alpha_list or [0.1, 0.3, 0.5, 0.7]
        self.alpha_scores = {a: [] for a in self.alpha_list}
        self.alpha_probs = {a: 1.0 / len(self.alpha_list) for a in self.alpha_list}

    def _select_alpha(self) -> float:
        """Chọn alpha theo xác suất adaptive."""
        r = random.random()
        cumulative = 0
        for alpha in self.alpha_list:
            cumulative += self.alpha_probs[alpha]
            if r <= cumulative:
                return alpha
        return self.alpha_list[-1]

    def _update_probabilities(self):
        """Cập nhật xác suất chọn alpha dựa trên kết quả."""
        avg_scores = {}
        for alpha in self.alpha_list:
            scores = self.alpha_scores[alpha]
            if scores:
                avg_scores[alpha] = sum(scores) / len(scores)
            else:
                avg_scores[alpha] = 0

        total = sum(avg_scores.values())
        if total > 0:
            for alpha in self.alpha_list:
                self.alpha_probs[alpha] = max(0.05, avg_scores[alpha] / total)
            # Normalize
            total_prob = sum(self.alpha_probs.values())
            for alpha in self.alpha_list:
                self.alpha_probs[alpha] /= total_prob

    def construct(self, stops_to_assign: list[Stop],
                  vehicles: list[dict], num_days: int,
                  depot_lat: float, depot_lon: float) -> Solution:
        """
        Xây dựng 1 solution ban đầu bằng GRASP construction.

        Args:
            stops_to_assign: Danh sách stop cần phân bổ
            vehicles: Danh sách vehicle info dicts
            num_days: Số ngày
            depot_lat, depot_lon: Tọa độ kho

        Returns:
            Solution
        """
        alpha = self._select_alpha()

        sol = Solution()
        # Tạo routes trống cho mỗi xe × ngày
        for day in range(num_days):
            for v in vehicles:
                sol.routes.append(Route(
                    vehicle_id=v['id'], vehicle_name=v['name'],
                    capacity_kg=v['capacity_kg'], day_index=day,
                    depot_lat=depot_lat, depot_lon=depot_lon
                ))

        # Danh sách stop chưa phân bổ
        unassigned = list(stops_to_assign)
        random.shuffle(unassigned)

        while unassigned:
            stop = unassigned[0]

            # Tìm tất cả insertion candidates (route, position, cost)
            candidates = []
            for route in sol.routes:
                if route.remaining_capacity_kg < stop.weight_kg * 0.9:
                    continue  # Không đủ tải
                for pos in range(route.num_stops + 1):
                    cost = _insertion_cost(route, stop, pos)
                    candidates.append((route, pos, cost))

            if not candidates:
                # Không có route nào nhận được → thử route ít tải nhất
                best_route = min(sol.routes, key=lambda r: r.total_load_kg)
                best_route.stops.append(stop)
                unassigned.pop(0)
                continue

            # Sort by cost
            candidates.sort(key=lambda c: c[2])

            # RCL (Restricted Candidate List): top alpha% candidates
            c_min = candidates[0][2]
            c_max = candidates[-1][2]
            threshold = c_min + alpha * (c_max - c_min)
            rcl = [c for c in candidates if c[2] <= threshold + 1e-6]
            if not rcl:
                rcl = candidates[:1]

            # Random chọn từ RCL
            chosen = random.choice(rcl)
            chosen[0].stops.insert(chosen[1], stop)
            unassigned.pop(0)

        # Score cho reactive update
        cost = sol.total_cost()
        quality = 1.0 / (cost + 1)  # Inverse cost = quality
        self.alpha_scores[alpha].append(quality)

        # Giữ max 20 scores per alpha
        for a in self.alpha_list:
            if len(self.alpha_scores[a]) > 20:
                self.alpha_scores[a] = self.alpha_scores[a][-20:]

        self._update_probabilities()

        return sol


# ============================================================
# PHẦN 4: VND + MULTI-ARMED BANDIT
# ============================================================

class MultiArmedBandit:
    """
    Upper Confidence Bound (UCB1) cho chọn neighborhood.
    Ghi nhận reward mỗi lần sử dụng neighborhood để ưu tiên cái tốt nhất.
    """

    def __init__(self, n_arms: int, exploration_c: float = 1.41):
        self.n_arms = n_arms
        self.counts = [0] * n_arms
        self.rewards = [0.0] * n_arms
        self.total_count = 0
        self.C = exploration_c

    def select_arm(self) -> int:
        """Chọn arm (neighborhood) theo UCB1."""
        # Chưa thử hết → thử arm chưa dùng
        for i in range(self.n_arms):
            if self.counts[i] == 0:
                return i

        # UCB1 score
        best_arm = 0
        best_score = -float('inf')
        for i in range(self.n_arms):
            avg = self.rewards[i] / self.counts[i]
            exploration = self.C * math.sqrt(math.log(self.total_count) / self.counts[i])
            score = avg + exploration
            if score > best_score:
                best_score = score
                best_arm = i
        return best_arm

    def update(self, arm: int, reward: float):
        """Cập nhật reward cho arm."""
        self.counts[arm] += 1
        self.rewards[arm] += reward
        self.total_count += 1


def _vnd_relocate(sol: Solution) -> tuple[Solution, float]:
    """Neighborhood 1: Relocate — chuyển 1 stop từ route A sang route B."""
    best_sol = sol
    best_improvement = 0

    routes_with_stops = [r for r in sol.routes if r.num_stops > 0]
    if len(routes_with_stops) < 1:
        return sol, 0

    for r1 in routes_with_stops:
        for si in range(r1.num_stops):
            stop = r1.stops[si]
            for r2 in sol.routes:
                if r2 is r1:
                    continue
                if r2.remaining_capacity_kg < stop.weight_kg * 0.9:
                    continue

                for pos in range(r2.num_stops + 1):
                    # Tính improvement
                    new_sol = sol.clone()
                    # Tìm r1, r2 tương ứng trong clone
                    cr1 = new_sol.routes[sol.routes.index(r1)]
                    cr2 = new_sol.routes[sol.routes.index(r2)]
                    moved_stop = cr1.stops.pop(si)
                    cr2.stops.insert(pos, moved_stop)

                    improvement = sol.total_cost() - new_sol.total_cost()
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_sol = new_sol

    return best_sol, best_improvement


def _vnd_swap(sol: Solution) -> tuple[Solution, float]:
    """Neighborhood 2: Swap — hoán đổi 2 stops giữa 2 routes."""
    best_sol = sol
    best_improvement = 0

    routes_with_stops = [r for r in sol.routes if r.num_stops > 0]
    if len(routes_with_stops) < 2:
        return sol, 0

    for i, r1 in enumerate(routes_with_stops):
        for j, r2 in enumerate(routes_with_stops):
            if j <= i:
                continue
            for si in range(r1.num_stops):
                for sj in range(r2.num_stops):
                    new_sol = sol.clone()
                    cr1 = new_sol.routes[sol.routes.index(r1)]
                    cr2 = new_sol.routes[sol.routes.index(r2)]

                    # Swap
                    cr1.stops[si], cr2.stops[sj] = cr2.stops[sj], cr1.stops[si]

                    # Check feasibility
                    if cr1.is_overloaded or cr2.is_overloaded:
                        continue

                    improvement = sol.total_cost() - new_sol.total_cost()
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_sol = new_sol

    return best_sol, best_improvement


def _vnd_two_opt_star(sol: Solution) -> tuple[Solution, float]:
    """Neighborhood 3: 2-Opt* — hoán đổi đuôi giữa 2 routes."""
    best_sol = sol
    best_improvement = 0

    routes_with_stops = [r for r in sol.routes if r.num_stops >= 2]
    if len(routes_with_stops) < 2:
        return sol, 0

    for i, r1 in enumerate(routes_with_stops):
        for j, r2 in enumerate(routes_with_stops):
            if j <= i:
                continue
            for k in range(1, r1.num_stops):
                for l in range(1, r2.num_stops):
                    new_sol = sol.clone()
                    cr1 = new_sol.routes[sol.routes.index(r1)]
                    cr2 = new_sol.routes[sol.routes.index(r2)]

                    # Swap tails
                    tail1 = cr1.stops[k:]
                    tail2 = cr2.stops[l:]
                    cr1.stops = cr1.stops[:k] + tail2
                    cr2.stops = cr2.stops[:l] + tail1

                    if cr1.is_overloaded or cr2.is_overloaded:
                        continue

                    improvement = sol.total_cost() - new_sol.total_cost()
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_sol = new_sol

    return best_sol, best_improvement


def _vnd_or_opt(sol: Solution) -> tuple[Solution, float]:
    """Neighborhood 4: Or-Opt — di chuyển chuỗi 2-3 stops liên tiếp."""
    best_sol = sol
    best_improvement = 0

    routes_with_stops = [r for r in sol.routes if r.num_stops >= 2]

    for r1 in routes_with_stops:
        for seg_len in [3, 2]:  # Thử chuỗi 3 trước, rồi 2
            if r1.num_stops < seg_len:
                continue
            for start in range(r1.num_stops - seg_len + 1):
                segment = r1.stops[start:start + seg_len]
                seg_weight = sum(s.weight_kg for s in segment)

                for r2 in sol.routes:
                    if r2 is r1:
                        continue
                    if r2.remaining_capacity_kg < seg_weight * 0.9:
                        continue

                    for pos in range(r2.num_stops + 1):
                        new_sol = sol.clone()
                        cr1 = new_sol.routes[sol.routes.index(r1)]
                        cr2 = new_sol.routes[sol.routes.index(r2)]

                        moved = cr1.stops[start:start + seg_len]
                        del cr1.stops[start:start + seg_len]
                        for k, s in enumerate(moved):
                            cr2.stops.insert(pos + k, s)

                        if cr2.is_overloaded:
                            continue

                        improvement = sol.total_cost() - new_sol.total_cost()
                        if improvement > best_improvement:
                            best_improvement = improvement
                            best_sol = new_sol

    return best_sol, best_improvement


def _vnd_cross_day(sol: Solution) -> tuple[Solution, float]:
    """Neighborhood 5: Cross-Day — chuyển stop sang ngày khác."""
    best_sol = sol
    best_improvement = 0

    routes_with_stops = [r for r in sol.routes if r.num_stops > 0]

    for r1 in routes_with_stops:
        for si in range(r1.num_stops):
            stop = r1.stops[si]
            for r2 in sol.routes:
                if r2 is r1 or r2.day_index == r1.day_index:
                    continue  # Phải khác ngày
                if r2.remaining_capacity_kg < stop.weight_kg * 0.9:
                    continue

                new_sol = sol.clone()
                cr1 = new_sol.routes[sol.routes.index(r1)]
                cr2 = new_sol.routes[sol.routes.index(r2)]

                moved = cr1.stops.pop(si)
                # Chèn vào vị trí tốt nhất
                best_pos = 0
                best_pos_cost = float('inf')
                for pos in range(cr2.num_stops + 1):
                    c = _insertion_cost(cr2, moved, pos)
                    if c < best_pos_cost:
                        best_pos_cost = c
                        best_pos = pos
                cr2.stops.insert(best_pos, moved)

                improvement = sol.total_cost() - new_sol.total_cost()
                if improvement > best_improvement:
                    best_improvement = improvement
                    best_sol = new_sol

    return best_sol, best_improvement


# Danh sách neighborhoods
NEIGHBORHOODS = [
    ("relocate", _vnd_relocate),
    ("swap", _vnd_swap),
    ("2-opt*", _vnd_two_opt_star),
    ("or-opt", _vnd_or_opt),
    ("cross-day", _vnd_cross_day),
]


def vnd_search(sol: Solution, max_iterations: int = 50) -> tuple[Solution, dict]:
    """
    Variable Neighborhood Descent với Multi-Armed Bandit.

    Returns:
        (improved_solution, stats_dict)
    """
    mab = MultiArmedBandit(len(NEIGHBORHOODS))
    best_sol = sol.clone()
    stats = {"iterations": 0, "improvements": 0, "neighborhood_usage": {}}

    for iteration in range(max_iterations):
        arm = mab.select_arm()
        name, func = NEIGHBORHOODS[arm]

        new_sol, improvement = func(best_sol)

        if improvement > 1e-6:
            best_sol = new_sol
            mab.update(arm, improvement)
            stats["improvements"] += 1
        else:
            mab.update(arm, 0)

        stats["iterations"] = iteration + 1
        stats["neighborhood_usage"][name] = mab.counts[arm]

    return best_sol, stats


# ============================================================
# PHẦN 5: LA-VNS (LOAD-AWARE VNS + STRATEGIC OSCILLATION)
# ============================================================

def vns_shaking(sol: Solution, k: int = 3) -> Solution:
    """
    Shaking: perturbation ngẫu nhiên lớn.
    Chuyển k stops random sang routes khác.
    """
    new_sol = sol.clone()
    routes_with_stops = [r for r in new_sol.routes if r.num_stops > 0]
    if not routes_with_stops:
        return new_sol

    for _ in range(k):
        if not routes_with_stops:
            break
        r1 = random.choice(routes_with_stops)
        if r1.num_stops == 0:
            continue
        si = random.randint(0, r1.num_stops - 1)
        stop = r1.stops.pop(si)

        # Chọn route ngẫu nhiên (có thể khác ngày)
        other_routes = [r for r in new_sol.routes if r is not r1]
        if other_routes:
            r2 = random.choice(other_routes)
            pos = random.randint(0, r2.num_stops)
            r2.stops.insert(pos, stop)

        routes_with_stops = [r for r in new_sol.routes if r.num_stops > 0]

    return new_sol


def strategic_oscillation_repair(sol: Solution) -> Solution:
    """
    Sửa các vi phạm capacity bằng cách chuyển hàng thừa sang xe/ngày khác.
    Strategic oscillation: cho phép vi phạm tạm thời ±10%, sau đó repair.
    """
    new_sol = sol.clone()
    max_repair_attempts = 50

    for attempt in range(max_repair_attempts):
        overloaded = [r for r in new_sol.routes if r.is_overloaded]
        if not overloaded:
            break

        r1 = overloaded[0]
        # Tìm stop nhẹ nhất để chuyển đi
        if r1.num_stops == 0:
            continue
        lightest_idx = min(range(r1.num_stops), key=lambda i: r1.stops[i].weight_kg)
        stop = r1.stops[lightest_idx]

        # Tìm route có dư capacity
        candidates = [
            r for r in new_sol.routes
            if r is not r1 and r.remaining_capacity_kg >= stop.weight_kg
        ]
        if candidates:
            r2 = min(candidates, key=lambda r: r.total_load_kg)
            r1.stops.pop(lightest_idx)
            r2.stops.append(stop)
        else:
            break  # Không tìm được xe nhận

    return new_sol


def la_vns(sol: Solution, max_iterations: int = 20,
           k_max: int = 5) -> tuple[Solution, dict]:
    """
    Load-Aware VNS với Strategic Oscillation.

    Args:
        sol: Solution ban đầu (đã qua VND)
        max_iterations: Số vòng lặp VNS
        k_max: Mức shaking tối đa

    Returns:
        (best_solution, stats)
    """
    best_sol = sol.clone()
    best_cost = best_sol.total_cost()
    stats = {"iterations": 0, "improvements": 0, "repairs": 0}

    k = 1
    for iteration in range(max_iterations):
        # Shaking
        shaken = vns_shaking(best_sol, k=k)

        # Repair nếu cần
        if not shaken.is_feasible():
            shaken = strategic_oscillation_repair(shaken)
            stats["repairs"] += 1

        # Local search (VND nhẹ)
        improved, _ = vnd_search(shaken, max_iterations=10)

        # Accept criterion
        new_cost = improved.total_cost()
        if new_cost < best_cost:
            best_sol = improved
            best_cost = new_cost
            stats["improvements"] += 1
            k = 1  # Reset shaking level
        else:
            k = min(k + 1, k_max)  # Tăng shaking

        stats["iterations"] = iteration + 1

    return best_sol, stats


# ============================================================
# PHẦN 6: ROUTE POOL MANAGER
# ============================================================

class RoutePool:
    """Bộ nhớ đệm lưu tất cả routes khả thi cho Set-Partitioning."""

    def __init__(self, max_size: int = 5000):
        self.max_size = max_size
        self.routes: list[dict] = []  # [{route: Route, cost: float, order_ids: set}]

    def add_from_solution(self, sol: Solution):
        """Thêm tất cả routes có stops từ 1 solution vào pool."""
        for route in sol.routes:
            if route.num_stops == 0:
                continue
            entry = {
                "route": route.clone(),
                "cost": route.cost(),
                "distance": route.total_distance(),
                "time": route.total_time(),
                "order_ids": set(route.order_ids()),
                "vehicle_id": route.vehicle_id,
                "day_index": route.day_index,
                "load_kg": route.total_load_kg,
            }
            self.routes.append(entry)

        # Loại bỏ routes xấu nếu vượt max_size
        if len(self.routes) > self.max_size:
            self.routes.sort(key=lambda r: r["cost"])
            self.routes = self.routes[:self.max_size]

    @property
    def size(self) -> int:
        return len(self.routes)


# ============================================================
# PHẦN 7: FULL MATHEURISTIC PIPELINE
# ============================================================

def run_matheuristic(
    stops: list[Stop],
    vehicles: list[dict],
    num_days: int = 5,
    depot_lat: float = 10.738,
    depot_lon: float = 106.722,
    grasp_iterations: int = 10,
    vnd_iterations: int = 30,
    vns_iterations: int = 15,
    progress_callback=None,
) -> tuple[Solution, RoutePool, dict]:
    """
    Chạy toàn bộ Matheuristic pipeline.

    Args:
        stops: Danh sách Stop cần phân bổ
        vehicles: Danh sách vehicle dicts [{id, name, capacity_kg}]
        num_days: Số ngày lập kế hoạch
        depot_lat, depot_lon: Tọa độ kho
        grasp_iterations: Số lần GRASP construction
        vnd_iterations: Số iterations VND mỗi solution
        vns_iterations: Số iterations VNS
        progress_callback: Callback(progress_pct, stage_name)

    Returns:
        (best_solution, route_pool, stats)
    """
    pool = RoutePool()
    grasp = ReactiveGRASP()
    best_sol = None
    best_cost = float('inf')
    stats = {
        "grasp_iterations": grasp_iterations,
        "vnd_stats": {},
        "vns_stats": {},
        "pool_size": 0,
        "best_cost": 0,
        "total_distance_km": 0,
    }

    print(f"\n[Matheuristic] Stops: {len(stops)}, Vehicles: {len(vehicles)}, Days: {num_days}")
    print(f"[Matheuristic] GRASP×{grasp_iterations} → VND×{vnd_iterations} → VNS×{vns_iterations}")

    # Phase 1: GRASP Construction + VND
    for i in range(grasp_iterations):
        if progress_callback:
            pct = 30 + int((i / grasp_iterations) * 30)
            progress_callback(pct, f"🔄 GRASP iteration {i + 1}/{grasp_iterations}")

        # Construct
        sol = grasp.construct(stops, vehicles, num_days, depot_lat, depot_lon)

        # VND improvement
        sol, vnd_s = vnd_search(sol, max_iterations=vnd_iterations)

        # Add to pool
        pool.add_from_solution(sol)

        cost = sol.total_cost()
        if cost < best_cost:
            best_cost = cost
            best_sol = sol.clone()
            print(f"  [GRASP {i + 1}] New best: {cost:,.0f} VND "
                  f"({sol.total_distance():.1f} km, {sol.total_vehicles_used()} xe)")

    stats["vnd_stats"] = {"completed": True}

    # Phase 2: VNS on best solution
    if progress_callback:
        progress_callback(75, f"🔀 VNS tìm kiếm phương án mới...")

    if best_sol:
        best_sol, vns_s = la_vns(best_sol, max_iterations=vns_iterations)
        pool.add_from_solution(best_sol)
        stats["vns_stats"] = vns_s
        print(f"  [VNS] Final: {best_sol.total_cost():,.0f} VND "
              f"({best_sol.total_distance():.1f} km)")

    stats["pool_size"] = pool.size
    stats["best_cost"] = best_sol.total_cost() if best_sol else 0
    stats["total_distance_km"] = best_sol.total_distance() if best_sol else 0

    return best_sol, pool, stats


# ============================================================
# PHẦN 8: STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  FLEX-VRP — Matheuristic Test")
    print("=" * 60)

    # Test stops
    test_stops = [
        Stop(1, "A1B2C3", "Tạp hóa Lan", 10.776, 106.699, 50, 300, "08:00", "12:00"),
        Stop(2, "D4E5F6", "Shop Hương", 10.783, 106.693, 40, 32, "09:00", "17:00"),
        Stop(3, "G7H8I9", "Đại lý Minh", 10.754, 106.663, 80, 480, "07:00", "11:00"),
        Stop(4, "J1K2L3", "Tiện Lợi 24h", 10.771, 106.668, 60, 240, "08:00", "22:00"),
        Stop(5, "M4N5O6", "ST Thanh", 10.802, 106.710, 70, 630, "08:00", "17:00"),
        Stop(6, "P7Q8R9", "Bà Hai", 10.799, 106.681, 30, 300, "07:30", "12:00"),
    ]

    test_vehicles = [
        {"id": 1, "name": "Xe 1T", "capacity_kg": 1000},
        {"id": 2, "name": "Xe 2.5T", "capacity_kg": 2500},
    ]

    best, pool, stats = run_matheuristic(
        test_stops, test_vehicles, num_days=3,
        grasp_iterations=5, vnd_iterations=15, vns_iterations=8,
    )

    print(f"\n{'─' * 60}")
    print(f"  KẾT QUẢ:")
    print(f"  • Chi phí: {best.total_cost():,.0f} VND")
    print(f"  • Quãng đường: {best.total_distance():.1f} km")
    print(f"  • Xe sử dụng: {best.total_vehicles_used()}")
    print(f"  • Route Pool: {pool.size} routes")
    print(f"  • Khả thi: {'✅' if best.is_feasible() else '❌'}")

    for r in best.routes:
        if r.num_stops > 0:
            print(f"\n  Ngày {r.day_index + 1} | {r.vehicle_name}:")
            print(f"    Stops: {[s.customer_name for s in r.stops]}")
            print(f"    Load: {r.total_load_kg:.0f}/{r.capacity_kg:.0f} kg")
            print(f"    Distance: {r.total_distance():.1f} km")

    print("\n✅ Matheuristic test hoàn tất!")
