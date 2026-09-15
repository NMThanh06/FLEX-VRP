<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Casts\Attribute;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Product extends Model
{
    protected $fillable = [
        'warehouse_id',
        'sku',
        'name',
        'description',
        'price',
        'weight_kg',
        'length_cm',
        'width_cm',
        'height_cm',
        'is_heavy',
        'is_fragile',
        'stock_quantity',
        'is_active',
    ];

    protected function casts(): array
    {
        return [
            'price' => 'decimal:2',
            'weight_kg' => 'decimal:3',
            'length_cm' => 'decimal:2',
            'width_cm' => 'decimal:2',
            'height_cm' => 'decimal:2',
            'is_heavy' => 'boolean',
            'is_fragile' => 'boolean',
            'stock_quantity' => 'integer',
            'is_active' => 'boolean',
        ];
    }

    // ── Computed Attributes ──

    /**
     * Thể tích sản phẩm tính từ L × W × H (cm³).
     */
    protected function volumeCm3(): Attribute
    {
        return Attribute::make(
            get: fn () => round($this->length_cm * $this->width_cm * $this->height_cm, 2),
        );
    }

    // ── Relationships ──

    /**
     * Kho chứa sản phẩm này.
     */
    public function warehouse(): BelongsTo
    {
        return $this->belongsTo(Warehouse::class);
    }

    /**
     * Chi tiết đơn hàng chứa sản phẩm này.
     */
    public function orderItems(): HasMany
    {
        return $this->hasMany(OrderItem::class);
    }
}
