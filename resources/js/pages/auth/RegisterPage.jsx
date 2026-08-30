import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Truck, ArrowRight, CheckCircle } from 'lucide-react';

export default function RegisterPage() {
    const [formData, setFormData] = useState({
        companyName: '',
        fullName: '',
        email: '',
        password: '',
        confirmPassword: '',
    });

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        // TODO: Xử lý logic đăng ký sau
        if (formData.password !== formData.confirmPassword) {
            alert("Mật khẩu không khớp!");
            return;
        }
        console.log('Register attempt:', formData);
    };

    return (
        <div className="min-h-screen grid grid-cols-1 lg:grid-cols-2 bg-white">
            {/* Cột trái: Form đăng ký */}
            <div className="flex flex-col justify-center px-8 sm:px-16 lg:px-24 py-12">
                <div className="max-w-md w-full mx-auto">
                    {/* Logo */}
                    <div className="mb-8">
                        <Link to="/" className="inline-flex items-center gap-2 group">
                            <div className="bg-blue-700 text-white p-2 rounded-lg group-hover:bg-blue-800 transition-colors">
                                <Truck size={24} />
                            </div>
                            <span className="text-xl font-800 tracking-tight text-gray-900">
                                FLEX<span className="text-blue-700 font-400">-VRP</span>
                            </span>
                        </Link>
                    </div>

                    <div className="mb-8">
                        <h1 className="text-3xl font-700 text-gray-900 mb-2">Tạo tài khoản</h1>
                        <p className="text-gray-500">Bắt đầu dùng thử miễn phí và trải nghiệm sức mạnh của FLEX-VRP.</p>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label className="block text-sm font-500 text-gray-700 mb-1.5" htmlFor="companyName">
                                Tên doanh nghiệp
                            </label>
                            <input
                                id="companyName"
                                name="companyName"
                                type="text"
                                required
                                value={formData.companyName}
                                onChange={handleChange}
                                className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all placeholder-gray-400 text-sm"
                                placeholder="Công ty TNHH Vận Tải XYZ"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-500 text-gray-700 mb-1.5" htmlFor="fullName">
                                Họ và tên
                            </label>
                            <input
                                id="fullName"
                                name="fullName"
                                type="text"
                                required
                                value={formData.fullName}
                                onChange={handleChange}
                                className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all placeholder-gray-400 text-sm"
                                placeholder="Nguyễn Văn A"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-500 text-gray-700 mb-1.5" htmlFor="email">
                                Email doanh nghiệp
                            </label>
                            <input
                                id="email"
                                name="email"
                                type="email"
                                required
                                value={formData.email}
                                onChange={handleChange}
                                className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all placeholder-gray-400 text-sm"
                                placeholder="nguyenvana@congty.com"
                            />
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                            <div>
                                <label className="block text-sm font-500 text-gray-700 mb-1.5" htmlFor="password">
                                    Mật khẩu
                                </label>
                                <input
                                    id="password"
                                    name="password"
                                    type="password"
                                    required
                                    value={formData.password}
                                    onChange={handleChange}
                                    className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all placeholder-gray-400 text-sm"
                                    placeholder="••••••••"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-500 text-gray-700 mb-1.5" htmlFor="confirmPassword">
                                    Xác nhận mật khẩu
                                </label>
                                <input
                                    id="confirmPassword"
                                    name="confirmPassword"
                                    type="password"
                                    required
                                    value={formData.confirmPassword}
                                    onChange={handleChange}
                                    className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all placeholder-gray-400 text-sm"
                                    placeholder="••••••••"
                                />
                            </div>
                        </div>

                        <div className="pt-2">
                            <button
                                type="submit"
                                className="w-full flex items-center justify-center gap-2 bg-blue-700 hover:bg-blue-800 text-white font-500 py-3 px-4 rounded-md transition-colors"
                            >
                                Đăng ký ngay
                                <ArrowRight size={18} />
                            </button>
                        </div>
                        
                        <p className="text-xs text-gray-500 text-center mt-4">
                            Bằng việc đăng ký, bạn đồng ý với <a href="#" className="text-blue-600 hover:underline">Điều khoản dịch vụ</a> và <a href="#" className="text-blue-600 hover:underline">Chính sách bảo mật</a> của chúng tôi.
                        </p>
                    </form>

                    <div className="mt-8 text-center text-sm text-gray-500">
                        Đã có tài khoản?{' '}
                        <Link to="/login" className="font-600 text-blue-600 hover:text-blue-700 transition-colors">
                            Đăng nhập
                        </Link>
                    </div>
                </div>
            </div>

            {/* Cột phải: Banner/Branding (Ẩn trên mobile) */}
            <div className="hidden lg:flex relative bg-blue-700 items-center justify-center overflow-hidden">
                {/* Background Pattern */}
                <div className="absolute inset-0 opacity-10">
                    <svg className="h-full w-full" xmlns="http://www.w3.org/2000/svg">
                        <defs>
                            <pattern id="grid-pattern" width="40" height="40" patternUnits="userSpaceOnUse">
                                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="white" strokeWidth="1" />
                            </pattern>
                        </defs>
                        <rect width="100%" height="100%" fill="url(#grid-pattern)" />
                    </svg>
                </div>
                
                <div className="relative z-10 p-16 max-w-lg">
                    <h2 className="text-4xl font-700 text-white mb-6 leading-tight">
                        Tối ưu hóa hành trình, <br />
                        nâng tầm chuỗi cung ứng.
                    </h2>
                    
                    <ul className="space-y-4">
                        {[
                            'Giảm đến 30% chi phí vận hành',
                            'Tự động hóa định tuyến xe tải đa điểm',
                            'Theo dõi thời gian thực & xuất báo cáo chi tiết'
                        ].map((item, idx) => (
                            <li key={idx} className="flex items-start gap-3 text-blue-100">
                                <CheckCircle className="shrink-0 mt-0.5 text-blue-300" size={20} />
                                <span className="text-lg">{item}</span>
                            </li>
                        ))}
                    </ul>
                    
                    <div className="mt-12 p-6 bg-blue-800/50 backdrop-blur-sm rounded-xl border border-blue-600/30">
                        <p className="text-blue-100 italic">
                            "FLEX-VRP đã giúp chúng tôi tiết kiệm hàng trăm giờ quy hoạch lộ trình mỗi tháng và cải thiện đáng kể sự hài lòng của đối tác B2B."
                        </p>
                        <div className="mt-4 flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-700">
                                HN
                            </div>
                            <div>
                                <div className="text-white font-500 text-sm">Hoàng Nam</div>
                                <div className="text-blue-200 text-xs">Giám đốc vận hành, Logistics Vietnam</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
