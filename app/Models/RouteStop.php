<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class RouteStop extends Model
{
    protected $fillable = [
        'route_id',
        'order_id',
        'stop_sequence',
        'latitude',
        'longitude',
        'address',
        'estimated_arrival',
        'estimated_departure',
        'actual_arrival',
        'distance_from_prev_km',
        'duration_from_prev_min',
        'status',
    ];

    protected function casts(): array
    {
        return [
            'stop_sequence' => 'integer',
            'latitude' => 'decimal:7',
            'longitude' => 'decimal:7',
            'estimated_arrival' => 'datetime',
            'estimated_departure' => 'datetime',
            'actual_arrival' => 'datetime',
            'distance_from_prev_km' => 'decimal:2',
            'duration_from_prev_min' => 'decimal:2',
        ];
    }

    // ── Relationships ──

    /**
     * Tuyến đường chứa điểm dừng này.
     */
    public function route(): BelongsTo
    {
        return $this->belongsTo(Route::class);
    }

    /**
     * Đơn hàng giao tại điểm dừng này.
     */
    public function order(): BelongsTo
    {
        return $this->belongsTo(Order::class);
    }
}
