# FloodEye (flood-tiny-person)

Phát hiện người kích thước nhỏ từ ảnh UAV trong vùng ngập lụt, hướng tới xử lý trên thiết bị biên.
Mô hình nền: YOLO26 (`ultralytics`). Tổng quan dự án, các bước và lý do: [docs/TONG_QUAN.md](docs/TONG_QUAN.md). Kế hoạch và tiến độ: [docs/ROADMAP.md](docs/ROADMAP.md). Giải thích kỹ thuật: [docs/TECHNICAL.md](docs/TECHNICAL.md). Kết quả đã có: [docs/results/](docs/results/).

## Cấu trúc

```
configs/            cấu hình; configs/experiments/ là một file cho mỗi thí nghiệm
shared/             dùng chung giữa edge và ground: đọc cấu hình, schema gói cảnh báo
edge/               chạy trên UAV: lấy mẫu khung hình, phát hiện, định vị, xác nhận, gửi cảnh báo
ground/             trạm mặt đất: FastAPI + SQLite + Leaflet, gộp cảnh báo thành sự cố
sim/                giả lập chuyến bay và đường truyền mạng
eval/               đánh giá AP/recall theo nhóm kích thước, báo cáo, biểu đồ
tools/              chuyển nhãn bộ dữ liệu, thống kê
scripts/            chạy baseline, SAHI, tính GSD, đo tốc độ
training/           huấn luyện (notebook Kaggle, yaml mô hình)
tests/              kiểm thử, chạy không cần mô hình
docker/             Dockerfile
data/, runs/        dữ liệu và kết quả chạy (không đưa lên git)
```

`edge/` đã có đủ pipeline lấy mẫu → phát hiện → định vị → xác nhận → outbox cảnh báo; `ground/` nhận cảnh báo và hiện trên bản đồ. Xem lịch ở ROADMAP.

Demo hai phía trên một máy, một lệnh (trạm mặt đất + pipeline, rồi giữ bản đồ mở tới khi Ctrl+C):

```bash
scripts/demo.sh [video.mp4] [trọng số] [geo|track]   # mặc định afo_demo.mp4, yolo26s.pt, geo; track: tracking có số ID
```

Demo trực tiếp để trình bày: video phát trong cửa sổ, người được tô màu kèm số ID và vệt đường đi, bảng đếm người ở góc
(Space tạm dừng, Q thoát; trên WSL cửa sổ mở qua WSLg):

```bash
.venv/bin/python scripts/live_demo.py --source video.mp4 --model runs/train/E2_s0/weights/best.pt
```

Từng bước:

```bash
# 1. Trạm mặt đất, mở http://localhost:8000 (hoặc: docker compose up ground)
FLOODEYE_GROUND_DB=runs/ground/ground.sqlite .venv/bin/python -m uvicorn --factory ground.app:default_app --port 8000

# 2. UAV phát lại video; telemetry giả lập bay thẳng, hoặc --telemetry file.csv / file.SRT của DJI
.venv/bin/python -m edge.main --config configs/edge.yaml --source video.mp4 --output runs/edge/demo \
    --ground-url http://localhost:8000 --save-video
# thêm --net-loss 0.2 --net-outage 30 90 để giả lập mạng chập chờn
# thêm --target-person-px 10 để thu nhỏ khung theo độ cao trước khi phát hiện (mô hình fine-tune, TECHNICAL mục 4.5)

# 3. Chạy lại phần sau detector mà không cần mô hình (RQ3): đọc lại phát hiện đã lưu
.venv/bin/python -m edge.main --config configs/edge.yaml --source video.mp4 --replay runs/edge/demo/detections.jsonl \
    --n-confirm 5 --output runs/edge/demo_n5
```

Có file `.SRT` mới thì kiểm tra trước bộ đọc có hiểu định dạng không: `.venv/bin/python -m edge.telemetry DJI_0001.SRT`. Khi chạy với telemetry giả lập, video có dòng chữ "TELEMETRY GIA LAP" và `run_config.json` ghi `telemetry_source`.

Mỗi lần chạy ghi vào `--output`: `detections.jsonl`, `confirmations.jsonl`, `alerts.jsonl`, `alerts_sent.jsonl` (từng lần gửi, kể cả thất bại), `timings.jsonl` (ms từng chặng), `outbox.sqlite`, `run_config.json`.

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
mkdir -p data/raw/visdrone
for split in train val; do      # chỉ cần đánh giá thì để mỗi val
  (cd data/raw/visdrone && curl -LO https://github.com/ultralytics/assets/releases/download/v0.0.0/VisDrone2019-DET-$split.zip \
    && unzip -q VisDrone2019-DET-$split.zip && rm VisDrone2019-DET-$split.zip)
  python tools/convert_visdrone.py --src data/raw/visdrone/VisDrone2019-DET-$split --split $split
done
python tools/check_visdrone.py  # đối chiếu với nhãn gốc từng ảnh; ghi runs/data/visdrone_check.json
```

Kết quả trong `data/processed/visdrone/`: `images/<tập>`, `labels/<tập>` (một lớp `person`, gộp `pedestrian` và `people`), `ignore/<tập>` (vùng bỏ qua của VisDrone, dùng khi đánh giá) và `stats_<tập>.json`. `check_visdrone.py` thoát với mã 1 nếu có ảnh mà số người khác nhãn gốc hoặc nhãn sai định dạng (TECHNICAL mục 6.7).

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
| `AP_lo`, `AP_hi`, `recall_lo`, `recall_hi` | khoảng tin cậy 95%, bootstrap 1.000 lần theo ảnh (`--bootstrap 0` để tắt) |

Quy ước theo nhóm kích thước giống COCO: nhãn ngoài nhóm được bỏ qua. Dự đoán rơi vào vùng bỏ qua (`--ignore`) không bị tính là sai.

### Các lưu ý khi đo

- Dự đoán để tính AP chạy với `conf: 0.001` và `max_det: 1000`.
- `infer_ms` là thời gian một lần gọi suy luận, gồm tiền và hậu xử lý, bỏ lượt làm nóng. Đo trên Mac chỉ để so sánh tương đối.
- SAHI mặc định gộp thêm một lượt suy luận toàn ảnh; `--no-standard-pred` tắt lượt này.

## Huấn luyện

Huấn luyện thật chạy trên Kaggle bằng [notebooks/kaggle_train.ipynb](notebooks/kaggle_train.ipynb); notebook chỉ lấy mã, chuẩn bị dữ liệu và gọi lệnh dưới.

### Trên Kaggle

1. Tài khoản phải xác minh số điện thoại (để bật GPU và Internet).
2. **Create → New Notebook → File → Import Notebook**, dán link GitHub của `notebooks/kaggle_train.ipynb`. Khung bên phải: **Accelerator: GPU T4**, bật **Internet**.
3. Ô đầu: `COMMIT` là mã commit đầy đủ của mã huấn luyện, `CONFIG` là thí nghiệm cần chạy.
4. **Chạy thử:** để `MODE = "smoke"`, bấm **Run All** (1 epoch trên 1/4 dữ liệu, bật mosaic, khoảng 15 phút kể cả tải dữ liệu). Log phải có `Using 4 dataloader workers` và không có `out of memory`. Xong bấm **Stop session**.
5. **Chạy thật:** đổi `MODE = "train"`, đặt `EPOCHS` sao cho cả lần chạy dưới khoảng 10 giờ, rồi **Save Version → Save & Run All (Commit)**. Có thể đóng trình duyệt; theo dõi ở tab Versions.
6. Chạy xong, tải `runs/train/<mã>/` trong Output về cùng chỗ trên máy.

Lần huấn luyện dài hơn một phiên 12 giờ (E3 với đầu P2) thì chia phiên: phiên 1 đặt `STOP_AFTER` (E3: 32), giữ `EPOCHS` là tổng số epoch để lịch tốc độ học không đổi. Tải `runs/train/<mã>/weights/last_resume.pt` lên thành một Kaggle Dataset. Phiên 2 thì Add Input dataset đó, đặt `MODE = "resume"` và `STOP_AFTER = None` (TECHNICAL mục 13.5).

Các thông báo lỗi bỏ qua được và hành vi của ultralytics cần biết khi chạy trên Kaggle: TECHNICAL mục 13.5.

### Trên máy cá nhân

Chỉ chạy thử để kiểm tra mã:

```bash
python training/train.py --config configs/experiments/E2_s0.yaml          # cần VisDrone train đã chuyển nhãn
python training/train.py --config configs/experiments/E2_s0.yaml --imgsz 320 --epochs 1 --fraction 0.05   # chạy thử
python training/train.py --config configs/experiments/E2_s0.yaml --resume # chạy tiếp khi bị ngắt
```

Thư mục `--output` chứa trọng số (`weights/best.pt`), `results.csv`, `data.yaml` và `run_config.json`.

## Công cụ khác

```bash
python scripts/gsd_calc.py                                  # mặc định: 82° góc chéo (Matrice 4T), video 4K
python scripts/gsd_calc.py --fov-type horizontal --fov-deg 74 --tilt-deg 30
python scripts/benchmark_speed.py --model yolo26s.pt --imgsz 640 1280
```

So sánh hai lần chạy có ý nghĩa thống kê không (bootstrap cặp; thêm `--cluster-pattern '^(\d+)_'` để lấy mẫu theo video):

```bash
python eval/compare_runs.py --a runs/visdrone/E4 --b runs/visdrone/E4tiled \
    --images data/processed/visdrone/images/val --labels data/processed/visdrone/labels/val \
    --ignore data/processed/visdrone/ignore/val --output runs/visdrone/compare_E4_E4tiled
```

RQ3 bằng mô phỏng (TECHNICAL mục 11.3, 15.4): sinh kịch bản, chạy pipeline với một chiến lược xác nhận, chấm điểm:

```bash
python -m sim.make_rq3 --output runs/rq3/demo --gps-sigma-m 3 --seed 0
python -m edge.main --config configs/edge.yaml --source runs/rq3/demo/frames.mp4 --telemetry runs/rq3/demo/telemetry.csv \
    --replay runs/rq3/demo/detections.jsonl --confirm geo --output runs/rq3/demo/geo
python eval/rq3_metrics.py --run runs/rq3/demo/geo --truth runs/rq3/demo/ground_truth.json   # ghi runs/rq3/demo/geo/rq3_eval/
```

Quét cả lưới tham số × seed từ một file YAML, chạy tiếp được khi bị ngắt: `python -m sim.sweep_rq3 --config configs/experiments/rq3_gps.yaml --jobs 4` (kết quả `runs/rq3/gps/summary.csv`). Muốn detector giả có recall theo cỡ người thay cho recall cố định thì gọi `sim.make_rq3` với `--recall-curve runs/e6_sds/eval/recall_by_pixels.csv --recall-model E2c` (ví dụ ở `configs/experiments/rq3_altitude.yaml`).

Recall theo số pixel trên người (E6): thu nhỏ ảnh nhiều mức, cắt ô ở mỗi mức, rồi gộp lại theo cỡ người. Lệnh đầy đủ ở `docs/results/e6_sds_pilot.md`:

```bash
python tools/rescale_dataset.py --images data/processed/sds_det/images/val --labels data/processed/sds_det/labels/val \
    --dst data/processed/sds_rescale --factors 1 2 3 4 6
python eval/recall_by_pixels.py --data data/processed/sds_rescale --runs runs/e6_sds --models E1 E2c \
    --factors 1 2 3 4 6 --cluster-pattern '^(v\d+)_' --output runs/e6_sds/eval
```

Cắt ô có thu nhỏ theo độ cao. Độ cao của từng ảnh đọc từ CSV có cột `image, alt_agl_m`; `tools/make_sds_det.py` ghi file này thành `meta_<split>.csv`:

```bash
python scripts/run_tiled.py --source data/processed/sds_det/images/val --model runs/train/E2c_s0/weights/best.pt \
    --tile 640 --overlap 0.2 --imgsz 640 --conf 0.001 --max-det 1000 --no-images \
    --altitude-csv data/processed/sds_det/meta_val.csv --target-person-px 10 --output runs/sds_det/E2c_tiled_px10
```

Gộp cảnh báo thành sự cố ở trạm mặt đất, chấm trên video thật có nhãn theo track (`docs/results/alert_memory.md`):

```bash
python eval/incident_merge_eval.py --videos val-m100-DJI_0001-v21 --mot data/processed/sds_mot --runs runs/sds \
    --confirm geo --output runs/sds/incident_merge.csv
```

Thời gian từng chặng (RQ2): `python eval/timing_summary.py --runs runs/edge/demo --output runs/edge/timing.csv`.

Nhãn tập lũ từ CVAT: `python tools/convert_cvat.py --xml task1.zip task2.zip … --images data/raw/flood/frames --dst data/processed/flood --split test` (nhận nhiều file xuất "CVAT for images 1.1", .zip hoặc .xml). Cả bước chuyển nhãn, dự đoán mọi `*_flood.yaml`, chấm theo kích thước và theo loại nhiễu: `scripts/eval_flood.sh <thư mục chứa các file xuất>`.

Dữ liệu: chia theo video, kiểm tra rò rỉ, xem kích thước người khi huấn luyện (TECHNICAL mục 13.4, 15.6):

```bash
python tools/split_by_video.py --images data/processed/finland/images/all --names train val --ratios 0.8 0.2 \
    --output data/processed/finland/splits            # ghi train.txt, val.txt dùng thẳng cho training/train.py
python tools/check_leakage.py --train data/processed/visdrone/images/train --eval data/processed/flood/images/test \
    --output runs/leakage/flood_test                   # thoát mã 1 nếu có video trùng hoặc ảnh gần trùng
python tools/label_size_stats.py --images data/processed/visdrone/images/val \
    --labels data/processed/visdrone/labels/val --imgsz 1280 --output runs/stats/visdrone_val_1280
```

Trên Jetson (chưa chạy thử, cần thiết bị):

```bash
yolo export model=yolo26s.pt format=engine half=True imgsz=1280 device=0
python scripts/benchmark_speed.py --model yolo26s.engine --imgsz 1280
```
