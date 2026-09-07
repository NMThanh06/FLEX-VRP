import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Truck, ArrowRight, CheckCircle, Loader2 } from 'lucide-react';

export default function LoginPage() {
    const { login } = useAuth();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const [formData, setFormData] = useState({
        email: '',
        password: '',
    });

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            await login(formData.email, formData.password);
            navigate('/');
        } catch (err) {
            setError(err.response?.data?.message || 'Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen grid grid-cols-1 lg:grid-cols-2 bg-white">
            {/* Cột trái: Form đăng nhập */}
            <div className="flex flex-col justify-center px-8 sm:px-16 lg:px-24 py-12">
                <div className="max-w-md w-full mx-auto">
                    {/* Logo */}
                    <div className="mb-10">
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
                        <h1 className="text-3xl font-700 text-gray-900 mb-2">Đăng nhập</h1>
                        <p className="text-gray-500">Chào mừng trở lại! Vui lòng nhập thông tin để tiếp tục.</p>
                    </div>

                    {error && (
                        <div className="mb-6 p-4 rounded-lg bg-red-50 text-red-700 text-sm border border-red-200">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div>
                            <label className="block text-sm font-500 text-gray-700 mb-2" htmlFor="email">
                                Email doanh nghiệp
                            </label>
                            <input
                                id="email"
                                name="email"
                                type="email"
                                required
                                value={formData.email}
                                onChange={handleChange}
                                className="w-full px-4 py-3 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all placeholder-gray-400 text-sm"
                                placeholder="nguyenvana@congty.com"
                            />
                        </div>

                        <div>
                            <div className="flex items-center justify-between mb-2">
                                <label className="block text-sm font-500 text-gray-700" htmlFor="password">
                                    Mật khẩu
                                </label>
                                <a href="#" className="text-sm font-500 text-blue-600 hover:text-blue-700">
                                    Quên mật khẩu?
                                </a>
                            </div>
                            <input
                                id="password"
                                name="password"
                                type="password"
                                required
                                value={formData.password}
                                onChange={handleChange}
                                className="w-full px-4 py-3 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all placeholder-gray-400 text-sm"
                                placeholder="••••••••"
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full flex items-center justify-center gap-2 bg-blue-700 hover:bg-blue-800 text-white font-500 py-3 px-4 rounded-md transition-all duration-200 hover:-translate-y-0.5 shadow-sm hover:shadow-md disabled:opacity-70 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-sm"
                        >
                            {loading ? (
                                <>
                                    <Loader2 size={18} className="animate-spin" />
                                    Đang xử lý...
                                </>
                            ) : (
                                <>
                                    Đăng nhập
                                    <ArrowRight size={18} />
                                </>
                            )}
                        </button>
                    </form>

                    <div className="mt-8 text-center text-sm text-gray-500">
                        Chưa có tài khoản?{' '}
                        <Link to="/register" className="font-600 text-blue-600 hover:text-blue-700 transition-colors">
                            Đăng ký ngay
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
                    

                </div>
            </div>
        </div>
    );
}
