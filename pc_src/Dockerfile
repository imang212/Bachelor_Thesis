## docker compose --profile gpu up --build
# Use official Ultralytics image with CUDA support for GPU inference
FROM ultralytics/ultralytics:8.3.0
WORKDIR /app
# Install system dependencies for PostgreSQL and OpenCV
RUN rm -f /etc/apt/sources.list.d/coral-edgetpu.list \
    && grep -rl "coral-edgetpu" /etc/apt/sources.list.d/ /etc/apt/sources.list 2>/dev/null | xargs -r rm -f \
    && apt-get update && apt-get install -y --no-install-recommends \
       libpq-dev gcc libgl1 libglib2.0-0 \
       pkg-config libcairo2-dev libgirepository1.0-dev \
       python3-gi gir1.2-gst-rtsp-server-1.0 \
       gstreamer1.0-tools \
       gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
       gstreamer1.0-plugins-bad gstreamer1.0-libav \
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