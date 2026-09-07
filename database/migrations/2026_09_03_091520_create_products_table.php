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
        Schema::create('products', function (Blueprint $table) {
            $table->id();
            $table->foreignId('warehouse_id')->constrained('warehouses')->cascadeOnDelete();
            $table->string('sku', 50)->unique();
            $table->string('name');
            $table->text('description')->nullable();
            $table->decimal('price', 15, 2)->default(0);            // VND
            $table->decimal('weight_kg', 10, 3);                     // Khối lượng
            $table->decimal('length_cm', 10, 2);                     // Dài
            $table->decimal('width_cm', 10, 2);                      // Rộng
            $table->decimal('height_cm', 10, 2);                     // Cao
            $table->boolean('is_heavy')->default(false);             // Hàng nặng
            $table->boolean('is_fragile')->default(false);           // Hàng dễ vỡ
            $table->unsignedInteger('stock_quantity')->default(0);
            $table->boolean('is_active')->default(true);
            $table->timestamps();

            $table->index('warehouse_id');
            $table->index(['is_active', 'stock_quantity']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('products');
    }
};
