<?php

namespace Database\Seeders;

use App\Models\User;
use App\Models\Warehouse;
use Illuminate\Database\Seeder;

class WarehouseSeeder extends Seeder
{
    /**
     * Seed 4 kho hàng tại HCM cho carrier.
     */
    public function run(): void
    {
        $carrier = User::where('role', 'carrier')->first();

        if (!$carrier) {
            $this->command->error('❌ Chưa có carrier user! Chạy UserSeeder trước.');
            return;
        }

        $warehouses = [
            [
                'name'          => 'Kho Trung Tâm Q7',
                'address'       => 'Lô C1, KCN Tân Thuận, Quận 7, TP.HCM',
                'latitude'      => 10.7380000,
                'longitude'     => 106.7220000,
                'contact_phone' => '0281234567',
            ],
            [
                'name'          => 'Kho Thủ Đức',
                'address'       => '15 Đường số 7, KCN Sóng Thần, Thủ Đức, TP.HCM',
                'latitude'      => 10.8510000,
                'longitude'     => 106.7560000,
                'contact_phone' => '0282345678',
            ],
            [
                'name'          => 'Kho Bình Tân',
                'address'       => '200 Kinh Dương Vương, Bình Tân, TP.HCM',
                'latitude'      => 10.7520000,
                'longitude'     => 106.6040000,
                'contact_phone' => '0283456789',
            ],
            [
                'name'          => 'Kho Quận 12',
                'address'       => '88 Quốc lộ 1A, Quận 12, TP.HCM',
                'latitude'      => 10.8680000,
                'longitude'     => 106.6420000,
                'contact_phone' => '0284567890',
            ],
        ];

        foreach ($warehouses as $wh) {
            Warehouse::create(array_merge($wh, [
                'user_id'   => $carrier->id,
                'is_active' => true,
            ]));
        }

        $this->command->info('✅ Seeded 4 warehouses (Q7, Thủ Đức, Bình Tân, Q12)');
    }
}
