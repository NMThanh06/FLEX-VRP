import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, Truck } from 'lucide-react';

const navLinks = [
    { label: 'Trang chủ', href: '/' },
    { label: 'Đơn của tôi', href: '/my-orders' },
    { label: 'Đặt hàng', href: '/order' },
    { label: 'Tối ưu xe', href: '/routing' },
    { label: 'Admin', href: '/admin-dashboard' },
];

export default function Navbar() {
    const [isOpen, setIsOpen] = useState(false);
    const [scrolled, setScrolled] = useState(false);

    useEffect(() => {
        const handleScroll = () => setScrolled(window.scrollY > 16);
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <header
            className={`fixed top-0 left-0 right-0 z-50 transition-all duration-200 ${
                scrolled
                    ? 'bg-white border-b border-gray-200 shadow-sm'
                    : 'bg-white border-b border-gray-200'
            }`}
        >
            <div className="max-w-7xl mx-auto px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">

                    {/* Logo */}
                    <Link to="/" className="flex items-center gap-2.5 shrink-0">
                        <div className="flex items-center justify-center w-8 h-8 bg-blue-700 rounded-md">
                            <Truck size={16} className="text-white" />
                        </div>
                        <span className="text-gray-900 font-700 text-lg tracking-tight">
                            FLEX<span className="text-blue-700">-VRP</span>
                        </span>
                    </Link>

                    {/* Desktop Nav */}
                    <nav className="hidden md:flex items-center gap-8">
                        {navLinks.map((link) => (
                            <a
                                key={link.label}
                                href={link.href}
                                className="text-sm font-500 text-gray-600 hover:text-blue-700 transition-colors duration-150"
                            >
                                {link.label}
                            </a>
                        ))}
                    </nav>

                    {/* Desktop Actions */}
                    <div className="hidden md:flex items-center gap-3">
                        <Link
                            to="/login"
                            className="text-sm font-500 text-gray-700 hover:text-blue-700 transition-colors duration-150 px-4 py-2"
                        >
                            Đăng nhập
                        </Link>
                        <Link
                            to="/register"
                            className="text-sm font-500 text-white bg-blue-700 hover:bg-blue-800 px-4 py-2 rounded-md transition-colors duration-150"
                        >
                            Dùng thử miễn phí
                        </Link>
                    </div>

                    {/* Mobile toggle */}
                    <button
                        onClick={() => setIsOpen(!isOpen)}
                        className="md:hidden p-2 text-gray-500 hover:text-gray-900 transition-colors"
                        aria-label="Toggle menu"
                    >
                        {isOpen ? <X size={20} /> : <Menu size={20} />}
                    </button>
                </div>
            </div>

            {/* Mobile Menu */}
            {isOpen && (
                <div className="md:hidden border-t border-gray-200 bg-white">
                    <div className="max-w-7xl mx-auto px-6 py-4 space-y-1">
                        {navLinks.map((link) => (
                            <a
                                key={link.label}
                                href={link.href}
                                onClick={() => setIsOpen(false)}
                                className="block py-2.5 text-sm font-500 text-gray-700 hover:text-blue-700 transition-colors"
                            >
                                {link.label}
                            </a>
                        ))}
                        <div className="pt-3 mt-3 border-t border-gray-100 flex flex-col gap-2">
                            <Link
                                to="/login"
                                onClick={() => setIsOpen(false)}
                                className="text-sm font-500 text-gray-700 py-2.5"
                            >
                                Đăng nhập
                            </Link>
                            <Link
                                to="/register"
                                onClick={() => setIsOpen(false)}
                                className="text-sm font-500 text-white bg-blue-700 hover:bg-blue-800 px-4 py-2.5 rounded-md text-center transition-colors"
                            >
                                Dùng thử miễn phí
                            </Link>
                        </div>
                    </div>
                </div>
            )}
        </header>
    );
}
