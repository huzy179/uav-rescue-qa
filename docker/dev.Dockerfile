# Ảnh CPU để chạy các script đánh giá (không dùng được GPU của máy Mac bên trong container).
# Ảnh edge, ground và edge-jetson sẽ được thêm khi hai gói đó có mã (xem docs/ROADMAP.md, mục 2).
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
RUN pip install torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cpu

COPY pyproject.toml .
COPY shared ./shared
COPY edge ./edge
COPY ground ./ground
COPY sim ./sim
COPY eval ./eval
RUN pip install -e ".[dev]"

COPY scripts ./scripts
COPY tools ./tools

ENTRYPOINT ["python"]
CMD ["scripts/gsd_calc.py"]
