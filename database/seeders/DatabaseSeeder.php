<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    use WithoutModelEvents;

    /**
     * Seed the application's database.
     */
    public function run(): void
    {
        $user = User::firstOrCreate(
            ['email' => 'retailer@example.com'],
            [
                'name' => 'Retailer Test',
                'password' => bcrypt('password'),
                'role' => 'retailer',
            ]
        );

        $carrier = User::firstOrCreate(
            ['email' => 'carrier@example.com'],
            [
                'name' => 'Carrier Test',
                'password' => bcrypt('password'),
                'role' => 'carrier',
            ]
        );

        $warehouse = \App\Models\Warehouse::firstOrCreate(
            ['name' => 'Kho Trung Tâm TP.HCM'],
            [
                'user_id' => $carrier->id,
                'address' => 'Khu Công Nghệ Cao, Quận 9, TP.HCM',
                'latitude' => 10.8501,
                'longitude' => 106.7972,
                'contact_phone' => '0901234567',
                'is_active' => true,
            ]
        );

        $warehouse2 = \App\Models\Warehouse::firstOrCreate(
            ['name' => 'Kho Cát Lái'],
            [
                'user_id' => $carrier->id,
                'address' => 'Cảng Cát Lái, TP.Thủ Đức',
                'latitude' => 10.7634,
                'longitude' => 106.7824,
                'contact_phone' => '0909876543',
                'is_active' => true,
            ]
        );

        \App\Models\Product::firstOrCreate(
            ['sku' => 'PROD-001'],
            [
                'warehouse_id' => $warehouse->id,
                'name' => 'Thùng mì Hảo Hảo',
                'description' => 'Mì tôm Hảo Hảo 30 gói',
                'price' => 120000,
                'weight_kg' => 2.5,
                'length_cm' => 30,
                'width_cm' => 20,
                'height_cm' => 15,
                'is_heavy' => false,
                'is_fragile' => true,
                'stock_quantity' => 1000,
                'is_active' => true,
            ]
        );

        \App\Models\Product::firstOrCreate(
            ['sku' => 'PROD-002'],
            [
                'warehouse_id' => $warehouse->id,
                'name' => 'Lốc 6 chai nước suối 1.5L',
                'description' => 'Nước tinh khiết',
                'price' => 60000,
                'weight_kg' => 9.2,
                'length_cm' => 30,
                'width_cm' => 20,
                'height_cm' => 35,
                'is_heavy' => true,
                'is_fragile' => false,
                'stock_quantity' => 500,
                'is_active' => true,
            ]
        );
        
        \App\Models\Product::firstOrCreate(
            ['sku' => 'PROD-003'],
            [
                'warehouse_id' => $warehouse->id,
                'name' => 'Thùng sữa tươi Vinamilk',
                'description' => 'Sữa tươi tiệt trùng 48 hộp',
                'price' => 320000,
                'weight_kg' => 9.5,
                'length_cm' => 35,
                'width_cm' => 25,
                'height_cm' => 12,
                'is_heavy' => true,
                'is_fragile' => false,
                'stock_quantity' => 300,
                'is_active' => true,
            ]
        );

        // Seed products for Kho Cát Lái
        \App\Models\Product::firstOrCreate(
            ['sku' => 'PROD-004'],
            [
                'warehouse_id' => $warehouse2->id,
                'name' => 'Bao gạo ST25 10kg',
                'description' => 'Gạo đặc sản Sóc Trăng',
                'price' => 250000,
                'weight_kg' => 10.0,
                'length_cm' => 45,
                'width_cm' => 30,
                'height_cm' => 15,
                'is_heavy' => true,
                'is_fragile' => false,
                'stock_quantity' => 200,
                'is_active' => true,
            ]
        );

        \App\Models\Product::firstOrCreate(
            ['sku' => 'PROD-005'],
            [
                'warehouse_id' => $warehouse2->id,
                'name' => 'Thùng bia Heineken',
                'description' => 'Bia lon 330ml x 24',
                'price' => 450000,
                'weight_kg' => 8.5,
                'length_cm' => 40,
                'width_cm' => 26,
                'height_cm' => 16,
                'is_heavy' => true,
                'is_fragile' => true,
                'stock_quantity' => 400,
                'is_active' => true,
            ]
        );
    }
}
