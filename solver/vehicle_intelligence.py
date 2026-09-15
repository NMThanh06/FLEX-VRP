"""
FLEX-VRP — Vehicle Intelligence System
Bộ Tiêu Chuẩn An Toàn Tải Trọng Xe Tải VN & Smart Vehicle Selector.

Áp dụng cho toàn bộ pipeline:
  Dinic Flow → Matheuristic (GRASP/VND/VNS) → Output Validation

Tiêu chuẩn tải trọng dựa trên:
  - Nghị định 100/2019/NĐ-CP (xử phạt quá tải)
  - Thông tư 46/2015/TT-BGTVT (tải trọng cho phép)
  - Thực tiễn vận hành logistics B2B tại TP.HCM
"""

from enum import IntEnum
from typing import NamedTuple


# ============================================================
# PHẦN 1: BỘ TIÊU CHUẨN AN TOÀN TẢI TRỌNG
# ============================================================

class LoadLevel(IntEnum):
    """Cấp độ tải trọng — dùng cho so sánh và phân loại."""
    UNDERLOAD = 0    # Quá ít hàng, lãng phí xe
    SAFE = 1         # An toàn, hiệu quả nhiên liệu tốt
    OPTIMAL = 2      # Tối ưu vận hành
    WARNING = 3      # Cần xác nhận carrier
    DANGER = 4       # Cảnh báo nghiêm trọng
    OVERLOAD = 5     # VI PHẠM PHÁP LUẬT


class LoadClassification(NamedTuple):
    """Kết quả phân loại tải trọng."""
    level: LoadLevel
    label: str            # Nhãn tiếng Việt
    label_en: str         # Nhãn tiếng Anh
    color: str            # Mã màu CSS cho UI
    icon: str             # Emoji icon
    description: str      # Mô tả chi tiết
    max_allowed: float    # Ngưỡng tối đa cho phép (ratio)
    penalty_multiplier: float  # Hệ số phạt chi phí


class LoadSafetyStandard:
    """
    Bộ Tiêu Chuẩn An Toàn Tải Trọng Xe Tải Việt Nam.

    Ngưỡng chính:
        ≤ 50%  : UNDERLOAD  — Lãng phí xe, nên dùng xe nhỏ hơn
        50-80% : SAFE       — An toàn, phanh tốt, tiết kiệm nhiên liệu
        80-90% : OPTIMAL    — Tối ưu vận hành (mục tiêu thuật toán)
        90-95% : WARNING    — Cần carrier xác nhận rủi ro
        95-100%: DANGER     — Cảnh báo nghiêm trọng, gần giới hạn pháp lý
        > 100% : OVERLOAD   — VI PHẠM — Tuyệt đối không cho phép

    Điều kiện đặc biệt:
        Mưa ngập      → giảm giới hạn xuống 80%
        Đường hẹp      → giảm giới hạn xuống 75%
        Hàng nguy hiểm → giảm giới hạn xuống 70%
    """

    # ── Ngưỡng cơ bản (ratio so với max_weight_kg) ──
    HARD_LIMIT = 1.00           # 100% — Tuyệt đối không vượt
    DANGER_THRESHOLD = 0.95     # 95% — Cảnh báo nghiêm trọng
    OPTIMAL_MAX = 0.90          # 90% — Giới hạn trên vùng tối ưu
    OPTIMAL_MIN = 0.80          # 80% — Giới hạn dưới vùng tối ưu
    SAFE_MIN = 0.50             # 50% — Dưới mức này = lãng phí xe

    # ── Hệ số giảm tải theo điều kiện ──
    RAIN_REDUCTION = 0.80       # Mưa ngập → giảm về 80%
    NARROW_ROAD_REDUCTION = 0.75  # Đường nội đô hẹp → 75%
    HAZMAT_REDUCTION = 0.70     # Hàng nguy hiểm → 70%

    # ── Bảng phân loại ──
    _CLASSIFICATIONS = {
        LoadLevel.UNDERLOAD: LoadClassification(
            level=LoadLevel.UNDERLOAD,
            label="Ít tải", label_en="Underload",
            color="#9b59b6", icon="📉",
            description="Dưới 50% tải trọng — Lãng phí xe, nên dùng xe nhỏ hơn",
            max_allowed=0.50, penalty_multiplier=1.2,  # Phạt nhẹ vì lãng phí
        ),
        LoadLevel.SAFE: LoadClassification(
            level=LoadLevel.SAFE,
            label="An toàn", label_en="Safe",
            color="#27ae60", icon="✅",
            description="50-80% tải trọng — An toàn, hiệu quả nhiên liệu tốt",
            max_allowed=0.80, penalty_multiplier=1.0,  # Không phạt
        ),
        LoadLevel.OPTIMAL: LoadClassification(
            level=LoadLevel.OPTIMAL,
            label="Tối ưu", label_en="Optimal",
            color="#2ecc71", icon="⭐",
            description="80-90% tải trọng — Mục tiêu vận hành lý tưởng",
            max_allowed=0.90, penalty_multiplier=1.0,
        ),
        LoadLevel.WARNING: LoadClassification(
            level=LoadLevel.WARNING,
            label="Cảnh báo", label_en="Warning",
            color="#f39c12", icon="⚠️",
            description="90-95% tải trọng — Cần carrier xác nhận rủi ro quá tải",
            max_allowed=0.95, penalty_multiplier=1.5,
        ),
        LoadLevel.DANGER: LoadClassification(
            level=LoadLevel.DANGER,
            label="Nguy hiểm", label_en="Danger",
            color="#e74c3c", icon="🔴",
            description="95-100% tải trọng — Gần giới hạn pháp lý, rủi ro phanh kém",
            max_allowed=1.00, penalty_multiplier=3.0,
        ),
        LoadLevel.OVERLOAD: LoadClassification(
            level=LoadLevel.OVERLOAD,
            label="QUÁ TẢI", label_en="OVERLOAD",
            color="#c0392b", icon="🚫",
            description="Vượt 100% tải trọng — VI PHẠM Nghị định 100/2019",
            max_allowed=1.00, penalty_multiplier=10.0,
        ),
    }

    @classmethod
    def classify(cls, load_ratio: float, conditions: dict = None) -> LoadClassification:
        """
        Phân loại tải trọng dựa trên tỉ lệ load/capacity.

        Args:
            load_ratio: Tỉ lệ tải trọng (VD: 0.85 = 85%)
            conditions: Dict điều kiện đặc biệt:
                - rain: bool — Trời mưa ngập
                - narrow_road: bool — Đường nội đô hẹp
                - hazmat: bool — Hàng nguy hiểm

        Returns:
            LoadClassification với level, label, color, penalty...
        """
        # Áp dụng giảm tải theo điều kiện
        effective_limit = cls.HARD_LIMIT
        if conditions:
            if conditions.get("rain"):
                effective_limit = min(effective_limit, cls.RAIN_REDUCTION)
            if conditions.get("narrow_road"):
                effective_limit = min(effective_limit, cls.NARROW_ROAD_REDUCTION)
            if conditions.get("hazmat"):
                effective_limit = min(effective_limit, cls.HAZMAT_REDUCTION)

        # Phân loại dựa trên ngưỡng có điều chỉnh
        if load_ratio > effective_limit:
            return cls._CLASSIFICATIONS[LoadLevel.OVERLOAD]
        elif load_ratio > cls.DANGER_THRESHOLD * (effective_limit / cls.HARD_LIMIT):
            return cls._CLASSIFICATIONS[LoadLevel.DANGER]
        elif load_ratio > cls.OPTIMAL_MAX * (effective_limit / cls.HARD_LIMIT):
            return cls._CLASSIFICATIONS[LoadLevel.WARNING]
        elif load_ratio > cls.OPTIMAL_MIN:
            return cls._CLASSIFICATIONS[LoadLevel.OPTIMAL]
        elif load_ratio > cls.SAFE_MIN:
            return cls._CLASSIFICATIONS[LoadLevel.SAFE]
        else:
            return cls._CLASSIFICATIONS[LoadLevel.UNDERLOAD]

    @classmethod
    def get_effective_limit(cls, conditions: dict = None) -> float:
        """Trả về giới hạn tải trọng hiệu lực sau khi xét điều kiện."""
        limit = cls.HARD_LIMIT
        if conditions:
            if conditions.get("rain"):
                limit = min(limit, cls.RAIN_REDUCTION)
            if conditions.get("narrow_road"):
                limit = min(limit, cls.NARROW_ROAD_REDUCTION)
            if conditions.get("hazmat"):
                limit = min(limit, cls.HAZMAT_REDUCTION)
        return limit

    @classmethod
    def get_target_range(cls) -> tuple[float, float]:
        """Trả về khoảng tải trọng mục tiêu (OPTIMAL)."""
        return (cls.OPTIMAL_MIN, cls.OPTIMAL_MAX)

    @classmethod
    def is_legal(cls, load_ratio: float, conditions: dict = None) -> bool:
        """Kiểm tra tải trọng có hợp pháp không."""
        limit = cls.get_effective_limit(conditions)
        return load_ratio <= limit

    @classmethod
    def penalty_factor(cls, load_ratio: float, conditions: dict = None) -> float:
        """Trả về hệ số phạt chi phí dựa trên tải trọng."""
        classification = cls.classify(load_ratio, conditions)
        return classification.penalty_multiplier

    @classmethod
    def format_display(cls, load_kg: float, capacity_kg: float,
                       conditions: dict = None) -> dict:
        """
        Trả về thông tin hiển thị cho UI.

        Returns:
            dict với keys: percentage, level, label, color, icon,
                           description, is_legal, penalty
        """
        if capacity_kg <= 0:
            return {
                "percentage": 0, "level": "SAFE", "label": "N/A",
                "color": "#95a5a6", "icon": "❓",
                "description": "Không có thông tin tải trọng xe",
                "is_legal": True, "penalty": 1.0,
            }

        ratio = load_kg / capacity_kg
        c = cls.classify(ratio, conditions)
        return {
            "percentage": round(ratio * 100, 1),
            "level": c.level.name,
            "label": c.label,
            "color": c.color,
            "icon": c.icon,
            "description": c.description,
            "is_legal": cls.is_legal(ratio, conditions),
            "penalty": c.penalty_multiplier,
        }


# ============================================================
# PHẦN 2: SMART VEHICLE SELECTOR
# ============================================================

class VehicleRecommendation(NamedTuple):
    """Kết quả recommend xe cho đơn hàng."""
    vehicle_id: int
    vehicle_name: str
    score: float           # Điểm phù hợp (0-100)
    predicted_load_pct: float  # % tải trọng dự kiến
    load_classification: str   # LoadLevel name
    reasons: list              # Danh sách lý do
    warnings: list             # Danh sách cảnh báo


# Preset kích thước thùng xe phổ biến tại VN (nếu DB không có)
VEHICLE_CARGO_PRESETS = {
    "xe_may": {
        "cargo_length_cm": 60, "cargo_width_cm": 40,
        "cargo_height_cm": 40, "max_weight_kg": 20,
        "fuel_cost_per_km": 1500,
    },
    "xe_van": {
        "cargo_length_cm": 250, "cargo_width_cm": 150,
        "cargo_height_cm": 150, "max_weight_kg": 800,
        "fuel_cost_per_km": 3500,
    },
    "xe_tai_500kg": {
        "cargo_length_cm": 280, "cargo_width_cm": 155,
        "cargo_height_cm": 145, "max_weight_kg": 500,
        "fuel_cost_per_km": 3000,
    },
    "xe_tai_1t": {
        "cargo_length_cm": 310, "cargo_width_cm": 160,
        "cargo_height_cm": 160, "max_weight_kg": 1000,
        "fuel_cost_per_km": 4000,
    },
    "xe_tai_1t5": {
        "cargo_length_cm": 370, "cargo_width_cm": 170,
        "cargo_height_cm": 170, "max_weight_kg": 1500,
        "fuel_cost_per_km": 4500,
    },
    "xe_tai_2t5": {
        "cargo_length_cm": 430, "cargo_width_cm": 190,
        "cargo_height_cm": 180, "max_weight_kg": 2500,
        "fuel_cost_per_km": 5500,
    },
    "xe_tai_3t5": {
        "cargo_length_cm": 500, "cargo_width_cm": 200,
        "cargo_height_cm": 200, "max_weight_kg": 3500,
        "fuel_cost_per_km": 6500,
    },
    "xe_tai_5t": {
        "cargo_length_cm": 600, "cargo_width_cm": 210,
        "cargo_height_cm": 210, "max_weight_kg": 5000,
        "fuel_cost_per_km": 7500,
    },
    "xe_tai_8t": {
        "cargo_length_cm": 750, "cargo_width_cm": 240,
        "cargo_height_cm": 240, "max_weight_kg": 8000,
        "fuel_cost_per_km": 9000,
    },
}


class SmartVehicleSelector:
    """
    AI chọn xe phù hợp nhất cho nhóm đơn hàng.

    Tiêu chí scoring (tổng 100 điểm):
        40đ — Tải trọng phù hợp (mục tiêu 80-90%)
        20đ — Thể tích phù hợp
        20đ — Chi phí vận hành thấp (xe nhỏ = rẻ hơn)
        10đ — Loại hàng tương thích (lạnh, nặng, dễ vỡ)
        10đ — Phù hợp tuyến đường (đường hẹp → xe nhỏ)
    """

    @staticmethod
    def recommend(
        total_weight_kg: float,
        total_volume_cbm: float,
        available_vehicles: list[dict],
        has_fragile: bool = False,
        has_cold: bool = False,
        narrow_roads: bool = False,
        conditions: dict = None,
    ) -> list[VehicleRecommendation]:
        """
        Recommend xe phù hợp nhất, sắp xếp theo điểm giảm dần.

        Args:
            total_weight_kg: Tổng khối lượng hàng cần chở
            total_volume_cbm: Tổng thể tích hàng (m³)
            available_vehicles: List dict xe khả dụng:
                [{id, name, capacity_kg, capacity_cbm, cost_per_km,
                  cargo_length_cm, cargo_width_cm, cargo_height_cm}]
            has_fragile: Có hàng dễ vỡ không
            has_cold: Cần xe đông lạnh không
            narrow_roads: Tuyến đường có đường hẹp không
            conditions: Điều kiện thời tiết/đường (rain, hazmat...)

        Returns:
            List[VehicleRecommendation] sắp xếp theo score giảm dần
        """
        recommendations = []
        effective_limit = LoadSafetyStandard.get_effective_limit(conditions)

        for v in available_vehicles:
            score = 0.0
            reasons = []
            warnings = []

            capacity_kg = v.get("capacity_kg") or v.get("max_weight_kg", 1000)
            capacity_cbm = v.get("capacity_cbm", 0)
            cost_per_km = v.get("cost_per_km", 5000)

            # Tính cargo volume từ kích thước nếu cbm không có
            if capacity_cbm <= 0:
                l = v.get("cargo_length_cm") or v.get("max_length_cm", 0)
                w = v.get("cargo_width_cm") or v.get("max_width_cm", 0)
                h = v.get("cargo_height_cm") or v.get("max_height_cm", 0)
                if l > 0 and w > 0 and h > 0:
                    capacity_cbm = (l * w * h) / 1_000_000  # cm³ → m³

            # ── 1. Tải trọng phù hợp (40 điểm) ──
            if capacity_kg <= 0:
                weight_score = 0
            else:
                load_ratio = total_weight_kg / capacity_kg
                effective_ratio = load_ratio / effective_limit

                if load_ratio > effective_limit:
                    weight_score = 0  # Quá tải → loại
                    warnings.append(f"Quá tải: {load_ratio:.0%} > {effective_limit:.0%}")
                elif LoadSafetyStandard.OPTIMAL_MIN <= load_ratio <= LoadSafetyStandard.OPTIMAL_MAX:
                    weight_score = 40  # Tối ưu
                    reasons.append(f"Tải trọng tối ưu ({load_ratio:.0%})")
                elif load_ratio < LoadSafetyStandard.SAFE_MIN:
                    weight_score = 10  # Quá nhỏ
                    warnings.append(f"Xe quá lớn (chỉ {load_ratio:.0%} tải)")
                elif load_ratio <= LoadSafetyStandard.OPTIMAL_MIN:
                    # 50-80%: tuyến tính từ 20→35 điểm
                    t = (load_ratio - LoadSafetyStandard.SAFE_MIN) / (
                        LoadSafetyStandard.OPTIMAL_MIN - LoadSafetyStandard.SAFE_MIN)
                    weight_score = 20 + t * 15
                    reasons.append(f"Tải trọng an toàn ({load_ratio:.0%})")
                else:
                    # 90-100%: giảm dần từ 35→5 điểm
                    t = (load_ratio - LoadSafetyStandard.OPTIMAL_MAX) / (
                        effective_limit - LoadSafetyStandard.OPTIMAL_MAX)
                    weight_score = 35 - t * 30
                    warnings.append(f"Tải trọng cao ({load_ratio:.0%})")

            score += weight_score

            # ── 2. Thể tích phù hợp (20 điểm) ──
            if capacity_cbm > 0 and total_volume_cbm > 0:
                vol_ratio = total_volume_cbm / capacity_cbm
                if vol_ratio > 1.0:
                    vol_score = 0
                    warnings.append(f"Quá thể tích: {vol_ratio:.0%}")
                elif 0.6 <= vol_ratio <= 0.9:
                    vol_score = 20
                    reasons.append(f"Thể tích vừa vặn ({vol_ratio:.0%})")
                elif vol_ratio < 0.3:
                    vol_score = 5
                else:
                    vol_score = 10 + (vol_ratio / 0.9) * 10
            else:
                vol_score = 10  # Không có thông tin → neutral
            score += vol_score

            # ── 3. Chi phí vận hành (20 điểm) ──
            # Xe nhỏ hơn = chi phí thấp hơn = điểm cao hơn
            if cost_per_km > 0:
                # Normalize: 1500 VND/km (xe máy) → 20đ, 10000 VND/km (xe 8T) → 2đ
                cost_score = max(2, min(20, 20 - (cost_per_km - 1500) / 500))
            else:
                cost_score = 10
            if weight_score > 0:  # Chỉ tính nếu xe chở được
                reasons.append(f"Chi phí {cost_per_km:,.0f} VND/km")
            score += cost_score

            # ── 4. Tương thích loại hàng (10 điểm) ──
            cargo_score = 10  # Mặc định đầy điểm
            if has_cold:
                has_cold_cap = v.get("has_cold_storage", False)
                if not has_cold_cap:
                    cargo_score = 0
                    warnings.append("Xe không có khoang lạnh")
                else:
                    reasons.append("Có khoang lạnh ✅")

            if has_fragile and capacity_kg > 5000:
                cargo_score = max(0, cargo_score - 3)
                warnings.append("Xe lớn → rung lắc, hàng dễ vỡ cần cẩn thận")
            score += cargo_score

            # ── 5. Phù hợp tuyến đường (10 điểm) ──
            road_score = 10
            if narrow_roads and capacity_kg > 3500:
                road_score = 2
                warnings.append("Xe quá lớn cho đường hẹp nội đô")
            elif narrow_roads and capacity_kg > 2500:
                road_score = 5
                warnings.append("Cần lái xe kinh nghiệm cho đường hẹp")
            score += road_score

            # ── Tổng hợp ──
            load_ratio = total_weight_kg / capacity_kg if capacity_kg > 0 else 0
            classification = LoadSafetyStandard.classify(load_ratio, conditions)

            recommendations.append(VehicleRecommendation(
                vehicle_id=v.get("id", 0),
                vehicle_name=v.get("name", "Unknown"),
                score=round(score, 1),
                predicted_load_pct=round(load_ratio * 100, 1),
                load_classification=classification.level.name,
                reasons=reasons,
                warnings=warnings,
            ))

        # Sort by score descending
        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations

    @staticmethod
    def auto_select(
        total_weight_kg: float,
        total_volume_cbm: float,
        available_vehicles: list[dict],
        **kwargs,
    ) -> dict | None:
        """
        Tự động chọn xe tốt nhất (score cao nhất, không quá tải).

        Returns:
            Vehicle dict hoặc None nếu không có xe phù hợp.
        """
        recs = SmartVehicleSelector.recommend(
            total_weight_kg, total_volume_cbm,
            available_vehicles, **kwargs,
        )
        # Lọc xe quá tải
        valid = [r for r in recs if r.load_classification != "OVERLOAD"]
        if not valid:
            return None

        best = valid[0]
        for v in available_vehicles:
            if v.get("id") == best.vehicle_id:
                return v
        return None


# ============================================================
# PHẦN 3: STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  FLEX-VRP — Vehicle Intelligence Test")
    print("=" * 60)

    # ── Test 1: Load Classifications ──
    print("\n📊 Test phân loại tải trọng:")
    test_ratios = [0.30, 0.55, 0.75, 0.85, 0.92, 0.97, 1.05]
    for ratio in test_ratios:
        c = LoadSafetyStandard.classify(ratio)
        print(f"  {ratio:.0%} → {c.icon} {c.label} ({c.level.name}) "
              f"| Phạt: x{c.penalty_multiplier}")

    # ── Test 2: Điều kiện đặc biệt ──
    print("\n🌧️ Test với điều kiện mưa ngập:")
    rain = {"rain": True}
    for ratio in [0.75, 0.82, 0.95]:
        c_normal = LoadSafetyStandard.classify(ratio)
        c_rain = LoadSafetyStandard.classify(ratio, rain)
        print(f"  {ratio:.0%} → Bình thường: {c_normal.icon} {c_normal.label} "
              f"| Mưa: {c_rain.icon} {c_rain.label}")

    # ── Test 3: Display format ──
    print("\n📋 Test format hiển thị:")
    display = LoadSafetyStandard.format_display(850, 1000)
    print(f"  850/1000 kg → {display['icon']} {display['label']} "
          f"({display['percentage']}%) | Hợp pháp: {display['is_legal']}")

    display_rain = LoadSafetyStandard.format_display(850, 1000, {"rain": True})
    print(f"  850/1000 kg (mưa) → {display_rain['icon']} {display_rain['label']} "
          f"({display_rain['percentage']}%) | Hợp pháp: {display_rain['is_legal']}")

    # ── Test 4: Smart Vehicle Selector ──
    print("\n🚛 Test Smart Vehicle Selector:")
    vehicles = [
        {"id": 1, "name": "Xe Van 800kg", "capacity_kg": 800,
         "capacity_cbm": 4.0, "cost_per_km": 3500},
        {"id": 2, "name": "Xe 1T", "capacity_kg": 1000,
         "capacity_cbm": 5.0, "cost_per_km": 4000},
        {"id": 3, "name": "Xe 2.5T", "capacity_kg": 2500,
         "capacity_cbm": 9.5, "cost_per_km": 5500},
        {"id": 4, "name": "Xe 5T", "capacity_kg": 5000,
         "capacity_cbm": 20.0, "cost_per_km": 7500},
    ]

    # Scenario: 750kg hàng, 3.5m³
    print("\n  Scenario: 750kg hàng, 3.5m³")
    recs = SmartVehicleSelector.recommend(750, 3.5, vehicles)
    for r in recs:
        print(f"  {'⭐' if r.score == recs[0].score else '  '} {r.vehicle_name}: "
              f"{r.score:.0f}đ | Tải: {r.predicted_load_pct:.0f}% ({r.load_classification})")
        if r.reasons:
            print(f"      ✅ {' | '.join(r.reasons)}")
        if r.warnings:
            print(f"      ⚠️ {' | '.join(r.warnings)}")

    # Scenario: 2000kg hàng, đường hẹp
    print("\n  Scenario: 2000kg hàng, đường hẹp")
    recs2 = SmartVehicleSelector.recommend(2000, 8.0, vehicles, narrow_roads=True)
    for r in recs2:
        print(f"  {'⭐' if r.score == recs2[0].score else '  '} {r.vehicle_name}: "
              f"{r.score:.0f}đ | Tải: {r.predicted_load_pct:.0f}% ({r.load_classification})")

    # ── Test 5: Auto select ──
    print("\n🎯 Test auto-select:")
    best = SmartVehicleSelector.auto_select(750, 3.5, vehicles)
    print(f"  750kg → Chọn: {best['name']} ({best['capacity_kg']}kg)")

    best2 = SmartVehicleSelector.auto_select(2000, 8.0, vehicles, narrow_roads=True)
    print(f"  2000kg (đường hẹp) → Chọn: {best2['name']} ({best2['capacity_kg']}kg)")

    print("\n✅ Vehicle Intelligence test hoàn tất!")
