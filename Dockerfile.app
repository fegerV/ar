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

COPY vertex-art-ar/requirements-simple.txt .
RUN pip install --no-cache-dir -r requirements-simple.txt

COPY vertex-art-ar/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]