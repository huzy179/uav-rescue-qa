# uav-flood-person

Phát hiện người kích thước nhỏ từ ảnh UAV trong vùng ngập lụt, hướng tới chạy trên thiết bị biên (Jetson).
Mô hình nền: YOLO26 (thư viện `ultralytics`). Giai đoạn hiện tại chỉ chạy thử baseline với trọng số COCO có sẵn, chưa huấn luyện.

## Cấu trúc

```
configs/      cấu hình thí nghiệm (YAML, dùng với --config)
scripts/      script chạy từ dòng lệnh
src/uavdet/   mã dùng chung (đọc ảnh/video, vẽ box, CSV, thống kê)
eval/         đánh giá so với nhãn (AP, recall theo nhóm kích thước)
training/     mã huấn luyện
notebooks/    notebook phân tích
data/         dữ liệu (không đưa lên git)
runs/         kết quả chạy (không đưa lên git)
```

## Cài đặt

Cần Python 3.10 trở lên. Chạy mọi lệnh từ thư mục gốc của dự án.

Dùng `venv`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Hoặc dùng `uv`:

```bash
uv venv --python 3.13
source .venv/bin/activate
uv pip install -r requirements.txt
```

Trên máy có GPU NVIDIA, cài bản `torch` đúng với phiên bản CUDA theo hướng dẫn tại https://pytorch.org trước khi cài `requirements.txt`.
Trên Jetson, dùng bản `torch` do NVIDIA phát hành cho JetPack.

## Chạy bằng Docker

Không cần cài Python trên máy; chỉ cần Docker (Docker Desktop hoặc OrbStack) đang chạy.

```bash
docker compose build
docker compose run --rm uavdet scripts/gsd_calc.py
docker compose run --rm uavdet scripts/run_baseline.py --source data/samples
docker compose run --rm uavdet scripts/run_sahi.py --source data/samples
```

Thư mục dự án được gắn vào `/app` trong container, nên `data/`, `runs/` và file trọng số nằm trên máy thật và mã nguồn sửa xong là dùng được ngay, không phải build lại. Chỉ build lại khi đổi `requirements.txt`.

Ảnh Docker này chạy bằng CPU. Container trên macOS không dùng được GPU của Apple Silicon (MPS), nên thời gian suy luận sẽ chậm hơn chạy trực tiếp bằng `.venv`.

## Kiểm tra GPU

```bash
python -c "import torch; print('torch', torch.__version__); print('CUDA:', torch.cuda.is_available()); print('MPS:', torch.backends.mps.is_available())"
yolo checks
```

Các script tự chọn thiết bị theo thứ tự CUDA, MPS (Apple Silicon), CPU. Dùng `--device` để chỉ định.

## Chạy

Trọng số (`yolo26s.pt`) được tự tải về thư mục hiện tại ở lần chạy đầu tiên.

### Baseline ở nhiều imgsz

```bash
python scripts/run_baseline.py --source data/samples
python scripts/run_baseline.py --source data/video.mp4 --imgsz 640 1280 1920 --conf 0.25 --vid-stride 10
```

Kết quả trong `runs/baseline/`:

| File | Nội dung |
|---|---|
| `imgsz_<N>/` | ảnh có vẽ box |
| `boxes.csv` | mỗi dòng một box: `image, method, imgsz, conf, width_px, height_px, x1, y1, x2, y2` (pixel trên ảnh gốc) |
| `per_image.csv` | mỗi dòng một ảnh: `image, method, imgsz, n_persons, infer_ms` |
| `summary.csv` | tổng số phát hiện, thời gian trung bình, số box theo nhóm kích thước |
| `box_size_hist.png` | phân bố kích thước box, so sánh các imgsz |
| `run_config.json` | phiên bản thư viện, model, thiết bị, tham số |

`infer_ms` là thời gian đo bằng đồng hồ cho một lần gọi suy luận, gồm cả tiền xử lý và hậu xử lý, không gồm đọc ảnh và lượt chạy làm nóng.

### SAHI

```bash
python scripts/run_sahi.py --source data/samples
python scripts/run_sahi.py --source data/samples --slice-size 640 --overlap 0.2 --no-standard-pred
```

Kết quả trong `runs/baseline/sahi/`, cùng định dạng với baseline (`method = sahi`, cột `imgsz` là kích thước lát cắt; ảnh nằm trong `images/`).
SAHI mặc định gộp thêm một lượt suy luận trên toàn ảnh; `--no-standard-pred` tắt lượt này.

Gộp hai kết quả để so sánh:

```python
import pandas as pd
boxes = pd.concat([pd.read_csv("runs/baseline/boxes.csv"), pd.read_csv("runs/baseline/sahi/boxes.csv")])
```

### Tính GSD

```bash
python scripts/gsd_calc.py
python scripts/gsd_calc.py --fov-deg 84 --width-px 3840 --altitudes 30 50 80 100 120 --imgsz 640
```

In bảng và lưu `runs/gsd/gsd_table.csv`. Công thức: `W = 2h·tan(FOV/2)`, `GSD = W / width_px`. Mặc định coi `--fov-deg` là góc ngang và camera chụp thẳng đứng.

```bash
python scripts/gsd_calc.py --fov-type diagonal --height-px 2160 --tilt-deg 30
```

`--fov-type diagonal` quy đổi góc chéo về góc ngang theo tỉ lệ khung hình. `--tilt-deg` là góc nghiêng so với phương thẳng đứng; khi đó bảng tính tại tâm ảnh với khoảng cách xiên `h / cos(góc nghiêng)`, phần ảnh xa hơn tâm sẽ có người nhỏ hơn.

### Dùng file cấu hình

`run_baseline.py` và `run_sahi.py` nhận `--config <file.yaml>`; khoá trong file trùng tên tham số, tham số gõ trên dòng lệnh được ưu tiên.

```bash
python scripts/run_baseline.py --config configs/baseline.yaml
python scripts/run_baseline.py --config configs/baseline.yaml --imgsz 1920
```

### Đánh giá so với nhãn

Cần nhãn định dạng YOLO (`class cx cy w h` chuẩn hoá, mỗi ảnh một file `.txt` cùng tên). Chạy dự đoán với ngưỡng conf rất thấp và không lưu ảnh, rồi đánh giá:

```bash
python scripts/run_baseline.py --config configs/baseline_eval.yaml --source data/val/images
python scripts/run_sahi.py --config configs/sahi_eval.yaml --source data/val/images
python eval/eval_by_size.py --runs runs/eval_preds/full runs/eval_preds/sahi_640 \
    --images data/val/images --labels data/val/labels --gt-classes 0
```

Kết quả trong `runs/eval/`: `eval_by_size.csv` và `eval_by_size.png`. Mỗi cấu hình có một dòng cho mọi kích thước và một dòng cho từng nhóm `<8`, `8-16`, `16-32`, `>32` px (cạnh ngắn của nhãn):

| Cột | Ý nghĩa |
|---|---|
| `n_gt` | số nhãn trong nhóm |
| `AP` | AP nội suy 101 điểm tại ngưỡng `--iou` (mặc định 0,5) |
| `recall`, `precision` | tại ngưỡng `--conf` (mặc định 0,25) |
| `recall_max` | recall khi giữ mọi dự đoán |

Quy ước theo nhóm kích thước giống COCO: nhãn ngoài nhóm được bỏ qua, dự đoán khớp với chúng không bị tính là sai. `--gt-classes` nhận nhiều mã lớp nếu bộ dữ liệu tách người thành nhiều lớp.

### Đo tốc độ

```bash
python scripts/benchmark_speed.py --model yolo26s.pt --imgsz 640 1280 1920
```

Đo thời gian mỗi lần gọi suy luận (gồm tiền và hậu xử lý) trên một ảnh 3840x2160, in trung bình, trung vị, p95 và FPS, lưu `runs/benchmark/benchmark.csv`.

Trên Jetson, xuất TensorRT rồi đo bằng cùng script (phần này chưa được chạy thử, vì cần thiết bị Jetson):

```bash
yolo export model=yolo26s.pt format=engine half=True imgsz=1280 device=0
python scripts/benchmark_speed.py --model yolo26s.engine --imgsz 1280
```
