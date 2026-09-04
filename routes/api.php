<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\AuthController;

use App\Http\Controllers\Api\OrderController;

Route::post('/register', [AuthController::class, 'register']);
Route::post('/login', [AuthController::class, 'login']);
Route::post('/logout', [AuthController::class, 'logout']);

// Temporary public endpoints for Orders for MVP test without auth barrier (or you can put them inside auth middleware)
// But according to the controller they mock user ID to 1 so let's keep them public for now to prevent token issues while developing.
Route::get('/warehouses', [OrderController::class, 'getWarehouses']);
Route::get('/products', [OrderController::class, 'getProducts']);
Route::get('/orders', [OrderController::class, 'getOrders']);
Route::post('/orders', [OrderController::class, 'store']);

Route::middleware('auth:sanctum')->group(function () {
    Route::get('/user', [AuthController::class, 'user']);
    Route::post('/profile', [AuthController::class, 'updateProfile']);

    // Carrier Management Routes
    Route::get('/management/warehouses', [\App\Http\Controllers\Api\ManagementController::class, 'getWarehouses']);
    Route::post('/management/warehouses', [\App\Http\Controllers\Api\ManagementController::class, 'storeWarehouse']);
    Route::put('/management/warehouses/{id}', [\App\Http\Controllers\Api\ManagementController::class, 'updateWarehouse']);
    Route::delete('/management/warehouses/{id}', [\App\Http\Controllers\Api\ManagementController::class, 'destroyWarehouse']);

    Route::get('/management/products', [\App\Http\Controllers\Api\ManagementController::class, 'getProducts']);
    Route::post('/management/products', [\App\Http\Controllers\Api\ManagementController::class, 'storeProduct']);
    Route::put('/management/products/{id}', [\App\Http\Controllers\Api\ManagementController::class, 'updateProduct']);
    Route::delete('/management/products/{id}', [\App\Http\Controllers\Api\ManagementController::class, 'destroyProduct']);
});
