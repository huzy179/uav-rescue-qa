# Ảnh chạy bằng CPU cho các script baseline (không dùng được GPU của máy Mac bên trong container).
FROM python:3.13-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    YOLO_CONFIG_DIR=/tmp/ultralytics \
    MPLCONFIGDIR=/tmp/matplotlib

# Thư viện hệ thống mà opencv-python cần.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cài torch bản CPU trước để pip không kéo bản CUDA nặng vài GB.
COPY requirements.txt .
RUN pip install torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

COPY src ./src
COPY scripts ./scripts

ENTRYPOINT ["python"]
CMD ["scripts/gsd_calc.py"]
