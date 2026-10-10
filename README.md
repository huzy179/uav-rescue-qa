# FloodEye (flood-tiny-person)

Phát hiện người kích thước nhỏ từ ảnh UAV trong vùng ngập lụt, hướng tới xử lý trên thiết bị biên.
Mô hình nền: YOLO26 (`ultralytics`). Kế hoạch và tiến độ: [docs/ROADMAP.md](docs/ROADMAP.md). Kết quả đã có: [docs/results/](docs/results/).

## Cấu trúc

```
configs/            cấu hình; configs/experiments/ là một file cho mỗi thí nghiệm
shared/             dùng chung giữa edge và ground: đọc cấu hình, schema gói cảnh báo
edge/               chạy trên UAV: lấy mẫu khung hình, phát hiện, định vị, xác nhận, gửi cảnh báo
ground/             trạm mặt đất: FastAPI + SQLite + Leaflet
sim/                giả lập chuyến bay và đường truyền mạng
eval/               đánh giá AP/recall theo nhóm kích thước, báo cáo, biểu đồ
tools/              chuyển nhãn bộ dữ liệu, thống kê
scripts/            chạy baseline, SAHI, tính GSD, đo tốc độ
training/           huấn luyện (notebook Kaggle, yaml mô hình)
tests/              kiểm thử, chạy không cần mô hình
docker/             Dockerfile
data/, runs/        dữ liệu và kết quả chạy (không đưa lên git)
```

`edge/` và `ground/` hiện mới có phần khung; xem lịch ở ROADMAP.

## Cài đặt

Cần Python 3.10 trở lên. Chạy mọi lệnh từ thư mục gốc của dự án.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"      # máy cá nhân: đủ mọi thứ
# pip install -e ".[edge]"   # chỉ phần chạy trên UAV (Jetson: cài torch của NVIDIA trước)
# pip install -e ".[ground]" # chỉ trạm mặt đất
pytest
```

Dùng `uv` thì thay hai lệnh cuối bằng `uv venv --python 3.13` và `uv pip install -e ".[dev]"`.

Trên máy có GPU NVIDIA, cài bản `torch` đúng với phiên bản CUDA theo hướng dẫn tại https://pytorch.org trước.

### Kiểm tra GPU

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available(), '| MPS:', torch.backends.mps.is_available())"
```

Các script tự chọn thiết bị theo thứ tự CUDA, MPS, CPU; dùng `--device` để chỉ định. Trọng số `yolo26s.pt` được tự tải ở lần chạy đầu.

### Docker

```bash
docker compose build
docker compose run --rm dev scripts/gsd_calc.py
docker compose run --rm dev scripts/run_baseline.py --source data/samples
```

Ảnh `dev` chạy bằng CPU: container trên macOS không dùng được GPU Apple Silicon. Thư mục dự án được gắn vào `/app`, nên `data/`, `runs/` và trọng số nằm trên máy thật. Ảnh `edge`, `ground` và `edge-jetson` cho demo sẽ được thêm sau.

## Dữ liệu

### VisDrone2019-DET

```bash
mkdir -p data/raw/visdrone && cd data/raw/visdrone
curl -LO https://github.com/ultralytics/assets/releases/download/v0.0.0/VisDrone2019-DET-val.zip
unzip -q VisDrone2019-DET-val.zip && cd ../../..
python tools/convert_visdrone.py --src data/raw/visdrone/VisDrone2019-DET-val --split val
```

Kết quả trong `data/processed/visdrone/`: `images/val`, `labels/val` (một lớp `person`, gộp `pedestrian` và `people`), `ignore/val` (vùng bỏ qua của VisDrone, dùng khi đánh giá) và `stats_val.json`.

## Chạy thí nghiệm

Mỗi thí nghiệm có một file cấu hình trong `configs/experiments/`. Ví dụ E0, E1, E4 trên VisDrone val:

```bash
python scripts/run_baseline.py --config configs/experiments/E0_visdrone.yaml
python scripts/run_baseline.py --config configs/experiments/E1_visdrone.yaml
python scripts/run_sahi.py --config configs/experiments/E4_visdrone.yaml

D=data/processed/visdrone
python eval/eval_by_size.py --runs runs/visdrone/E0 runs/visdrone/E1 runs/visdrone/E4 \
    --images $D/images/val --labels $D/labels/val --ignore $D/ignore/val --iou 0.5 \
    --output runs/visdrone/eval_iou0.5
```

Tham số gõ trên dòng lệnh được ưu tiên hơn giá trị trong file cấu hình.

### Kết quả của một lần chạy

`run_baseline.py` và `run_sahi.py` ghi vào thư mục `--output`:

| File | Nội dung |
|---|---|
| `boxes.csv` | mỗi dòng một box: `image, method, imgsz, conf, width_px, height_px, x1, y1, x2, y2` (pixel trên ảnh gốc) |
| `per_image.csv` | mỗi dòng một ảnh: `image, method, imgsz, n_persons, infer_ms` |
| `summary.csv`, `box_size_hist.png` | tổng hợp và phân bố kích thước box |
| `imgsz_<N>/` hoặc `images/` | ảnh có vẽ box (tắt bằng `--no-images`) |
| `run_config.json` | phiên bản thư viện, model, mã băm trọng số, thiết bị, tham số |

`eval_by_size.py` ghi `eval_by_size.csv` và `eval_by_size.png`. Mỗi cấu hình có một dòng cho mọi kích thước và một dòng cho từng nhóm `<8`, `8-16`, `16-32`, `>32` px (cạnh ngắn của nhãn):

| Cột | Ý nghĩa |
|---|---|
| `AP` | AP nội suy 101 điểm tại ngưỡng `--iou` |
| `recall`, `precision` | tại ngưỡng `--conf` (mặc định 0,25) |
| `recall_max` | recall khi giữ mọi dự đoán |

Quy ước theo nhóm kích thước giống COCO: nhãn ngoài nhóm được bỏ qua. Dự đoán rơi vào vùng bỏ qua (`--ignore`) không bị tính là sai.

### Các lưu ý khi đo

- Dự đoán để tính AP chạy với `conf: 0.001` và `max_det: 1000`.
- `infer_ms` là thời gian một lần gọi suy luận, gồm tiền và hậu xử lý, bỏ lượt làm nóng. Đo trên Mac chỉ để so sánh tương đối.
- SAHI mặc định gộp thêm một lượt suy luận toàn ảnh; `--no-standard-pred` tắt lượt này.

## Công cụ khác

```bash
python scripts/gsd_calc.py                                  # mặc định: 82° góc chéo (Matrice 4T), video 4K
python scripts/gsd_calc.py --fov-type horizontal --fov-deg 74 --tilt-deg 30
python scripts/benchmark_speed.py --model yolo26s.pt --imgsz 640 1280
```

Trên Jetson (chưa chạy thử, cần thiết bị):

```bash
yolo export model=yolo26s.pt format=engine half=True imgsz=1280 device=0
python scripts/benchmark_speed.py --model yolo26s.engine --imgsz 1280
```
