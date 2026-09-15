<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class LoadingPlan extends Model
{
    protected $fillable = [
        'route_id',
        'order_item_id',
        'vehicle_id',
        'pos_x_cm',
        'pos_y_cm',
        'pos_z_cm',
        'length_cm',
        'width_cm',
        'height_cm',
        'rotation_axis',
        'loading_sequence',
    ];

    protected function casts(): array
    {
        return [
            'pos_x_cm' => 'decimal:2',
            'pos_y_cm' => 'decimal:2',
            'pos_z_cm' => 'decimal:2',
            'length_cm' => 'decimal:2',
            'width_cm' => 'decimal:2',
            'height_cm' => 'decimal:2',
            'rotation_axis' => 'integer',
            'loading_sequence' => 'integer',
        ];
    }

    // ── Relationships ──

    /**
     * Tuyến đường liên quan.
     */
    public function route(): BelongsTo
    {
        return $this->belongsTo(Route::class);
    }

    /**
     * Item hàng hóa được xếp.
     */
    public function orderItem(): BelongsTo
    {
        return $this->belongsTo(OrderItem::class);
    }

    /**
     * Xe chứa hàng.
     */
    public function vehicle(): BelongsTo
    {
        return $this->belongsTo(Vehicle::class);
    }
}
