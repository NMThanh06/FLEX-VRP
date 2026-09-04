<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use App\Models\Warehouse;
use App\Models\Product;

class ManagementController extends Controller
{
    // ==========================================
    // WAREHOUSE MANAGEMENT
    // ==========================================

    public function getWarehouses(Request $request)
    {
        // Allow optional filtering by carrier (user_id) if we want to restrict carriers to their own warehouses
        $user = $request->user();
        if ($user->role === 'carrier') {
            $warehouses = Warehouse::withCount('orders')->where('user_id', $user->id)->get();
        } else {
            $warehouses = Warehouse::withCount('orders')->get();
        }
        return response()->json($warehouses);
    }

    public function storeWarehouse(Request $request)
    {
        $request->validate([
            'name' => 'required|string|max:255',
            'address' => 'required|string',
            'latitude' => 'nullable|numeric',
            'longitude' => 'nullable|numeric',
            'contact_phone' => 'nullable|string',
            'is_active' => 'boolean',
        ]);

        $user = $request->user();

        $warehouse = Warehouse::create([
            'user_id' => $user->id, // assign to the creator
            'name' => $request->name,
            'address' => $request->address,
            'latitude' => $request->latitude,
            'longitude' => $request->longitude,
            'contact_phone' => $request->contact_phone,
            'is_active' => $request->is_active ?? true,
        ]);

        return response()->json(['message' => 'Warehouse created successfully', 'warehouse' => $warehouse], 201);
    }

    public function updateWarehouse(Request $request, $id)
    {
        $warehouse = Warehouse::findOrFail($id);

        // Check ownership if carrier
        if ($request->user()->role === 'carrier' && $warehouse->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $request->validate([
            'name' => 'required|string|max:255',
            'address' => 'required|string',
            'latitude' => 'nullable|numeric',
            'longitude' => 'nullable|numeric',
            'contact_phone' => 'nullable|string',
            'is_active' => 'boolean',
        ]);

        $warehouse->update($request->only(['name', 'address', 'latitude', 'longitude', 'contact_phone', 'is_active']));

        return response()->json(['message' => 'Warehouse updated successfully', 'warehouse' => $warehouse]);
    }

    public function destroyWarehouse(Request $request, $id)
    {
        $warehouse = Warehouse::withCount('orders')->findOrFail($id);

        if ($request->user()->role === 'carrier' && $warehouse->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        if ($warehouse->orders_count > 0) {
            return response()->json(['message' => 'Cannot delete warehouse because it has associated orders.'], 422);
        }

        // Cascade delete products
        $warehouse->products()->delete();
        $warehouse->delete();

        return response()->json(['message' => 'Warehouse and its products deleted successfully']);
    }


    // ==========================================
    // PRODUCT MANAGEMENT
    // ==========================================

    public function getProducts(Request $request)
    {
        $warehouseId = $request->query('warehouse_id');
        $query = Product::query();

        if ($warehouseId) {
            $query->where('warehouse_id', $warehouseId);
        } else {
            // Optional: return all products for the carrier's warehouses
            $user = $request->user();
            if ($user->role === 'carrier') {
                $warehouseIds = Warehouse::where('user_id', $user->id)->pluck('id');
                $query->whereIn('warehouse_id', $warehouseIds);
            }
        }

        return response()->json($query->get());
    }

    public function storeProduct(Request $request)
    {
        $request->validate([
            'warehouse_id' => 'required|exists:warehouses,id',
            'sku' => 'required|string|unique:products,sku',
            'name' => 'required|string|max:255',
            'description' => 'nullable|string',
            'price' => 'required|numeric|min:0',
            'weight_kg' => 'required|numeric|min:0',
            'length_cm' => 'required|numeric|min:0',
            'width_cm' => 'required|numeric|min:0',
            'height_cm' => 'required|numeric|min:0',
            'is_heavy' => 'boolean',
            'is_fragile' => 'boolean',
            'stock_quantity' => 'required|integer|min:0',
            'is_active' => 'boolean',
        ]);

        $warehouse = Warehouse::findOrFail($request->warehouse_id);
        if ($request->user()->role === 'carrier' && $warehouse->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized to add products to this warehouse'], 403);
        }

        $product = Product::create($request->all());

        return response()->json(['message' => 'Product created successfully', 'product' => $product], 201);
    }

    public function updateProduct(Request $request, $id)
    {
        $product = Product::findOrFail($id);
        $warehouse = $product->warehouse;

        if ($request->user()->role === 'carrier' && $warehouse->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $request->validate([
            'sku' => 'required|string|unique:products,sku,'.$product->id,
            'name' => 'required|string|max:255',
            'description' => 'nullable|string',
            'price' => 'required|numeric|min:0',
            'weight_kg' => 'required|numeric|min:0',
            'length_cm' => 'required|numeric|min:0',
            'width_cm' => 'required|numeric|min:0',
            'height_cm' => 'required|numeric|min:0',
            'is_heavy' => 'boolean',
            'is_fragile' => 'boolean',
            'stock_quantity' => 'required|integer|min:0',
            'is_active' => 'boolean',
        ]);

        $product->update($request->all());

        return response()->json(['message' => 'Product updated successfully', 'product' => $product]);
    }

    public function destroyProduct(Request $request, $id)
    {
        $product = Product::findOrFail($id);
        $warehouse = $product->warehouse;

        if ($request->user()->role === 'carrier' && $warehouse->user_id !== $request->user()->id) {
            return response()->json(['message' => 'Unauthorized'], 403);
        }

        $product->delete();

        return response()->json(['message' => 'Product deleted successfully']);
    }
}
