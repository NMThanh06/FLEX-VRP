<?php

namespace Database\Seeders;

use App\Models\Product;
use App\Models\Warehouse;
use Illuminate\Database\Seeder;

class ProductSeeder extends Seeder
{
    /**
     * Seed 30 mặt hàng mẫu: thực phẩm, mỹ phẩm, nước giải khát, gia dụng.
     * Tất cả thuộc kho chính (Kho Trung Tâm Q7).
     */
    public function run(): void
    {
        $warehouse = Warehouse::where('name', 'Kho Trung Tâm Q7')->first();

        if (!$warehouse) {
            $this->command->error('❌ Chưa có kho! Chạy WarehouseSeeder trước.');
            return;
        }

        $products = [
            // ── Thực phẩm ──
            ['sku' => 'TP-001', 'name' => 'Thùng mì gói Hảo Hảo (30 gói)',     'price' => 135000,  'weight_kg' => 5.000,  'length_cm' => 40, 'width_cm' => 30, 'height_cm' => 25, 'is_heavy' => true,  'is_fragile' => false, 'stock' => 500, 'desc' => 'Mì ăn liền Hảo Hảo thùng 30 gói'],
            ['sku' => 'TP-002', 'name' => 'Thùng phở Vifon (24 gói)',            'price' => 168000,  'weight_kg' => 4.800,  'length_cm' => 38, 'width_cm' => 28, 'height_cm' => 25, 'is_heavy' => true,  'is_fragile' => false, 'stock' => 300, 'desc' => 'Phở bò Vifon thùng 24 gói'],
            ['sku' => 'TP-003', 'name' => 'Thùng bánh Oreo (48 gói)',            'price' => 240000,  'weight_kg' => 3.000,  'length_cm' => 35, 'width_cm' => 25, 'height_cm' => 20, 'is_heavy' => false, 'is_fragile' => true,  'stock' => 200, 'desc' => 'Bánh Oreo thùng 48 gói nhỏ'],
            ['sku' => 'TP-004', 'name' => 'Thùng snack Pringles (12 lon)',        'price' => 360000,  'weight_kg' => 1.500,  'length_cm' => 30, 'width_cm' => 22, 'height_cm' => 30, 'is_heavy' => false, 'is_fragile' => true,  'stock' => 150, 'desc' => 'Snack Pringles thùng 12 lon'],
            ['sku' => 'TP-005', 'name' => 'Thùng kẹo cao su Extra (50 hộp)',     'price' => 500000,  'weight_kg' => 0.500,  'length_cm' => 25, 'width_cm' => 20, 'height_cm' => 15, 'is_heavy' => false, 'is_fragile' => false, 'stock' => 400, 'desc' => 'Kẹo cao su Extra thùng 50 hộp'],
            ['sku' => 'TP-006', 'name' => 'Thùng đường Biên Hòa (20 kg)',        'price' => 380000,  'weight_kg' => 10.000, 'length_cm' => 35, 'width_cm' => 25, 'height_cm' => 30, 'is_heavy' => true,  'is_fragile' => false, 'stock' => 250, 'desc' => 'Đường kính trắng Biên Hòa bao 20kg'],
            ['sku' => 'TP-007', 'name' => 'Thùng bột mì (25 kg)',                'price' => 275000,  'weight_kg' => 5.000,  'length_cm' => 40, 'width_cm' => 25, 'height_cm' => 15, 'is_heavy' => true,  'is_fragile' => false, 'stock' => 300, 'desc' => 'Bột mì đa dụng bao 25kg'],
            ['sku' => 'TP-008', 'name' => 'Thùng muối I-ốt (50 gói)',            'price' => 120000,  'weight_kg' => 5.000,  'length_cm' => 30, 'width_cm' => 20, 'height_cm' => 20, 'is_heavy' => true,  'is_fragile' => false, 'stock' => 500, 'desc' => 'Muối I-ốt thùng 50 gói 100g'],

            // ── Nước giải khát ──
            ['sku' => 'NGK-001', 'name' => 'Thùng Coca-Cola (24 lon)',           'price' => 220000,  'weight_kg' => 8.500,  'length_cm' => 40, 'width_cm' => 30, 'height_cm' => 15, 'is_heavy' => true,  'is_fragile' => false, 'stock' => 600, 'desc' => 'Coca-Cola thùng 24 lon 330ml'],
            ['sku' => 'NGK-002', 'name' => 'Thùng nước suối Lavie (24 chai)',    'price' => 95000,   'weight_kg' => 6.000,  'length_cm' => 38, 'width_cm' => 25, 'height_cm' => 22, 'is_heavy' => true,  'is_fragile' => false, 'stock' => 800, 'desc' => 'Nước suối Lavie thùng 24 chai 500ml'],
            ['sku' => 'NGK-003', 'name' => 'Thùng bia Tiger (24 lon)',            'price' => 330000,  'weight_kg' => 9.000,  'length_cm' => 40, 'width_cm' => 30, 'height_cm' => 15, 'is_heavy' => true,  'is_fragile' => false, 'stock' => 400, 'desc' => 'Bia Tiger thùng 24 lon 330ml'],
            ['sku' => 'NGK-004', 'name' => 'Thùng nước tăng lực Red Bull (24 lon)', 'price' => 280000, 'weight_kg' => 4.000, 'length_cm' => 35, 'width_cm' => 25, 'height_cm' => 12, 'is_heavy' => false, 'is_fragile' => false, 'stock' => 350, 'desc' => 'Red Bull thùng 24 lon 250ml'],
            ['sku' => 'NGK-005', 'name' => 'Thùng sữa Vinamilk (48 hộp)',        'price' => 350000,  'weight_kg' => 6.000,  'length_cm' => 42, 'width_cm' => 28, 'height_cm' => 18, 'is_heavy' => false, 'is_fragile' => true,  'stock' => 500, 'desc' => 'Sữa tươi Vinamilk thùng 48 hộp 180ml'],
            ['sku' => 'NGK-006', 'name' => 'Thùng trà xanh Không Độ (24 chai)',  'price' => 180000,  'weight_kg' => 7.200,  'length_cm' => 38, 'width_cm' => 26, 'height_cm' => 22, 'is_heavy' => true,  'is_fragile' => false, 'stock' => 450, 'desc' => 'Trà xanh Không Độ thùng 24 chai 500ml'],

            // ── Gia vị & Nước chấm ──
            ['sku' => 'GV-001', 'name' => 'Thùng nước mắm Chinsu (12 chai)',     'price' => 210000,  'weight_kg' => 6.000,  'length_cm' => 35, 'width_cm' => 25, 'height_cm' => 28, 'is_heavy' => true,  'is_fragile' => true,  'stock' => 300, 'desc' => 'Nước mắm Chinsu thùng 12 chai 500ml'],
            ['sku' => 'GV-002', 'name' => 'Thùng dầu ăn Neptune (6 chai)',       'price' => 450000,  'weight_kg' => 10.000, 'length_cm' => 38, 'width_cm' => 28, 'height_cm' => 30, 'is_heavy' => true,  'is_fragile' => false, 'stock' => 200, 'desc' => 'Dầu ăn Neptune thùng 6 chai 1L'],
            ['sku' => 'GV-003', 'name' => 'Thùng tương ớt Chinsu (24 chai)',     'price' => 288000,  'weight_kg' => 7.200,  'length_cm' => 35, 'width_cm' => 25, 'height_cm' => 25, 'is_heavy' => true,  'is_fragile' => true,  'stock' => 250, 'desc' => 'Tương ớt Chinsu thùng 24 chai 250g'],

            // ── Gia dụng ──
            ['sku' => 'GD-001', 'name' => 'Thùng bột giặt OMO (12 túi)',         'price' => 480000,  'weight_kg' => 5.000,  'length_cm' => 45, 'width_cm' => 30, 'height_cm' => 25, 'is_heavy' => true,  'is_fragile' => false, 'stock' => 350, 'desc' => 'Bột giặt OMO thùng 12 túi 800g'],
            ['sku' => 'GD-002', 'name' => 'Thùng nước rửa chén Sunlight (12 chai)', 'price' => 360000, 'weight_kg' => 4.800, 'length_cm' => 40, 'width_cm' => 28, 'height_cm' => 22, 'is_heavy' => false, 'is_fragile' => false, 'stock' => 400, 'desc' => 'Nước rửa chén Sunlight thùng 12 chai 400ml'],
            ['sku' => 'GD-003', 'name' => 'Thùng giấy vệ sinh (12 cuộn)',        'price' => 85000,   'weight_kg' => 2.000,  'length_cm' => 40, 'width_cm' => 30, 'height_cm' => 40, 'is_heavy' => false, 'is_fragile' => false, 'stock' => 600, 'desc' => 'Giấy vệ sinh thùng 12 cuộn đôi'],
            ['sku' => 'GD-004', 'name' => 'Thùng xà bông Lifebuoy (48 cục)',     'price' => 192000,  'weight_kg' => 1.500,  'length_cm' => 30, 'width_cm' => 20, 'height_cm' => 18, 'is_heavy' => false, 'is_fragile' => false, 'stock' => 500, 'desc' => 'Xà bông Lifebuoy thùng 48 cục 90g'],
            ['sku' => 'GD-005', 'name' => 'Thùng khăn giấy Pulppy (24 hộp)',     'price' => 168000,  'weight_kg' => 1.000,  'length_cm' => 45, 'width_cm' => 30, 'height_cm' => 30, 'is_heavy' => false, 'is_fragile' => false, 'stock' => 300, 'desc' => 'Khăn giấy Pulppy thùng 24 hộp'],

            // ── Mỹ phẩm ──
            ['sku' => 'MP-001', 'name' => 'Thùng kem dưỡng da (24 hũ)',          'price' => 720000,  'weight_kg' => 0.500,  'length_cm' => 25, 'width_cm' => 18, 'height_cm' => 15, 'is_heavy' => false, 'is_fragile' => true,  'stock' => 150, 'desc' => 'Kem dưỡng da thùng 24 hũ 50ml'],
            ['sku' => 'MP-002', 'name' => 'Thùng sữa rửa mặt (24 tuýp)',        'price' => 600000,  'weight_kg' => 0.800,  'length_cm' => 28, 'width_cm' => 20, 'height_cm' => 15, 'is_heavy' => false, 'is_fragile' => true,  'stock' => 200, 'desc' => 'Sữa rửa mặt thùng 24 tuýp 120ml'],
            ['sku' => 'MP-003', 'name' => 'Thùng son môi (48 cây)',              'price' => 960000,  'weight_kg' => 0.300,  'length_cm' => 22, 'width_cm' => 15, 'height_cm' => 12, 'is_heavy' => false, 'is_fragile' => true,  'stock' => 100, 'desc' => 'Son môi thùng 48 cây'],
            ['sku' => 'MP-004', 'name' => 'Thùng dầu gội TRESemmé (12 chai)',    'price' => 540000,  'weight_kg' => 4.800,  'length_cm' => 35, 'width_cm' => 25, 'height_cm' => 25, 'is_heavy' => false, 'is_fragile' => false, 'stock' => 250, 'desc' => 'Dầu gội TRESemmé thùng 12 chai 640ml'],
            ['sku' => 'MP-005', 'name' => 'Thùng sữa tắm Dove (12 chai)',       'price' => 480000,  'weight_kg' => 4.200,  'length_cm' => 35, 'width_cm' => 25, 'height_cm' => 22, 'is_heavy' => false, 'is_fragile' => false, 'stock' => 200, 'desc' => 'Sữa tắm Dove thùng 12 chai 530g'],

            // ── Đồ lạnh / đông ──
            ['sku' => 'DL-001', 'name' => 'Thùng xúc xích Vissan (50 cây)',     'price' => 250000,  'weight_kg' => 3.500,  'length_cm' => 30, 'width_cm' => 22, 'height_cm' => 20, 'is_heavy' => false, 'is_fragile' => true,  'stock' => 180, 'desc' => 'Xúc xích Vissan thùng 50 cây'],
            ['sku' => 'DL-002', 'name' => 'Thùng kem Wall (24 hộp)',             'price' => 420000,  'weight_kg' => 3.000,  'length_cm' => 35, 'width_cm' => 25, 'height_cm' => 22, 'is_heavy' => false, 'is_fragile' => true,  'stock' => 120, 'desc' => 'Kem Wall các vị thùng 24 hộp'],

            // ── Gia vị bổ sung ──
            ['sku' => 'GV-004', 'name' => 'Thùng nước tương Maggi (24 chai)',    'price' => 192000,  'weight_kg' => 5.400,  'length_cm' => 32, 'width_cm' => 24, 'height_cm' => 25, 'is_heavy' => true,  'is_fragile' => true,  'stock' => 280, 'desc' => 'Nước tương Maggi thùng 24 chai 300ml'],
        ];

        foreach ($products as $p) {
            Product::create([
                'warehouse_id'   => $warehouse->id,
                'sku'            => $p['sku'],
                'name'           => $p['name'],
                'description'    => $p['desc'],
                'price'          => $p['price'],
                'weight_kg'      => $p['weight_kg'],
                'length_cm'      => $p['length_cm'],
                'width_cm'       => $p['width_cm'],
                'height_cm'      => $p['height_cm'],
                'is_heavy'       => $p['is_heavy'],
                'is_fragile'     => $p['is_fragile'],
                'stock_quantity' => $p['stock'],
                'is_active'      => true,
            ]);
        }

        $this->command->info('✅ Seeded 30 products (thực phẩm, nước giải khát, gia vị, gia dụng, mỹ phẩm, đồ lạnh)');
    }
}
