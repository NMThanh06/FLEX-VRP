<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

class UserSeeder extends Seeder
{
    /**
     * Seed users: 1 Admin, 1 Carrier, 4 Retailers (tạp hóa HCM).
     */
    public function run(): void
    {
        // ── Admin ──
        User::create([
            'name'      => 'Admin FLEX-VRP',
            'email'     => 'admin@flex-vrp.vn',
            'password'  => Hash::make('password'),
            'role'      => 'admin',
            'phone'     => '0900000000',
            'address'   => 'Quận 7, TP.HCM',
        ]);

        // ── Carrier (Đơn vị vận chuyển) ──
        User::create([
            'name'      => 'Vận Tải SmartLog',
            'email'     => 'carrier@flex-vrp.vn',
            'password'  => Hash::make('password'),
            'role'      => 'carrier',
            'phone'     => '0901000000',
            'address'   => 'KCN Tân Thuận, Quận 7, TP.HCM',
            'latitude'  => 10.7380000,
            'longitude' => 106.7220000,
        ]);

        // ── Retailers (4 tiệm tạp hóa) ──
        $retailers = [
            [
                'name'      => 'Tạp hóa Chị Lan',
                'email'     => 'chilan@flex-vrp.vn',
                'phone'     => '0901234001',
                'address'   => '45 Nguyễn Huệ, Quận 1, TP.HCM',
                'latitude'  => 10.7760000,
                'longitude' => 106.6990000,
            ],
            [
                'name'      => 'Shop Mỹ Phẩm Hương',
                'email'     => 'huong@flex-vrp.vn',
                'phone'     => '0901234002',
                'address'   => '120 Võ Văn Tần, Quận 3, TP.HCM',
                'latitude'  => 10.7825000,
                'longitude' => 106.6925000,
            ],
            [
                'name'      => 'Đại lý Thực phẩm Minh',
                'email'     => 'minh@flex-vrp.vn',
                'phone'     => '0901234003',
                'address'   => '78 Trần Hưng Đạo, Quận 5, TP.HCM',
                'latitude'  => 10.7540000,
                'longitude' => 106.6630000,
            ],
            [
                'name'      => 'Cửa hàng Tiện Lợi 24h',
                'email'     => 'tienloi@flex-vrp.vn',
                'phone'     => '0901234004',
                'address'   => '200 Sư Vạn Hạnh, Quận 10, TP.HCM',
                'latitude'  => 10.7710000,
                'longitude' => 106.6680000,
            ],
        ];

        foreach ($retailers as $retailer) {
            User::create(array_merge($retailer, [
                'password' => Hash::make('password'),
                'role'     => 'retailer',
            ]));
        }

        $this->command->info('✅ Seeded 6 users: 1 Admin, 1 Carrier, 4 Retailers');
    }
}
