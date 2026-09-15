<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class OrderItem extends Model
{
    protected $fillable = [
        'order_id',
        'product_id',
        'quantity',
        'unit_price',
        'subtotal',
        'item_weight_kg',
        'item_volume_cm3',
    ];

    protected function casts(): array
    {
        return [
            'quantity' => 'integer',
            'unit_price' => 'decimal:2',
            'subtotal' => 'decimal:2',
            'item_weight_kg' => 'decimal:3',
            'item_volume_cm3' => 'decimal:2',
        ];
    }

    // ── Relationships ──

    /**
     * Đơn hàng chứa item này.
     */
    public function order(): BelongsTo
    {
        return $this->belongsTo(Order::class);
    }

    /**
     * Sản phẩm tham chiếu.
     */
    public function product(): BelongsTo
    {
        return $this->belongsTo(Product::class);
    }

    /**
     * Kế hoạch xếp hàng cho item này.
     */
    public function loadingPlans(): HasMany
    {
        return $this->hasMany(LoadingPlan::class);
    }
}
