<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use App\Models\Warehouse;
use App\Models\Product;
use App\Models\Order;
use App\Models\OrderItem;
use Illuminate\Support\Str;

class OrderController extends Controller
{
    public function getWarehouses()
    {
        $warehouses = Warehouse::where('is_active', true)->get();
        return response()->json($warehouses);
    }

    public function getProducts(Request $request)
    {
        $warehouseId = $request->query('warehouse_id');
        if (!$warehouseId) {
            return response()->json([]);
        }
        $products = Product::where('warehouse_id', $warehouseId)
                            ->where('is_active', true)
                            ->get();
        return response()->json($products);
    }

    public function getOrders(Request $request)
    {
        // Currently we don't have auth fully setup in the request context (or mock it to user 1)
        // In real app: $userId = $request->user()->id;
        $userId = 1; // Mock user ID for retailer
        
        $orders = Order::with(['warehouse', 'items.product'])
                        ->where('retailer_id', $userId)
                        ->orderBy('created_at', 'desc')
                        ->get();
        
        return response()->json($orders);
    }

    public function store(Request $request)
    {
        $request->validate([
            'warehouse_id' => 'required|exists:warehouses,id',
            'time_window_start' => 'required|date',
            'time_window_end' => 'required|date|after:time_window_start',
            'notes' => 'nullable|string',
            'items' => 'required|array|min:1',
            'items.*.product_id' => 'required|exists:products,id',
            'items.*.quantity' => 'required|integer|min:1',
        ]);

        // In real app: $userId = $request->user()->id;
        $userId = 1; // Mock

        // Calculate totals
        $totalWeight = 0;
        $totalVolume = 0;
        $totalAmount = 0;

        foreach ($request->items as $item) {
            $product = Product::find($item['product_id']);
            $qty = $item['quantity'];
            
            $totalWeight += $product->weight_kg * $qty;
            $totalVolume += ($product->length_cm * $product->width_cm * $product->height_cm) * $qty;
            $totalAmount += $product->price * $qty;
        }

        $order = Order::create([
            'order_code' => 'ORD-' . date('Y') . '-' . strtoupper(Str::random(5)),
            'retailer_id' => $userId,
            'warehouse_id' => $request->warehouse_id,
            'status' => 'pending',
            'total_weight_kg' => $totalWeight,
            'total_volume_cm3' => $totalVolume,
            'total_amount' => $totalAmount,
            'time_window_start' => $request->time_window_start,
            'time_window_end' => $request->time_window_end,
            'notes' => $request->notes,
        ]);

        foreach ($request->items as $item) {
            $product = Product::find($item['product_id']);
            $qty = $item['quantity'];
            $subtotal = $product->price * $qty;
            $itemWeight = $product->weight_kg * $qty;
            $itemVolume = ($product->length_cm * $product->width_cm * $product->height_cm) * $qty;

            OrderItem::create([
                'order_id' => $order->id,
                'product_id' => $product->id,
                'quantity' => $qty,
                'unit_price' => $product->price,
                'subtotal' => $subtotal,
                'item_weight_kg' => $itemWeight,
                'item_volume_cm3' => $itemVolume,
            ]);
        }

        return response()->json([
            'message' => 'Order created successfully',
            'order' => $order->load('items.product')
        ], 201);
    }
}
