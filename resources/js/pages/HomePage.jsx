import React from 'react';
import { Link } from 'react-router-dom';
import {
    Route,
    Package,
    Truck,
    BarChart3,
    ArrowRight,
    CheckCircle,
    Clock,
    ShieldCheck,
    Zap,
    MapPin,
    Users,
} from 'lucide-react';


/* ─── Data ──────────────────────────────────────────────── */
const stats = [
    { value: '30%', label: 'Giảm chi phí vận hành' },
    { value: '2×', label: 'Tăng hiệu suất giao hàng' },
    { value: '<5 phút', label: 'Thời gian tối ưu hóa' },
    { value: '99.9%', label: 'Uptime hệ thống' },
];

const features = [
    {
        icon: Route,
        title: 'Tối ưu tuyến đường đa kỳ',
        description:
            'Thuật toán FMPMD-CVRP-TW tự động gom đơn, chia đơn và lên lịch trình đa ngày. Kết hợp dữ liệu giao thông và thời tiết thực tế.',
    },
    {
        icon: Package,
        title: 'Xếp hàng 3D thông minh',
        description:
            'Tính toán tọa độ xếp hàng LIFO trong thùng xe: hàng nặng dưới đáy, hàng dễ vỡ trên cùng. Render mô hình 3D trực quan.',
    },
    {
        icon: BarChart3,
        title: 'Dashboard realtime',
        description:
            'Theo dõi trạng thái giao hàng theo thời gian thực qua WebSocket. Bản đồ tuyến đường và biểu đồ hiệu suất tích hợp.',
    },
    {
        icon: Truck,
        title: 'Quản lý đội xe toàn diện',
        description:
            'Theo dõi trạng thái, tải trọng, chi phí từng xe. Cảnh báo tự động khi gần vượt tải hay lịch bảo dưỡng.',
    },
    {
        icon: Zap,
        title: 'Tích hợp n8n Automation',
        description:
            'Tự động gửi thông báo qua email/SMS khi đơn hàng thay đổi trạng thái. Không cần code thêm.',
    },
    {
        icon: ShieldCheck,
        title: 'Bảo mật doanh nghiệp',
        description:
            'Xác thực Sanctum, phân quyền theo vai trò, rate limiting. Dữ liệu mã hóa và tuân thủ tiêu chuẩn bảo mật.',
    },
];

const howItWorks = [
    {
        step: '01',
        title: 'Retailer đặt hàng',
        description: 'Tạp hóa / shop duyệt danh mục, chọn sản phẩm và chọn khung giờ nhận hàng phù hợp.',
    },
    {
        step: '02',
        title: 'Carrier xác nhận',
        description: 'Nhà kho xem danh sách đơn hàng, xác nhận và chọn đội xe sẽ thực hiện giao hàng.',
    },
    {
        step: '03',
        title: 'Hệ thống tối ưu hóa',
        description: 'Bấm "Tối ưu hóa" — thuật toán tự động tính lộ trình tốt nhất và sơ đồ xếp hàng 3D.',
    },
    {
        step: '04',
        title: 'Giao hàng & Theo dõi',
        description: 'Tài xế thực hiện theo lộ trình. Carrier và Retailer theo dõi realtime trên dashboard.',
    },
];

const roles = [
    {
        icon: Truck,
        title: 'Dành cho Carrier',
        subtitle: 'Kho hàng & Nhà vận chuyển',
        benefits: [
            'Quản lý đội xe và danh mục hàng hóa',
            'Tối ưu lộ trình với 1 cú bấm',
            'Sơ đồ xếp hàng 3D chi tiết',
            'Dashboard tổng quan hiệu suất',
        ],
        cta: 'Bắt đầu miễn phí',
        href: '/register',
        highlight: true,
    },
    {
        icon: Users,
        title: 'Dành cho Retailer',
        subtitle: 'Tạp hóa & Cửa hàng bán lẻ',
        benefits: [
            'Đặt hàng nhanh qua catalog online',
            'Chọn khung giờ nhận hàng linh hoạt',
            'Theo dõi đơn hàng realtime',
            'Nhận thông báo tự động qua SMS/Email',
        ],
        cta: 'Đăng ký ngay',
        href: '/register',
        highlight: false,
    },
];

/* ─── Section Components ─────────────────────────────────── */

function SectionLabel({ children }) {
    return (
        <span className="inline-block text-xs font-600 uppercase tracking-widest text-blue-700 mb-3">
            {children}
        </span>
    );
}

function SectionHeading({ children }) {
    return (
        <h2 className="text-3xl font-700 text-gray-900 tracking-tight">
            {children}
        </h2>
    );
}

function SectionSubheading({ children }) {
    return (
        <p className="mt-4 text-base text-gray-500 max-w-2xl leading-relaxed">
            {children}
        </p>
    );
}

/* ─── Page ───────────────────────────────────────────────── */

export default function HomePage() {
    return (
        <div className="min-h-screen bg-white">

            {/* ── Hero ─────────────────────────────────────── */}
            <section className="pt-32 pb-20 px-6 lg:px-8">
                <div className="max-w-7xl mx-auto">
                    <div className="max-w-3xl">
                        {/* Badge */}
                        <div className="inline-flex items-center gap-2 px-3 py-1 border border-blue-200 bg-blue-50 rounded-full text-xs font-500 text-blue-700 mb-8">
                            <span className="w-1.5 h-1.5 bg-blue-600 rounded-full"></span>
                            Giải pháp B2B cho chuỗi cung ứng vận tải
                        </div>

                        {/* Heading */}
                        <h1 className="text-5xl lg:text-6xl font-800 text-gray-900 tracking-tight leading-tight">
                            Tối ưu giao hàng,<br />
                            <span className="text-blue-700">tối đa lợi nhuận</span>
                        </h1>

                        <p className="mt-6 text-lg text-gray-500 leading-relaxed max-w-2xl">
                            FLEX-VRP tự động hóa định tuyến giao hàng đa kỳ và tính toán sơ đồ xếp hàng 3D — giúp doanh nghiệp vận tải B2B giảm chi phí, tăng hiệu quả ngay từ ngày đầu tiên.
                        </p>

                        {/* CTAs */}
                        <div className="mt-10 flex flex-wrap items-center gap-4">
                            <Link
                                to="/register"
                                className="inline-flex items-center gap-2 px-6 py-3 bg-blue-700 hover:bg-blue-800 text-white text-sm font-600 rounded-md transition-colors duration-150"
                            >
                                Dùng thử miễn phí
                                <ArrowRight size={16} />
                            </Link>
                            <a
                                href="#how-it-works"
                                className="inline-flex items-center gap-2 px-6 py-3 border border-gray-300 hover:border-gray-400 text-gray-700 text-sm font-500 rounded-md transition-colors duration-150"
                            >
                                Xem cách hoạt động
                            </a>
                        </div>

                        {/* Trust signals */}
                        <div className="mt-10 flex flex-wrap items-center gap-6">
                            {['Không cần thẻ tín dụng', 'Cài đặt trong 5 phút', 'Hỗ trợ 24/7'].map((item) => (
                                <div key={item} className="flex items-center gap-2 text-sm text-gray-500">
                                    <CheckCircle size={14} className="text-blue-600 shrink-0" />
                                    {item}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </section>

            {/* ── Stats ────────────────────────────────────── */}
            <section className="border-y border-gray-200 bg-gray-50">
                <div className="max-w-7xl mx-auto px-6 lg:px-8 py-12">
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
                        {stats.map((stat) => (
                            <div key={stat.value} className="text-center">
                                <p className="text-3xl font-800 text-blue-700">{stat.value}</p>
                                <p className="mt-1 text-sm text-gray-500">{stat.label}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── Features ─────────────────────────────────── */}
            <section id="features" className="py-24 px-6 lg:px-8">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-14">
                        <SectionLabel>Tính năng</SectionLabel>
                        <SectionHeading>Mọi thứ bạn cần để vận hành hiệu quả</SectionHeading>
                        <div className="flex justify-center">
                            <SectionSubheading>
                                Từ tối ưu lộ trình đến theo dõi thời gian thực — FLEX-VRP cung cấp đầy đủ công cụ cho chuỗi cung ứng vận tải B2B.
                            </SectionSubheading>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {features.map((feature) => {
                            const Icon = feature.icon;
                            return (
                                <div
                                    key={feature.title}
                                    className="p-6 border border-gray-200 rounded-lg hover:border-blue-200 hover:bg-blue-50 transition-all duration-200 group"
                                >
                                    <div className="w-9 h-9 flex items-center justify-center bg-blue-100 rounded-md mb-4 group-hover:bg-blue-200 transition-colors">
                                        <Icon size={18} className="text-blue-700" />
                                    </div>
                                    <h3 className="text-base font-600 text-gray-900 mb-2">
                                        {feature.title}
                                    </h3>
                                    <p className="text-sm text-gray-500 leading-relaxed">
                                        {feature.description}
                                    </p>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </section>

            {/* ── How it works ─────────────────────────────── */}
            <section id="how-it-works" className="py-24 px-6 lg:px-8 bg-gray-50 border-y border-gray-200">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-14">
                        <SectionLabel>Quy trình</SectionLabel>
                        <SectionHeading>Hoạt động như thế nào?</SectionHeading>
                        <div className="flex justify-center">
                            <SectionSubheading>
                                Chỉ 4 bước đơn giản từ khi đặt hàng đến khi giao hàng thành công.
                            </SectionSubheading>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                        {howItWorks.map((item, index) => (
                            <div key={item.step} className="relative">
                                <div className="relative z-10">
                                    <div className="text-3xl font-800 text-blue-700 mb-4 inline-block">
                                        {item.step}
                                    </div>
                                    <h3 className="text-base font-600 text-gray-900 mb-2">
                                        {item.title}
                                    </h3>
                                    <p className="text-sm text-gray-500 leading-relaxed pr-4">
                                        {item.description}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── Roles / Solutions ────────────────────────── */}
            <section id="solutions" className="py-24 px-6 lg:px-8">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-14">
                        <SectionLabel>Giải pháp</SectionLabel>
                        <SectionHeading>Phù hợp với từng vai trò</SectionHeading>
                        <div className="flex justify-center">
                            <SectionSubheading>
                                FLEX-VRP được thiết kế riêng cho cả nhà vận chuyển và nhà bán lẻ trong cùng một hệ thống.
                            </SectionSubheading>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
                        {roles.map((role) => {
                            const Icon = role.icon;
                            return (
                                <div
                                    key={role.title}
                                    className={`p-8 rounded-lg border ${
                                        role.highlight
                                            ? 'border-blue-700 bg-blue-700 text-white'
                                            : 'border-gray-200 bg-white'
                                    }`}
                                >
                                    <div className={`w-10 h-10 rounded-md flex items-center justify-center mb-5 ${
                                        role.highlight ? 'bg-blue-600' : 'bg-blue-100'
                                    }`}>
                                        <Icon size={20} className={role.highlight ? 'text-white' : 'text-blue-700'} />
                                    </div>

                                    <p className={`text-xs font-500 uppercase tracking-wider mb-1 ${
                                        role.highlight ? 'text-blue-200' : 'text-blue-700'
                                    }`}>
                                        {role.subtitle}
                                    </p>
                                    <h3 className={`text-xl font-700 mb-5 ${
                                        role.highlight ? 'text-white' : 'text-gray-900'
                                    }`}>
                                        {role.title}
                                    </h3>

                                    <ul className="space-y-3 mb-7">
                                        {role.benefits.map((benefit) => (
                                            <li key={benefit} className="flex items-start gap-2.5">
                                                <CheckCircle
                                                    size={15}
                                                    className={`mt-0.5 shrink-0 ${
                                                        role.highlight ? 'text-blue-300' : 'text-blue-600'
                                                    }`}
                                                />
                                                <span className={`text-sm ${
                                                    role.highlight ? 'text-blue-100' : 'text-gray-600'
                                                }`}>
                                                    {benefit}
                                                </span>
                                            </li>
                                        ))}
                                    </ul>

                                    <Link
                                        to={role.href}
                                        className={`inline-flex items-center gap-2 text-sm font-600 transition-colors ${
                                            role.highlight
                                                ? 'text-white hover:text-blue-200'
                                                : 'text-blue-700 hover:text-blue-800'
                                        }`}
                                    >
                                        {role.cta}
                                        <ArrowRight size={15} />
                                    </Link>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </section>

            {/* ── CTA Banner ───────────────────────────────── */}
            <section id="contact" className="py-20 px-6 lg:px-8 bg-blue-700">
                <div className="max-w-7xl mx-auto text-center">
                    <h2 className="text-3xl font-700 text-white tracking-tight">
                        Sẵn sàng tối ưu hóa vận hành?
                    </h2>
                    <p className="mt-4 text-base text-blue-200 max-w-xl mx-auto">
                        Bắt đầu dùng thử miễn phí ngay hôm nay. Không cần thẻ tín dụng, không cần cam kết dài hạn.
                    </p>
                    <div className="mt-8 flex flex-wrap justify-center gap-4">
                        <Link
                            to="/register"
                            className="inline-flex items-center gap-2 px-6 py-3 bg-white hover:bg-gray-100 text-blue-700 text-sm font-600 rounded-md transition-colors duration-150"
                        >
                            Bắt đầu miễn phí
                            <ArrowRight size={16} />
                        </Link>
                        <a
                            href="mailto:contact@flex-vrp.com"
                            className="inline-flex items-center gap-2 px-6 py-3 border border-blue-500 hover:border-blue-300 text-white text-sm font-500 rounded-md transition-colors duration-150"
                        >
                            Liên hệ tư vấn
                        </a>
                    </div>
                </div>
            </section>

        </div>
    );
}
