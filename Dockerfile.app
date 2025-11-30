FROM python:3.11-slim

# Установка всех необходимых системных зависимостей для OpenCV и других библиотек
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-dev \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libglu1-mesa \
    libglib2.0-0 \
    libgtk-3-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libatlas-base-dev \
    gfortran \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create data directory for persistent storage (database, etc.)
RUN mkdir -p /app/data && chmod 755 /app/data

COPY vertex-ar/requirements-simple.txt .
RUN pip install --no-cache-dir -r requirements-simple.txt

COPY vertex-ar/ .

EXPOSE 8000

# Use shell form to allow environment variable expansion
# Default workers calculated at runtime based on CPU count
CMD uvicorn app.main:app \
    --host ${APP_HOST:-0.0.0.0} \
    --port ${APP_PORT:-8000} \
    --workers ${UVICORN_WORKERS:-$(python -c "import psutil; print((2 * (psutil.cpu_count() or 1)) + 1)")} \
    --timeout-keep-alive ${UVICORN_TIMEOUT_KEEP_ALIVE:-5} \
    --backlog ${UVICORN_BACKLOG:-2048} \
    $(if [ "${UVICORN_LIMIT_CONCURRENCY:-0}" != "0" ]; then echo "--limit-concurrency ${UVICORN_LIMIT_CONCURRENCY}"; fi) \
    $(if [ "${UVICORN_PROXY_HEADERS:-true}" = "true" ]; then echo "--proxy-headers"; fi) \
    --timeout-graceful-shutdown ${UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN:-30}