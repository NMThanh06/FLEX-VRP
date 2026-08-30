<!DOCTYPE html>
<html lang="vi">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <meta name="description"
        content="FLEX-VRP — Hệ thống tối ưu định tuyến giao hàng và xếp hàng 3D cho doanh nghiệp vận tải B2B">
    <title>FLEX-VRP — SmartLog B2B</title>
    @viteReactRefresh
    @vite(['resources/css/app.css', 'resources/js/app.jsx'])
</head>

<body>
    <div id="root"></div>
</body>

</html>