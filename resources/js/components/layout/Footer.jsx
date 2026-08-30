import React from 'react';
import { Link } from 'react-router-dom';
import { Truck, Mail, Phone, MapPin, ExternalLink } from 'lucide-react';

const footerLinks = {
    'Sản phẩm': [
        { label: 'Tối ưu tuyến đường', href: '#' },
        { label: 'Xếp hàng 3D', href: '#' },
        { label: 'Quản lý đội xe', href: '#' },
        { label: 'Dashboard realtime', href: '#' },
    ],
    'Doanh nghiệp': [
        { label: 'Về chúng tôi', href: '#about' },
        { label: 'Giải pháp', href: '#solutions' },
        { label: 'Đối tác', href: '#' },
        { label: 'Tuyển dụng', href: '#' },
    ],
    'Hỗ trợ': [
        { label: 'Tài liệu API', href: '#' },
        { label: 'Hướng dẫn sử dụng', href: '#' },
        { label: 'FAQ', href: '#' },
        { label: 'Liên hệ hỗ trợ', href: '#contact' },
    ],
};

export default function Footer() {
    const currentYear = new Date().getFullYear();

    return (
        <footer className="bg-gray-900 text-gray-300">
            {/* Main footer content */}
            <div className="max-w-7xl mx-auto px-6 lg:px-8 py-14">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-10">

                    {/* Brand column */}
                    <div className="lg:col-span-2 space-y-4">
                        <Link to="/" className="flex items-center gap-2.5 w-fit">
                            <div className="flex items-center justify-center w-8 h-8 bg-blue-600 rounded-md">
                                <Truck size={16} className="text-white" />
                            </div>
                            <span className="text-white font-700 text-lg tracking-tight">
                                FLEX<span className="text-blue-400">-VRP</span>
                            </span>
                        </Link>

                        <p className="text-sm text-gray-400 leading-relaxed max-w-xs">
                            Hệ thống tối ưu định tuyến giao hàng và xếp hàng 3D cho doanh nghiệp vận tải B2B. Tiết kiệm chi phí, nâng cao hiệu quả vận hành.
                        </p>

                        {/* Contact info */}
                        <div className="space-y-2 pt-2">
                            <div className="flex items-center gap-2.5 text-sm text-gray-400">
                                <Phone size={14} className="text-blue-400 shrink-0" />
                                <span>+84 28 1234 5678</span>
                            </div>
                            <div className="flex items-center gap-2.5 text-sm text-gray-400">
                                <Mail size={14} className="text-blue-400 shrink-0" />
                                <span>contact@flex-vrp.com</span>
                            </div>
                            <div className="flex items-start gap-2.5 text-sm text-gray-400">
                                <MapPin size={14} className="text-blue-400 shrink-0 mt-0.5" />
                                <span>Quận 7, TP. Hồ Chí Minh, Việt Nam</span>
                            </div>
                        </div>
                    </div>

                    {/* Link columns */}
                    {Object.entries(footerLinks).map(([group, links]) => (
                        <div key={group} className="space-y-4">
                            <h3 className="text-sm font-600 text-white uppercase tracking-wider">
                                {group}
                            </h3>
                            <ul className="space-y-2.5">
                                {links.map((link) => (
                                    <li key={link.label}>
                                        <a
                                            href={link.href}
                                            className="text-sm text-gray-400 hover:text-white transition-colors duration-150"
                                        >
                                            {link.label}
                                        </a>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>
            </div>

            {/* Bottom bar */}
            <div className="border-t border-gray-800">
                <div className="max-w-7xl mx-auto px-6 lg:px-8 py-5 flex flex-col sm:flex-row items-center justify-between gap-3">
                    <p className="text-xs text-gray-500">
                        © {currentYear} FLEX-VRP. Bảo lưu mọi quyền.
                    </p>
                    <div className="flex items-center gap-5">
                        <a href="#" className="text-xs text-gray-500 hover:text-gray-300 transition-colors">
                            Chính sách bảo mật
                        </a>
                        <a href="#" className="text-xs text-gray-500 hover:text-gray-300 transition-colors">
                            Điều khoản sử dụng
                        </a>
                    </div>
                </div>
            </div>
        </footer>
    );
}
