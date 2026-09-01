import React from 'react';
import { Package, Search, Filter, Eye, Clock, CheckCircle, Truck, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

const mockOrders = [
    { id: 'ORD-2026-001', pickup: 'Kho A, Quận 7, TP.HCM', delivery: 'Kho B, Biên Hòa, Đồng Nai', date: '30/08/2026', status: 'pending', items: '120 kg, Hàng tiêu chuẩn' },
    { id: 'ORD-2026-002', pickup: 'Cảng Cát Lái, Thủ Đức', delivery: 'KCN Sóng Thần, Bình Dương', date: '29/08/2026', status: 'routing', items: '450 kg, Hàng cồng kềnh' },
    { id: 'ORD-2026-003', pickup: 'KCN Tân Tạo, Bình Tân', delivery: 'Kho C, Quận 9, TP.HCM', date: '28/08/2026', status: 'delivering', items: '50 kg, Hàng dễ vỡ' },
    { id: 'ORD-2026-004', pickup: 'Sân bay Tân Sơn Nhất', delivery: 'Quận 1, TP.HCM', date: '27/08/2026', status: 'completed', items: '15 kg, Hàng tiêu chuẩn' },
];

const StatusBadge = ({ status }) => {
    switch (status) {
        case 'pending': return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-500 bg-gray-100 text-gray-700"><Clock size={12} /> Chờ xử lý</span>;
        case 'routing': return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-500 bg-purple-100 text-purple-700"><Package size={12} /> Đang lên tuyến</span>;
        case 'delivering': return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-500 bg-blue-100 text-blue-700"><Truck size={12} /> Đang giao</span>;
        case 'completed': return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-500 bg-green-100 text-green-700"><CheckCircle size={12} /> Đã hoàn thành</span>;
        default: return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-500 bg-red-100 text-red-700"><AlertCircle size={12} /> Lỗi</span>;
    }
};

export default function MyOrdersPage() {
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
                                    <th className="px-6 py-4">Điểm lấy hàng</th>
                                    <th className="px-6 py-4">Điểm giao hàng</th>
                                    <th className="px-6 py-4">Thông tin hàng</th>
                                    <th className="px-6 py-4">Ngày yêu cầu</th>
                                    <th className="px-6 py-4">Trạng thái</th>
                                    <th className="px-6 py-4 text-right">Thao tác</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200">
                                {mockOrders.map((order) => (
                                    <tr key={order.id} className="hover:bg-gray-50/50 transition-colors">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-600 text-gray-900">
                                            {order.id}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                            <div className="max-w-[200px] truncate" title={order.pickup}>{order.pickup}</div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                            <div className="max-w-[200px] truncate" title={order.delivery}>{order.delivery}</div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                            {order.items}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                            {order.date}
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
                    
                    {/* Pagination */}
                    <div className="p-4 border-t border-gray-200 flex items-center justify-between text-sm text-gray-500">
                        <div>Hiển thị 1 - 4 của 4 đơn hàng</div>
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
