<?php

namespace Database\Seeders;

use App\Models\User;
use App\Models\Vehicle;
use Illuminate\Database\Seeder;

class VehicleSeeder extends Seeder
{
    /**
     * Seed 4 xe tải cho carrier: 1T, 2.5T, 3.5T, 5T.
     */
    public function run(): void
    {
        $carrier = User::where('role', 'carrier')->first();

        if (!$carrier) {
            $this->command->error('❌ Chưa có carrier user! Chạy UserSeeder trước.');
            return;
        }

        $vehicles = [
            [
                'license_plate'  => '51C-12345',
                'name'           => 'Xe tải nhỏ 1T (Suzuki Carry)',
                'max_weight_kg'  => 1000.00,
                'max_length_cm'  => 300.00,   // Thùng: 300×160×160 cm
                'max_width_cm'   => 160.00,
                'max_height_cm'  => 160.00,
                'cost_per_km'    => 4500.00,   // VND/km
            ],
            [
                'license_plate'  => '51D-23456',
                'name'           => 'Xe tải trung 2.5T (Hyundai Porter)',
                'max_weight_kg'  => 2500.00,
                'max_length_cm'  => 430.00,   // Thùng: 430×190×185 cm
                'max_width_cm'   => 190.00,
                'max_height_cm'  => 185.00,
                'cost_per_km'    => 6500.00,
            ],
            [
                'license_plate'  => '51D-34567',
                'name'           => 'Xe tải 3.5T (Isuzu QKR)',
                'max_weight_kg'  => 3500.00,
                'max_length_cm'  => 450.00,   // Thùng: 450×195×195 cm
                'max_width_cm'   => 195.00,
                'max_height_cm'  => 195.00,
                'cost_per_km'    => 7500.00,
            ],
            [
                'license_plate'  => '51H-45678',
                'name'           => 'Xe tải lớn 5T (Isuzu NQR)',
                'max_weight_kg'  => 5000.00,
                'max_length_cm'  => 600.00,   // Thùng: 600×220×210 cm
                'max_width_cm'   => 220.00,
                'max_height_cm'  => 210.00,
                'cost_per_km'    => 9500.00,
            ],
        ];

        foreach ($vehicles as $v) {
            Vehicle::create(array_merge($v, [
                'user_id' => $carrier->id,
                'status'  => 'available',
            ]));
        }

        $this->command->info('✅ Seeded 4 vehicles: 1T, 2.5T, 3.5T, 5T');
    }
}
