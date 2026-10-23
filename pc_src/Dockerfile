#FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04
#ENV DEBIAN_FRONTEND=noninteractive
#RUN apt-get update && apt-get install -y \
#    python3 \
#    python3-pip \
#    python3-dev \
#    python3-paho-mqtt \
#    ffmpeg \
#    libsm6 \
#    libxext6 \
#    libglib2.0-0 \
#    libgl1 \
#    build-essential \
#    git \
#    curl \
#    && rm -rf /var/lib/apt/lists/*
#WORKDIR /app
#COPY requirements.txt .
#RUN pip3 install --upgrade pip \
#    && pip3 install -r requirements.txt
#COPY . .
#CMD ["python3", "yoloTrafficDetectionSystem_PC_GPU.py"]
# Use official Ultralytics image with CUDA support for GPU inference
FROM ultralytics/ultralytics:latest
WORKDIR /app
# Install system dependencies for PostgreSQL and OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
# Copy and install Python requirements
COPY pc_src/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt python-dotenv psycopg2-binary paho-mqtt shapely
# Copy shared 'common' package and PC source scripts
COPY common/ ./common/
COPY pc_src/ ./pc_src/
# Ensure Python sees the root directory to import 'common'
ENV PYTHONPATH=/app
# Run the GPU detection script by default
CMD ["python3", "pc_src/yoloTrafficDetectionSystem_PC_GPU.py"]