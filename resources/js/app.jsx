import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes as RouterRoutes, Route as RouterRoute } from 'react-router-dom';
import Navbar from './components/layout/Navbar';
import Footer from './components/layout/Footer';
import MainLayout from './components/layout/MainLayout';
import HomePage from './pages/HomePage';
import CreateOrderPage from './pages/CreateOrderPage';
import MyOrdersPage from './pages/MyOrdersPage';
import RoutingOptimizationPage from './pages/RoutingOptimizationPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import '../css/app.css';

function App() {
    return (
        <BrowserRouter>
            <RouterRoutes>
                <RouterRoute element={<MainLayout />}>
                    <RouterRoute path="/" element={<HomePage />} />
                    <RouterRoute path="/order" element={<CreateOrderPage />} />
                    <RouterRoute path="/my-orders" element={<MyOrdersPage />} />
                    <RouterRoute path="/routing" element={<RoutingOptimizationPage />} />
                    <RouterRoute path="/admin-dashboard" element={<AdminDashboardPage />} />
                </RouterRoute>
                <RouterRoute path="/login" element={<LoginPage />} />
                <RouterRoute path="/register" element={<RegisterPage />} />
            </RouterRoutes>
        </BrowserRouter>
    );
}

const rootElement = document.getElementById('root');
if (rootElement) {
    createRoot(rootElement).render(<App />);
}
