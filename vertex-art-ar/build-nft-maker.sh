#!/bin/bash

# Скрипт для сборки Docker-образа для генерации NFT-маркеров

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker before running this script."
    exit 1
fi

echo "Создание Docker-образа для генерации NFT-маркеров..."

# Check if required files exist
if [ ! -f "generate-nft.js" ]; then
    echo "Error: generate-nft.js not found in current directory"
    exit 1
fi

if [ ! -f "nft_maker.py" ]; then
    echo "Error: nft_maker.py not found in current directory"
    exit 1
fi

# Создаем временный файл Dockerfile
cat > /tmp/Dockerfile.nft-maker-tmp << 'EOF'
FROM node:16-alpine

# Установка зависимостей
RUN apk add --no-cache \
    python3 \
    py3-pip \
    g++ \
    make \
    py3-numpy \
    py3-pillow \
    git \
    build-base \
    openblas-dev

# Создаем директорию для работы
WORKDIR /app

# Устанавливаем Python зависимости
RUN pip3 install numpy pillow

# Клонируем репозиторий ar.js
RUN git clone https://github.com/AR-js-org/AR.js.git /tmp/AR.js

# Устанавливаем зависимости для генерации NFT-маркеров
RUN cd /tmp/AR.js && npm install

# Копирование скриптов для генерации маркеров
COPY generate-nft.js /app/generate-nft.js
COPY nft_maker.py /app/nft_maker.py

# Точка входа
ENTRYPOINT ["node", "/app/generate-nft.js"]
EOF

# Собираем Docker-образ
if docker build -f /tmp/Dockerfile.nft-maker-tmp -t nft-maker .; then
    echo "Docker-образ nft-maker успешно создан"
    
    # Проверяем, что образ существует
    if docker image inspect nft-maker &> /dev/null; then
        echo "Образ nft-maker проверен и готов к использованию"
    else
        echo "Ошибка: Образ nft-maker не найден после сборки"
        exit 1
    fi
else
    echo "Ошибка при сборке Docker-образа"
    exit 1
fi

# Удаляем временный файл
rm /tmp/Dockerfile.nft-maker-tmp

echo "Docker-образ nft-maker успешно создан"