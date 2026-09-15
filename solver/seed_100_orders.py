import os
import json
import random
import uuid
from datetime import datetime, timedelta

# Import db module
import db

HCMC_STREETS = [
    "Lê Duẩn, Quận 1", "Nguyễn Huệ, Quận 1", "Đồng Khởi, Quận 1", "Pasteur, Quận 1", "Hai Bà Trưng, Quận 1",
    "Trần Hưng Đạo, Quận 1", "Bùi Viện, Quận 1", "Phạm Ngũ Lão, Quận 1", "Lý Tự Trọng, Quận 1", "Nguyễn Đình Chiểu, Quận 3",
    "Điện Biên Phủ, Quận 3", "Võ Văn Tần, Quận 3", "Nguyễn Thị Minh Khai, Quận 3", "Lê Văn Sỹ, Quận 3", "Trần Quốc Thảo, Quận 3",
    "Nguyễn Trãi, Quận 5", "An Dương Vương, Quận 5", "Trần Bình Trọng, Quận 5", "Châu Văn Liêm, Quận 5", "Hùng Vương, Quận 5",
    "Nguyễn Tri Phương, Quận 10", "3 Tháng 2, Quận 10", "Sư Vạn Hạnh, Quận 10", "Lý Thái Tổ, Quận 10", "Tô Hiến Thành, Quận 10",
    "Hồng Bàng, Quận 6", "Kinh Dương Vương, Quận 6", "Bình Tiên, Quận 6", "Phạm Văn Chí, Quận 6", "Hậu Giang, Quận 6",
    "Lũy Bán Bích, Tân Phú", "Âu Cơ, Tân Phú", "Tân Sơn Nhì, Tân Phú", "Thoại Ngọc Hầu, Tân Phú", "Hòa Bình, Tân Phú",
    "Trường Chinh, Tân Bình", "Cộng Hòa, Tân Bình", "Hoàng Văn Thụ, Tân Bình", "Bạch Đằng, Tân Bình", "Phổ Quang, Tân Bình",
    "Nguyễn Kiệm, Gò Vấp", "Quang Trung, Gò Vấp", "Phan Văn Trị, Gò Vấp", "Nguyễn Thái Sơn, Gò Vấp", "Lê Đức Thọ, Gò Vấp",
    "Phạm Văn Đồng, Thủ Đức", "Võ Văn Ngân, Thủ Đức", "Kha Vạn Cân, Thủ Đức", "Lê Văn Việt, Quận 9", "Đỗ Xuân Hợp, Quận 9",
    "Nguyễn Duy Trinh, Quận 2", "Trần Não, Quận 2", "Mai Chí Thọ, Quận 2", "Xa lộ Hà Nội, Quận 2", "Thảo Điền, Quận 2",
    "Nguyễn Tất Thành, Quận 4", "Hoàng Diệu, Quận 4", "Bến Vân Đồn, Quận 4", "Khánh Hội, Quận 4", "Tôn Đản, Quận 4",
    "Huỳnh Tấn Phát, Quận 7", "Nguyễn Văn Linh, Quận 7", "Nguyễn Thị Thập, Quận 7", "Lê Văn Lương, Quận 7", "Trần Xuân Soạn, Quận 7",
    "Phạm Hùng, Bình Chánh", "Quốc lộ 50, Bình Chánh", "Nguyễn Hữu Trí, Bình Chánh", "Nguyễn Thị Tú, Bình Tân", "Kinh Dương Vương, Bình Tân",
    "Hương Lộ 2, Bình Tân", "Tân Kỳ Tân Quý, Bình Tân", "Lê Văn Quới, Bình Tân", "Tỉnh lộ 10, Bình Tân", "Mã Lò, Bình Tân",
    "Nguyễn Oanh, Gò Vấp", "Phạm Huy Thông, Gò Vấp", "Dương Quảng Hàm, Gò Vấp", "Thống Nhất, Gò Vấp", "Lê Hoàng Phái, Gò Vấp",
    "Nguyễn Cư Trinh, Quận 1", "Cống Quỳnh, Quận 1", "Tôn Đức Thắng, Quận 1", "Nam Kỳ Khởi Nghĩa, Quận 1", "Lê Lợi, Quận 1",
    "Phạm Văn Hai, Tân Bình", "Nguyễn Trọng Tuyển, Tân Bình", "Huỳnh Văn Bánh, Phú Nhuận", "Phan Xích Long, Phú Nhuận", "Nguyễn Văn Trỗi, Phú Nhuận",
    "Phan Đăng Lưu, Phú Nhuận", "Thích Quảng Đức, Phú Nhuận", "Phan Đình Phùng, Phú Nhuận", "Ngô Gia Tự, Quận 10", "Thành Thái, Quận 10",
    "Vĩnh Viễn, Quận 10", "Ngô Quyền, Quận 10", "Nguyễn Chí Thanh, Quận 11", "Lãnh Binh Thăng, Quận 11", "Bình Thới, Quận 11"
]

COMPANIES = [
    "Cửa hàng Tiện lợi", "Siêu thị Mini", "Nhà thuốc", "Đại lý Nước giải khát",
    "Tạp hóa", "Kho sỉ", "Đại lý Bánh kẹo", "Công ty TNHH", "Cửa hàng VLXD", "Trạm phân phối"
]

PRODUCTS = [
    {"name": "Thùng bia Tiger", "weight": 8.0, "w": 40, "d": 30, "h": 20},
    {"name": "Thùng mì Hảo Hảo", "weight": 3.0, "w": 45, "d": 35, "h": 25},
    {"name": "Thùng sữa Vinamilk", "weight": 6.5, "w": 35, "d": 25, "h": 20},
    {"name": "Bao gạo ST25", "weight": 25.0, "w": 60, "d": 40, "h": 15},
    {"name": "Thùng nước tinh khiết Aquafina", "weight": 12.0, "w": 35, "d": 25, "h": 25},
    {"name": "Lốc nước mắm Nam Ngư", "weight": 4.5, "w": 30, "d": 20, "h": 25},
    {"name": "Hộp bánh quy Danisa", "weight": 1.2, "w": 25, "d": 25, "h": 10},
    {"name": "Thùng nước yến", "weight": 5.0, "w": 35, "d": 25, "h": 15},
    {"name": "Lốc giấy vệ sinh", "weight": 1.5, "w": 50, "d": 30, "h": 30},
    {"name": "Thùng dầu ăn Tường An", "weight": 10.0, "w": 30, "d": 20, "h": 35}
]

def generate_data():
    orders = []
    
    # 1. Tạo 100 địa điểm (Khách hàng)
    locations = []
    for i in range(1, 101):
        street = random.choice(HCMC_STREETS)
        number = random.randint(1, 999)
        company = random.choice(COMPANIES)
        name = f"{company} {number} {street.split(',')[0]}"
        address = f"{number} {street}, TP. HCM"
        lat = 10.7 + random.uniform(0.01, 0.15)
        lon = 106.6 + random.uniform(0.01, 0.15)
        
        locations.append({
            "id": i,
            "name": name,
            "address": address,
            "lat": lat,
            "lon": lon
        })
        
    print(f"✅ Đã tạo {len(locations)} khách hàng/địa điểm.")

    # 2. Tạo 100 đơn hàng
    start_date = datetime.now().date()
    
    for i in range(1, 101):
        loc = random.choice(locations)
        # Số lượng mặt hàng mỗi đơn từ 50 - 500 thùng/kiện như user yêu cầu
        total_quantity = random.randint(50, 500)
        
        # Chọn ngẫu nhiên 1-3 loại sản phẩm cho đơn này
        num_products = random.randint(1, 3)
        order_items = []
        rem_qty = total_quantity
        total_weight = 0.0
        
        for p_idx in range(num_products):
            prod = random.choice(PRODUCTS)
            if p_idx == num_products - 1:
                p_qty = rem_qty
            else:
                p_qty = random.randint(10, max(11, rem_qty // 2))
                rem_qty -= p_qty
                
            if p_qty <= 0: continue
            
            p_weight = round(prod["weight"] * p_qty, 1)
            total_weight += p_weight
            
            order_items.append({
                "product_name": prod["name"],
                "quantity": p_qty,
                "weight_kg": p_weight,
                "width_cm": prod["w"],
                "depth_cm": prod["d"],
                "height_cm": prod["h"]
            })
            
        # Giao hàng gấp (is_urgent) ~ 10%
        is_urgent = 1 if random.random() < 0.1 else 0
        
        # Ngày đặt và ngày giao
        days_offset = random.randint(0, 4)
        order_date = start_date + timedelta(days=days_offset)
        
        time_windows = [("08:00", "12:00"), ("13:00", "17:00"), ("08:00", "17:00")]
        tw = random.choice(time_windows)
        
        order = {
            "order_code": f"B2B-{10000 + i}",
            "customer_name": loc["name"],
            "customer_address": loc["address"],
            "customer_lat": loc["lat"],
            "customer_lon": loc["lon"],
            "total_quantity": total_quantity,
            "total_weight_kg": round(total_weight, 1),
            "order_date": order_date.strftime("%Y-%m-%d"),
            "delivery_date_preferred": order_date.strftime("%Y-%m-%d"),
            "time_window_start": tw[0],
            "time_window_end": tw[1],
            "is_urgent": is_urgent,
            "status": "pending",
            "items": order_items
        }
        orders.append(order)

    print(f"✅ Đã tạo {len(orders)} đơn hàng mẫu.")

    # Lưu thành file json để dùng lâu dài
    data = {
        "locations": locations,
        "orders": orders
    }
    
    file_path = os.path.join(os.path.dirname(__file__), "100_orders_hcm.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Đã lưu file: {file_path}")
    return data

def seed_to_db(data):
    print("🔄 Đang đẩy 100 đơn vào DB...")
    
    # Save locations/customers first
    for loc in data["locations"]:
        db.save_customer(loc["name"], loc["address"], loc["lat"], loc["lon"])
        
    customers_in_db = db.get_customers()
    cust_map = {c["name"]: c["id"] for c in customers_in_db}
    
    # Save orders
    for o in data["orders"]:
        cust_id = cust_map.get(o["customer_name"])
        saved = db.save_order(
            customer_id=cust_id,
            order_code=o["order_code"],
            total_quantity=o["total_quantity"],
            total_weight_kg=o["total_weight_kg"],
            order_date=o["order_date"],
            delivery_date_preferred=o["delivery_date_preferred"],
            time_window_start=o["time_window_start"],
            time_window_end=o["time_window_end"],
            source="manual",
            status=o["status"],
            is_urgent=o["is_urgent"]
        )
        
        if saved and "id" in saved:
            # save items
            db.replace_order_items(saved["id"], o["items"])
            
    print("✅ Đã hoàn thành Seed dữ liệu 100 đơn hàng vào CSDL!")

if __name__ == "__main__":
    generated = generate_data()
    seed_to_db(generated)
