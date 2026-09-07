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
import ProfilePage from './pages/ProfilePage';
import WarehouseManagementPage from './pages/WarehouseManagementPage';
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import '../css/app.css';
import './bootstrap';

import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                <RouterRoutes>
                    <RouterRoute element={<MainLayout />}>
                        <RouterRoute path="/" element={<HomePage />} />
                        <RouterRoute path="/order" element={
                            <ProtectedRoute>
                                <CreateOrderPage />
                            </ProtectedRoute>
                        } />
                        <RouterRoute path="/my-orders" element={
                            <ProtectedRoute>
                                <MyOrdersPage />
                            </ProtectedRoute>
                        } />
                        <RouterRoute path="/routing" element={
                            <ProtectedRoute allowedRoles={['admin', 'carrier']}>
                                <RoutingOptimizationPage />
                            </ProtectedRoute>
                        } />
                        <RouterRoute path="/admin-dashboard" element={
                            <ProtectedRoute allowedRoles={['admin', 'carrier']}>
                                <AdminDashboardPage />
                            </ProtectedRoute>
                        } />
                        <RouterRoute path="/warehouses-management" element={
                            <ProtectedRoute allowedRoles={['admin', 'carrier']}>
                                <WarehouseManagementPage />
                            </ProtectedRoute>
                        } />
                        <RouterRoute path="/profile" element={
                            <ProtectedRoute>
                                <ProfilePage />
                            </ProtectedRoute>
                        } />
                    </RouterRoute>
                    <RouterRoute path="/login" element={<LoginPage />} />
                    <RouterRoute path="/register" element={<RegisterPage />} />
                </RouterRoutes>
            </BrowserRouter>
        </AuthProvider>
    );
}

const rootElement = document.getElementById('root');
if (rootElement) {
    createRoot(rootElement).render(<App />);
}
