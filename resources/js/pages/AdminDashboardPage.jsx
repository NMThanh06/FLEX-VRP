import React from 'react';
import { Users, Truck, Package, DollarSign, Activity, TrendingUp, Calendar, AlertCircle, CheckCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

const StatCard = ({ title, value, change, icon: Icon, colorClass }) => (
    <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
        <div className="flex items-start justify-between">
            <div>
                <p className="text-sm font-500 text-gray-500 mb-1">{title}</p>
                <h3 className="text-2xl font-700 text-gray-900">{value}</h3>
            </div>
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorClass}`}>
                <Icon size={20} />
            </div>
        </div>
        <div className="mt-4 flex items-center gap-1 text-sm">
            <TrendingUp size={16} className="text-green-500" />
            <span className="text-green-600 font-500">{change}</span>
            <span className="text-gray-400">so với tháng trước</span>
        </div>
    </div>
);

export default function AdminDashboardPage() {
    return (
        <div className="bg-gray-50 min-h-[calc(100vh-64px)] py-8 px-4 sm:px-6 lg:px-8">
            <div className="max-w-7xl mx-auto">
                
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
                    <div>
                        <h1 className="text-2xl font-700 text-gray-900">Dashboard Tổng quan</h1>
                        <p className="text-sm text-gray-500 mt-1">Xin chào Admin! Dưới đây là hiệu suất hệ thống FLEX-VRP ngày hôm nay.</p>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="bg-white border border-gray-200 px-4 py-2 rounded-md text-sm font-500 text-gray-700 flex items-center gap-2">
                            <Calendar size={16} className="text-gray-400" />
                            30 Tháng 08, 2026
                        </div>
                        <Link to="/routing" className="bg-blue-700 hover:bg-blue-800 text-white px-4 py-2 rounded-md text-sm font-500 transition-colors">
                            Chạy Tối ưu Lộ trình
                        </Link>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                    <StatCard 
                        title="Tổng Đơn hàng" 
                        value="1,284" 
                        change="+12.5%" 
                        icon={Package} 
                        colorClass="bg-blue-100 text-blue-700"
                    />
                    <StatCard 
                        title="Xe đang chạy" 
                        value="45 / 50" 
                        change="+5.2%" 
                        icon={Truck} 
                        colorClass="bg-indigo-100 text-indigo-700"
                    />
                    <StatCard 
                        title="Chi phí tiết kiệm" 
                        value="124.5M" 
                        change="+18.3%" 
                        icon={DollarSign} 
                        colorClass="bg-green-100 text-green-700"
                    />
                    <StatCard 
                        title="Khách hàng B2B" 
                        value="86" 
                        change="+3 mới" 
                        icon={Users} 
                        colorClass="bg-orange-100 text-orange-700"
                    />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    
                    {/* Main Chart Area Placeholder */}
                    <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-lg font-600 text-gray-900">Hiệu suất Giao hàng</h2>
                            <select className="text-sm border border-gray-300 rounded-md px-3 py-1.5 outline-none focus:border-blue-500">
                                <option>7 ngày qua</option>
                                <option>30 ngày qua</option>
                            </select>
                        </div>
                        <div className="h-72 flex items-center justify-center bg-gray-50 border border-dashed border-gray-200 rounded-lg">
                            <div className="text-center">
                                <Activity className="mx-auto text-gray-400 mb-2" size={32} />
                                <p className="text-gray-500 text-sm">Biểu đồ đang được cập nhật</p>
                            </div>
                        </div>
                    </div>

                    {/* Right Column */}
                    <div className="space-y-6">
                        
                        {/* System Health */}
                        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                            <h2 className="text-lg font-600 text-gray-900 mb-4">Trạng thái Hệ thống</h2>
                            <div className="space-y-4">
                                <div>
                                    <div className="flex justify-between text-sm mb-1">
                                        <span className="text-gray-600">Tải Server (CPU)</span>
                                        <span className="font-500 text-gray-900">34%</span>
                                    </div>
                                    <div className="w-full bg-gray-100 rounded-full h-2">
                                        <div className="bg-blue-500 h-2 rounded-full" style={{ width: '34%' }}></div>
                                    </div>
                                </div>
                                <div>
                                    <div className="flex justify-between text-sm mb-1">
                                        <span className="text-gray-600">Memory</span>
                                        <span className="font-500 text-gray-900">62%</span>
                                    </div>
                                    <div className="w-full bg-gray-100 rounded-full h-2">
                                        <div className="bg-blue-500 h-2 rounded-full" style={{ width: '62%' }}></div>
                                    </div>
                                </div>
                                <div className="mt-4 p-3 bg-green-50 text-green-700 rounded-lg flex items-start gap-2 text-sm">
                                    <CheckCircle size={16} className="mt-0.5 shrink-0" />
                                    <span>Hệ thống AI Tối ưu (VRP) đang hoạt động bình thường.</span>
                                </div>
                            </div>
                        </div>

                        {/* Recent Alerts */}
                        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                            <h2 className="text-lg font-600 text-gray-900 mb-4 flex items-center justify-between">
                                Cảnh báo
                                <span className="bg-red-100 text-red-600 text-xs px-2 py-0.5 rounded-full font-600">2</span>
                            </h2>
                            <div className="space-y-3">
                                <div className="flex items-start gap-3 border-b border-gray-100 pb-3">
                                    <div className="w-8 h-8 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center shrink-0 mt-0.5">
                                        <AlertCircle size={16} />
                                    </div>
                                    <div>
                                        <p className="text-sm font-500 text-gray-900">Xe 51D-987.65 trễ giờ</p>
                                        <p className="text-xs text-gray-500">Dự kiến trễ 15p tại Kho B do kẹt xe.</p>
                                    </div>
                                </div>
                                <div className="flex items-start gap-3">
                                    <div className="w-8 h-8 rounded-full bg-red-100 text-red-600 flex items-center justify-center shrink-0 mt-0.5">
                                        <Truck size={16} />
                                    </div>
                                    <div>
                                        <p className="text-sm font-500 text-gray-900">Xe 59C-111.22 cần bảo dưỡng</p>
                                        <p className="text-xs text-gray-500">Đã chạy 10,000km kể từ lần bảo dưỡng trước.</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>

            </div>
        </div>
    );
}
