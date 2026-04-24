FROM python:3.11-slim AS base

# System deps: ffmpeg + libs for easyocr / torch CPU
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create media dir
RUN mkdir -p /data/media

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
