#!/bin/bash
# ============================================
# FLEX-VRP — Entrypoint Script
# Chạy tự động khi container app khởi động
# ============================================

set -e

echo "🚀 FLEX-VRP: Bắt đầu khởi tạo..."

# 1. Copy .env nếu chưa có
if [ ! -f .env ]; then
    echo "📄 Tạo file .env từ .env.example..."
    cp .env.example .env
fi

# 2. Cài đặt Composer dependencies
if [ ! -d vendor ]; then
    echo "📦 Cài đặt Composer dependencies..."
    composer install --no-interaction --optimize-autoloader
fi

# 3. Generate APP_KEY nếu chưa có
if grep -q "APP_KEY=$" .env 2>/dev/null || grep -q "APP_KEY=base64:$" .env 2>/dev/null; then
    echo "🔑 Generate APP_KEY..."
    php artisan key:generate --force
fi

# 4. Cài đặt NPM dependencies
if [ ! -d node_modules ]; then
    echo "📦 Cài đặt NPM dependencies..."
    npm install
fi

# 5. Chờ MySQL sẵn sàng
echo "⏳ Chờ MySQL khởi động..."
max_retries=30
retry=0
until php artisan db:monitor --databases=mysql > /dev/null 2>&1 || [ $retry -ge $max_retries ]; do
    retry=$((retry + 1))
    echo "  Đang chờ MySQL... ($retry/$max_retries)"
    sleep 2
done

if [ $retry -ge $max_retries ]; then
    echo "⚠️  Không kết nối được MySQL sau ${max_retries} lần thử. Tiếp tục khởi động..."
fi

# 6. Chạy Database Migration
echo "🗄️  Chạy Database Migration..."
php artisan migrate --force 2>/dev/null || echo "⚠️  Migration failed hoặc đã chạy rồi."

# 7. Cache config cho performance
echo "⚡ Cache config..."
php artisan config:cache
php artisan route:cache
php artisan view:cache

# 8. Phân quyền storage
echo "📁 Phân quyền storage & cache..."
chmod -R 775 storage bootstrap/cache 2>/dev/null || true

echo ""
echo "✅ ═══════════════════════════════════════════"
echo "   FLEX-VRP đã sẵn sàng!"
echo "   🌐 App:   http://localhost:8000"
echo "   🗄️  MySQL: localhost:3306"
echo "   🔴 Redis: localhost:6379"
echo "═══════════════════════════════════════════════"
echo ""

# Chạy command truyền vào (php-fpm)
exec "$@"
