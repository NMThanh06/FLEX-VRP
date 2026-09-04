import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Plus, Edit2, Trash2, MapPin, Package, AlertCircle, X, Check } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const Modal = ({ isOpen, onClose, title, children }) => {
    if (!isOpen) return null;
    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between p-6 border-b border-gray-100 sticky top-0 bg-white z-10">
                    <h3 className="text-xl font-600 text-gray-900">{title}</h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                        <X size={24} />
                    </button>
                </div>
                <div className="p-6">
                    {children}
                </div>
            </div>
        </div>
    );
};

export default function WarehouseManagementPage() {
    const { user } = useAuth();
    
    // States
    const [warehouses, setWarehouses] = useState([]);
    const [selectedWarehouseId, setSelectedWarehouseId] = useState(null);
    const [products, setProducts] = useState([]);
    
    const [loadingWarehouses, setLoadingWarehouses] = useState(true);
    const [loadingProducts, setLoadingProducts] = useState(false);

    // Modals state
    const [isWarehouseModalOpen, setWarehouseModalOpen] = useState(false);
    const [isProductModalOpen, setProductModalOpen] = useState(false);
    const [editingWarehouse, setEditingWarehouse] = useState(null);
    const [editingProduct, setEditingProduct] = useState(null);

    // Forms
    const [warehouseForm, setWarehouseForm] = useState({ name: '', address: '', contact_phone: '', latitude: '', longitude: '' });
    const [productForm, setProductForm] = useState({ sku: '', name: '', description: '', price: '', weight_kg: '', length_cm: '', width_cm: '', height_cm: '', is_heavy: false, is_fragile: false, stock_quantity: '' });

    // Fetch Warehouses
    const fetchWarehouses = async () => {
        setLoadingWarehouses(true);
        try {
            const res = await axios.get('/api/management/warehouses');
            setWarehouses(res.data);
            if (res.data.length > 0 && !selectedWarehouseId) {
                setSelectedWarehouseId(res.data[0].id);
            }
        } catch (error) {
            console.error("Error fetching warehouses", error);
        } finally {
            setLoadingWarehouses(false);
        }
    };

    useEffect(() => {
        fetchWarehouses();
    }, []);

    // Fetch Products when warehouse changes
    useEffect(() => {
        let isMounted = true;
        if (selectedWarehouseId) {
            setLoadingProducts(true);
            axios.get(`/api/management/products?warehouse_id=${selectedWarehouseId}`)
                .then(res => {
                    if (isMounted) {
                        setProducts(res.data);
                        setLoadingProducts(false);
                    }
                })
                .catch(err => {
                    if (isMounted) {
                        console.error("Error fetching products", err);
                        setLoadingProducts(false);
                    }
                });
        }
        return () => { isMounted = false; };
    }, [selectedWarehouseId]);


    // ==========================================
    // WAREHOUSE ACTIONS
    // ==========================================
    const openWarehouseModal = (warehouse = null) => {
        if (warehouse) {
            setEditingWarehouse(warehouse);
            setWarehouseForm({
                name: warehouse.name,
                address: warehouse.address,
                contact_phone: warehouse.contact_phone || '',
                latitude: warehouse.latitude || '',
                longitude: warehouse.longitude || ''
            });
        } else {
            setEditingWarehouse(null);
            setWarehouseForm({ name: '', address: '', contact_phone: '', latitude: '', longitude: '' });
        }
        setWarehouseModalOpen(true);
    };

    const handleWarehouseSubmit = async (e) => {
        e.preventDefault();
        try {
            if (editingWarehouse) {
                await axios.put(`/api/management/warehouses/${editingWarehouse.id}`, warehouseForm);
            } else {
                await axios.post('/api/management/warehouses', warehouseForm);
            }
            setWarehouseModalOpen(false);
            fetchWarehouses();
        } catch (error) {
            alert("Lỗi lưu kho: " + (error.response?.data?.message || "Lỗi không xác định"));
        }
    };

    const deleteWarehouse = async (warehouse) => {
        if (!window.confirm(`Bạn có chắc chắn muốn xóa kho "${warehouse.name}"? Mọi sản phẩm trong kho này cũng sẽ bị xóa!`)) return;
        try {
            await axios.delete(`/api/management/warehouses/${warehouse.id}`);
            if (selectedWarehouseId === warehouse.id) setSelectedWarehouseId(null);
            fetchWarehouses();
        } catch (error) {
            alert("Không thể xóa kho: " + (error.response?.data?.message || "Lỗi không xác định"));
        }
    };


    // ==========================================
    // PRODUCT ACTIONS
    // ==========================================
    const openProductModal = (product = null) => {
        if (product) {
            setEditingProduct(product);
            setProductForm({
                sku: product.sku,
                name: product.name,
                description: product.description || '',
                price: product.price,
                weight_kg: product.weight_kg,
                length_cm: product.length_cm,
                width_cm: product.width_cm,
                height_cm: product.height_cm,
                is_heavy: product.is_heavy,
                is_fragile: product.is_fragile,
                stock_quantity: product.stock_quantity
            });
        } else {
            setEditingProduct(null);
            setProductForm({ sku: '', name: '', description: '', price: '', weight_kg: '', length_cm: '', width_cm: '', height_cm: '', is_heavy: false, is_fragile: false, stock_quantity: '' });
        }
        setProductModalOpen(true);
    };

    const handleProductSubmit = async (e) => {
        e.preventDefault();
        try {
            const payload = { ...productForm, warehouse_id: selectedWarehouseId };
            if (editingProduct) {
                await axios.put(`/api/management/products/${editingProduct.id}`, payload);
            } else {
                await axios.post('/api/management/products', payload);
            }
            setProductModalOpen(false);
            // Refresh products
            setLoadingProducts(true);
            const res = await axios.get(`/api/management/products?warehouse_id=${selectedWarehouseId}`);
            setProducts(res.data);
            setLoadingProducts(false);
        } catch (error) {
            alert("Lỗi lưu sản phẩm: " + (error.response?.data?.message || "Lỗi không xác định"));
        }
    };

    const deleteProduct = async (product) => {
        if (!window.confirm(`Bạn có chắc chắn muốn xóa sản phẩm "${product.name}"?`)) return;
        try {
            await axios.delete(`/api/management/products/${product.id}`);
            setProducts(products.filter(p => p.id !== product.id));
        } catch (error) {
            alert("Lỗi xóa sản phẩm: " + (error.response?.data?.message || "Lỗi không xác định"));
        }
    };


    // ==========================================
    // RENDER
    // ==========================================
    return (
        <div className="bg-gray-50 min-h-[calc(100vh-64px)] py-8 px-4 sm:px-6 lg:px-8">
            <div className="max-w-7xl mx-auto">
                <div className="mb-8 flex justify-between items-end">
                    <div>
                        <h1 className="text-2xl font-700 text-gray-900">Quản lý Kho & Sản phẩm</h1>
                        <p className="text-sm text-gray-500 mt-1">Thêm, sửa, xóa các điểm tập kết hàng hóa và danh mục sản phẩm.</p>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    {/* WAREHOUSE LIST (Left Col) */}
                    <div className="lg:col-span-4 space-y-4">
                        <div className="flex items-center justify-between mb-2">
                            <h2 className="text-lg font-600 text-gray-900 flex items-center gap-2">
                                <MapPin size={20} className="text-blue-600" />
                                Danh sách Kho
                            </h2>
                            <button 
                                onClick={() => openWarehouseModal()}
                                className="text-sm bg-blue-100 text-blue-700 px-3 py-1.5 rounded-md font-500 hover:bg-blue-200 flex items-center gap-1"
                            >
                                <Plus size={16} /> Thêm kho
                            </button>
                        </div>

                        {loadingWarehouses ? (
                            <div className="p-8 text-center text-gray-500">Đang tải kho hàng...</div>
                        ) : warehouses.length === 0 ? (
                            <div className="p-8 text-center bg-white border border-dashed border-gray-300 rounded-xl text-gray-500">
                                Chưa có kho hàng nào
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {warehouses.map(w => (
                                    <div 
                                        key={w.id} 
                                        className={`p-4 rounded-xl border transition-all cursor-pointer ${
                                            selectedWarehouseId === w.id 
                                                ? 'bg-blue-50 border-blue-300 shadow-sm' 
                                                : 'bg-white border-gray-200 hover:border-blue-200'
                                        }`}
                                        onClick={() => setSelectedWarehouseId(w.id)}
                                    >
                                        <div className="flex justify-between items-start mb-2">
                                            <h3 className="font-600 text-gray-900">{w.name}</h3>
                                            <div className="flex gap-1" onClick={e => e.stopPropagation()}>
                                                <button onClick={() => openWarehouseModal(w)} className="p-1.5 text-gray-400 hover:text-blue-600 rounded bg-white hover:bg-blue-50">
                                                    <Edit2 size={14} />
                                                </button>
                                                <button onClick={() => deleteWarehouse(w)} className="p-1.5 text-gray-400 hover:text-red-600 rounded bg-white hover:bg-red-50">
                                                    <Trash2 size={14} />
                                                </button>
                                            </div>
                                        </div>
                                        <p className="text-xs text-gray-500 mb-2 line-clamp-2">{w.address}</p>
                                        <div className="flex items-center justify-between text-xs font-500">
                                            <span className="text-blue-700 bg-blue-100/50 px-2 py-0.5 rounded">{w.orders_count || 0} đơn hàng</span>
                                            <span className={w.is_active ? 'text-green-600' : 'text-red-500'}>{w.is_active ? 'Hoạt động' : 'Tạm khóa'}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* PRODUCT LIST (Right Col) */}
                    <div className="lg:col-span-8">
                        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 min-h-[500px]">
                            {selectedWarehouseId ? (
                                <>
                                    <div className="flex items-center justify-between mb-6 pb-4 border-b border-gray-100">
                                        <div>
                                            <h2 className="text-lg font-600 text-gray-900 flex items-center gap-2">
                                                <Package size={20} className="text-blue-600" />
                                                Sản phẩm thuộc kho
                                            </h2>
                                            <p className="text-sm text-gray-500">{warehouses.find(w=>w.id === selectedWarehouseId)?.name}</p>
                                        </div>
                                        <button 
                                            onClick={() => openProductModal()}
                                            className="text-sm bg-blue-700 text-white px-4 py-2 rounded-md font-500 hover:bg-blue-800 flex items-center gap-2"
                                        >
                                            <Plus size={16} /> Thêm sản phẩm
                                        </button>
                                    </div>

                                    {loadingProducts ? (
                                        <div className="py-12 text-center text-gray-500">Đang tải danh mục sản phẩm...</div>
                                    ) : products.length === 0 ? (
                                        <div className="py-16 flex flex-col items-center justify-center text-gray-500 border border-dashed border-gray-200 rounded-lg bg-gray-50">
                                            <Package size={48} className="text-gray-300 mb-3" />
                                            <p>Kho này chưa có sản phẩm nào.</p>
                                            <p className="text-sm">Bấm "Thêm sản phẩm" để bắt đầu nhập hàng.</p>
                                        </div>
                                    ) : (
                                        <div className="overflow-x-auto">
                                            <table className="w-full text-left border-collapse">
                                                <thead>
                                                    <tr className="border-b border-gray-200 text-sm text-gray-500">
                                                        <th className="py-3 font-500">SKU</th>
                                                        <th className="py-3 font-500">Tên SP</th>
                                                        <th className="py-3 font-500">Giá</th>
                                                        <th className="py-3 font-500">Trọng lượng</th>
                                                        <th className="py-3 font-500">Tồn kho</th>
                                                        <th className="py-3 font-500 text-right">Thao tác</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {products.map(p => (
                                                        <tr key={p.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                                                            <td className="py-3 text-sm font-500 text-gray-900">{p.sku}</td>
                                                            <td className="py-3 text-sm">
                                                                <div className="text-gray-900 font-500 line-clamp-1">{p.name}</div>
                                                                <div className="text-xs text-gray-500 flex gap-2 mt-1">
                                                                    {p.is_heavy ? <span className="text-orange-600">Hàng nặng</span> : null}
                                                                    {p.is_fragile ? <span className="text-red-600">Dễ vỡ</span> : null}
                                                                </div>
                                                            </td>
                                                            <td className="py-3 text-sm text-gray-700">{new Intl.NumberFormat('vi-VN').format(p.price)} ₫</td>
                                                            <td className="py-3 text-sm text-gray-700">{p.weight_kg} kg</td>
                                                            <td className="py-3 text-sm text-gray-700">
                                                                <span className={p.stock_quantity > 0 ? "text-green-600 font-600" : "text-red-500"}>
                                                                    {p.stock_quantity}
                                                                </span>
                                                            </td>
                                                            <td className="py-3 text-right">
                                                                <div className="flex items-center justify-end gap-2">
                                                                    <button onClick={() => openProductModal(p)} className="p-1.5 text-blue-600 hover:bg-blue-50 rounded" title="Sửa"><Edit2 size={16}/></button>
                                                                    <button onClick={() => deleteProduct(p)} className="p-1.5 text-red-600 hover:bg-red-50 rounded" title="Xóa"><Trash2 size={16}/></button>
                                                                </div>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}
                                </>
                            ) : (
                                <div className="h-full flex flex-col items-center justify-center text-gray-400 py-24">
                                    <MapPin size={48} className="mb-4 text-gray-200" />
                                    <p>Vui lòng chọn một Kho hàng bên trái để xem sản phẩm.</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* WAREHOUSE MODAL */}
            <Modal isOpen={isWarehouseModalOpen} onClose={() => setWarehouseModalOpen(false)} title={editingWarehouse ? "Sửa Kho hàng" : "Thêm Kho mới"}>
                <form onSubmit={handleWarehouseSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-500 text-gray-700 mb-1">Tên kho *</label>
                        <input type="text" required value={warehouseForm.name} onChange={e => setWarehouseForm({...warehouseForm, name: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md outline-none focus:border-blue-500" placeholder="VD: Kho Tân Bình" />
                    </div>
                    <div>
                        <label className="block text-sm font-500 text-gray-700 mb-1">Địa chỉ *</label>
                        <input type="text" required value={warehouseForm.address} onChange={e => setWarehouseForm({...warehouseForm, address: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md outline-none focus:border-blue-500" />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-500 text-gray-700 mb-1">Vĩ độ (Latitude)</label>
                            <input type="number" step="any" value={warehouseForm.latitude} onChange={e => setWarehouseForm({...warehouseForm, latitude: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md outline-none focus:border-blue-500" />
                        </div>
                        <div>
                            <label className="block text-sm font-500 text-gray-700 mb-1">Kinh độ (Longitude)</label>
                            <input type="number" step="any" value={warehouseForm.longitude} onChange={e => setWarehouseForm({...warehouseForm, longitude: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md outline-none focus:border-blue-500" />
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm font-500 text-gray-700 mb-1">Số điện thoại liên hệ</label>
                        <input type="text" value={warehouseForm.contact_phone} onChange={e => setWarehouseForm({...warehouseForm, contact_phone: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md outline-none focus:border-blue-500" />
                    </div>
                    <div className="pt-4 flex justify-end gap-3">
                        <button type="button" onClick={() => setWarehouseModalOpen(false)} className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">Hủy</button>
                        <button type="submit" className="px-4 py-2 bg-blue-700 text-white rounded-md hover:bg-blue-800">Lưu Kho hàng</button>
                    </div>
                </form>
            </Modal>

            {/* PRODUCT MODAL */}
            <Modal isOpen={isProductModalOpen} onClose={() => setProductModalOpen(false)} title={editingProduct ? "Sửa Sản phẩm" : "Thêm Sản phẩm mới"}>
                <form onSubmit={handleProductSubmit} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-500 text-gray-700 mb-1">Mã SKU *</label>
                            <input type="text" required value={productForm.sku} onChange={e => setProductForm({...productForm, sku: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md outline-none focus:border-blue-500" placeholder="VD: SP001" />
                        </div>
                        <div>
                            <label className="block text-sm font-500 text-gray-700 mb-1">Giá bán (VNĐ) *</label>
                            <input type="number" required min="0" value={productForm.price} onChange={e => setProductForm({...productForm, price: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md outline-none focus:border-blue-500" />
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm font-500 text-gray-700 mb-1">Tên Sản phẩm *</label>
                        <input type="text" required value={productForm.name} onChange={e => setProductForm({...productForm, name: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md outline-none focus:border-blue-500" />
                    </div>
                    <div>
                        <label className="block text-sm font-500 text-gray-700 mb-1">Khối lượng (kg) *</label>
                        <input type="number" step="0.01" required min="0" value={productForm.weight_kg} onChange={e => setProductForm({...productForm, weight_kg: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md outline-none focus:border-blue-500" />
                    </div>
                    
                    <div className="grid grid-cols-3 gap-4">
                        <div>
                            <label className="block text-sm font-500 text-gray-700 mb-1">Dài (cm) *</label>
                            <input type="number" required min="0" value={productForm.length_cm} onChange={e => setProductForm({...productForm, length_cm: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md outline-none focus:border-blue-500" />
                        </div>
                        <div>
                            <label className="block text-sm font-500 text-gray-700 mb-1">Rộng (cm) *</label>
                            <input type="number" required min="0" value={productForm.width_cm} onChange={e => setProductForm({...productForm, width_cm: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md outline-none focus:border-blue-500" />
                        </div>
                        <div>
                            <label className="block text-sm font-500 text-gray-700 mb-1">Cao (cm) *</label>
                            <input type="number" required min="0" value={productForm.height_cm} onChange={e => setProductForm({...productForm, height_cm: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md outline-none focus:border-blue-500" />
                        </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4 border-t border-b border-gray-100 py-3 my-2">
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input type="checkbox" checked={productForm.is_heavy} onChange={e => setProductForm({...productForm, is_heavy: e.target.checked})} className="rounded text-blue-600 focus:ring-blue-500" />
                            <span className="text-sm text-gray-700">Hàng nặng</span>
                        </label>
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input type="checkbox" checked={productForm.is_fragile} onChange={e => setProductForm({...productForm, is_fragile: e.target.checked})} className="rounded text-blue-600 focus:ring-blue-500" />
                            <span className="text-sm text-gray-700">Dễ vỡ</span>
                        </label>
                    </div>

                    <div>
                        <label className="block text-sm font-500 text-gray-700 mb-1">Số lượng tồn kho *</label>
                        <input type="number" required min="0" value={productForm.stock_quantity} onChange={e => setProductForm({...productForm, stock_quantity: e.target.value})} className="w-full px-3 py-2 border border-gray-300 rounded-md outline-none focus:border-blue-500" />
                    </div>

                    <div className="pt-4 flex justify-end gap-3">
                        <button type="button" onClick={() => setProductModalOpen(false)} className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">Hủy</button>
                        <button type="submit" className="px-4 py-2 bg-blue-700 text-white rounded-md hover:bg-blue-800">Lưu Sản phẩm</button>
                    </div>
                </form>
            </Modal>

        </div>
    );
}
