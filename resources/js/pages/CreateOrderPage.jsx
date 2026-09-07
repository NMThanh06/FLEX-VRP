import React, { useState, useEffect } from 'react';
import { MapPin, Package, Calendar, Truck, ArrowRight, Info, CheckCircle2, Plus, Minus, ShoppingCart, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';

export default function CreateOrderPage() {
    const [warehouses, setWarehouses] = useState([]);
    const [products, setProducts] = useState([]);
    
    const { user } = useAuth();
    
    const [formData, setFormData] = useState({
        warehouse_id: '',
        time_window_start: '',
        time_window_end: '',
        notes: '',
        sender_name: user?.name || '',
        sender_company: user?.company || '',
        sender_address: user?.address || ''
    });

    const [cart, setCart] = useState([]); // Array of { product, quantity }
    const [isSubmitted, setIsSubmitted] = useState(false);
    const [createdOrder, setCreatedOrder] = useState(null);
    
    // Loading states
    const [loadingWarehouses, setLoadingWarehouses] = useState(true);
    const [loadingProducts, setLoadingProducts] = useState(false);
    const [loadingSubmit, setLoadingSubmit] = useState(false);

    useEffect(() => {
        // Fetch warehouses on mount
        axios.get('/api/warehouses')
            .then(res => {
                setWarehouses(res.data);
                setLoadingWarehouses(false);
            })
            .catch(err => {
                console.error("Error fetching warehouses", err);
                setLoadingWarehouses(false);
            });
    }, []);

    useEffect(() => {
        let isMounted = true; // For avoiding race conditions

        if (formData.warehouse_id) {
            setLoadingProducts(true);
            axios.get(`/api/products?warehouse_id=${formData.warehouse_id}`)
                .then(res => {
                    if (isMounted) {
                        setProducts(res.data);
                        setCart([]); // Reset cart when warehouse changes
                        setLoadingProducts(false);
                    }
                })
                .catch(err => {
                    if (isMounted) {
                        console.error("Error fetching products", err);
                        setLoadingProducts(false);
                    }
                });
        } else {
            setProducts([]);
            setCart([]);
            setLoadingProducts(false);
        }

        return () => {
            isMounted = false; // Cleanup flag on unmount or when warehouse_id changes
        };
    }, [formData.warehouse_id]);

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const addToCart = (product) => {
        const existing = cart.find(item => item.product.id === product.id);
        if (existing) {
            setCart(cart.map(item => item.product.id === product.id ? { ...item, quantity: item.quantity + 1 } : item));
        } else {
            setCart([...cart, { product, quantity: 1 }]);
        }
    };

    const updateQuantity = (productId, delta) => {
        setCart(cart.map(item => {
            if (item.product.id === productId) {
                const newQty = item.quantity + delta;
                return newQty > 0 ? { ...item, quantity: newQty } : null;
            }
            return item;
        }).filter(Boolean));
    };

    const cartTotals = cart.reduce((acc, item) => {
        acc.weight += item.product.weight_kg * item.quantity;
        acc.volume += (item.product.length_cm * item.product.width_cm * item.product.height_cm) * item.quantity;
        acc.price += item.product.price * item.quantity;
        return acc;
    }, { weight: 0, volume: 0, price: 0 });

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (cart.length === 0) {
            alert("Vui lòng chọn ít nhất 1 sản phẩm!");
            return;
        }

        setLoadingSubmit(true);
        try {
            // First hit the sanctum CSRF cookie endpoint just to be sure we have the latest token
            await axios.get('/sanctum/csrf-cookie');

            const payload = {
                warehouse_id: formData.warehouse_id,
                time_window_start: formData.time_window_start,
                time_window_end: formData.time_window_end,
                notes: formData.notes,
                items: cart.map(item => ({
                    product_id: item.product.id,
                    quantity: item.quantity
                }))
            };

            const response = await axios.post('/api/orders', payload);

            if (response.status === 201 || response.status === 200) {
                setCreatedOrder(response.data.order);
                setIsSubmitted(true);
                window.scrollTo(0, 0);
            }
        } catch (error) {
            console.error("Submit error", error);
            const msg = error.response?.data?.message || "Lỗi kết nối máy chủ";
            alert("Lỗi: " + msg);
        } finally {
            setLoadingSubmit(false);
        }
    };

    if (isSubmitted) {
        return (
            <div className="max-w-3xl mx-auto px-6 py-24 text-center">
                <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                    <CheckCircle2 className="text-green-600" size={40} />
                </div>
                <h1 className="text-3xl font-700 text-gray-900 mb-4">Tạo đơn hàng thành công!</h1>
                <p className="text-gray-500 mb-2">Mã đơn hàng: <strong className="text-gray-900">{createdOrder?.order_code}</strong></p>
                <p className="text-gray-500 mb-8 max-w-lg mx-auto">
                    Đơn hàng của bạn đã được đưa vào hệ thống và đang chờ Carrier tiếp nhận. Thuật toán tối ưu sẽ tự động sắp xếp xe trong thời gian tới.
                </p>
                <div className="flex justify-center gap-4">
                    <Link to="/orders" className="px-6 py-3 border border-gray-300 text-gray-700 font-500 rounded-md hover:bg-gray-50 transition-colors">
                        Xem đơn hàng
                    </Link>
                    <button 
                        onClick={() => {
                            setIsSubmitted(false);
                            setCart([]);
                            setFormData({ ...formData, notes: '' }); // keep warehouse and dates
                        }}
                        className="px-6 py-3 bg-blue-700 text-white font-500 rounded-md hover:bg-blue-800 transition-colors"
                    >
                        Tạo đơn mới
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-gray-50 min-h-[calc(100vh-64px)] py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-7xl mx-auto">
                
                <div className="mb-8">
                    <h1 className="text-3xl font-700 text-gray-900">Tạo đơn hàng vận chuyển</h1>
                    <p className="mt-2 text-sm text-gray-500">Chọn kho hàng, thêm sản phẩm vào giỏ và chỉ định thời gian giao hàng mong muốn.</p>
                </div>

                <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    
                    {/* Left Column: Form Fields */}
                    <div className="lg:col-span-2 space-y-6">
                        
                        {/* Section: Thông tin Người gửi */}
                        <div className="bg-white p-6 sm:p-8 rounded-xl border border-gray-200 shadow-sm">
                            <h2 className="text-lg font-600 text-gray-900 mb-6 flex items-center gap-2">
                                <Info className="text-blue-600" size={20} />
                                Thông tin Người đặt / Người gửi
                            </h2>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div>
                                    <label className="block text-sm font-500 text-gray-700 mb-2">Họ và tên</label>
                                    <input
                                        type="text"
                                        name="sender_name"
                                        value={formData.sender_name}
                                        onChange={handleChange}
                                        className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all text-sm"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-500 text-gray-700 mb-2">Tên Công ty</label>
                                    <input
                                        type="text"
                                        name="sender_company"
                                        value={formData.sender_company}
                                        onChange={handleChange}
                                        className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all text-sm"
                                    />
                                </div>
                                <div className="md:col-span-2">
                                    <label className="block text-sm font-500 text-gray-700 mb-2">Địa chỉ</label>
                                    <input
                                        type="text"
                                        name="sender_address"
                                        value={formData.sender_address}
                                        onChange={handleChange}
                                        className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all text-sm"
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Section: Thông tin Kho & Thời gian */}
                        <div className="bg-white p-6 sm:p-8 rounded-xl border border-gray-200 shadow-sm">
                            <h2 className="text-lg font-600 text-gray-900 mb-6 flex items-center gap-2">
                                <MapPin className="text-blue-600" size={20} />
                                Thông tin Lấy & Nhận hàng
                            </h2>
                            
                            <div className="space-y-6">
                                <div>
                                    <label className="block text-sm font-500 text-gray-700 mb-2">Chọn Kho xuất hàng (Carrier)</label>
                                    <select
                                        name="warehouse_id"
                                        required
                                        value={formData.warehouse_id}
                                        onChange={handleChange}
                                        disabled={loadingWarehouses}
                                        className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all text-sm bg-white disabled:bg-gray-100"
                                    >
                                        <option value="">{loadingWarehouses ? 'Đang tải danh sách kho...' : '-- Chọn Kho hàng --'}</option>
                                        {warehouses.map(w => (
                                            <option key={w.id} value={w.id}>{w.name} ({w.address})</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="h-px bg-gray-100 my-2"></div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div>
                                        <label className="block text-sm font-500 text-gray-700 mb-2">Khung giờ nhận (Bắt đầu)</label>
                                        <input
                                            type="datetime-local"
                                            name="time_window_start"
                                            required
                                            value={formData.time_window_start}
                                            onChange={handleChange}
                                            className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all text-sm"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-500 text-gray-700 mb-2">Khung giờ nhận (Kết thúc)</label>
                                        <input
                                            type="datetime-local"
                                            name="time_window_end"
                                            required
                                            value={formData.time_window_end}
                                            onChange={handleChange}
                                            className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all text-sm"
                                        />
                                    </div>
                                </div>
                                
                                <div>
                                    <label className="block text-sm font-500 text-gray-700 mb-2">Ghi chú giao hàng</label>
                                    <textarea
                                        name="notes"
                                        rows="2"
                                        value={formData.notes}
                                        onChange={handleChange}
                                        placeholder="Ví dụ: Gọi điện trước khi giao..."
                                        className="w-full px-4 py-2.5 rounded-md border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all placeholder-gray-400 text-sm resize-y"
                                    ></textarea>
                                </div>
                            </div>
                        </div>

                        {/* Section: Danh mục sản phẩm */}
                        <div className="bg-white p-6 sm:p-8 rounded-xl border border-gray-200 shadow-sm">
                            <h2 className="text-lg font-600 text-gray-900 mb-6 flex items-center gap-2">
                                <Package className="text-blue-600" size={20} />
                                Danh mục Sản phẩm
                            </h2>
                            
                            {!formData.warehouse_id ? (
                                <div className="text-center py-8 text-gray-500 text-sm bg-gray-50 rounded-lg border border-dashed border-gray-300">
                                    Vui lòng chọn Kho xuất hàng ở trên để xem danh sách sản phẩm.
                                </div>
                            ) : loadingProducts ? (
                                <div className="text-center py-8 text-gray-500 text-sm bg-gray-50 rounded-lg border border-dashed border-gray-300 flex flex-col items-center justify-center gap-2">
                                    <Loader2 className="animate-spin text-blue-500" size={24} />
                                    Đang tải sản phẩm...
                                </div>
                            ) : products.length === 0 ? (
                                <div className="text-center py-8 text-gray-500 text-sm bg-gray-50 rounded-lg border border-dashed border-gray-300">
                                    Kho này hiện không có sản phẩm nào.
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    {products.map(product => (
                                        <div key={product.id} className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors flex flex-col justify-between">
                                            <div>
                                                <h3 className="font-600 text-gray-900 text-sm mb-1">{product.name}</h3>
                                                <p className="text-xs text-gray-500 mb-2">SKU: {product.sku} | Tồn: {product.stock_quantity}</p>
                                                <div className="flex flex-wrap gap-2 mb-3">
                                                    <span className="text-[10px] px-2 py-0.5 bg-gray-100 text-gray-600 rounded">{product.weight_kg} kg</span>
                                                    <span className="text-[10px] px-2 py-0.5 bg-gray-100 text-gray-600 rounded">{product.length_cm}x{product.width_cm}x{product.height_cm} cm</span>
                                                </div>
                                            </div>
                                            <div className="flex items-center justify-between mt-2 pt-3 border-t border-gray-100">
                                                <span className="font-600 text-blue-700">{new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(product.price)}</span>
                                                <button 
                                                    type="button" 
                                                    onClick={() => addToCart(product)}
                                                    className="p-1.5 bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 transition-colors"
                                                    title="Thêm vào giỏ"
                                                >
                                                    <Plus size={16} />
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Right Column: Order Summary & Actions */}
                    <div className="lg:col-span-1">
                        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm sticky top-24">
                            <h2 className="text-lg font-600 text-gray-900 mb-4 flex items-center gap-2">
                                <ShoppingCart size={20} className="text-blue-600" />
                                Giỏ hàng của bạn
                            </h2>
                            
                            {cart.length === 0 ? (
                                <div className="text-center py-6 text-gray-400 text-sm">
                                    Chưa có sản phẩm nào
                                </div>
                            ) : (
                                <div className="space-y-4 mb-6 max-h-60 overflow-y-auto pr-2">
                                    {cart.map(item => (
                                        <div key={item.product.id} className="flex justify-between items-start gap-2 text-sm border-b border-gray-50 pb-3">
                                            <div className="flex-1">
                                                <p className="font-500 text-gray-800 line-clamp-1" title={item.product.name}>{item.product.name}</p>
                                                <p className="text-xs text-gray-500">{new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(item.product.price)} x {item.quantity}</p>
                                            </div>
                                            <div className="flex items-center gap-2 shrink-0">
                                                <button type="button" onClick={() => updateQuantity(item.product.id, -1)} className="p-1 bg-gray-100 rounded text-gray-600 hover:bg-gray-200"><Minus size={12} /></button>
                                                <span className="w-4 text-center font-500 text-xs">{item.quantity}</span>
                                                <button type="button" onClick={() => updateQuantity(item.product.id, 1)} className="p-1 bg-gray-100 rounded text-gray-600 hover:bg-gray-200"><Plus size={12} /></button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            <div className="space-y-3 mb-6 bg-gray-50 p-4 rounded-lg">
                                <div className="flex justify-between items-center text-sm">
                                    <span className="text-gray-500">Tổng trọng lượng</span>
                                    <span className="font-600 text-gray-700">{cartTotals.weight.toFixed(2)} kg</span>
                                </div>
                                <div className="flex justify-between items-center text-sm">
                                    <span className="text-gray-500">Tổng thể tích</span>
                                    <span className="font-600 text-gray-700">{(cartTotals.volume / 1000000).toFixed(3)} m³</span>
                                </div>
                                <div className="h-px bg-gray-200 my-1"></div>
                                <div className="flex justify-between items-center">
                                    <span className="font-600 text-gray-900">Tổng tiền hàng</span>
                                    <span className="font-700 text-blue-700 text-lg">
                                        {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(cartTotals.price)}
                                    </span>
                                </div>
                            </div>

                            <div className="bg-blue-50 p-4 rounded-lg flex items-start gap-3 mb-6">
                                <Info className="text-blue-600 shrink-0 mt-0.5" size={18} />
                                <p className="text-xs text-blue-800 leading-relaxed">
                                    Chi tiết thể tích và khối lượng này sẽ được thuật toán <strong>3D Bin Packing</strong> tính toán sơ đồ bốc xếp khi xếp xe.
                                </p>
                            </div>

                            <button
                                type="submit"
                                disabled={loadingSubmit || cart.length === 0}
                                className="w-full flex items-center justify-center gap-2 bg-blue-700 hover:bg-blue-800 disabled:bg-blue-300 text-white font-600 py-3.5 px-4 rounded-md transition-colors"
                            >
                                {loadingSubmit ? (
                                    <><Loader2 size={18} className="animate-spin" /> Đang xử lý...</>
                                ) : (
                                    <><Truck size={18} /> Xác nhận Đặt hàng</>
                                )}
                            </button>
                        </div>
                    </div>

                </form>
            </div>
        </div>
    );
}
