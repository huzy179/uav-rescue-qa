# Lộ trình thực hiện FloodEye (theo đề cương chi tiết bản final)

Đề tài: Nghiên cứu phát hiện người kích thước nhỏ từ ảnh UAV trong vùng ngập lụt, hướng tới xử lý trên thiết bị biên.

Mốc cố định: nộp đề cương **16/10** · khung code **30/10** · khoá tập test lũ **11/11** (lùi từ 4/11, quyết định #10) · bắt đầu RQ2 **9/11** · bảo vệ **15/12/2026**.
Ngân sách thời gian: khoảng 150 giờ (Phụ lục B của đề cương); từ 21/10 dành 15–20 giờ mỗi tuần.

Kế hoạch điều chỉnh ngày 21/10/2026 (mục 1). Lịch gốc theo đề cương xem lịch sử git của file này.

Tài liệu này chuyển đề cương thành việc cần làm theo tuần (mục 1), cách tổ chức và viết mã (mục 2–3), kế hoạch thí nghiệm (mục 4), những điểm kỹ thuật cần để ý (mục 5) và các quyết định còn treo (mục 6).

---

## 1. Lịch theo tuần

### 1.1. Trạng thái và nhật ký

**Trạng thái 8/11** (chi tiết từng khâu: TONG_QUAN mục 8; mỗi kết quả một file trong `docs/results/`):

| Mảng | Trạng thái |
|---|---|
| Dữ liệu | **Rủi ro lớn nhất.** Tập test lũ 188 khung từ 9 nguồn, **chưa gán**; gán 7–9/11, khoá **11/11** (#10). Đã rà trùng với 5 tập train (`flood_truoc_khoa.md`) |
| Câu hỏi 1 (phát hiện) | Xong trên VisDrone, AFO, SeaDronesSee: mô hình chính E2c; P2, thêm C2A, ngưỡng theo cỡ, phóng to người nhỏ, lượt toàn ảnh đều âm. Chờ tập lũ |
| Câu hỏi 2 (tốc độ) | **Xong 8/11** (`rq2_t4.md`): chín biến thể trên Kaggle T4; chọn FP16 với thu nhỏ theo độ cao; INT8 không đáng (nhanh thêm ít, nén độ tin cậy); hồ sơ thiết bị đã hiệu chỉnh, thiết bị yếu mô phỏng xong. Chương 5 mục 5.2 đã điền |
| Câu hỏi 3 (xác nhận, gửi) | Mô phỏng đủ lưới (tần số, độ cao, GPS, la bàn, mạng, mất theo cụm, nhóm người) và ba đoạn SeaDronesSee thật |
| Viết | Nháp chương 1–5 (7–8/11), câu hỏi 2 đã điền; chờ tập lũ; chương 2 còn tra trích dẫn và đọc toàn văn; khung chương 6 |
| Thiết bị | Không có Jetson (#2): đo trên T4, thiết bị yếu chỉ ước lượng bằng giả lập |

Từ nay tới 11/11 ưu tiên gán nhãn; mã chỉ viết khi khoá tập hoặc một thí nghiệm cần.

**Nhật ký 7/11** (mỗi mục một file kết quả; trạng thái mỗi cải tiến ở `CAI_TIEN.md`):
- Viết: nháp chương 1 (mở đầu), chương 3 (phương pháp), chương 4, chương 5.
- **E2e (thêm C2A) xong, âm**: kém E2c ở người nhỏ (VisDrone val −0,029 AP50, < 8 px −0,053), SeaDronesSee +0,041 không có ý nghĩa; giữ E2c, #14 khép lại (`E2e.md`).
- Câu hỏi 2: chạy thử hai biến thể trên T4 xong; lần chạy đủ đầu lỗi xuất INT8 (TensorRT 11 trên T4), đã ghim TensorRT 10 và để `run_rq2.py` bỏ qua engine lỗi; chuẩn bị `after_rq2.py`, `rq2_report.py`, `rq3_device.yaml`.
- 8/11: đầu một-một không NMS của YOLO26 (`nms_free.md`): mất recall vận hành trên VisDrone, không nhanh hơn trên PyTorch; giữ mặc định có NMS. Dùng lại ô không đổi khi drone đứng yên (`tile_skip.md`): bớt ô nhưng recall giảm tới 0,238 vì người bơi cử động; không dùng.
- 8/11: **câu hỏi 2 xong** (`rq2_t4.md`): FP16 nhanh hơn PyTorch 1,833–3,028 lần gần như không mất độ chính xác; INT8 mất một nửa recall vận hành < 8 px ở conf 0,25 vì nén độ tin cậy; biên Pareto chọn FP16 + thu nhỏ theo độ cao; thu nhỏ khung 4K trên CPU (46,28 ms) chậm hơn suy luận 6 ô. Hồ sơ thiết bị thêm số hạng thu nhỏ khung; mô phỏng thiết bị yếu: Orin NX, Orin Nano Super chỉ đạt 4 khung/giây ở 30–50 m. Sửa lỗi bảng so cặp của `rq2_report.py` (cặp cùng B bị đè), thêm biên Pareto và phân bố độ tin cậy.
- 8/11: cỡ người dự kiến so với nhãn (`person_px_check.md`): box người bơi lớn hơn giả định 0,5 m khoảng 1,8–2,6 lần; mô phỏng với người 1,0 m cho thu nhỏ theo độ cao giúp rõ hơn (30 m bỏ sót 0,867 → 0,400).
- Cải tiến âm, giữ làm tuỳ chọn: phóng to người nhỏ (`upscale_small.md`), lượt toàn ảnh sau thu nhỏ (`full_pass.md`), đồng bộ và làm mượt gimbal (`georef_sync.md`), ngưỡng theo cỡ (`conf_by_size.md`), đếm người theo cụm hoặc theo khung trong cửa sổ (`rq3_group.md`, #18).
- Cải tiến có lợi, tuỳ chọn (mô phỏng): định vị theo góc gimbal (`georef_pitch.md`, chưa tốt hơn tính chung), tự hiệu chỉnh la bàn (`rq3_yawcalib.md`), bán kính theo độ chính xác GPS bộ thu báo (`rq3_gpsacc.md`), mất gói theo cụm trong giả lập mạng (`rq3_burst.md`).
- Sân thử trong `python -m console` (13 câu hỏi dựng sẵn); số người ước tính mỗi sự cố (`group_size`).
- Dọn dẹp: cắt E5 (YOLO11s), bỏ cấu hình E2b, E2d, `benchmark_speed.py`, `live_demo.py`; chạy lại E0, E4, cắt ô tự viết và `rq3_gps.yaml` trên máy này vì thư mục kết quả cũ không còn; skill `/try-improvement`.

**Nhật ký 21/10–6/11** (tóm tắt; chi tiết trong lịch sử git của file này):
- 21–23/10: E0, E1, E4 trên VisDrone; E2 (VisDrone) và E2c (+ AFO) xong, E2c thành mô hình chính (`visdrone_E2.md`, `E2c.md`, `afo_E1_E2.md`).
- 26–28/10: E3 (P2) xong, âm (`E3.md`); E6 thử trên SeaDronesSee dẫn tới thu nhỏ theo độ cao (`e6_sds_pilot.md`, `scale_by_altitude.md`, #13); mô phỏng câu hỏi 3 theo độ cao, cơ chế `bytetrack_cmc` bỏ sót (`rq3_altitude.md`, `rq3_cmc_cause.md`); gộp sự cố ở trạm (`alert_memory.md`); `scripts/eval_flood.sh`.
- 2–4/11: luồng câu hỏi 2 trên Kaggle (`run_rq2.py`); tần số theo độ cao (`rq3_adaptive.md`, `rq3_altprofile.md`); sai số vị trí từ vị trí trong ảnh; demo hai drone; giao diện `python -m console`; giả lập thời gian thiết bị biên, demo bảo vệ một lệnh (`demo_bao_ve.sh`).
- 4/11: chốt #7, #10 (lùi khoá tới 11/11), #13, #14, #15; gộp hai nguồn San Angelo, tập còn 188 khung, không trùng với tập train.
- 5–6/11: bảng thuật ngữ chuẩn, tab "Hiểu dự án"; sai số vị trí và vùng tìm 95% (`rq3_geoerr.md`); thăm dò đường truyền (`rq3_network.md`, #17 bật); màn hình điều phối, lớp đáp án, công cụ cho đội đi cứu; E2e phiên 1 và 2.

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
| 21–23/10 | Gom video lũ, ghi `sources.csv`; dựng dự án CVAT theo LABELING.md; gán thử | E2 lượt 1 xong → `eval_by_size` trên VisDrone val, `compare_runs` với E1 | Push, xem CI chạy | Chương 2 | 30–50 | 23/10: bảng VisDrone (E0, E1, E4, cắt ô riêng); E2 nếu kịp; demo pipeline + trạm mặt đất (telemetry giả lập); RQ3 chạy thử; hỏi cô quyết định #1, #7, #10 |
| 24–30/10 | Gán nhãn; tải FinlandProper, chia theo video, `check_leakage` (thực tế: FinlandProper tạm bỏ) | E2 lượt 2 (VisDrone + FinlandProper) trên Kaggle (thực tế: E2c = VisDrone + AFO, xong 23/10; E3 xong 28/10) | Bộ chuyển nhãn FinlandProper; yaml đầu P2 cho E3 | Chương 3 | 150 | 30/10: E2 lượt 1 đầy đủ; tiến độ gán nhãn |
| 31/10–6/11 | Gán nốt, rà theo LABELING mục 7, `check_leakage` với mọi tập train, **khoá** (`MANIFEST.sha256`) | ~~E3 (P2) trên Kaggle~~ (xong 28/10); E2e (E2c + C2A) trên Kaggle; RQ2 trên T4 nếu kịp | | Chương 4 | 188; khoá lùi tới 11/11 (#10) | 6/11: tiến độ gán nhãn, lý do lùi khoá |
| 7–13/11 | **Khoá 11/11**: rà, `check_leakage` (kể cả C2A), `MANIFEST.sha256` | E0–E2c, E3, E4 (cắt ô, không thu nhỏ: tập lũ không có độ cao bay, quyết định #13) trên tập lũ; ~~E5 (YOLO11s)~~ (cắt 7/11); E6 nếu cô duyệt; recall theo loại nhiễu; **RQ2 trên T4 bắt đầu sớm 7/11** (chạy thử hai biến thể xong; lần chạy đủ đầu lỗi xuất INT8 với TensorRT 11, đã ghim TensorRT 10 và chạy lại) | ~~Script recall theo thẻ nhiễu~~, ~~`rescale_dataset.py`~~, ~~notebook RQ2 trên Kaggle~~, ~~xử lý sau RQ2 (`scripts/after_rq2.py`)~~ (đã có); 7/11 làm thêm các mục `CAI_TIEN.md` không cần GPU (xem các khối cập nhật 7/11) | Chương 5 (RQ1) | | 13/11: bảng RQ1 đầy đủ |
| 14–20/11 | | 3 seed cho cấu hình cuối (nếu đủ giờ GPU, không thì ghi giới hạn); ~~**RQ3** quét đủ lưới (mô phỏng)~~ (phần lớn xong 6–7/11) + ~~điều tra cơ chế `bytetrack_cmc` bỏ sót~~ (xong 26/10); RQ2 xong (dự kiến sớm hơn, ngay khi Kaggle chạy xong: `after_rq2.py`, `rq3_device.yaml`) | ~~Recall theo kích thước trong mô phỏng~~ (đã có, `RecallCurve`); thay đường recall E6 thử bằng đường đo trên tập lũ nếu có | | | 20/11: kết quả RQ2, RQ3 |
| 21–27/11 | | Phân tích lỗi; demo trên video lũ thật; ~~hiệu chỉnh hồ sơ thiết bị từ RQ2 và `rq3_device.yaml`~~ (xong 8/11); đổi cỡ khung trên GPU nếu còn giờ (CAI_TIEN mục 2) | | Chương 5 (RQ2, RQ3), chương 6 | | 27/11: demo bảo vệ (`scripts/demo_bao_ve.sh`), diễn tập một lần có mạng để giữ ô bản đồ |
| 28/11–4/12 | | | **Đóng băng mã 28/11** | Bản thảo đầy đủ | | 4/12: bản thảo |
| 5–11/12 | | | | Sửa theo góp ý; slide; video demo dự phòng | | 11/12: bản hoàn chỉnh |

### 1.4. Ngân sách GPU Kaggle

Mỗi lần huấn luyện ở 1280 khoảng 8–10 giờ T4 (E2 lượt 1, 60 epoch: khoảng 8 giờ). Hạn mức khoảng 30 giờ mỗi tuần (cần kiểm tra trên tài khoản).

| Tuần | Lần chạy | Giờ GPU ước lượng |
|---|---|---|
| 21–23/10 | E2 lượt 1 | 8 |
| 24–30/10 | E2 lượt 2 (thêm FinlandProper); thực tế: E3 | 10 |
| 31/10–6/11 | ~~E3 (P2)~~ đã chạy trước (hai phiên); giờ trống: E2e (E2c + C2A, quyết định #14), phiên 1. Tập train gấp khoảng 1,66 lần E2c nên một phiên 12 giờ không đủ 55 epoch; phần còn lại chạy tiếp (`resume`) tuần sau | 10 |
| 7–13/11 | ~~E2e phiên 2~~ (xong 7/11); ~~E5 (YOLO11s)~~ (cắt 7/11); ~~xuất TensorRT, đo RQ2~~ (xong 8/11) | 6 + 2 |
| 14–20/11 | 2 seed thêm cho cấu hình cuối | 20 |

Không tuần nào vượt hạn mức nếu không chạy lại. Lần chạy hỏng thì đẩy seed sang Colab (như đề cương).

### 1.5. Khi trễ

Thứ tự cắt của đề cương giữ nguyên: phần mở rộng (nhiều drone, xếp ưu tiên) → độ đẹp trạm mặt đất → E3 → `sim/netem`. Đã cắt: mọi việc cần Jetson (`docker/edge-jetson.Dockerfile`, đo điện năng thật).

Riêng tập test lũ, nếu tới 4/11 chưa đủ 200 khung đã rà: **giữ khoá với số khung đang có nếu từ 150 trở lên** (khoảng tin cậy rộng hơn, ghi vào giới hạn), hoặc lùi khoá tối đa tới 11/11. Lùi quá 11/11 thì RQ1 trên tập lũ không kịp báo cáo 13/11. Chọn cách nào là quyết định #10, hỏi cô ngày 23/10. **Chốt 4/11: lùi khoá tới 11/11** (chưa gán khung nào nên không thể khoá với 150).

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

Trạng thái 31/10: đã có `docker/ground.Dockerfile` và `docker/dev.Dockerfile` (chạy các script đánh giá); `compose.yaml` có hai dịch vụ `dev`, `ground`. `docker/edge.Dockerfile` và demo nhiều drone bằng compose **chưa viết**; demo hiện chạy bằng `scripts/demo.sh` trên máy. Đây là phần mở rộng, cắt trước theo mục 1.5.

### Cài đặt không dùng Docker

Cài theo vai trò: `pip install -e ".[edge]"` trên Jetson, `pip install -e ".[ground]"` cho trạm mặt đất, `pip install -e ".[dev]"` trên Mac. Cách này thay cho ba file `requirements-*.txt` và bỏ được đoạn `sys.path.insert` ở đầu các script.

### Mã hiện có đi về đâu (đã chuyển xong, `src/` không còn)

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

Câu hỏi con của RQ1–RQ3 (RQ1a…RQ3e), trả lời bằng thí nghiệm nào, trạng thái: TONG_QUAN mục 1.3 (đề xuất 6/11, quyết định #16).

### RQ1

| Mã | Cấu hình | Cần thêm |
|---|---|---|
| E0 | YOLO26s COCO, 640 | Đã có |
| E1 | 1280 | Đã có |
| E2 | Fine-tune (VisDrone; FinlandProper tạm bỏ) | Xong: E2 (VisDrone), **E2c (+ AFO), mô hình chính**; E2b (+ C2A) và E2d (+ HydroVigilance) không chạy, cấu hình xoá 7/11; E2e (E2c + C2A) xong 7/11, kết quả âm: kém E2c ở người nhỏ, không hơn có ý nghĩa ở người to (#14, `E2e.md`) |
| E3 | E2c + đầu P2 | Xong 28/10, không đáng chi phí (`docs/results/E3.md`) |
| E4 | E2c + cắt ô | Xong trên VisDrone và SDS; thêm biến thể thu nhỏ theo độ cao (`--target-person-px`), chỉ đánh giá trên SDS (#13); trên tập lũ chờ nhãn, chỉ cắt ô |
| E5 | E2c với YOLO11s | **Cắt 7/11** (việc đầu tiên trong thứ tự cắt, mục 1.5; tiết kiệm khoảng 10 giờ GPU); cấu hình đã xoá, lấy lại từ lịch sử git nếu cô yêu cầu |
| E6 | Recall theo số pixel trên người (thu nhỏ nhiều mức); 48 MP và 4K là hai điểm trên đường cong | Đã có `tools/rescale_dataset.py`, `eval/recall_by_pixels.py`; chạy thử trên SDS (`e6_sds_pilot.md`); xem mục 5.3 |

Đánh giá trên: VisDrone val và test-dev, AFO test, SeaDronesSee (người dưới nước, độc lập với dữ liệu huấn luyện), tập test lũ (TECHNICAL 15.1). FinlandProper dự kiến ban đầu đã tạm bỏ (162 GB). Theo mục 8.5 của đề cương:
- AP ở conf 0,001, recall vận hành ở conf 0,25;
- `max_det=1000`;
- IoU 0,3 cho nhóm dưới 8 px;
- 3 seed cho thí nghiệm có huấn luyện.

### RQ2

Cấu hình tốt nhất của RQ1 × {FP16, INT8} × chế độ công suất. Đo theo từng chặng (cắt ô, suy luận, gộp, `georef`, `confirm`). Đầu ra là đường recall theo FPS, đánh dấu ngưỡng 2 FPS. **Đo trên Kaggle T4** (chốt 21/10: không có Jetson); bỏ trục chế độ công suất; báo thứ hạng tương đối giữa các cấu hình, không quy đổi ra FPS trên Jetson (TECHNICAL mục 14.4). Thực hiện: `notebooks/kaggle_rq2.ipynb` (ghim TensorRT 10.16; INT8 với TensorRT 11 không build được trên T4) → tải `runs/rq2/` → `scripts/after_rq2.py` (so cặp, hiệu chỉnh hồ sơ thiết bị) → `rq3_device.yaml` (thiết bị yếu, mô phỏng) → `docs/results/rq2_t4.md`, chương 5 mục 5.2. **Xong 8/11.**

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

Nhãn theo thời gian lấy từ `sim/flight.py` (mục 3.5); kiểm chứng trên video thật bằng SeaDronesSee-MOT (có `track_id` và metadata bay, `docs/results/sds_mot_confirm.md`).

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

Giới hạn phải ghi rõ: thu nhỏ ảnh không tái tạo được nhiễu cảm biến, độ nhòe và mức nén của camera thật. Có thể thêm làm mờ và nén JPEG ở mỗi mức để gần thực tế hơn, nhưng vẫn gọi là mô phỏng. Hỏi cô hôm thứ Sáu.

Đã chạy thử 26/10 trên SeaDronesSee 4K (thu nhỏ 1, 2, 3, 4, 6 lần; `docs/results/e6_sds_pilot.md`). Phát hiện phụ quan trọng hơn dự kiến: mô hình fine-tune yếu với người **to**, dẫn tới thu nhỏ khung theo độ cao (quyết định #13).

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
| 1 | Đồng ý đặt lại E6 thành khảo sát recall theo số pixel trên người (mục 5.3)? | Cô | 23/10 |
| 2 | ~~Lab có hỗ trợ mua Jetson không?~~ → chốt 21/10: không có; RQ2 trên Kaggle T4 | Cô | Xong |
| 3 | Có bắt buộc bài báo trước khi bảo vệ không? | Cô, khoa | 16/10 |
| 4 | Hạn nộp quyển? | Khoa | 16/10 |
| 5 | Có video DJI kèm `.SRT` nào để thử `telemetry` với dữ liệu thật không? | Học viên | 23/10 |
| 6 | ~~Tài khoản Kaggle đã xác minh số điện thoại chưa?~~ → xong (E2 chạy được với Internet) | Học viên | Xong |
| 7 | ~~Khoảng tin cậy trên tập test lũ lấy mẫu theo video (cluster bootstrap) thay vì theo ảnh?~~ → chốt 4/11: **theo video** (TECHNICAL 15.3); báo cô 6/11 | Học viên, hỏi cô | Xong |
| 8 | ~~Đặt bộ bọc ByteTrack ở đâu~~ → đã chốt 21/10: bọc trong `detector.py` | Học viên | Xong |
| 9 | RQ3: ByteTrack giữ ngưỡng tạo track 0,25 như bài gốc, hay hạ về bằng conf detector để cùng đầu vào với `geo`? (TECHNICAL 9.2) **Đề xuất 4/11 (chờ học viên chốt):** hạ về bằng conf detector (0,1) cho bảng chính, để hai chiến lược cùng đầu vào; báo 0,25 làm phân tích độ nhạy. Trên SDS v21, v5, v13 hai ngưỡng cho cùng số người được cảnh báo (`sds_mot_confirm.md`), nên chọn cách công bằng không làm đổi kết luận | Học viên | Trước RQ3 (14/11) |
| 10 | ~~Tới 4/11 chưa đủ 200 khung đã rà: khoá với số đang có (tối thiểu 150) hay lùi khoá tới 11/11?~~ → chốt 4/11: **lùi khoá tới 11/11** (mục 1.5); báo cô 6/11 | Cô | Xong |
| 11 | So E2 với E0/E1 trên VisDrone test-dev thay vì val? E2 chọn `best.pt` theo val nên val thiên vị E2 (TECHNICAL 13.5). Đã chạy cả hai tập cho E1, E2: mức tăng giữ nguyên trên test-dev (`docs/results/visdrone_E2.md`); cần cô chọn tập nào là bảng chính | Học viên, hỏi cô | 23/10 |
| 12 | Dùng video lũ có bản quyền (YouTube, báo chí) cho tập test, chỉ công bố nhãn và nguồn, không phát hành lại ảnh: có được chấp nhận? C2A không ghi giấy phép trên GitHub (bản Kaggle ghi MIT, `flood_truoc_khoa.md`): dùng để huấn luyện có ổn? | Cô | 23/10 |
| 13 | ~~Đưa "thu nhỏ khung theo độ cao" thành một đóng góp, đánh giá trên tập lũ cạnh E4?~~ → chốt 4/11: **chỉ đánh giá trên SDS** (có độ cao từ metadata) và trong mô phỏng RQ3. 188 khung lũ lấy từ video YouTube, không có độ cao bay; suy độ cao từ nhãn là dùng nhãn test để đặt tham số. Tập lũ chạy E4 cắt ô không thu nhỏ; ghi giới hạn | Học viên | Xong |
| 14 | ~~Tuần 31/10–6/11 dư khoảng 10 giờ GPU vì E3 xong sớm: seed thứ hai của E2c, E2d, hay E2c + C2A?~~ → chốt 4/11: **E2e = E2c + C2A** (`E2e_s0.yaml`), vì E2c yếu với người to (`e6_sds_pilot.md`) | Học viên | Xong |
| 15 | ~~4/10 video lũ dưới 1080p: tải lại hay giữ?~~ → chốt 4/11: **giữ** (74 khung sau khi gộp San Angelo; bỏ thì còn 114, dưới mức 150), ngoại lệ ghi ở LABELING mục 6 và phần giới hạn của luận văn | Học viên | Xong |
| 17 | ~~Bật thăm dò đường truyền (`--link-probe-s 2`) mặc định trong `configs/edge.yaml` và cấu hình demo?~~ → chốt 6/11: **bật** (`configs/edge.yaml`, `configs/demo/*.yaml`). Mô phỏng: không mất cảnh báo nào, độ trễ lớn nhất giảm ở mọi mức mất gói và mất sóng, dữ liệu gửi gần như không đổi (`rq3_network.md`). Đổi mặc định không làm thay đổi bảng RQ3 cũ (các bảng đó không giả lập mạng). | Học viên | Xong |
| 18 | ~~Bật đếm số người theo cụm (`group_count: clusters`) mặc định?~~ → chốt 7/11: **không bật**. Mô phỏng tốt hơn (nhóm 4 người, recall 0,7: đúng số người 0,303 → 0,524) nhưng video thật SDS v21 kém hơn (0,792 → 0,583, đếm thừa 8/24) vì một người bị tách thành nhiều cụm; cách thứ ba (đếm theo khung trong cửa sổ) hết đếm thừa nhưng vẫn kém (0,750) (`rq3_group.md`). Giữ cả hai làm tuỳ chọn | Học viên | Xong |
| 19 | **Thu nhỏ theo độ cao bay còn là đóng góp không?** Tra 7/11 thấy hai công trình làm đúng ý này: Messmer và cộng sự (ICPR 2022, đổi cỡ ảnh UAV theo độ cao) và Ahmed, Pizarro (OCEANS 2025, thu nhỏ theo độ cao + số ô động, trên chính SeaDronesSee). Đề xuất: **không gọi là phương pháp mới**; giữ thành đóng góp hẹp "đưa vào pipeline thiết bị biên theo telemetry, đo cùng lúc độ chính xác theo nhóm cỡ và khối lượng tính", hoặc chuyển xuống phần hiện thực hoá; trích hai bài ở chương 2, 3. Cần đọc toàn văn hai bài để so. Kèm theo: đóng góp xác nhận theo mặt đất cũng nên viết hẹp (ghép theo toạ độ thế giới đã có cho theo dõi xe từ drone, MIDDTD 2025; phần mới là đo ở tần số xử lý thấp cho cứu nạn, so với ghép trên ảnh) | Cô | Báo cáo 13/11 |
| 16 | Trình bày câu hỏi nghiên cứu: giữ ba câu của đề cương, thêm câu hỏi con đo được cho mỗi câu, và luận điểm xuyên suốt "dữ liệu bay giúp cả ba khâu" (báo cáo 6/11). Đã viết vào TONG_QUAN mục 1.3–1.4 dưới dạng đề xuất; cô không đồng ý thì trả về bản cũ trong lịch sử git | Cô | Buổi gặp 6/11 |
