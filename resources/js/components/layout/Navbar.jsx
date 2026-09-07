import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, Truck, ChevronDown, User, LogOut, Loader2 } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

export default function Navbar() {
    const { user, logout } = useAuth();
    const [isOpen, setIsOpen] = useState(false);
    const [scrolled, setScrolled] = useState(false);
    const [isProfileOpen, setIsProfileOpen] = useState(false);
    const [isLoggingOut, setIsLoggingOut] = useState(false);
    const dropdownRef = useRef(null);

    // Xử lý click ra ngoài dropdown
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsProfileOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Lọc menu theo role
    const getNavLinks = () => {
        const links = [{ label: 'Trang chủ', href: '/' }];
        
        if (user) {
            links.push({ label: 'Đơn của tôi', href: '/my-orders' });
            links.push({ label: 'Đặt hàng', href: '/order' });
            if (user.role === 'admin' || user.role === 'carrier') {
                links.push({ label: 'Dashboard', href: '/admin-dashboard' });
            }
            
            if (user.role === 'admin' || user.role === 'carrier') {
                links.push({ label: 'Tối ưu lộ trình', href: '/routing' });
            }

            if (user.role === 'carrier') {
                links.push({ label: 'Quản lý Kho', href: '/warehouses-management' });
            }
        }
        return links;
    };

    const activeLinks = getNavLinks();

    useEffect(() => {
        const handleScroll = () => setScrolled(window.scrollY > 16);
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    const handleLogout = async () => {
        setIsProfileOpen(false);
        setIsOpen(false);
        setIsLoggingOut(true);
        try {
            await logout();
        } catch (error) {
            console.error("Logout failed", error);
        } finally {
            setIsLoggingOut(false);
        }
    };

    return (
        <header
            className={`fixed top-0 left-0 right-0 z-50 transition-all duration-200 ${
                scrolled
                    ? 'bg-white border-b border-gray-200 shadow-sm'
                    : 'bg-white border-b border-gray-200'
            }`}
        >
            {/* Loading Overlay for Logout */}
            {isLoggingOut && (
                <div className="fixed inset-0 bg-white/70 backdrop-blur-sm z-[100] flex flex-col items-center justify-center">
                    <Loader2 className="animate-spin text-blue-600 mb-4" size={48} />
                    <p className="text-lg font-600 text-gray-800">Đang đăng xuất...</p>
                </div>
            )}

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
                        {activeLinks.map((link) => (
                            <Link
                                key={link.label}
                                to={link.href}
                                className="text-sm font-500 text-gray-600 hover:text-blue-700 hover:bg-blue-50 px-3 py-2 rounded-md transition-all duration-200"
                            >
                                {link.label}
                            </Link>
                        ))}
                    </nav>

                    {/* Desktop Actions */}
                    <div className="hidden md:flex items-center gap-3">
                        {user ? (
                            <div className="relative" ref={dropdownRef}>
                                <button
                                    onClick={() => setIsProfileOpen(!isProfileOpen)}
                                    className="flex items-center gap-2 text-sm font-500 text-gray-700 hover:text-blue-700 transition-colors duration-150 py-2"
                                >
                                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold">
                                        {user.name.charAt(0).toUpperCase()}
                                    </div>
                                    <span>{user.name}</span>
                                    <ChevronDown size={16} className={`transition-transform duration-200 ${isProfileOpen ? 'rotate-180' : ''}`} />
                                </button>

                                {isProfileOpen && (
                                    <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg py-1 border border-gray-100 z-50">
                                        <Link
                                            to="/profile"
                                            onClick={() => setIsProfileOpen(false)}
                                            className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-blue-700 transition-colors"
                                        >
                                            <User size={16} />
                                            Trang cá nhân
                                        </Link>
                                        <button
                                            onClick={handleLogout}
                                            disabled={isLoggingOut}
                                            className="flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 w-full text-left transition-colors"
                                        >
                                            <LogOut size={16} />
                                            Đăng xuất
                                        </button>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <>
                                <Link
                                    to="/login"
                                    className="text-sm font-500 text-gray-700 hover:text-blue-700 transition-colors duration-150 px-4 py-2"
                                >
                                    Đăng nhập
                                </Link>
                                <Link
                                    to="/register"
                                    className="text-sm font-500 text-white bg-blue-700 hover:bg-blue-800 px-4 py-2 rounded-md transition-all duration-200 hover:-translate-y-0.5 shadow-sm hover:shadow-md"
                                >
                                    Dùng thử miễn phí
                                </Link>
                            </>
                        )}
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
                        {activeLinks.map((link) => (
                            <Link
                                key={link.label}
                                to={link.href}
                                onClick={() => setIsOpen(false)}
                                className="block py-2.5 text-sm font-500 text-gray-700 hover:text-blue-700 transition-colors"
                            >
                                {link.label}
                            </Link>
                        ))}
                        <div className="pt-3 mt-3 border-t border-gray-100 flex flex-col gap-2">
                            {user ? (
                                <>
                                    <Link
                                        to="/profile"
                                        onClick={() => setIsOpen(false)}
                                        className="flex items-center gap-2 text-sm font-500 text-gray-700 py-2.5"
                                    >
                                        <User size={18} />
                                        Trang cá nhân
                                    </Link>
                                    <button
                                        onClick={handleLogout}
                                        disabled={isLoggingOut}
                                        className="flex items-center gap-2 text-sm font-500 text-red-600 py-2.5 text-left"
                                    >
                                        <LogOut size={18} />
                                        Đăng xuất
                                    </button>
                                </>
                            ) : (
                                <>
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
                                </>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </header>
    );
}
