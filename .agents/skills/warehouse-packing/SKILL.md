---
name: warehouse-packing
description: >-
  Các quy tắc và hướng dẫn xếp hàng 3D thực tế cho xe tải chở hàng. 
  Sử dụng skill này khi cần tinh chỉnh thuật toán không gian 3D, tính toán ổn định kiện hàng, và các ràng buộc khi bốc/dỡ hàng LIFO.
---

# Quy Tắc Xếp Hàng Kho Vận Thực Tế (FLEX-VRP 3D Packing)

Skill này hướng dẫn các nguyên tắc vật lý và an toàn khi xếp hàng trong thùng xe tải để tránh rơi vỡ và đảm bảo tính nhân trắc học cho nhân viên bốc vác (không dẫm đạp lên hàng khác).

## 1. Nguyên Tắc An Toàn & Ổn Định Chống Lật
- **Hàng Nặng Nằm Dưới (Heavy Bottom)**: Các kiện hàng nặng (is_heavy) luôn phải được xếp ở tầng trệt (Z=0) hoặc xếp chồng lên nhau thành tối đa 2-3 tầng nhưng tuyệt đối không được đè lên hàng nhẹ hơn.
- **Hàng Dễ Vỡ Nằm Trên (Fragile Top)**: Hàng dễ vỡ (is_fragile) luôn phải xếp ở tầng cao nhất và tuyệt đối không được có vật gì đè lên.
- **Khóa Cạnh Chống Lật (Lateral Support)**: Mọi kiện hàng khi xếp ở tầng 2 trở lên BẮT BUỘC phải có điểm tựa ngang để xe chạy không bị rơi. Điểm tựa này có thể là vách thùng xe (Cabin, Trái, Phải) hoặc các kiện hàng kề bên (neighbor) có cùng độ cao. Không được tạo ra các cột tháp rời rạc.
- **Diện Tích Tiếp Xúc Đáy (Support Ratio)**: Để xếp một kiện hàng lên tầng cao, nó cần được đỡ bởi một mặt phẳng ổn định phía dưới (diện tích tiếp xúc mặt đáy tối thiểu 80%).

## 2. Nguyên Tắc Bốc Dỡ & Nhân Trắc Học (LIFO & Human Access)
- **Vào Trước Ra Sau (LIFO)**: Các kiện hàng giao ở trạm cuối (Delivery Order lớn) phải được xếp ở phía sâu trong thùng xe sát Cabin (Y nhỏ). Các kiện giao trạm đầu (Delivery Order nhỏ) phải được xếp ở phía ngoài cùng, sát cửa sau (Y lớn) để dỡ trước.
- **Lối Đi Và Chỗ Đứng Tác Nghiệp (Access Corridor)**: Khi xếp kiện hàng, phải tính đến việc nhân viên có chỗ đứng để nâng/đặt hàng mà không dẫm lên hàng khác. Nghĩa là phải lấp đầy các tầng Z từ dưới lên trên cho một mặt cắt Y nhất định trước khi lùi ra phía cửa xe.
- **Trình Tự Bốc Lên Xe (Load Order)**: Xếp từ Cabin ra Cửa (ưu tiên 1), Xếp từ Sàn lên Nóc (ưu tiên 2). Nhân viên sẽ đứng ở khoảng trống phía cửa sau và lùi dần. Trình tự này tương ứng với biến `load_order` trong mã nguồn.

## 3. Cân Bằng Trọng Tâm (Center of Gravity)
- Phân bổ trọng lượng đồng đều giữa vách trái và vách phải của xe (Balance Ratio) để tránh nghiêng xe. Tỉ lệ cân bằng tối thiểu phải đạt 70%.

## Hướng dẫn cập nhật thuật toán
Nếu bạn cần thay đổi logic trong `solver/bin_packing.py`, hãy đảm bảo:
- Tuân thủ nghiêm ngặt kiểm tra tại hàm `_find_best_position_3d` (xác định tầng, điểm tựa vách, diện tích tiếp xúc).
- Khuyến khích (thưởng điểm) cho việc các khối hàng nêm chặt lại với nhau để giảm khoảng trống (gap penalty).
