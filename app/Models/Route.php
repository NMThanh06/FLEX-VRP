<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Route extends Model
{
    protected $fillable = [
        'route_code',
        'carrier_id',
        'vehicle_id',
        'delivery_date',
        'period_index',
        'total_distance_km',
        'total_duration_min',
        'total_load_kg',
        'status',
        'solver_metadata',
    ];

    protected function casts(): array
    {
        return [
            'delivery_date' => 'date',
            'period_index' => 'integer',
            'total_distance_km' => 'decimal:2',
            'total_duration_min' => 'decimal:2',
            'total_load_kg' => 'decimal:2',
            'solver_metadata' => 'array',
        ];
    }

    // ── Relationships ──

    /**
     * Carrier tạo tuyến đường.
     */
    public function carrier(): BelongsTo
    {
        return $this->belongsTo(User::class, 'carrier_id');
    }

    /**
     * Xe chạy tuyến đường.
     */
    public function vehicle(): BelongsTo
    {
        return $this->belongsTo(Vehicle::class);
    }

    /**
     * Các điểm dừng trên tuyến.
     */
    public function stops(): HasMany
    {
        return $this->hasMany(RouteStop::class)->orderBy('stop_sequence');
    }

    /**
     * Kế hoạch xếp hàng trên tuyến.
     */
    public function loadingPlans(): HasMany
    {
        return $this->hasMany(LoadingPlan::class);
    }
}
