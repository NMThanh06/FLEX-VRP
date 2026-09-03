<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

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

    protected $casts = [
        'time_window_start' => 'datetime',
        'time_window_end' => 'datetime',
    ];

    public function retailer()
    {
        return $this->belongsTo(User::class, 'retailer_id');
    }

    public function warehouse()
    {
        return $this->belongsTo(Warehouse::class);
    }

    public function items()
    {
        return $this->hasMany(OrderItem::class);
    }
}
