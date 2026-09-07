<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

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

    public function warehouse()
    {
        return $this->belongsTo(Warehouse::class);
    }
}
