import csv
import os
import random
import math

def generate_hcm_locations(num_locations=100, output_file='../database/data/locations.csv'):
    print(f"Bắt đầu tạo {num_locations} địa điểm ngẫu nhiên tại TP.HCM...")
    
    # Bounding box khu vực trung tâm TP.HCM
    # Min Lat: 10.7, Max Lat: 10.85
    # Min Lng: 106.6, Max Lng: 106.8
    min_lat, max_lat = 10.7000, 10.8500
    min_lng, max_lng = 106.6000, 106.8000
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    districts = [
        "Quận 1", "Quận 3", "Quận 4", "Quận 5", "Quận 10", 
        "Quận Phú Nhuận", "Quận Bình Thạnh", "Quận Tân Bình"
    ]
    streets = [
        "Lê Lợi", "Nguyễn Huệ", "Trần Hưng Đạo", "Cách Mạng Tháng Tám", 
        "Nguyễn Thị Minh Khai", "Điện Biên Phủ", "Hai Bà Trưng", "Pasteur",
        "Nam Kỳ Khởi Nghĩa", "Nguyễn Đình Chiểu", "Võ Văn Tần"
    ]
    
    with open(output_file, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'latitude', 'longitude', 'address', 'type'])
        
        for i in range(num_locations):
            lat = random.uniform(min_lat, max_lat)
            lng = random.uniform(min_lng, max_lng)
            
            name = f"Cửa hàng {i + 1}"
            house_number = random.randint(1, 999)
            street = random.choice(streets)
            district = random.choice(districts)
            
            address = f"{house_number} {street}, {district}, TP.HCM"
            shop_type = random.choice(["grocery", "supermarket", "convenience"])
            
            writer.writerow([name, round(lat, 6), round(lng, 6), address, shop_type])
            
    print(f"Đã tạo thành công {num_locations} địa điểm vào {output_file}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(script_dir, '../database/data/locations.csv')
    generate_hcm_locations(100, out_path)
