import React, { useState } from 'react';
import { MapPin, Package, Calendar, Truck, ArrowRight, Info, CheckCircle2 } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function CreateOrderPage() {
    const [formData, setFormData] = useState({
        pickupAddress: '',
        pickupDate: '',
        deliveryAddress: '',
        deliveryDate: '',
        packageType: 'standard',
        weight: '',
        volume: '',
        notes: ''
    });

    const [isSubmitted, setIsSubmitted] = useState(false);

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        // Giả lập call API thành công
        setIsSubmitted(true);
        window.scrollTo(0, 0);
    };

    if (isSubmitted) {
        return (
            <div className="max-w-3xl mx-auto px-6 py-24 text-center">
                <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                    <CheckCircle2 className="text-green-600" size={40} />
                </div>
                <h1 className="text-3xl font-700 text-gray-900 mb-4">Tạo đơn hàng thành công!</h1>
                <p className="text-gray-500 mb-8 max-w-lg mx-auto">
                    Đơn hàng của bạn đã được đưa vào hệ thống và đang chờ Carrier tiếp nhận. Chúng tôi sẽ thông báo qua email khi có tài xế nhận đơn.
                </p>
                <div className="flex justify-center gap-4">
                    <Link to="/" className="px-6 py-3 border border-gray-300 text-gray-700 font-500 rounded-md hover:bg-gray-50 transition-colors">
                        Về trang chủ
                    </Link>
                    <button 
                        onClick={() => setIsSubmitted(false)}
                        className="px-6 py-3 bg-blue-700 text-white font-500 rounded-md hover:bg-blue-800 transition-colors"
                    >
                        Tạo đơn hàng khác
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-gray-50 min-h-[calc(100vh-64px)] py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-7xl mx-auto">
                
                <div className="mb-8">
                    <h1 className="text-3xl font-700 text-gray-900">Tạo đơn hàng vận chuyển</h1>
                    <p className="mt-2 text-sm text-gray-500">Nhập thông tin điểm đi, điểm đến và chi tiết hàng hóa để hệ thống tính toán tối ưu.</p>
                </div>

                <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    
                    {/* Left Column: Form Fields */}
                    <div className="lg:col-span-2 space-y-6">
                        
                        {/* Section: Tuyến đường */}
                        <div className="bg-white p-6 sm:p-8 rounded-xl border border-gray-200 shadow-sm">
                            <h2 className="text-lg font-600 text-gray-900 mb-6 flex items-center gap-2">
                                <MapPin className="text-blue-600" size={20} />
                                Lộ trình vận chuyển
                            </h2>
                            
                            <div className="space-y-6">
                                {/* Điểm lấy hàng */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div>
                                        <label className="block text-sm font-500 text-gray-700 mb-2">Địa chỉ lấy hàng</label>
                                        <input
                                            type="text"
                                            name="pickupAddress"
                                            required
                                            value={formData.pickupAddress}
                                            onChange={handleChange}
                                            placeholder="Ví dụ: Kho A, Quận 7, TP.HCM"
                                            className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all placeholder-gray-400 text-sm"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-500 text-gray-700 mb-2">Ngày lấy hàng (dự kiến)</label>
                                        <input
                                            type="date"
                                            name="pickupDate"
                                            required
                                            value={formData.pickupDate}
                                            onChange={handleChange}
                                            className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all text-sm"
                                        />
                                    </div>
                                </div>

                                <div className="h-px bg-gray-100 my-2"></div>

                                {/* Điểm giao hàng */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div>
                                        <label className="block text-sm font-500 text-gray-700 mb-2">Địa chỉ giao hàng</label>
                                        <input
                                            type="text"
                                            name="deliveryAddress"
                                            required
                                            value={formData.deliveryAddress}
                                            onChange={handleChange}
                                            placeholder="Ví dụ: Kho B, Biên Hòa, Đồng Nai"
                                            className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all placeholder-gray-400 text-sm"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-500 text-gray-700 mb-2">Ngày giao hàng (yêu cầu)</label>
                                        <input
                                            type="date"
                                            name="deliveryDate"
                                            required
                                            value={formData.deliveryDate}
                                            onChange={handleChange}
                                            className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all text-sm"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Section: Hàng hóa */}
                        <div className="bg-white p-6 sm:p-8 rounded-xl border border-gray-200 shadow-sm">
                            <h2 className="text-lg font-600 text-gray-900 mb-6 flex items-center gap-2">
                                <Package className="text-blue-600" size={20} />
                                Chi tiết hàng hóa
                            </h2>
                            
                            <div className="space-y-6">
                                <div>
                                    <label className="block text-sm font-500 text-gray-700 mb-2">Loại hàng hóa</label>
                                    <select 
                                        name="packageType"
                                        value={formData.packageType}
                                        onChange={handleChange}
                                        className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all text-sm bg-white"
                                    >
                                        <option value="standard">Hàng tiêu chuẩn (Đóng thùng)</option>
                                        <option value="fragile">Hàng dễ vỡ</option>
                                        <option value="cold">Hàng đông lạnh</option>
                                        <option value="oversized">Hàng cồng kềnh</option>
                                    </select>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div>
                                        <label className="block text-sm font-500 text-gray-700 mb-2">
                                            Tổng trọng lượng (kg)
                                        </label>
                                        <input
                                            type="number"
                                            name="weight"
                                            min="0"
                                            step="0.1"
                                            required
                                            value={formData.weight}
                                            onChange={handleChange}
                                            placeholder="0.0"
                                            className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all placeholder-gray-400 text-sm"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-500 text-gray-700 mb-2">
                                            Thể tích ước tính (m³)
                                        </label>
                                        <input
                                            type="number"
                                            name="volume"
                                            min="0"
                                            step="0.01"
                                            required
                                            value={formData.volume}
                                            onChange={handleChange}
                                            placeholder="0.00"
                                            className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all placeholder-gray-400 text-sm"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-500 text-gray-700 mb-2">Ghi chú cho tài xế</label>
                                    <textarea
                                        name="notes"
                                        rows="3"
                                        value={formData.notes}
                                        onChange={handleChange}
                                        placeholder="Ghi chú thêm về bốc xếp, lưu ý khi vận chuyển..."
                                        className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all placeholder-gray-400 text-sm resize-y"
                                    ></textarea>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Right Column: Order Summary & Actions */}
                    <div className="lg:col-span-1">
                        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm sticky top-24">
                            <h2 className="text-lg font-600 text-gray-900 mb-4">Tóm tắt đơn hàng</h2>
                            
                            <div className="space-y-4 mb-6">
                                <div className="flex justify-between items-center text-sm">
                                    <span className="text-gray-500">Phí vận chuyển cơ bản</span>
                                    <span className="font-500 text-gray-900">Đang tính toán...</span>
                                </div>
                                <div className="flex justify-between items-center text-sm">
                                    <span className="text-gray-500">Phụ phí (loại hàng)</span>
                                    <span className="font-500 text-gray-900">--</span>
                                </div>
                                <div className="h-px bg-gray-100"></div>
                                <div className="flex justify-between items-center">
                                    <span className="font-600 text-gray-900">Tổng chi phí (dự kiến)</span>
                                    <span className="font-700 text-blue-700 text-lg">Hệ thống báo giá</span>
                                </div>
                            </div>

                            <div className="bg-blue-50 p-4 rounded-lg flex items-start gap-3 mb-6">
                                <Info className="text-blue-600 shrink-0 mt-0.5" size={18} />
                                <p className="text-xs text-blue-800 leading-relaxed">
                                    Đơn hàng của bạn sẽ được thuật toán <strong>FMPMD-CVRP-TW</strong> tự động đưa vào lộ trình tối ưu nhất để có mức giá tốt nhất.
                                </p>
                            </div>

                            <button
                                type="submit"
                                className="w-full flex items-center justify-center gap-2 bg-blue-700 hover:bg-blue-800 text-white font-600 py-3.5 px-4 rounded-md transition-colors"
                            >
                                Đặt xe ngay
                                <Truck size={18} />
                            </button>
                        </div>
                    </div>

                </form>
            </div>
        </div>
    );
}
