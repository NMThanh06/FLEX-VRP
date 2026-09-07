<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('orders', function (Blueprint $table) {
            $table->id();
            $table->string('order_code', 30)->unique();
            $table->foreignId('retailer_id')->constrained('users')->cascadeOnDelete();
            $table->foreignId('warehouse_id')->constrained('warehouses')->cascadeOnDelete();
            $table->enum('status', [
                'pending', 'confirmed', 'optimizing',
                'scheduled', 'in_transit', 'delivered', 'cancelled'
            ])->default('pending');
            $table->decimal('total_weight_kg', 12, 3)->default(0);
            $table->decimal('total_volume_cm3', 15, 2)->default(0);
            $table->decimal('total_amount', 15, 2)->default(0);      // VND
            $table->dateTime('time_window_start');
            $table->dateTime('time_window_end');
            $table->text('notes')->nullable();
            $table->timestamps();

            $table->index('retailer_id');
            $table->index('warehouse_id');
            $table->index('status');
            $table->index(['time_window_start', 'time_window_end']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('orders');
    }
};
