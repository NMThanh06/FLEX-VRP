<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Order extends Model
{
    protected $fillable = [
        'order_code',
        'retailer_id',
        'warehouse_id',
        'status',
        'total_weight_kg',
        'total_volume_cm3',
        'total_amount',
        'time_window_start',
        'time_window_end',
        'notes',
    ];

    protected function casts(): array
    {
        return [
            'total_weight_kg' => 'decimal:3',
            'total_volume_cm3' => 'decimal:2',
            'total_amount' => 'decimal:2',
            'time_window_start' => 'datetime',
            'time_window_end' => 'datetime',
        ];
    }

    // ── Relationships ──

    /**
     * Retailer đặt đơn hàng này.
     */
    public function retailer(): BelongsTo
    {
        return $this->belongsTo(User::class, 'retailer_id');
    }

    /**
     * Kho xuất hàng.
     */
    public function warehouse(): BelongsTo
    {
        return $this->belongsTo(Warehouse::class);
    }

    /**
     * Chi tiết sản phẩm trong đơn hàng.
     */
    public function items(): HasMany
    {
        return $this->hasMany(OrderItem::class);
    }

    /**
     * Điểm dừng giao hàng liên quan đến đơn.
     */
    public function routeStops(): HasMany
    {
        return $this->hasMany(RouteStop::class);
    }
}
