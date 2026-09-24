# TODO: Kế Hoạch Phát Triển Hệ Thống (Next Phase)

Dưới đây là chi tiết các hạng mục công việc cần triển khai tiếp theo, được chia theo từng phần cụ thể:

## 1. Giao diện (Frontend & Mobile)
- [ ] **Thống kê AI (AI Dashboard):**
  - Xây dựng bảng điều khiển theo dõi công việc của AI (AI agent).
  - Thống kê tỷ lệ tính toán đúng/sai hoặc các cảnh báo.
  - Hiển thị chi tiết các quyết định (decision-making) của AI trong quá trình lập kế hoạch tuyến đường.
- [ ] **Module Nhập Liệu (Data Import):**
  - Giao diện nhập đơn hàng hàng loạt (upload file CSV/Excel các đơn cần giao).
  - Giao diện nhập và quản lý địa chỉ kho bãi (Warehouse).
  - Giao diện nhập và quản lý thông tin xe tải (Vehicle).
- [ ] **Giao diện Tài xế (Mobile Driver App):**
  - Thiết kế màn hình responsive/mobile cho tài xế.
  - Hiển thị danh sách việc cần làm (to-do list lộ trình).
  - Cung cấp các thông tin đã được tính toán và lên kế hoạch sẵn (thứ tự giao, bản đồ, thông tin đơn hàng).
- [ ] **Tùy chỉnh UI/UX:**
  - Điều chỉnh lại tông màu giao diện toàn hệ thống cho phù hợp, hiện đại và chuyên nghiệp hơn.

## 2. Hệ thống (Backend)
- [ ] **Chatbot:**
  - Fix lỗi và nâng cấp Chatbot để tra cứu đơn hàng chính xác và thông minh hơn.
- [ ] **Quản lý Tài xế (Driver Management):**
  - Quản lý danh sách và hồ sơ tài xế.
  - Cập nhật thuật toán: Đánh giá và lưu trữ **mức độ quen thuộc của tài xế trên mỗi tuyến đường** (sử dụng thông số này làm một trọng số trong thuật toán chia chuyến sau này).

## 3. Data & Thuật toán
- [ ] **Phân tích dữ liệu chạy thực tế (Proof of Value):**
  - Tìm kiếm và sử dụng tập dữ liệu vận tải gần đây (data thực tế).
  - Chạy mô phỏng (backtesting) và xuất báo cáo chứng minh hệ thống này giúp tối ưu hóa những gì (tiết kiệm bao nhiêu % quãng đường, thời gian, chi phí) so với cách chạy cũ.
- [ ] **Tích hợp Vietmap & Ràng buộc giao thông:**
  - Tích hợp Vietmap API để lấy dữ liệu đường đi (routing) chính xác tại Việt Nam.
  - Bổ sung hệ thống **cấm đường theo khung giờ** (tương tự dịch vụ đọc biển báo tự động) vào ràng buộc của thuật toán VRP (không cho phép xe đi vào các đường cấm tải/cấm giờ ở các khung giờ nhất định).
