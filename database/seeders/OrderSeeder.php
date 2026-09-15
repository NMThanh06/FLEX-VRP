<?php

namespace Database\Seeders;

use App\Models\Order;
use App\Models\OrderItem;
use App\Models\Product;
use App\Models\User;
use App\Models\Warehouse;
use Carbon\Carbon;
use Illuminate\Database\Seeder;
use Illuminate\Support\Str;

class OrderSeeder extends Seeder
{
    /**
     * Seed 6 đơn hàng mẫu cho kịch bản MVP.
     * 4 retailer đặt hàng, time windows khác nhau.
     */
    public function run(): void
    {
        $warehouse = Warehouse::where('name', 'Kho Trung Tâm Q7')->first();
        $retailers = User::where('role', 'retailer')->get();

        if (!$warehouse || $retailers->isEmpty()) {
            $this->command->error('❌ Chưa có kho hoặc retailer! Chạy WarehouseSeeder & UserSeeder trước.');
            return;
        }

        // Preload tất cả products để tra cứu SKU
        $products = Product::where('warehouse_id', $warehouse->id)->get()->keyBy('sku');

        $now = Carbon::now();

        $ordersConfig = [
            // ── ĐƠN LỚN (cần Split Delivery) ──
            [
                'retailer_idx' => 2,  // Đại lý Thực phẩm Minh (Q5)
                'code'         => 'ORD-' . $now->format('Ymd') . '-0001',
                'status'       => 'confirmed',
                'tw_start'     => $now->copy()->addDay()->setTime(7, 0),
                'tw_end'       => $now->copy()->addDay()->setTime(11, 0),
                'notes'        => 'Đơn lớn - cần chia nhiều ngày giao',
                'items'        => [
                    ['sku' => 'TP-001', 'qty' => 100],  // Mì Hảo Hảo
                    ['sku' => 'NGK-001', 'qty' => 80],  // Coca-Cola
                    ['sku' => 'NGK-005', 'qty' => 50],  // Sữa Vinamilk
                ],
            ],
            [
                'retailer_idx' => 3,  // Cửa hàng Tiện Lợi 24h (Q10)
                'code'         => 'ORD-' . $now->format('Ymd') . '-0002',
                'status'       => 'confirmed',
                'tw_start'     => $now->copy()->addDay()->setTime(8, 0),
                'tw_end'       => $now->copy()->addDay()->setTime(22, 0),
                'notes'        => 'Đơn lớn - giao giờ nào cũng được',
                'items'        => [
                    ['sku' => 'NGK-003', 'qty' => 120], // Bia Tiger
                    ['sku' => 'GV-002', 'qty' => 60],   // Dầu ăn Neptune
                ],
            ],

            // ── ĐƠN VỪA ──
            [
                'retailer_idx' => 0,  // Tạp hóa Chị Lan (Q1)
                'code'         => 'ORD-' . $now->format('Ymd') . '-0003',
                'status'       => 'confirmed',
                'tw_start'     => $now->copy()->addDay()->setTime(8, 0),
                'tw_end'       => $now->copy()->addDay()->setTime(12, 0),
                'notes'        => 'Giao buổi sáng, cửa trước',
                'items'        => [
                    ['sku' => 'NGK-002', 'qty' => 30],  // Nước Lavie
                    ['sku' => 'TP-003', 'qty' => 20],   // Bánh Oreo
                    ['sku' => 'GD-001', 'qty' => 15],   // Bột giặt OMO
                ],
            ],
            [
                'retailer_idx' => 1,  // Shop Mỹ Phẩm Hương (Q3)
                'code'         => 'ORD-' . $now->format('Ymd') . '-0004',
                'status'       => 'pending',
                'tw_start'     => $now->copy()->addDays(2)->setTime(9, 0),
                'tw_end'       => $now->copy()->addDays(2)->setTime(17, 0),
                'notes'        => 'Hàng dễ vỡ, xếp cẩn thận',
                'items'        => [
                    ['sku' => 'MP-001', 'qty' => 40],   // Kem dưỡng da
                    ['sku' => 'MP-002', 'qty' => 30],   // Sữa rửa mặt
                    ['sku' => 'MP-003', 'qty' => 15],   // Son môi
                ],
            ],

            // ── ĐƠN NHỎ (gom đơn cùng tuyến) ──
            [
                'retailer_idx' => 0,  // Tạp hóa Chị Lan (Q1) — đơn bổ sung
                'code'         => 'ORD-' . $now->format('Ymd') . '-0005',
                'status'       => 'confirmed',
                'tw_start'     => $now->copy()->addDay()->setTime(8, 0),
                'tw_end'       => $now->copy()->addDay()->setTime(12, 0),
                'notes'        => 'Đơn bổ sung, gom chung xe',
                'items'        => [
                    ['sku' => 'GD-003', 'qty' => 10],   // Giấy vệ sinh
                    ['sku' => 'GD-004', 'qty' => 8],    // Xà bông Lifebuoy
                ],
            ],
            [
                'retailer_idx' => 2,  // Đại lý Thực phẩm Minh (Q5) — đơn nhỏ
                'code'         => 'ORD-' . $now->format('Ymd') . '-0006',
                'status'       => 'pending',
                'tw_start'     => $now->copy()->addDays(2)->setTime(7, 0),
                'tw_end'       => $now->copy()->addDays(2)->setTime(11, 0),
                'notes'        => 'Đơn nhỏ bổ sung',
                'items'        => [
                    ['sku' => 'TP-008', 'qty' => 10],   // Muối I-ốt
                    ['sku' => 'GV-001', 'qty' => 30],   // Nước mắm Chinsu
                ],
            ],
        ];

        foreach ($ordersConfig as $oc) {
            $retailer = $retailers[$oc['retailer_idx']];

            // Tính tổng trước
            $totalWeight = 0;
            $totalVolume = 0;
            $totalAmount = 0;
            $itemsData = [];

            foreach ($oc['items'] as $itemCfg) {
                $product = $products[$itemCfg['sku']] ?? null;
                if (!$product) {
                    $this->command->warn("⚠️ Không tìm thấy sản phẩm SKU: {$itemCfg['sku']}");
                    continue;
                }

                $qty = $itemCfg['qty'];
                $unitPrice = $product->price;
                $subtotal = $qty * $unitPrice;
                $itemWeight = $qty * $product->weight_kg;
                $itemVolume = $qty * $product->volume_cm3;

                $totalWeight += $itemWeight;
                $totalVolume += $itemVolume;
                $totalAmount += $subtotal;

                $itemsData[] = [
                    'product_id'     => $product->id,
                    'quantity'       => $qty,
                    'unit_price'     => $unitPrice,
                    'subtotal'       => $subtotal,
                    'item_weight_kg' => $itemWeight,
                    'item_volume_cm3' => $itemVolume,
                ];
            }

            // Tạo đơn hàng
            $order = Order::create([
                'order_code'      => $oc['code'],
                'retailer_id'     => $retailer->id,
                'warehouse_id'    => $warehouse->id,
                'status'          => $oc['status'],
                'total_weight_kg' => $totalWeight,
                'total_volume_cm3' => $totalVolume,
                'total_amount'    => $totalAmount,
                'time_window_start' => $oc['tw_start'],
                'time_window_end'   => $oc['tw_end'],
                'notes'           => $oc['notes'],
            ]);

            // Tạo order items
            foreach ($itemsData as $itemData) {
                OrderItem::create(array_merge($itemData, [
                    'order_id' => $order->id,
                ]));
            }

            $itemCount = count($itemsData);
            $this->command->line("  📦 {$order->order_code}: {$retailer->name} — {$itemCount} SP, {$totalWeight}kg");
        }

        $this->command->info('✅ Seeded 6 orders (4 confirmed, 2 pending)');
    }
}
