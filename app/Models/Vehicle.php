<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Casts\Attribute;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Vehicle extends Model
{
    protected $fillable = [
        'user_id',
        'license_plate',
        'name',
        'max_weight_kg',
        'max_length_cm',
        'max_width_cm',
        'max_height_cm',
        'status',
        'cost_per_km',
    ];

    protected function casts(): array
    {
        return [
            'max_weight_kg' => 'decimal:2',
            'max_length_cm' => 'decimal:2',
            'max_width_cm' => 'decimal:2',
            'max_height_cm' => 'decimal:2',
            'cost_per_km' => 'decimal:2',
        ];
    }

    // ── Computed Attributes ──

    /**
     * Thể tích tối đa thùng xe tính từ L × W × H (cm³).
     * Dùng accessor thay vì storedAs để linh hoạt (MySQL cũng hỗ trợ storedAs).
     */
    protected function maxVolumeCm3(): Attribute
    {
        return Attribute::make(
            get: fn () => round($this->max_length_cm * $this->max_width_cm * $this->max_height_cm, 2),
        );
    }

    // ── Relationships ──

    /**
     * Carrier sở hữu xe này.
     */
    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    /**
     * Các tuyến đường xe đã chạy.
     */
    public function routes(): HasMany
    {
        return $this->hasMany(Route::class);
    }

    /**
     * Kế hoạch xếp hàng trên xe.
     */
    public function loadingPlans(): HasMany
    {
        return $this->hasMany(LoadingPlan::class);
    }
}
