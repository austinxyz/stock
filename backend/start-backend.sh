#!/bin/bash

# Load environment variables
export JWT_SECRET="stock-app-jwt-secret-key-change-this-in-production-use-256-bit-random-key"
export DB_PASSWORD="helloworld"
export DB_HOST="10.0.0.7"
export DB_PORT="37719"
export DB_NAME="stock"
export DB_USER="austinxu"

# Start Spring Boot
cd "$(dirname "$0")"
mvn spring-boot:run
