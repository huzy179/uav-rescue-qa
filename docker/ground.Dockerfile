# Trạm mặt đất: FastAPI + SQLite, không có torch hay opencv (nhẹ).
FROM python:3.13-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    FLOODEYE_GROUND_DB=/data/ground.sqlite

WORKDIR /app
COPY pyproject.toml .
COPY shared ./shared
COPY ground ./ground
# setuptools tìm cả edge, sim, eval: tạo gói rỗng để cài được mà không chép mã của UAV.
RUN mkdir edge sim eval && touch edge/__init__.py sim/__init__.py eval/__init__.py \
    && pip install ".[ground]"

EXPOSE 8000
CMD ["uvicorn", "--factory", "ground.app:default_app", "--host", "0.0.0.0", "--port", "8000"]
