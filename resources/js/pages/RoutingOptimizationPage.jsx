import React, { useState } from 'react';
import { Truck, Map, Settings, Play, CheckCircle, Package, ArrowRight, Activity, MapPin } from 'lucide-react';

const mockRoutes = [
    {
        vehicle: 'Xe tải 1.5 tấn (59C-123.45)',
        driver: 'Nguyễn Văn A',
        utilization: '85%',
        stops: 4,
        distance: '45 km',
        cost: '450,000 VND',
        path: [
            'Kho Tổng (Quận 7)',
            'Đại lý A (Quận 4)',
            'Đại lý B (Quận 1)',
            'CH Tiện lợi C (Bình Thạnh)',
            'Kho Tổng (Quận 7)'
        ]
    },
    {
        vehicle: 'Xe tải 2.5 tấn (51D-987.65)',
        driver: 'Trần Văn B',
        utilization: '92%',
        stops: 5,
        distance: '62 km',
        cost: '620,000 VND',
        path: [
            'Kho Tổng (Quận 7)',
            'Siêu thị D (Quận 2)',
            'Kho E (Quận 9)',
            'Đại lý F (Thủ Đức)',
            'Kho Tổng (Quận 7)'
        ]
    }
];

export default function RoutingOptimizationPage() {
    const [isOptimizing, setIsOptimizing] = useState(false);
    const [showResults, setShowResults] = useState(false);
    const [vehicles, setVehicles] = useState([
        { id: 1, type: 'Xe tải 1.5 tấn', count: 2, capacity: '1500kg' },
        { id: 2, type: 'Xe tải 2.5 tấn', count: 1, capacity: '2500kg' },
    ]);

    const handleOptimize = () => {
        setIsOptimizing(true);
        setShowResults(false);
        // Giả lập delay tính toán VRP
        setTimeout(() => {
            setIsOptimizing(false);
            setShowResults(true);
        }, 2000);
    };

    return (
        <div className="bg-gray-50 min-h-[calc(100vh-64px)] py-8 px-4 sm:px-6 lg:px-8">
            <div className="max-w-7xl mx-auto">
                <div className="mb-6">
                    <h1 className="text-2xl font-700 text-gray-900">Tối ưu hóa Lộ trình (VRP)</h1>
                    <p className="text-sm text-gray-500 mt-1">Tính toán đường đi ngắn nhất, phân bổ đơn hàng tự động cho đội xe hiện có.</p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    
                    {/* Left Column: Settings & Inputs */}
                    <div className="lg:col-span-1 space-y-6">
                        
                        {/* Đơn hàng chờ xử lý */}
                        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-base font-600 text-gray-900 flex items-center gap-2">
                                    <Package className="text-blue-600" size={18} />
                                    Đơn hàng chờ xếp xe
                                </h2>
                                <span className="bg-blue-100 text-blue-700 text-xs font-600 px-2.5 py-1 rounded-full">
                                    24 đơn
                                </span>
                            </div>
                            <p className="text-sm text-gray-500 mb-4">
                                Tổng khối lượng: <strong>4,250 kg</strong><br/>
                                Khu vực: TP.HCM, Đồng Nai, Bình Dương
                            </p>
                            <button className="w-full text-sm font-500 text-blue-600 border border-blue-200 bg-blue-50 hover:bg-blue-100 py-2 rounded-md transition-colors">
                                Xem danh sách đơn
                            </button>
                        </div>

                        {/* Thông tin đội xe */}
                        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-base font-600 text-gray-900 flex items-center gap-2">
                                    <Truck className="text-blue-600" size={18} />
                                    Đội xe sẵn sàng
                                </h2>
                                <button className="text-blue-600 hover:text-blue-800 text-sm font-500">
                                    + Thêm loại xe
                                </button>
                            </div>
                            
                            <div className="space-y-3 mb-6">
                                {vehicles.map((v) => (
                                    <div key={v.id} className="flex items-center justify-between p-3 border border-gray-100 bg-gray-50 rounded-lg">
                                        <div>
                                            <div className="text-sm font-600 text-gray-900">{v.type}</div>
                                            <div className="text-xs text-gray-500">Tải trọng: {v.capacity}</div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm text-gray-600">Số lượng:</span>
                                            <input 
                                                type="number" 
                                                defaultValue={v.count}
                                                className="w-16 px-2 py-1 text-center border border-gray-300 rounded-md text-sm outline-none focus:border-blue-500"
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Cấu hình nâng cao */}
                            <div className="mb-6">
                                <h3 className="text-sm font-600 text-gray-900 mb-3 flex items-center gap-2">
                                    <Settings size={16} className="text-gray-500" />
                                    Cấu hình thuật toán
                                </h3>
                                <div className="space-y-2">
                                    <label className="flex items-center gap-2 text-sm text-gray-700">
                                        <input type="checkbox" defaultChecked className="rounded text-blue-600 focus:ring-blue-500" />
                                        Ưu tiên giảm thiểu khoảng cách
                                    </label>
                                    <label className="flex items-center gap-2 text-sm text-gray-700">
                                        <input type="checkbox" defaultChecked className="rounded text-blue-600 focus:ring-blue-500" />
                                        Tuân thủ khung giờ giao hàng (Time Windows)
                                    </label>
                                    <label className="flex items-center gap-2 text-sm text-gray-700">
                                        <input type="checkbox" defaultChecked className="rounded text-blue-600 focus:ring-blue-500" />
                                        Cân bằng tải trọng giữa các xe
                                    </label>
                                </div>
                            </div>

                            <button 
                                onClick={handleOptimize}
                                disabled={isOptimizing}
                                className={`w-full flex items-center justify-center gap-2 font-600 py-3 px-4 rounded-md transition-colors ${
                                    isOptimizing 
                                    ? 'bg-blue-400 text-white cursor-not-allowed' 
                                    : 'bg-blue-700 hover:bg-blue-800 text-white'
                                }`}
                            >
                                {isOptimizing ? (
                                    <>
                                        <Activity className="animate-pulse" size={20} />
                                        Đang tính toán ma trận...
                                    </>
                                ) : (
                                    <>
                                        <Play size={18} fill="currentColor" />
                                        Chạy mô hình Tối ưu
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    {/* Right Column: Map & Results */}
                    <div className="lg:col-span-2 space-y-6">
                        
                        {/* Map Placeholder */}
                        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden h-[400px] relative flex items-center justify-center bg-gray-100">
                            <div className="absolute inset-0 opacity-20 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]"></div>
                            {!showResults ? (
                                <div className="text-center relative z-10">
                                    <Map className="mx-auto text-gray-400 mb-3" size={48} />
                                    <p className="text-gray-500">Bản đồ tuyến đường sẽ hiển thị tại đây <br/>sau khi thuật toán chạy xong.</p>
                                </div>
                            ) : (
                                <div className="text-center relative z-10 w-full h-full bg-blue-50/80 flex flex-col items-center justify-center">
                                    {/* Mock Map View */}
                                    <Map className="mx-auto text-blue-600 mb-3" size={48} />
                                    <p className="text-blue-800 font-600 text-lg">Đã render bản đồ 2 tuyến đường</p>
                                    <p className="text-blue-600 text-sm">Hiển thị đường đi thực tế của các xe trên Google Maps</p>
                                </div>
                            )}
                        </div>

                        {/* Routing Results */}
                        {showResults && (
                            <div className="bg-white rounded-xl border border-green-200 shadow-sm overflow-hidden">
                                <div className="bg-green-50 p-4 border-b border-green-200 flex items-center justify-between">
                                    <div className="flex items-center gap-2 text-green-800">
                                        <CheckCircle size={20} className="text-green-600" />
                                        <h2 className="font-600">Tối ưu hóa thành công</h2>
                                    </div>
                                    <div className="text-sm font-500 text-green-700">
                                        Thời gian giải: 1.8s
                                    </div>
                                </div>
                                <div className="p-0">
                                    {mockRoutes.map((route, idx) => (
                                        <div key={idx} className="border-b border-gray-100 last:border-0 p-5">
                                            <div className="flex justify-between items-start mb-4">
                                                <div>
                                                    <h3 className="text-base font-700 text-gray-900 flex items-center gap-2">
                                                        <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs">#{idx + 1}</span>
                                                        {route.vehicle}
                                                    </h3>
                                                    <p className="text-sm text-gray-500 mt-1">Tài xế: {route.driver}</p>
                                                </div>
                                                <div className="text-right">
                                                    <div className="text-sm font-600 text-gray-900">{route.distance}</div>
                                                    <div className="text-xs text-gray-500">Chi phí: {route.cost}</div>
                                                </div>
                                            </div>

                                            <div className="bg-gray-50 rounded-lg p-4">
                                                <div className="flex items-center justify-between text-xs font-500 text-gray-500 mb-3">
                                                    <span>Tỷ lệ lấp đầy: <span className="text-blue-600 font-700">{route.utilization}</span></span>
                                                    <span>Số điểm dừng: {route.stops}</span>
                                                </div>
                                                
                                                {/* Route visualization */}
                                                <div className="flex flex-wrap items-center gap-2 text-sm">
                                                    {route.path.map((stop, i) => (
                                                        <React.Fragment key={i}>
                                                            <div className="flex items-center gap-1.5 text-gray-700 font-500">
                                                                <MapPin size={14} className={i === 0 || i === route.path.length - 1 ? 'text-blue-600' : 'text-gray-400'} />
                                                                {stop}
                                                            </div>
                                                            {i < route.path.length - 1 && (
                                                                <ArrowRight size={14} className="text-gray-300" />
                                                            )}
                                                        </React.Fragment>
                                                    ))}
                                                </div>
                                            </div>
                                            
                                            <div className="mt-4 flex justify-end">
                                                <button className="text-sm font-500 text-blue-600 hover:text-blue-800">
                                                    Chi tiết lộ trình & Xếp hàng 3D &rarr;
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
