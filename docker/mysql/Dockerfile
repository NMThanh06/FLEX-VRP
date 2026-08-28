FROM mysql:8.0

# Custom MySQL configuration
COPY docker/mysql/my.cnf /etc/mysql/conf.d/custom.cnf

# Create initialization directory
RUN mkdir -p /docker-entrypoint-initdb.d
