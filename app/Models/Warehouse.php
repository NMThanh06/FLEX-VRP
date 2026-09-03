<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Warehouse extends Model
{
    protected $fillable = [
        'user_id',
        'name',
        'address',
        'latitude',
        'longitude',
        'contact_phone',
        'is_active',
    ];

    public function user()
    {
        return $this->belongsTo(User::class);
    }

    public function products()
    {
        return $this->hasMany(Product::class);
    }
}
