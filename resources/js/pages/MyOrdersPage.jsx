import React, { useState, useEffect } from 'react';
import { Package, Search, Filter, Eye, Clock, CheckCircle, Truck, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

const StatusBadge = ({ status }) => {
    switch (status) {
        case 'pending': return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-500 bg-gray-100 text-gray-700"><Clock size={12} /> Chờ xử lý</span>;
        case 'optimizing': return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-500 bg-purple-100 text-purple-700"><Package size={12} /> Đang tính toán</span>;
        case 'scheduled': return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-500 bg-blue-100 text-blue-700"><Truck size={12} /> Đã lên lịch</span>;
        case 'in_transit': return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-500 bg-yellow-100 text-yellow-700"><Truck size={12} /> Đang giao</span>;
        case 'delivered': return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-500 bg-green-100 text-green-700"><CheckCircle size={12} /> Hoàn thành</span>;
        default: return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-500 bg-gray-100 text-gray-700">{status}</span>;
    }
};

const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    // Fix Safari/iOS issue with date strings containing spaces
    const safeString = dateString.replace(' ', 'T');
    const date = new Date(safeString);
    return isNaN(date.getTime()) ? 'Invalid Date' : date.toLocaleString('vi-VN');
};

export default function MyOrdersPage() {
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('/api/orders')
            .then(res => res.json())
            .then(data => {
                setOrders(data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching orders", err);
                setLoading(false);
            });
    }, []);

    return (
        <div className="bg-gray-50 min-h-[calc(100vh-64px)] py-10 px-4 sm:px-6 lg:px-8">
            <div className="max-w-7xl mx-auto">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
                    <div>
                        <h1 className="text-2xl font-700 text-gray-900">Đơn hàng của tôi</h1>
                        <p className="text-sm text-gray-500 mt-1">Quản lý và theo dõi trạng thái các đơn hàng bạn đã đặt.</p>
                    </div>
                    <Link to="/order" className="inline-flex items-center justify-center gap-2 bg-blue-700 hover:bg-blue-800 text-white font-500 py-2.5 px-5 rounded-md transition-colors text-sm">
                        <Package size={16} />
                        Tạo đơn mới
                    </Link>
                </div>

                <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
                    {/* Toolbar */}
                    <div className="p-4 border-b border-gray-200 flex flex-col sm:flex-row gap-4 justify-between items-center bg-gray-50/50">
                        <div className="relative w-full sm:w-80">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                            <input 
                                type="text" 
                                placeholder="Tìm theo mã đơn, địa chỉ..." 
                                className="w-full pl-10 pr-4 py-2 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none text-sm transition-all"
                            />
                        </div>
                        <button className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-md text-sm font-500 text-gray-700 hover:bg-gray-50 transition-colors w-full sm:w-auto justify-center">
                            <Filter size={16} />
                            Lọc trạng thái
                        </button>
                    </div>

                    {/* Table */}
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-gray-50 border-b border-gray-200 text-xs uppercase tracking-wider text-gray-500 font-600">
                                    <th className="px-6 py-4">Mã đơn</th>
                                    <th className="px-6 py-4">Kho lấy hàng</th>
                                    <th className="px-6 py-4">Chi tiết hàng</th>
                                    <th className="px-6 py-4">Khung giờ nhận</th>
                                    <th className="px-6 py-4">Trạng thái</th>
                                    <th className="px-6 py-4 text-right">Thao tác</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200">
                                {loading ? (
                                    <tr>
                                        <td colSpan="6" className="px-6 py-8 text-center text-gray-500">
                                            Đang tải dữ liệu...
                                        </td>
                                    </tr>
                                ) : orders.length === 0 ? (
                                    <tr>
                                        <td colSpan="6" className="px-6 py-8 text-center text-gray-500">
                                            Bạn chưa có đơn hàng nào.
                                        </td>
                                    </tr>
                                ) : orders.map((order) => (
                                    <tr key={order.id} className="hover:bg-gray-50/50 transition-colors">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-600 text-gray-900">
                                            {order.order_code}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                            <div className="max-w-[200px] truncate" title={order.warehouse?.name}>
                                                {order.warehouse?.name || 'N/A'}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                            {order.items?.length || 0} SP - {order.total_weight_kg} kg
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                            <div className="text-xs">
                                                {formatDate(order.time_window_start)} <br/>
                                                {`-> ${formatDate(order.time_window_end)}`}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <StatusBadge status={order.status} />
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-500">
                                            <button className="inline-flex items-center gap-1.5 text-blue-600 hover:text-blue-800 transition-colors">
                                                <Eye size={16} /> Chi tiết
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    
                    {/* Pagination (Mocked for now) */}
                    <div className="p-4 border-t border-gray-200 flex items-center justify-between text-sm text-gray-500">
                        <div>Hiển thị {orders.length} đơn hàng</div>
                        <div className="flex items-center gap-1">
                            <button className="px-3 py-1 border border-gray-200 rounded text-gray-400 cursor-not-allowed">Trước</button>
                            <button className="px-3 py-1 bg-blue-50 text-blue-700 font-600 border border-blue-200 rounded">1</button>
                            <button className="px-3 py-1 border border-gray-200 rounded text-gray-400 cursor-not-allowed">Sau</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
