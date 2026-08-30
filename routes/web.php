<?php

use Illuminate\Support\Facades\Route;

// Mọi route web đều trả về React SPA shell
// React Router sẽ tự xử lý điều hướng phía client
Route::get('/{any}', function () {
    return view('app');
})->where('any', '^(?!api).*$');
