# Lộ trình thực hiện FloodEye (theo đề cương chi tiết bản final)

Đề tài: Nghiên cứu phát hiện người kích thước nhỏ từ ảnh UAV trong vùng ngập lụt, hướng tới xử lý trên thiết bị biên.

Mốc cố định: nộp đề cương **16/10** · khung code **30/10** · khoá tập test lũ **4/11** · bắt đầu RQ2 **9/11** · bảo vệ **15/12/2026**.
Ngân sách thời gian: khoảng 150 giờ (Phụ lục B của đề cương); từ 21/10 dành 15–20 giờ mỗi tuần.

Kế hoạch điều chỉnh ngày 21/10/2026 (mục 1). Lịch gốc theo đề cương xem lịch sử git của file này.

Tài liệu này chuyển đề cương thành việc cần làm theo tuần (mục 1), cách tổ chức và viết mã (mục 2–3), kế hoạch thí nghiệm (mục 4), những điểm kỹ thuật cần để ý (mục 5) và các quyết định còn treo (mục 6).

---

## 1. Lịch theo tuần

### 1.1. Trạng thái ngày 21/10

| Mảng | So với lịch gốc | Chi tiết |
|---|---|---|
| Code | **Sớm 1–2 tuần** | Đủ pipeline UAV (3 chiến lược xác nhận, outbox), trạm mặt đất, giả lập mạng và chuyến bay, quét lưới RQ3, đánh giá thống kê (bootstrap cặp, theo video), công cụ chia tập và kiểm tra rò rỉ, chuyển nhãn CVAT, CI. Xem TECHNICAL mục 6.1 |
| Thí nghiệm | Chậm khoảng 3 ngày | E0, E1, E4 trên VisDrone val xong; đối chiếu cắt ô riêng với SAHI xong; **E2 lượt 1 (VisDrone, 60 epoch) xong 22/10** (7,4 giờ T4): AP50 trên VisDrone val 0,497 → 0,758, nhóm dưới 8 px 0,167 → 0,554; giữ nguyên xu hướng trên test-dev; **nhưng kém mô hình gốc với người dưới nước** (AFO test: AP50 0,147 → 0,103, có ý nghĩa thống kê; `docs/results/afo_E1_E2.md`), nên E2 lượt 2 thêm AFO (`E2c_s0.yaml`); **E2c xong 23/10** (9,1 giờ): AFO test 0,103 → 0,568, VisDrone val chỉ giảm 0,011 (`docs/results/E2c.md`) (`docs/results/visdrone_E2.md`); RQ3 đã chạy thử bằng mô phỏng |
| Dữ liệu | **Chậm 2 tuần, rủi ro lớn nhất** | Tập test lũ **chưa gán khung nào** (26/10: 212 khung đóng gói sẵn cho CVAT trong `Downloads/floodeye_cvat`, 10 task theo video); 22/10 đã trích **227 khung** từ 10 video (YouTube, NIDARX CC0) vào `data/raw/flood/frames`, đã loại tay khung không phải góc UAV (`frames_loai/ly_do.csv`); 2 video còn 480p. Đã rà Kaggle, Hugging Face, Zenodo, Roboflow: không có bộ công khai nào gồm ảnh UAV lũ thật có khung người. Thêm dữ liệu huấn luyện: AFO (đang dùng trong E2c), HydroVigilance (`E2d_s0.yaml`) (lịch gốc: 100 khung tới 23/10, khoá 4/11); FinlandProper chưa tải |
| Thiết bị | Đã chốt | **Không có Jetson**: RQ2 đo trên Kaggle T4, báo thứ hạng tương đối (TECHNICAL mục 14.4) |

Hệ quả: từ giờ tới khi khoá tập test, thời gian dồn cho **dữ liệu** và **thí nghiệm**; code chỉ làm khi một thí nghiệm cần.

### 1.2. Phân bổ giờ mỗi tuần (15–20 giờ)

| Tuần | Gán nhãn và dữ liệu | Thí nghiệm | Viết | Code |
|---|---|---|---|---|
| 21–30/10 | 8–10 giờ | 3–4 giờ | 2–3 giờ | ≤ 2 giờ |
| 31/10–13/11 | 3–4 giờ (khoá, rà) | 8–10 giờ | 3–4 giờ | ≤ 2 giờ |
| 14/11–4/12 | 0 | 5–7 giờ | 8–10 giờ | ≤ 2 giờ, đóng băng 28/11 |
| 5–11/12 | 0 | 0 | 15–20 giờ | 0 |

Số khung gán được mỗi giờ là **ước lượng** (khoảng 15–20 khung mỗi giờ, kể cả phóng to người nhỏ và rà lại); đo lại sau 50 khung đầu và chỉnh bảng dưới.

### 1.3. Lịch theo tuần

Cột "Gán nhãn" là số khung tập test lũ đã gán, cộng dồn.

| Tuần | Dữ liệu | Thí nghiệm | Code (chỉ khi cần) | Viết | Gán nhãn | Báo cáo thứ Sáu |
|---|---|---|---|---|---|---|
| 21–23/10 | Gom video lũ, ghi `sources.csv`; dựng dự án CVAT theo LABELING.md; gán thử | E2 lượt 1 xong → `eval_by_size` trên VisDrone val, `compare_runs` với E1 | Push, xem CI chạy | Chương 2 | 30–50 | 23/10: bảng VisDrone (E0, E1, E4, cắt ô riêng); E2 nếu kịp; demo pipeline + trạm mặt đất (telemetry giả lập); RQ3 chạy thử; hỏi thầy quyết định #1, #7, #10 |
| 24–30/10 | Gán nhãn; tải FinlandProper, chia theo video, `check_leakage` | E2 lượt 2 (VisDrone + FinlandProper) trên Kaggle | Bộ chuyển nhãn FinlandProper; yaml đầu P2 cho E3 | Chương 3 | 150 | 30/10: E2 lượt 1 đầy đủ; tiến độ gán nhãn |
| 31/10–6/11 | Gán nốt, rà theo LABELING mục 7, `check_leakage` với mọi tập train, **khoá** (`MANIFEST.sha256`) | E3 (P2) trên Kaggle; E0–E2 trên tập test lũ | | Chương 4 | 200–250, **khoá 4/11** | 6/11: RQ1 trên tập test lũ (E0–E2) |
| 7–13/11 | | E3, E4 (cắt ô) trên tập lũ và FinlandProper; E5 (YOLO11s); E6 nếu thầy duyệt; recall theo loại nhiễu; **RQ2 bắt đầu 9/11**: xuất TensorRT FP16/INT8 trên T4, đo từng chặng | Script recall theo thẻ nhiễu; notebook RQ2 trên Kaggle; `rescale_dataset.py` nếu E6 được duyệt | Chương 5 (RQ1) | | 13/11: bảng RQ1 đầy đủ |
| 14–20/11 | | 3 seed cho cấu hình cuối; **RQ3** quét đủ lưới (mô phỏng) + điều tra cơ chế `bytetrack_cmc` bỏ sót; RQ2 xong | Recall theo kích thước trong mô phỏng (lấy từ RQ1) | | | 20/11: kết quả RQ2, RQ3 |
| 21–27/11 | | Phân tích lỗi; demo trên video lũ thật | | Chương 5 (RQ2, RQ3), chương 6 | | 27/11: demo trạm mặt đất |
| 28/11–4/12 | | | **Đóng băng mã 28/11** | Bản thảo đầy đủ | | 4/12: bản thảo |
| 5–11/12 | | | | Sửa theo góp ý; slide; video demo dự phòng | | 11/12: bản hoàn chỉnh |

### 1.4. Ngân sách GPU Kaggle

Mỗi lần huấn luyện ở 1280 khoảng 8–10 giờ T4 (E2 lượt 1, 60 epoch: khoảng 8 giờ). Hạn mức khoảng 30 giờ mỗi tuần (cần kiểm tra trên tài khoản).

| Tuần | Lần chạy | Giờ GPU ước lượng |
|---|---|---|
| 21–23/10 | E2 lượt 1 | 8 |
| 24–30/10 | E2 lượt 2 (thêm FinlandProper) | 10 |
| 31/10–6/11 | E3 (P2) | 10 |
| 7–13/11 | E5 (YOLO11s); xuất TensorRT, đo RQ2 | 9 + 2 |
| 14–20/11 | 2 seed thêm cho cấu hình cuối | 20 |

Không tuần nào vượt hạn mức nếu không chạy lại. Lần chạy hỏng thì đẩy seed sang Colab (như đề cương).

### 1.5. Khi trễ

Thứ tự cắt của đề cương giữ nguyên: phần mở rộng (nhiều drone, xếp ưu tiên) → độ đẹp trạm mặt đất → E3 → `sim/netem`. Đã cắt: mọi việc cần Jetson (`docker/edge-jetson.Dockerfile`, đo điện năng thật).

Riêng tập test lũ, nếu tới 4/11 chưa đủ 200 khung đã rà: **giữ khoá với số khung đang có nếu từ 150 trở lên** (khoảng tin cậy rộng hơn, ghi vào giới hạn), hoặc lùi khoá tối đa tới 11/11. Lùi quá 11/11 thì RQ1 trên tập lũ không kịp báo cáo 13/11. Chọn cách nào là quyết định #10, hỏi thầy ngày 23/10.

Không cắt tập test lũ và phần đánh giá.

---

## 2. Cấu trúc mã

Giữ cấu trúc ở Phụ lục A của đề cương, thêm `tools/` và `tests/`, đóng gói bằng `pyproject.toml`:

```
flood-tiny-person/
├── pyproject.toml          # một gói, ba nhóm phụ thuộc: [edge], [ground], [dev]
├── configs/
│   ├── edge.yaml
│   └── experiments/        # E0.yaml … E6.yaml, rq2_*.yaml, rq3_*.yaml
├── shared/
│   ├── schema.py           # Detection, Alert, AlertCrop (Pydantic)
│   └── config.py           # đọc YAML thành đối tượng Pydantic
├── edge/
│   ├── sampler.py
│   ├── telemetry.py
│   ├── detector.py
│   ├── georef.py
│   ├── confirm.py
│   ├── alerts.py
│   └── main.py
├── ground/                 # FastAPI + SQLite + Leaflet; gộp cảnh báo, xếp ưu tiên
├── sim/
│   ├── netem.py            # bộ giả lập mạng
│   └── flight.py           # sinh telemetry giả lập: đường bay, độ cao, vận tốc
├── eval/                   # AP/recall theo kích thước và nhiễu; benchmark; chỉ số RQ3
├── training/               # train.py + notebook Kaggle mỏng; yaml đầu P2
├── tools/                  # chuyển nhãn, thống kê kích thước, trích khung, khoá tập test
├── tests/                  # pytest, chạy không cần mô hình
└── scripts/                # run_baseline, run_sahi, gsd_calc (đã có)
```

### Docker

Giữ Docker để đóng gói demo, tách theo vai trò:

| File | Nội dung | Dùng khi |
|---|---|---|
| `docker/ground.Dockerfile` | Python slim + FastAPI, không có torch (nhẹ) | Demo trạm mặt đất |
| `docker/edge.Dockerfile` | torch CPU + ultralytics + `edge/` | Giả lập UAV trên laptop |
| `docker/edge-jetson.Dockerfile` | Dựa trên ảnh Ultralytics cho JetPack | **Đã cắt** (21/10: không có Jetson) |
| `compose.yaml` | `ground` + 2–3 dịch vụ `edge`, mỗi dịch vụ phát lại một video | Demo nhiều drone (mục 9 của đề cương) bằng một lệnh `docker compose up` |

Ảnh `edge` và `ground` được viết khi hai gói đó có mã (tuần 24–30/10). Ảnh hiện tại (chạy các script đánh giá) giữ đến lúc đó.

### Cài đặt không dùng Docker

Cài theo vai trò: `pip install -e ".[edge]"` trên Jetson, `pip install -e ".[ground]"` cho trạm mặt đất, `pip install -e ".[dev]"` trên Mac. Cách này thay cho ba file `requirements-*.txt` và bỏ được đoạn `sys.path.insert` ở đầu các script.

### Mã hiện có đi về đâu

| Hiện tại | Chuyển thành |
|---|---|
| `src/uavdet/sources.py` | `edge/sampler.py` |
| `src/uavdet/device.py` | `edge/detector.py` |
| `src/uavdet/report.py`, `metrics.py`, `draw.py` | `eval/` |
| `src/uavdet/cli.py` | `shared/config.py` |
| `scripts/*.py`, `eval/eval_by_size.py` | giữ lệnh chạy, đổi chỗ import |

---

## 3. Gợi ý cách viết mã

Mười điểm dưới đây nhằm ba mục đích: mã chạy được trên cả Mac lẫn Jetson; thí nghiệm RQ3 tái lập được; và kiểm tra được từng khối mà không phải chạy cả mô hình.

### 3.1. Mỗi khối là một giao diện, có bản giả để kiểm thử

```python
class Detector(Protocol):
    def detect(self, frame: np.ndarray) -> list[Detection]: ...

class TelemetrySource(Protocol):
    def at(self, t: float) -> Telemetry: ...

class Transport(Protocol):
    def send(self, message: bytes) -> bool: ...
```

`main.py` chỉ nối các khối lại. Kiểm thử dùng `FakeDetector` (trả box định sẵn) và `FakeTransport` (ghi lại thông điệp), nên cả pipeline chạy trong vài giây trên máy bất kỳ. Ultralytics chỉ được import trong `detector.py`.

### 3.2. Dùng đồng hồ mô phỏng, không dùng đồng hồ thật

Toàn bộ pipeline lấy thời gian từ dấu thời gian của khung hình (`frame_time`), không gọi `time.time()`. Bộ giả lập mạng cũng chạy theo đồng hồ này, với seed cố định.

Nhờ vậy:
- một lần chạy RQ3 cho cùng kết quả mỗi lần chạy lại;
- chạy nhanh hơn thời gian thực được: quét hết lưới N × FPS × độ cao × vận tốc × kịch bản mạng trong vài phút.

Thời gian xử lý thật (cho RQ2) vẫn đo riêng bằng `perf_counter`, ghi vào log, không ảnh hưởng tới đồng hồ mô phỏng.

### 3.3. Mỗi chặng ghi log JSONL; chỉ số tính sau từ log

Mỗi lần chạy sinh một thư mục gồm `detections.jsonl`, `confirmations.jsonl`, `alerts_sent.jsonl`, `alerts_received.jsonl`, `timings.jsonl` và `run_config.json`. Script trong `eval/` đọc log và nhãn để tính báo động giả mỗi phút, thời gian tới cảnh báo, tỉ lệ bỏ sót, tỉ lệ mất cảnh báo.

Lợi ích: đổi cách tính chỉ số không phải chạy lại mô hình; log cũng chính là dữ liệu để vẽ biểu đồ cho luận văn.

### 3.4. `detector.py` tự cắt ô và chạy theo lô

Tự cắt ô rồi đưa cả lô vào một lần gọi `model.predict`, sau đó gộp kết quả bằng NMS giữa các ô. Cùng một mã chạy được `.pt`, `.onnx` và `.engine`; trên TensorRT, chạy theo lô nhanh hơn rõ so với từng ô.

SAHI giữ trong `scripts/run_sahi.py` làm mốc cho E4, để đối chiếu kết quả của bộ cắt ô tự viết. Mỗi lần gọi trả về cả thời gian từng phần (cắt ô, suy luận, gộp) để RQ2 có số liệu từng chặng.

### 3.5. `georef.py` là hàm thuần, có cả hàm ngược

Viết `pixel_to_gps(px, py, telemetry, camera)` và hàm ngược `gps_to_pixel(...)`. Hai lợi ích:
- kiểm thử: đi một vòng pixel → GPS → pixel phải ra đúng điểm ban đầu, và so với vài trường hợp tính tay;
- giả lập: `sim/flight.py` dùng hàm ngược để đặt "người thật" tại toạ độ cố định trên mặt nước, rồi biết họ xuất hiện ở pixel nào trong từng khung. Đây là cách tạo nhãn theo thời gian cho RQ3 và đo sai số định vị khi cộng nhiễu vào GPS, độ cao, hướng bay.

### 3.6. `confirm.py` có ba chiến lược, cùng một giao diện

| Chiến lược | Cách làm | Dự đoán |
|---|---|---|
| `bytetrack` | Đúng như đề cương. Dùng bộ ByteTrack có sẵn trong ultralytics như một thư viện độc lập, vì vòng `model.track()` không đi được với bộ cắt ô tự viết | Gãy ở 2 FPS; giữ làm mốc so sánh |
| `bytetrack_cmc` | Trước khi ghép, dịch box của khung trước theo chuyển động camera: tính từ telemetry (vận tốc, hướng, độ cao, qua `gps_to_pixel`), hoặc ước lượng phép biến đổi ảnh giữa hai khung | Hoạt động nếu telemetry đủ chính xác |
| `geo` | Đổi sang toạ độ mặt đất bằng `georef`, gom các phát hiện trong bán kính r qua N khung | Đơn giản, không phụ thuộc tốc độ khung; rủi ro gộp nhầm hai người đứng gần nhau |

Chọn bằng cấu hình, so sánh cả ba trong RQ3; lý do xem mục 5.2. Cả ba trả về cùng kiểu `Confirmation(cluster_id, frames_seen, …)`. Với `bytetrack_cmc`, cách bù bằng telemetry làm trước vì có sẵn từ `georef`; cách ước lượng từ ảnh chỉ làm nếu còn thời gian.

### 3.7. `alerts.py` dùng mẫu outbox

Bảng SQLite `outbox(alert_id, kind, payload, status, attempts, created_at)`:
- Mỗi cảnh báo sinh hai thông điệp: `coords` (vài trăm byte) và `crop` (ảnh cắt), cùng `alert_id`; `coords` luôn được gửi trước.
- Gửi, chờ xác nhận; không được xác nhận thì thử lại theo thời gian chờ tăng dần.
- Trạm mặt đất bỏ qua `alert_id` đã có. Nhờ vậy gửi lại bao nhiêu lần cũng không sinh cảnh báo trùng.

Đây đúng là cơ chế "lưu và gửi bù, toạ độ trước, ảnh sau" của đề cương, và cho RQ3 số liệu rõ ràng: số lần thử, độ trễ giao, tỉ lệ mất.

### 3.8. `sim/netem.py` là một lớp bọc quanh `Transport`

`NetemTransport(inner, loss=0.2, delay_ms=(200, 800), outages=[(60, 150)], seed=0)` bọc lấy transport thật (HTTP tới `ground/`) hoặc transport giả. Chạy được trên Mac, không cần `tc` của Linux. Kịch bản mạng ghi trong `configs/experiments/rq3_*.yaml`.

### 3.9. Cấu hình bằng Pydantic, mỗi thí nghiệm một file

`shared/config.py` đọc YAML thành đối tượng Pydantic, nên sai tên khoá hay sai kiểu bị báo lỗi ngay lúc khởi động, không phải giữa lần chạy. Mỗi thí nghiệm E0–E6 và RQ2, RQ3 có một file trong `configs/experiments/`. Bảng kết quả trong luận văn ghi rõ file cấu hình nào sinh ra nó.

### 3.10. Notebook Kaggle chỉ là lớp vỏ

Notebook chỉ làm ba việc: clone kho mã ở một commit cố định, cài gói, gọi `python training/train.py --config configs/experiments/E2.yaml`. Mọi logic nằm trong `training/train.py`, có thể chạy thử vài epoch trên Mac. Kết quả (trọng số, `results.csv`, `run_config.json`) lưu thành Kaggle Dataset có phiên bản.

### Kiểm thử tối thiểu

`tests/` gồm: vòng `georef` đi và về; `confirm` với chuỗi phát hiện định sẵn; outbox khi mất mạng rồi có lại; schema của gói cảnh báo; các phép tính AP/recall (đã có ví dụ tính tay). GitHub Actions chạy `pytest` mỗi lần push (đã có, `.github/workflows/tests.yml`); không cần GPU vì không đụng tới mô hình.

---

## 4. Thí nghiệm

### RQ1

| Mã | Cấu hình | Cần thêm |
|---|---|---|
| E0 | YOLO26s COCO, 640 | Đã có |
| E1 | 1280 | Đã có |
| E2 | Fine-tune (VisDrone + FinlandProper, thêm C2A nếu kịp) | `training/train.py`, notebook |
| E3 | E2 + đầu P2 | yaml mô hình |
| E4 | E2/E3 + cắt ô | `detector.py` (đối chiếu với SAHI) |
| E5 | E2 với YOLO11s | Không |
| E6 | Recall theo số pixel trên người (thu nhỏ nhiều mức); 48 MP và 4K là hai điểm trên đường cong | `tools/rescale_dataset.py`, xem mục 5.3 |

Đánh giá trên ba tập: VisDrone val, test của FinlandProper, tập test lũ. Theo mục 8.5 của đề cương:
- AP ở conf 0,001, recall vận hành ở conf 0,25;
- `max_det=1000`;
- IoU 0,3 cho nhóm dưới 8 px;
- 3 seed cho thí nghiệm có huấn luyện.

### RQ2

Cấu hình tốt nhất của RQ1 × {FP16, INT8} × chế độ công suất. Đo theo từng chặng (cắt ô, suy luận, gộp, `georef`, `confirm`). Đầu ra là đường recall theo FPS, đánh dấu ngưỡng 2 FPS. **Đo trên Kaggle T4** (chốt 21/10: không có Jetson); bỏ trục chế độ công suất; báo thứ hạng tương đối giữa các cấu hình, không quy đổi ra FPS trên Jetson (TECHNICAL mục 14.4).

### RQ3

| Biến | Giá trị |
|---|---|
| N | 1, 3, 5, 10 |
| Chiến lược xác nhận | `bytetrack`, `bytetrack_cmc`, `geo` |
| Bán kính gom của `geo` | 1, 2, 3, 5, 8 m |
| Nhiễu telemetry | GPS σ = 0, 2, 5 m; lệch góc camera 0, 1, 3° |
| FPS | 1, 2, 4 |
| Độ cao × vận tốc | 30/50/80/100 m × 5/10 m/s |
| Mạng | tốt; mất gói 10–30%; mất sóng 30–120 s |

Nhãn theo thời gian lấy từ `sim/flight.py` (mục 3.5), hoặc từ chuỗi khung của FinlandProper nếu bộ này có nhãn liên tục (cần kiểm tra khi tải về).

Chỉ số thêm cho phần xác nhận: số lần **gộp nhầm** (hai người thành một cảnh báo) và **tách nhầm** (một người thành nhiều cảnh báo), theo bán kính gom và mức nhiễu telemetry. Bán kính gom của `geo` phải gắn với sai số định vị: GPS lệch vài mét; camera lệch 1° ở 50 m làm điểm chiếu lệch khoảng 0,9 m (50 × tan 1°). Đây cũng là chỗ định lượng giới hạn của giả định "camera nhìn thẳng xuống".

---

## 5. Những điểm kỹ thuật cần để ý

### 5.1. Bảng GSD vẫn coi 82° là góc ngang

Bảng ở mục 4.2 của đề cương vẫn tính với 82° là góc ngang. Theo hiểu biết của tôi, FOV 82° của Matrice 4T là góc chéo; tiêu cự tương đương 24 mm cũng ứng với góc ngang chỉ khoảng 74°. Nếu đúng vậy:
- người ở 50 m là khoảng 25 px, không phải 22 px;
- thời gian người nằm trong khung ở 50 m, bay 10 m/s, là khoảng 4,3 s, không phải 5 s.

Thêm hai lập luận củng cố: tiêu cự tương đương 24 mm trên khổ full-frame cho góc chéo khoảng 84° và góc ngang khoảng 74°; DJI ghi Matrice 4E (cùng 24 mm) là 84°, tức hãng dùng góc chéo cho cả dòng sản phẩm. Từ góc chéo 82°, góc ngang khi quay 4K khoảng 70–74° tuỳ cách camera cắt khung, nên người ở 50 m khoảng 25–28 px.

Kết luận của đề cương không đổi, và hơi có lợi hơn: người lớn hơn, vùng phủ hẹp hơn, thời gian người nằm trong khung ngắn hơn khoảng 15%. Đề cương đã nộp thì giữ nguyên. Trong luận văn ghi thành mục "Điều chỉnh cho luận văn":
- tính góc ngang từ tiêu cự tương đương và chế độ cắt khung của video, ghi rõ giả định (`gsd_calc.py --fov-type diagonal`; mặc định của script sẽ đổi thành 82°, góc chéo);
- với từng bộ dữ liệu, tính GSD từ metadata thật (độ cao, thông số camera) nếu có, thay vì dùng một con số chung.

### 5.2. ByteTrack ở 2 FPS

UAV bay 10 m/s, xử lý 2 FPS: mặt đất dịch khoảng 5 m giữa hai khung. Ở 50 m (GSD khoảng 2 cm/px), quãng đó là khoảng 200–250 px, trong khi box người chỉ khoảng 25 px. Độ chồng lấn giữa hai khung bằng 0, nên ByteTrack không ghép được. Bộ lọc Kalman cũng không cứu được, vì chuyển động ở đây do camera di chuyển chứ không phải do người.

Vì vậy mã có ba chiến lược (mục 3.6). So sánh `bytetrack` → `bytetrack_cmc` → `geo` là một kết quả đáng viết trong RQ3: chỉ ra vì sao cách tracking thông dụng gãy trên UAV ở tần số khung thấp, và cách khắc phục.

### 5.3. E6: đổi thành khảo sát recall theo số pixel trên người

Chưa thấy bộ dữ liệu công khai nào có ảnh 48 MP từ UAV kèm nhãn người (FinlandProper là 1920×1024). Thay vì so trực tiếp "48 MP với 4K", E6 được đặt lại như sau:

1. Lấy ảnh độ phân giải cao nhất có nhãn.
2. Thu nhỏ theo nhiều mức (1×, 1/1,5, 1/2,1, 1/3, 1/4) bằng `tools/rescale_dataset.py`; nhãn được co theo cùng tỉ lệ.
3. Chạy cùng mô hình, vẽ đường **recall theo kích thước người tính bằng pixel**.
4. 48 MP và 4K chỉ là hai điểm trên đường cong (chênh khoảng 2,1 lần mỗi chiều). Ghép với bảng GSD, cùng đường cong đó trả lời câu "bay cao tối đa bao nhiêu", nên E6 nối thẳng vào khuyến nghị độ cao bay.

Giới hạn phải ghi rõ: thu nhỏ ảnh không tái tạo được nhiễu cảm biến, độ nhòe và mức nén của camera thật. Có thể thêm làm mờ và nén JPEG ở mỗi mức để gần thực tế hơn, nhưng vẫn gọi là mô phỏng. Hỏi thầy hôm thứ Sáu.

### 5.4. Vùng bỏ qua của VisDrone

Đề cương ghi "phát hiện trong vùng ignored bị tính là báo nhầm". Có thể làm tốt hơn với ít công: giữ các vùng đó thành một file riêng khi chuyển nhãn, và để `eval/` bỏ qua phát hiện rơi vào vùng đó. Mã so khớp hiện tại đã có khái niệm nhãn bị bỏ qua, chỉ cần mở rộng thêm.

### 5.5. Hạn mức Kaggle

Mỗi lần fine-tune ở 1280 trên T4 có thể mất nhiều giờ. Ba seed × nhiều cấu hình sẽ chạm hạn mức tuần. Nên:
- thử nhanh bằng YOLO26n hoặc ít epoch;
- chỉ chạy đủ 3 seed cho cấu hình cuối;
- luân phiên với Colab như đề cương đã ghi.

---

## 6. Quyết định còn treo

| # | Câu hỏi | Ai quyết | Hạn |
|---|---|---|---|
| 1 | Đồng ý đặt lại E6 thành khảo sát recall theo số pixel trên người (mục 5.3)? | Thầy | 23/10 |
| 2 | ~~Lab có hỗ trợ mua Jetson không?~~ → chốt 21/10: không có; RQ2 trên Kaggle T4 | Thầy | Xong |
| 3 | Có bắt buộc bài báo trước khi bảo vệ không? | Thầy, khoa | 16/10 |
| 4 | Hạn nộp quyển? | Khoa | 16/10 |
| 5 | Có video DJI kèm `.SRT` nào để thử `telemetry` với dữ liệu thật không? | Học viên | 23/10 |
| 6 | ~~Tài khoản Kaggle đã xác minh số điện thoại chưa?~~ → xong (E2 chạy được với Internet) | Học viên | Xong |
| 7 | Khoảng tin cậy trên tập test lũ lấy mẫu theo video (cluster bootstrap) thay vì theo ảnh? Theo ảnh làm khoảng tin cậy hẹp giả khi nhiều khung cùng video (TECHNICAL 15.3) | Học viên, hỏi thầy | Trước khi khoá tập test (4/11) |
| 8 | ~~Đặt bộ bọc ByteTrack ở đâu~~ → đã chốt 21/10: bọc trong `detector.py` | Học viên | Xong |
| 9 | RQ3: ByteTrack giữ ngưỡng tạo track 0,25 như bài gốc, hay hạ về bằng conf detector để cùng đầu vào với `geo`? (TECHNICAL 9.2) | Học viên | Trước RQ3 (14/11) |
| 10 | Tới 4/11 chưa đủ 200 khung đã rà: khoá với số đang có (tối thiểu 150) hay lùi khoá tới 11/11? (mục 1.5) | Thầy | 23/10 |
| 11 | So E2 với E0/E1 trên VisDrone test-dev thay vì val? E2 chọn `best.pt` theo val nên val thiên vị E2 (TECHNICAL 13.5). Đã chạy cả hai tập cho E1, E2: mức tăng giữ nguyên trên test-dev (`docs/results/visdrone_E2.md`); cần thầy chọn tập nào là bảng chính | Học viên, hỏi thầy | 23/10 |
| 12 | Dùng video lũ có bản quyền (YouTube, báo chí) cho tập test, chỉ công bố nhãn và nguồn, không phát hành lại ảnh: có được chấp nhận? C2A không ghi giấy phép trên GitHub: dùng để huấn luyện có ổn? | Thầy | 23/10 |
| 13 | Đưa "thu nhỏ khung theo độ cao" (`scale_by_altitude.md`) thành một đóng góp của khối phát hiện, đánh giá trên tập lũ cạnh E4 (cắt ô cố định)? Chọn mục tiêu px trên dữ liệu ngoài tập test lũ | Học viên, hỏi thầy | Trước khi chạy RQ1 trên tập lũ |
