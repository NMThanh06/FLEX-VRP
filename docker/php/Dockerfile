FROM php:8.2-fpm

# Arguments
ARG USER_ID=1000
ARG GROUP_ID=1000

# Set working directory
WORKDIR /var/www/html

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    libpng-dev \
    libjpeg-dev \
    libfreetype6-dev \
    libonig-dev \
    libxml2-dev \
    libzip-dev \
    libicu-dev \
    zip \
    unzip \
    supervisor \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install \
        pdo_mysql \
        mbstring \
        exif \
        pcntl \
        bcmath \
        gd \
        zip \
        intl \
        opcache \
    && pecl install redis \
    && docker-php-ext-enable redis \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Composer
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# Install Node.js 24.x (LTS)
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create system user
RUN groupadd -g ${GROUP_ID} flexvrp \
    && useradd -u ${USER_ID} -g flexvrp -m -s /bin/bash flexvrp \
    && chown -R flexvrp:flexvrp /var/www/html

# PHP configuration
COPY docker/php/php.ini /usr/local/etc/php/conf.d/custom.ini

# Fix PHP-FPM listen address
RUN echo "[www]\nlisten = 0.0.0.0:9000" > /usr/local/etc/php-fpm.d/zz-custom.conf

# Switch to non-root user
USER flexvrp

EXPOSE 9000
CMD ["php-fpm"]
