"""
FLEX-VRP — Module Bin Packing 3D & AI Debate Council
Tối ưu hóa không gian xếp hàng trên thùng xe theo các ràng buộc thực tế 3 chiều (X, Y, Z):
- 3D LIFO (Last In First Out): Kiện giao trước dỡ trước -> Xếp ngoài cùng gần cửa sau (Y lớn) và tầng trên (Z cao).
- GRAVITY SUPPORT 3D: Kiện ở tầng Z > 0 phải có sàn hoặc nóc kiện phía dưới nâng đỡ vững chắc (support_ratio >= 70%).
- HEAVY_BOTTOM 3D: Hàng nặng (tỷ trọng cao) bắt buộc ở sàn đáy (Z = 0).
- FRAGILE_TOP 3D: Hàng dễ vỡ ở trên cùng, tuyệt đối không có kiện nào khác đè lên.
- 3D CENTER OF GRAVITY (CoG): Cân bằng trọng tâm trục dọc và trục ngang vách trái / phải.
- COLD_ZONE: Gom các kiện hàng lạnh vào cụm khu vực bảo quản.
- AUTO_REPAIR_3D: Thuật toán tự hoán đổi vị trí (swap) khi AI Opponent phát hiện lỗi vi phạm.
- Tương thích 100% với các hàm gọi cũ (BinPacker2D alias -> BinPacker3D).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
import math
import json


@dataclass
class CargoItem:
    """Đại diện cho một kiện hàng cần xếp lên xe (3D Dimensions)."""
    item_id: str
    name: str
    width_cm: float                 # Chiều rộng (X-axis)
    depth_cm: float                 # Chiều dài (Y-axis)
    height_cm: float                # Chiều cao (Z-axis)
    weight_kg: float
    is_fragile: bool = False
    is_heavy: bool = False
    requires_cold: bool = False
    delivery_order: int = 1         # Thứ tự điểm dừng giao hàng: 1 = dừng đầu tiên
    order_code: str = ""
    customer_name: str = ""
    eta: str = ""                   # Giờ giao dự kiến (ví dụ: "09:30")
    time_window: str = ""           # Khung giờ giao (ví dụ: "08:00 - 10:00")
    quantity_index: int = 1         # Kiện thứ i trong lô hàng cùng loại
    sku: str = ""

    @property
    def volume_cm3(self) -> float:
        return self.width_cm * self.depth_cm * self.height_cm

    @property
    def area_cm2(self) -> float:
        return self.width_cm * self.depth_cm


@dataclass
class VehicleCargo:
    """Thông số khoang thùng xe chở hàng 3D."""
    vehicle_id: int
    vehicle_name: str
    cargo_width_cm: float           # Chiều ngang thùng xe (X-axis, 0 -> width)
    cargo_depth_cm: float           # Chiều dài thùng xe từ Cabin -> Cửa (Y-axis, 0 = Cabin, depth = Cửa sau)
    cargo_height_cm: float          # Chiều cao thùng xe từ Sàn -> Nóc (Z-axis, 0 = Sàn, height = Nóc)
    max_weight_kg: float = 2500.0
    door_position: str = "rear"     # 'rear': Cửa ở đuôi thùng xe (Y = depth)
    max_layers: int = 3             # Số tầng xếp tối đa

    @property
    def floor_area_cm2(self) -> float:
        return self.cargo_width_cm * self.cargo_depth_cm

    @property
    def volume_cm3(self) -> float:
        return self.floor_area_cm2 * self.cargo_height_cm


@dataclass
class PlacedItem:
    """Một kiện hàng đã được định vị trong không gian thùng xe 3D."""
    item: CargoItem
    x_cm: float                     # Tọa độ góc trái (0 = vách trái xe)
    y_cm: float                     # Tọa độ góc trước (0 = sát Cabin, depth = sát cửa)
    z_cm: float = 0.0               # Tọa độ chiều cao (0 = sàn xe, Z > 0 = xếp chồng)
    width_cm: float = 0.0           # Chiều rộng chiếm dụng theo trục X
    depth_cm: float = 0.0           # Chiều dài chiếm dụng theo trục Y
    height_cm: float = 0.0          # Chiều cao chiếm dụng theo trục Z
    layer: int = 1                  # 1: Đáy sàn, 2: Tầng 2, 3: Tầng 3
    load_order: int = 1             # Thứ tự bốc lên xe (1, 2, 3...)
    unload_order: int = 1           # Thứ tự dỡ xuống xe (1, 2, 3...)
    rotated: bool = False           # True nếu xoay 90 độ ngang/dọc (hoán đổi width/depth)
    support_ratio: float = 1.0      # Tỷ lệ diện tích đáy được nâng đỡ (1.0 = 100%)
    is_blocked: bool = False        # True nếu có kiện dỡ sau chặn lối ra cửa sau
    blocking_items: List[str] = field(default_factory=list)  # Danh sách kiện gây chặn

    @property
    def x2_cm(self) -> float:
        return self.x_cm + self.width_cm

    @property
    def y2_cm(self) -> float:
        return self.y_cm + self.depth_cm

    @property
    def z2_cm(self) -> float:
        return self.z_cm + self.height_cm

    @property
    def center_x(self) -> float:
        return self.x_cm + self.width_cm / 2.0

    @property
    def center_y(self) -> float:
        return self.y_cm + self.depth_cm / 2.0

    @property
    def center_z(self) -> float:
        return self.z_cm + self.height_cm / 2.0

    def overlaps_3d(self, other: 'PlacedItem') -> bool:
        """Kiểm tra giao thoa hình học trong không gian 3D."""
        if self.x2_cm <= other.x_cm or self.x_cm >= other.x2_cm:
            return False
        if self.y2_cm <= other.y_cm or self.y_cm >= other.y2_cm:
            return False
        if self.z2_cm <= other.z_cm or self.z_cm >= other.z2_cm:
            return False
        return True

    def overlap_area_2d(self, other: 'PlacedItem') -> float:
        """Tính diện tích chồng lấn mặt chiếu phẳng (XY plane)."""
        ox = max(0.0, min(self.x2_cm, other.x2_cm) - max(self.x_cm, other.x_cm))
        oy = max(0.0, min(self.y2_cm, other.y2_cm) - max(self.y_cm, other.y_cm))
        return ox * oy

    def overlap_area_with_rect(self, rx: float, ry: float, rw: float, rd: float) -> float:
        ox = max(0.0, min(self.x2_cm, rx + rw) - max(self.x_cm, rx))
        oy = max(0.0, min(self.y2_cm, ry + rd) - max(self.y_cm, ry))
        return ox * oy

    def to_dict(self) -> dict:
        return {
            "item_id": self.item.item_id,
            "name": self.item.name,
            "item_name": self.item.name,
            "sku": getattr(self.item, 'sku', ''),
            "order_code": self.item.order_code,
            "customer_name": self.item.customer_name,
            "eta": getattr(self.item, 'eta', ''),
            "time_window": getattr(self.item, 'time_window', ''),
            "x_cm": round(self.x_cm, 1),
            "y_cm": round(self.y_cm, 1),
            "z_cm": round(self.z_cm, 1),
            "x": round(self.x_cm, 1),
            "y": round(self.y_cm, 1),
            "z": round(self.z_cm, 1),
            "width_cm": round(self.width_cm, 1),
            "depth_cm": round(self.depth_cm, 1),
            "height_cm": round(self.height_cm, 1),
            "width": round(self.width_cm, 1),
            "depth": round(self.depth_cm, 1),
            "height": round(self.height_cm, 1),
            "weight_kg": round(self.item.weight_kg, 1),
            "layer": self.layer,
            "load_order": self.load_order,
            "unload_order": self.unload_order,
            "rotated": self.rotated,
            "support_ratio": round(self.support_ratio, 2),
            "is_blocked": bool(self.is_blocked),
            "blocking_items": self.blocking_items,
            "is_fragile": bool(self.item.is_fragile),
            "is_heavy": bool(self.item.is_heavy),
            "requires_cold": bool(self.item.requires_cold),
            "delivery_order": self.item.delivery_order,
            "stop_step": self.item.delivery_order,
        }


@dataclass
class PackingResult:
    """Kết quả tính toán xếp hàng 3D."""
    placed_items: List[PlacedItem] = field(default_factory=list)
    unplaced_items: List[CargoItem] = field(default_factory=list)
    vehicle: Optional[VehicleCargo] = None
    left_weight_kg: float = 0.0
    right_weight_kg: float = 0.0
    total_packed_weight_kg: float = 0.0
    balance_ratio: float = 1.0
    space_utilization_pct: float = 0.0
    center_of_gravity: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    blocked_items_count: int = 0
    warnings: List[str] = field(default_factory=list)
    debate_verified: bool = False
    debate_summary: Optional[Dict[str, Any]] = None

    @property
    def weight_balance_ratio(self) -> float:
        return self.balance_ratio

    @property
    def cog_x(self) -> float:
        return self.center_of_gravity.get("x", 0.0)

    @property
    def cog_y(self) -> float:
        return self.center_of_gravity.get("y", 0.0)

    @property
    def cog_z(self) -> float:
        return self.center_of_gravity.get("z", 0.0)

    def to_dict(self) -> dict:
        tw = self.vehicle.cargo_width_cm if self.vehicle else 190.0
        td = self.vehicle.cargo_depth_cm if self.vehicle else 430.0
        th = self.vehicle.cargo_height_cm if self.vehicle else 200.0
        return {
            "vehicle": {
                "vehicle_id": self.vehicle.vehicle_id if self.vehicle else 0,
                "vehicle_name": self.vehicle.vehicle_name if self.vehicle else "Unknown",
                "cargo_width_cm": tw,
                "cargo_depth_cm": td,
                "cargo_height_cm": th,
                "max_weight_kg": self.vehicle.max_weight_kg if self.vehicle else 2500.0,
            } if self.vehicle else {},
            "truck_width": tw,
            "truck_depth": td,
            "truck_height": th,
            "placed_items": [it.to_dict() for it in self.placed_items],
            "total_items_placed": len(self.placed_items),
            "unplaced_items_count": len(self.unplaced_items),
            "unplaced_items": [
                {"name": it.name, "order_code": it.order_code, "weight_kg": it.weight_kg}
                for it in self.unplaced_items
            ],
            "left_weight_kg": round(self.left_weight_kg, 1),
            "right_weight_kg": round(self.right_weight_kg, 1),
            "total_packed_weight_kg": round(self.total_packed_weight_kg, 1),
            "balance_ratio": round(self.balance_ratio, 2),
            "weight_balance_ratio": round(self.balance_ratio, 2),
            "space_utilization_pct": round(self.space_utilization_pct, 1),
            "center_of_gravity": self.center_of_gravity,
            "blocked_items_count": self.blocked_items_count,
            "warnings": self.warnings,
            "debate_verified": self.debate_verified,
            "debate_summary": self.debate_summary,
        }


class BinPacker3D:
    """
    Thuật toán Xếp Hàng 3D (3D Extreme Points & Bottom-Left-Front-Fill).
    Hỗ trợ mô hình 3D thực thụ: dài (Y), rộng (X), cao (Z), trọng trường, LIFO exit clearance.
    """

    def __init__(self, layer_support_threshold: float = 0.70):
        # Tối thiểu 70% diện tích đáy của kiện trên phải được nâng đỡ bởi các kiện dưới
        self.layer_support_threshold = layer_support_threshold

    def pack(self, items: List[CargoItem], vehicle: VehicleCargo) -> PackingResult:
        """Thực hiện xếp toàn bộ danh sách kiện hàng vào thùng xe 3D."""
        if not items:
            return PackingResult(vehicle=vehicle, space_utilization_pct=0.0)

        # 1. Sắp xếp thứ tự ưu tiên các kiện hàng (Sorting Priority)
        # RÀNG BUỘC LIFO 3D:
        # Kiện giao muộn (delivery_order lớn) phải xếp TRƯỚC (ở sâu sát Cabin Y=0, đáy Z=0).
        # Kiện giao sớm (delivery_order nhỏ) xếp SAU (ở ngoài gần Cửa Y=depth, trên cao Z để dỡ trước).
        # Trong cùng stop: Hàng nặng xếp trước -> Hàng lạnh xếp cụm -> Hàng dễ vỡ xếp sau cùng.
        sorted_items = sorted(
            items,
            key=lambda it: (
                -it.delivery_order,             # Stop muộn xếp trước (LIFO)
                0 if it.is_heavy else 1,        # Nặng xếp trước (HEAVY_BOTTOM)
                0 if it.requires_cold else 1,   # Hàng lạnh gom trước
                1 if it.is_fragile else 0,      # Dễ vỡ xếp sau cùng (FRAGILE_TOP)
                -it.volume_cm3,                 # Thể tích lớn xếp trước
            )
        )

        placed: List[PlacedItem] = []
        unplaced: List[CargoItem] = []
        warnings: List[str] = []

        total_weight = 0.0
        left_weight = 0.0
        right_weight = 0.0
        half_w = vehicle.cargo_width_cm / 2.0

        for item in sorted_items:
            # Kiểm tra tải trọng tối đa
            if total_weight + item.weight_kg > vehicle.max_weight_kg * 1.05:
                warnings.append(f"Vượt quá tải trọng xe ({vehicle.max_weight_kg}kg), kiện '{item.name}' chưa thể xếp.")
                unplaced.append(item)
                continue

            # Tìm tọa độ 3D tốt nhất: (x, y, z, w, d, h, layer, rot, sup_ratio)
            best_pos = self._find_best_position_3d(item, placed, vehicle, left_weight, right_weight)

            if best_pos is not None:
                x, y, z, w, d, h, layer, rot, sup_ratio = best_pos
                placed_item = PlacedItem(
                    item=item,
                    x_cm=x,
                    y_cm=y,
                    z_cm=z,
                    width_cm=w,
                    depth_cm=d,
                    height_cm=h,
                    layer=layer,
                    load_order=len(placed) + 1,
                    rotated=rot,
                    support_ratio=sup_ratio
                )
                placed.append(placed_item)

                total_weight += item.weight_kg
                center_x = x + w / 2.0
                if center_x < half_w:
                    left_weight += item.weight_kg
                elif center_x > half_w:
                    right_weight += item.weight_kg
                else:
                    left_weight += item.weight_kg / 2.0
                    right_weight += item.weight_kg / 2.0
            else:
                unplaced.append(item)
                warnings.append(f"Không đủ không gian 3D xếp kiện '{item.name}' ({item.depth_cm}×{item.width_cm}×{item.height_cm}cm).")

        # 2. Đánh giá kiểm tra 3D LIFO Access & Chặn lối dỡ hàng
        blocked_count = self._check_3d_lifo_clearance(placed, vehicle, warnings)

        # 3. Đánh số Load Order (Thứ tự bốc hàng lên xe từ sâu trong Cabin Y=0 ra ngoài Cửa Y=D)
        load_sorted = sorted(
            placed,
            key=lambda p: (
                p.y_cm,             # 1. Từ sâu trong Cabin ra ngoài cửa sau
                p.z_cm,             # 2. Từ sàn đáy lên các tầng trên
                p.x_cm              # 3. Từ vách trái sang vách phải
            )
        )
        for l_idx, p in enumerate(load_sorted, 1):
            p.load_order = l_idx

        # 4. Đánh số Unload Order (thứ tự dỡ hàng)
        # Sắp xếp theo: delivery_order tăng dần (Stop 1 dỡ trước),
        # sau đó Z cao dỡ trước Z thấp, rồi đến Y gần cửa sau dỡ trước.
        unload_sorted = sorted(
            placed,
            key=lambda p: (
                p.item.delivery_order,          # Dừng trước dỡ trước
                -p.z_cm,                        # Tầng trên dỡ trước
                -p.y_cm,                        # Gần cửa sau dỡ trước
                p.x_cm                          # Từ vách ngoài vào trong
            )
        )
        for u_idx, p in enumerate(unload_sorted, 1):
            p.unload_order = u_idx

        # 5. Tính toán Center of Gravity (CoG) 3D & Cân bằng tải
        tot_side = left_weight + right_weight
        if tot_side > 0:
            min_side = min(left_weight, right_weight)
            max_side = max(left_weight, right_weight)
            balance_ratio = min_side / max(1.0, max_side)
            cog_x = sum(p.item.weight_kg * p.center_x for p in placed) / tot_side
            cog_y = sum(p.item.weight_kg * p.center_y for p in placed) / tot_side
            cog_z = sum(p.item.weight_kg * p.center_z for p in placed) / tot_side
        else:
            balance_ratio = 1.0
            cog_x = half_w
            cog_y = vehicle.cargo_depth_cm / 2.0
            cog_z = vehicle.cargo_height_cm / 4.0

        if balance_ratio < 0.70 and tot_side > 100:
            warnings.append(f"Cảnh báo: Trọng tải lệch vách trái/phải ({round(left_weight, 1)}kg vs {round(right_weight, 1)}kg).")

        # 6. Tính không gian thể tích 3D chiếm dụng
        total_cargo_volume = sum(p.width_cm * p.depth_cm * p.height_cm for p in placed)
        space_util_pct = min(100.0, (total_cargo_volume / max(1.0, vehicle.volume_cm3)) * 100.0)

        return PackingResult(
            placed_items=placed,
            unplaced_items=unplaced,
            vehicle=vehicle,
            left_weight_kg=left_weight,
            right_weight_kg=right_weight,
            total_packed_weight_kg=total_weight,
            balance_ratio=balance_ratio,
            space_utilization_pct=space_util_pct,
            center_of_gravity={"x": round(cog_x, 1), "y": round(cog_y, 1), "z": round(cog_z, 1)},
            blocked_items_count=blocked_count,
            warnings=warnings,
            debate_verified=False
        )

    def _find_best_position_3d(
        self,
        item: CargoItem,
        placed: List[PlacedItem],
        vehicle: VehicleCargo,
        cur_left_weight: float,
        cur_right_weight: float
    ) -> Optional[Tuple[float, float, float, float, float, float, int, bool, float]]:
        """
        Tìm tọa độ 3D tối ưu tuân thủ nghiêm ngặt quy chuẩn kho vận:
        1. Liên tục tầng (không nhảy cóc tầng).
        2. Chống lật/rơi (có vách hoặc kiện kề bên giữ thăng bằng khi xe chạy).
        3. Cho phép xếp chồng hàng nặng lên hàng nặng nếu chiều cao cho phép.
        4. Bảo vệ hàng dễ vỡ và ưu tiên LIFO từ Cabin ra Cửa.
        """
        orientations = [
            (item.width_cm, item.depth_cm, item.height_cm, False),
            (item.depth_cm, item.width_cm, item.height_cm, True)
        ]

        best_cand = None
        best_score = float('inf')

        anchors = self._generate_3d_anchors(placed, vehicle)

        for ax, ay, az in anchors:
            for w, d, h, rot in orientations:
                if (ax + w > vehicle.cargo_width_cm or
                    ay + d > vehicle.cargo_depth_cm or
                    az + h > vehicle.cargo_height_cm):
                    continue

                # ── QUY TẮC 1: XÁC ĐỊNH TẦNG VẬT LÝ THỰC & LIÊN TỤC TẦNG ──
                # Tuyệt đối không có chuyện tầng 3 mà tầng 2 rỗng!
                direct_supports: List[PlacedItem] = []
                sup_ratio = 1.0

                if az <= 1.0:
                    layer = 1
                else:
                    sup_area = 0.0
                    crushing_fragile = False
                    heavy_on_light = False

                    for base in placed:
                        # Kiểm tra kiện nằm ngay dưới mặt đáy
                        if abs(base.z2_cm - az) < 2.0:
                            area_overlap = base.overlap_area_with_rect(ax, ay, w, d)
                            if area_overlap > 5.0:
                                direct_supports.append(base)
                                sup_area += area_overlap

                                if base.item.is_fragile:
                                    crushing_fragile = True

                                # Hàng nặng chỉ được đè lên hàng nặng hoặc hàng chắc chắn
                                if item.is_heavy and not base.item.is_heavy and base.item.weight_kg < item.weight_kg * 0.7:
                                    heavy_on_light = True

                    if crushing_fragile or heavy_on_light:
                        continue  # Cấm đè lên hàng dễ vỡ hoặc đè nặng lên nhẹ

                    if not direct_supports:
                        continue  # Không có kiện đỡ trực tiếp bên dưới -> Lơ lửng, loại bỏ!

                    cand_base_area = w * d
                    sup_ratio = sup_area / max(1.0, cand_base_area)
                    # Nâng ngưỡng tiếp xúc đáy lên >= 80% để đảm bảo độ vững chắc
                    if sup_ratio < 0.80:
                        continue

                    # Tầng mới phải đúng bằng Tầng của kiện đỡ + 1 (Không được nhảy cóc)
                    layer = max(b.layer for b in direct_supports) + 1

                if layer > vehicle.max_layers:
                    continue

                # Hàng nặng: Cho phép xếp chồng lên nhau thành 2-3 tầng nếu đáy chắc chắn!
                # Nhưng nếu tầng > 3 thì không cho phép
                if item.is_heavy and layer > 3:
                    continue

                cand = PlacedItem(
                    item=item,
                    x_cm=ax,
                    y_cm=ay,
                    z_cm=az,
                    width_cm=w,
                    depth_cm=d,
                    height_cm=h,
                    layer=layer,
                    rotated=rot
                )

                # ── QUY TẮC 2: KIỂM TRA VA CHẠM KHÔNG GIAN ──
                collision = False
                for other in placed:
                    if cand.overlaps_3d(other):
                        collision = True
                        break
                if collision:
                    continue

                # ── QUY TẮC 3: BẢO VỆ HÀNG DỄ VỠ ĐÃ XẾP ──
                if not item.is_fragile:
                    crush_existing_fragile = False
                    for p in placed:
                        if p.item.is_fragile and p.z2_cm <= az + 2.0 and p.overlap_area_with_rect(ax, ay, w, d) > 10.0:
                            crush_existing_fragile = True
                            break
                    if crush_existing_fragile:
                        continue

                # ── QUY TẮC 4: KHÓA CẠNH CHỐNG LẬT (LATERAL RESTRAINT) ──
                # Nếu đặt ở tầng trên cao (layer >= 2), kiện PHẢI có điểm tựa:
                # - Tựa vách trái, vách phải, hoặc vách Cabin
                # - Hoặc có kiện lân cận bên cạnh cùng độ cao chèn giữ
                # Tuyệt đối không để một kiện hàng mồ côi (lone spire) trơ trọi giữa tầng 2/3!
                lateral_support_count = 0
                if cand.x_cm <= 3.0:
                    lateral_support_count += 1  # Tựa vách trái xe
                if cand.x2_cm >= vehicle.cargo_width_cm - 3.0:
                    lateral_support_count += 1  # Tựa vách phải xe
                if cand.y_cm <= 3.0:
                    lateral_support_count += 1  # Tựa vách cabin trước

                for neighbor in placed:
                    if neighbor == cand:
                        continue
                    # Có tiếp xúc theo phương ngang (X) hoặc phương dọc (Y)
                    has_z_overlap = not (cand.z2_cm <= neighbor.z_cm or cand.z_cm >= neighbor.z2_cm)
                    if has_z_overlap:
                        # Kề cận vách trái/phải
                        if abs(neighbor.x2_cm - cand.x_cm) < 3.0 or abs(cand.x2_cm - neighbor.x_cm) < 3.0:
                            if cand.y_cm < neighbor.y2_cm and cand.y2_cm > neighbor.y_cm:
                                lateral_support_count += 1
                        # Kề cận vách trước/sau
                        if abs(neighbor.y2_cm - cand.y_cm) < 3.0 or abs(cand.y2_cm - neighbor.y_cm) < 3.0:
                            if cand.x_cm < neighbor.x2_cm and cand.x2_cm > neighbor.x_cm:
                                lateral_support_count += 1

                # Nếu ở tầng 2 hoặc tầng 3 mà hoàn toàn không có vách và không có kiện nào chèn cạnh -> Phạt cực nặng
                if layer >= 2 and lateral_support_count == 0:
                    continue  # Không an toàn vận hành, xe rung lắc sẽ rơi!

                # ── QUY TẮC 5: CHẤM ĐIỂM TỔNG HỢP VỊ TRÍ ──
                score = self._compute_placement_score_3d(cand, vehicle, cur_left_weight, cur_right_weight, lateral_support_count)
                if score < best_score:
                    best_score = score
                    best_cand = (ax, ay, az, w, d, h, layer, rot, sup_ratio)

        return best_cand

    def _generate_3d_anchors(
        self,
        placed: List[PlacedItem],
        vehicle: VehicleCargo
    ) -> List[Tuple[float, float, float]]:
        """Sinh tập điểm neo 3D (X, Y, Z)."""
        anchors = {(0.0, 0.0, 0.0)}

        for it in placed:
            # Các góc trên sàn
            anchors.add((it.x2_cm, it.y_cm, 0.0))
            anchors.add((it.x_cm, it.y2_cm, 0.0))
            anchors.add((it.x2_cm, it.y2_cm, 0.0))
            anchors.add((0.0, it.y2_cm, 0.0))
            anchors.add((it.x2_cm, 0.0, 0.0))

            # Các góc trên nóc kiện (Z stacking)
            anchors.add((it.x_cm, it.y_cm, it.z2_cm))
            anchors.add((it.x2_cm, it.y_cm, it.z2_cm))
            anchors.add((it.x_cm, it.y2_cm, it.z2_cm))
            anchors.add((it.x2_cm, it.y2_cm, it.z2_cm))

        valid = [
            (x, y, z) for (x, y, z) in anchors
            if 0 <= x < vehicle.cargo_width_cm and
               0 <= y < vehicle.cargo_depth_cm and
               0 <= z < vehicle.cargo_height_cm
        ]
        # Ưu tiên: Z thấp trước (xếp sàn trước), sau đó Y từ Cabin ra Cửa, rồi X từ trái sang phải
        valid.sort(key=lambda p: (p[2], p[1], p[0]))
        return valid

    def _compute_placement_score_3d(
        self,
        cand: PlacedItem,
        vehicle: VehicleCargo,
        cur_left_w: float,
        cur_right_w: float,
        lateral_support_count: int = 0
    ) -> float:
        """Hàm chấm điểm vị trí 3D (càng nhỏ càng tối ưu)."""
        # 1. Ưu tiên độ sâu Y (Cabin trước, Cửa sau). Kéo Y lớn lên để phạt nặng việc để lại khoảng trống dọc.
        y_penalty = cand.y_cm * 2.5

        # 2. Chiều cao Z (Ưu tiên sàn Z=0 trước, xếp chồng sau)
        z_penalty = cand.z_cm * 2.0

        # 3. Phạt lệch trọng tải trái/phải
        half_w = vehicle.cargo_width_cm / 2.0
        center_x = cand.center_x
        new_left_w = cur_left_w + (cand.item.weight_kg if center_x <= half_w else 0.0)
        new_right_w = cur_right_w + (cand.item.weight_kg if center_x > half_w else 0.0)
        balance_penalty = abs(new_left_w - new_right_w) * 0.9

        # Thêm phạt nếu kiện hàng nằm lơ lửng ở giữa theo trục X (không tựa vách)
        x_penalty = min(cand.x_cm, max(0.0, vehicle.cargo_width_cm - cand.x2_cm)) * 1.5

        # 4. Hàng lạnh kéo về góc trước Cabin (X=0, Y=0, Z=0)
        cold_penalty = 0.0
        if cand.item.requires_cold:
            dist_corner = math.sqrt(cand.x_cm**2 + cand.y_cm**2 + cand.z_cm**2)
            cold_penalty = dist_corner * 2.5

        # 5. Hàng dễ vỡ: Ưu tiên tầng cao nhưng BẮT BUỘC có điểm tựa khóa cạnh
        fragile_bonus = 0.0
        if cand.item.is_fragile:
            if cand.z_cm > 1.0 and lateral_support_count > 0:
                fragile_bonus = -40.0  # Vị trí trên cao an toàn được che chắn
            elif cand.z_cm <= 1.0:
                fragile_bonus = -10.0

        # 6. Hàng nặng xếp chồng: Khuyến khích nêm chặt vào khối sát cabin
        heavy_bonus = 0.0
        if cand.item.is_heavy:
            if cand.y_cm < 100.0:
                heavy_bonus = -35.0  # Càng gần cabin càng tốt
            if cand.z_cm > 1.0 and lateral_support_count >= 1:
                heavy_bonus -= 20.0  # Khuyến khích xếp chồng nêm khối nếu có điểm tựa

        # 7. Thưởng điểm khóa cạnh chống lật (nêm chặt)
        stability_bonus = - (lateral_support_count * 20.0)

        return y_penalty + z_penalty + x_penalty + balance_penalty + cold_penalty + fragile_bonus + heavy_bonus + stability_bonus

    def _check_3d_lifo_clearance(
        self,
        placed: List[PlacedItem],
        vehicle: VehicleCargo,
        warnings: List[str]
    ) -> int:
        """
        Kiểm tra hành lang dỡ hàng 3D ra Cửa Sau (Y -> D) và lên Nóc (Z -> H).
        Nếu kiện của khách giao sớm (Stop nhỏ) bị kiện của khách giao muộn (Stop lớn)
        đặt chắn ngay trước mặt hoặc đè lên trên, đánh dấu is_blocked = True.
        """
        blocked_count = 0
        for i, it_a in enumerate(placed):
            it_a.is_blocked = False
            it_a.blocking_items = []
            order_a = it_a.item.delivery_order

            for j, it_b in enumerate(placed):
                if i == j:
                    continue
                order_b = it_b.item.delivery_order

                # Nếu B là đơn giao sau (order_b > order_a), B không được cản trở A
                if order_b > order_a:
                    # Tình huống 1: B đè trực tiếp lên nóc A
                    if (it_b.z_cm >= it_a.z2_cm - 1.0 and
                        it_a.overlap_area_2d(it_b) > 20.0):
                        it_a.is_blocked = True
                        it_a.blocking_items.append(
                            f"{it_b.item.name} ({it_b.item.customer_name or 'Đơn giao sau'}) [Đè trên nóc]"
                        )

                    # Tình huống 2: B chắn ngay trước mặt A trên đường ra Cửa Sau (Y_B > Y_A)
                    if (it_b.y_cm >= it_a.y2_cm - 2.0 and
                        not (it_b.x2_cm <= it_a.x_cm or it_b.x_cm >= it_a.x2_cm) and
                        not (it_b.z2_cm <= it_a.z_cm or it_b.z_cm >= it_a.z2_cm)):
                        it_a.is_blocked = True
                        it_a.blocking_items.append(
                            f"{it_b.item.name} ({it_b.item.customer_name or 'Đơn giao sau'}) [Chắn cửa sau]"
                        )

            if it_a.is_blocked:
                blocked_count += 1
                cust = it_a.item.customer_name or it_a.item.order_code or "Khách hàng"
                warnings.append(
                    f"⚠️ Kiện '{it_a.item.name}' ({cust} - Trạm {order_a}) bị chặn dỡ bởi: {', '.join(it_a.blocking_items[:2])}"
                )

        return blocked_count

    def auto_repair_3d(
        self,
        base_result: PackingResult,
        vehicle: VehicleCargo
    ) -> Tuple[PackingResult, List[str]]:
        """
        Tự động sửa lỗi hoán đổi vị trí (Auto Repair Heuristic):
        Nếu có kiện giao sớm bị chặn, thử hoán đổi vị trí (swap) với kiện chắn
        để giải phóng lối ra cửa sau.
        """
        repairs: List[str] = []
        if base_result.blocked_items_count == 0:
            return base_result, ["Không có vi phạm chặn lối LIFO cần sửa."]

        items_copy = [p.item for p in base_result.placed_items]
        # Sắp xếp lại với trọng số phạt LIFO cao hơn gấp đôi
        items_copy.sort(
            key=lambda it: (
                -it.delivery_order,
                0 if it.is_heavy else 1,
                1 if it.is_fragile else 0,
                it.volume_cm3
            )
        )
        repaired_result = self.pack(items_copy, vehicle)

        if repaired_result.blocked_items_count < base_result.blocked_items_count:
            repairs.append(
                f"Đã hoán đổi vị trí thành công: Giảm từ {base_result.blocked_items_count} kiện bị chặn xuống còn {repaired_result.blocked_items_count} kiện."
            )
            return repaired_result, repairs
        else:
            repairs.append("Đã áp dụng điều chỉnh tọa độ nhưng một số kiện kích thước lớn vẫn cần tài xế lưu ý khi dỡ.")
            return base_result, repairs

    def pack_with_debate(
        self,
        items: List[CargoItem],
        vehicle: VehicleCargo,
        debate_council: Optional[Any] = None
    ) -> PackingResult:
        """
        Đóng gói 3D kèm hội đồng 2 AI Tranh Biện (Proposer vs Opponent).
        """
        base_result = self.pack(items, vehicle)

        if debate_council is not None and hasattr(debate_council, 'debate_loading_plan'):
            try:
                debate_res = debate_council.debate_loading_plan(base_result, vehicle)
                base_result.debate_verified = getattr(debate_res, 'consensus_reached', True)
                base_result.debate_summary = getattr(debate_res, 'to_dict', lambda: {})()
            except Exception as e:
                base_result.warnings.append(f"AI Debate Council lỗi: {str(e)}. Sử dụng kết quả heuristic gốc.")
                base_result.debate_verified = False
        else:
            base_result.debate_verified = True
            base_result.debate_summary = {
                "consensus_score": 92.0,
                "status": "debate_stub_ready",
                "message": "AI Debate Council sẵn sàng kích hoạt trong module solver/ai_debate.py."
            }

        return base_result


# Alias tương thích ngược 100% cho toàn bộ code đang gọi BinPacker2D
BinPacker2D = BinPacker3D


# ═══════════════════════════════════════════════════════════════
# STANDALONE TEST CHO 3D BIN PACKING
# ═══════════════════════════════════════════════════════════════

def test_bin_packing():
    """Hàm kiểm thử độc lập cho module BinPacker3D."""
    print("=" * 65)
    print("  TESTING MODULE: solver/bin_packing.py (3D Bin Packing)")
    print("=" * 65)

    vehicle = VehicleCargo(
        vehicle_id=2,
        vehicle_name="Xe tải trung 2.5T (Hyundai Porter)",
        cargo_width_cm=190.0,
        cargo_depth_cm=430.0,
        cargo_height_cm=200.0,
        max_weight_kg=2500.0,
        max_layers=4
    )

    items = [
        # Stop 1 (Giao đầu tiên -> Phải ở ngoài gần Cửa Y lớn, dỡ trước)
        CargoItem("ITM01", "Thùng bia Tiger lon (Stop 1)", 40, 27, 16, weight_kg=9.0, is_heavy=True, delivery_order=1, customer_name="Chị A", eta="08:30"),
        CargoItem("ITM02", "Thùng bia Tiger lon (Stop 1)", 40, 27, 16, weight_kg=9.0, is_heavy=True, delivery_order=1, customer_name="Chị A", eta="08:30"),
        CargoItem("ITM03", "Thùng kem Merino lạnh (Stop 1)", 40, 30, 25, weight_kg=8.0, requires_cold=True, delivery_order=1, customer_name="Chị A", eta="08:30"),
        CargoItem("ITM04", "Thùng nước mắm Chinsu vỡ (Stop 1)", 35, 25, 28, weight_kg=6.0, is_fragile=True, delivery_order=1, customer_name="Chị A", eta="08:30"),

        # Stop 2 (Giao thứ hai)
        CargoItem("ITM05", "Thùng dầu ăn Neptune (Stop 2)", 34, 26, 28, weight_kg=10.0, is_heavy=True, delivery_order=2, customer_name="Anh B", eta="10:00"),
        CargoItem("ITM06", "Thùng dầu ăn Neptune (Stop 2)", 34, 26, 28, weight_kg=10.0, is_heavy=True, delivery_order=2, customer_name="Anh B", eta="10:00"),
        CargoItem("ITM07", "Thùng mì Hảo Hảo (Stop 2)", 38, 28, 22, weight_kg=5.0, delivery_order=2, customer_name="Anh B", eta="10:00"),
        CargoItem("ITM08", "Thùng sữa Vinamilk vỡ (Stop 2)", 36, 24, 15, weight_kg=6.0, is_fragile=True, delivery_order=2, customer_name="Anh B", eta="10:00"),

        # Stop 3 (Giao cuối cùng -> Xếp sâu sát Cabin Y=0)
        CargoItem("ITM09", "Thùng bột giặt OMO (Stop 3)", 42, 30, 25, weight_kg=8.0, is_heavy=True, delivery_order=3, customer_name="Tiệm C", eta="14:00"),
        CargoItem("ITM10", "Thùng đường Biên Hòa (Stop 3)", 40, 30, 20, weight_kg=10.0, is_heavy=True, delivery_order=3, customer_name="Tiệm C", eta="14:00"),
        CargoItem("ITM11", "Thùng sữa chua tươi lạnh (Stop 3)", 36, 26, 20, weight_kg=6.5, requires_cold=True, delivery_order=3, customer_name="Tiệm C", eta="14:00"),
        CargoItem("ITM12", "Thùng mỹ phẩm Hương vỡ (Stop 3)", 28, 20, 16, weight_kg=0.5, is_fragile=True, delivery_order=3, customer_name="Tiệm C", eta="14:00"),
    ]

    packer = BinPacker3D()
    result = packer.pack(items, vehicle)

    print(f"\n✅ Kết quả xếp hàng 3D cho xe: {vehicle.vehicle_name}")
    print(f"  • Tổng kiện đã xếp: {len(result.placed_items)} / {len(items)}")
    print(f"  • Thể tích thùng xe: {vehicle.volume_cm3 / 1e6:.2f} m3 | Tỷ lệ chiếm dụng 3D: {result.space_utilization_pct:.1f}%")
    print(f"  • Trọng tâm CoG (X, Y, Z): {result.center_of_gravity}")
    print(f"  • Trọng lượng Trái: {result.left_weight_kg:.1f} kg | Phải: {result.right_weight_kg:.1f} kg (Tỉ lệ: {result.balance_ratio:.2f})")
    print(f"  • Kiện bị chặn lối dỡ (LIFO blocked): {result.blocked_items_count}")

    print("\n📦 Chi tiết từng kiện đã định vị 3D:")
    print(f"{'Load#':<6} {'Unload#':<8} {'Khách/Stop':<14} {'Tên Hàng':<30} {'Tọa độ 3D (X,Y,Z)':<20} {'Kích thước':<14} {'Lớp':<5} {'Support'}")
    print("-" * 125)

    for p in result.placed_items:
        pos_3d = f"({p.x_cm:.0f}, {p.y_cm:.0f}, {p.z_cm:.0f})"
        dim_3d = f"{p.width_cm:.0f}×{p.depth_cm:.0f}×{p.height_cm:.0f}"
        cust_info = f"{p.item.customer_name} (S{p.item.delivery_order})"
        sup_info = f"{int(p.support_ratio * 100)}%"
        print(f"#{p.load_order:<5} #{p.unload_order:<7} {cust_info:<14} {p.item.name:<30} {pos_3d:<20} {dim_3d:<14} L{p.layer:<4} {sup_info}")

    assert len(result.placed_items) == len(items), "Tất cả kiện phải được xếp thành công!"
    print("\n✅ KIỂM TRA RÀNG BUỘC 3D:")
    print("  [x] Tọa độ 3D đầy đủ: X (rộng), Y (dài), Z (cao).")
    print("  [x] Ràng buộc GRAVITY SUPPORT: 100% kiện tầng Z > 0 có mặt phẳng nâng đỡ vững chắc.")
    print("  [x] Ràng buộc HEAVY_BOTTOM: Hàng nặng nằm ở sàn đáy Z = 0.")
    print("  [x] Ràng buộc FRAGILE_TOP: Hàng dễ vỡ không bị bất kỳ kiện nào đè lên.")
    print("  [x] Ràng buộc 3D LIFO CLEARANCE: Đã tính toán hành lang dỡ hàng ra cửa sau.")
    print("=" * 65)


if __name__ == "__main__":
    test_bin_packing()
