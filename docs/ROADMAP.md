# Lộ trình thực hiện FloodEye (theo đề cương chi tiết bản final)

Đề tài: Nghiên cứu phát hiện người kích thước nhỏ từ ảnh UAV trong vùng ngập lụt, hướng tới xử lý trên thiết bị biên.

Mốc cố định: nộp đề cương **16/10** · khung code và chốt Jetson **30/10** · bắt đầu RQ2 **9/11** · bảo vệ **15/12/2026**.
Ngân sách thời gian: khoảng 150 giờ, 10–20 giờ mỗi tuần (Phụ lục B của đề cương).

Tài liệu này chuyển đề cương thành việc cần làm theo tuần (mục 1), cách tổ chức và viết mã (mục 2–3), kế hoạch thí nghiệm (mục 4), những điểm kỹ thuật cần để ý (mục 5) và các quyết định còn treo (mục 6).

---

## 1. Lịch theo tuần

Cột "Báo cáo" bám đúng mục 11 của đề cương. Cột "Gán nhãn" là số khung tập test lũ đã gán nhãn cộng dồn.

| Tuần | Code | Thí nghiệm | Gán nhãn | Viết | Báo cáo thứ Sáu |
|---|---|---|---|---|---|
| 10–16/10 | Tái cấu trúc kho (mục 2); `eval/` thêm `max_det`, vùng bỏ qua, khoảng tin cậy; script chuyển nhãn VisDrone | **E0, E1, E4 trên VisDrone val**; tải FinlandProper; dựng notebook Kaggle | Hướng dẫn gán nhãn; gom video; 50 | Nộp đề cương | 16/10: đề cương, bảng VisDrone E0/E1/E4, tiến độ gán nhãn |
| 17–23/10 | `sampler`, `telemetry` (giả lập + SRT), `detector` (ảnh lớn, cắt ô theo lô), `georef`, `confirm` bản đầu | **E2** lượt 1 trên Kaggle (VisDrone + FinlandProper) | 100 | Chương 2 | 23/10: fine-tune đầu tiên; video chạy phát hiện + tracking |
| 24–30/10 | `confirm` hoàn chỉnh, `alerts` (outbox SQLite), `ground/` | E2 lượt 2; ước lượng tốc độ để chốt Jetson | 200 | Chương 3 | 30/10: **khung code xong**, cảnh báo trên bản đồ; **chốt Jetson** |
| 31/10–6/11 | `sim/netem`; đo thời gian từng chặng | **E3** (P2); E2 thêm seed; **khoá tập test lũ** (khoảng 4/11) | 250–300, khoá | Chương 4 | 6/11: RQ1 trên tập test lũ (E0–E3) |
| 7–13/11 | Xuất TensorRT trên Kaggle T4 (và Jetson nếu có) | **E4, E5, E6**; phân tích theo loại nhiễu; **RQ2 bắt đầu 9/11** | | Chương 5 (RQ1) | 13/11: bảng RQ1 đầy đủ |
| 14–20/11 | Giao diện trạm mặt đất | **RQ2**; **RQ3** | | | 20/11: kết quả RQ2, RQ3 |
| 21–27/11 | Nhiều drone, xếp ưu tiên (chỉ khi RQ đã xong) | Hoàn tất RQ3; phân tích lỗi | | Chương 5 (RQ2, RQ3), chương 6 | 27/11: demo trạm mặt đất |
| 28/11–4/12 | Đóng băng mã | | | Bản thảo đầy đủ | 4/12: bản thảo, phần mở rộng nếu kịp |
| 5–11/12 | | | | Sửa theo góp ý; slide; video demo dự phòng | 11/12: bản hoàn chỉnh |

Nếu trễ, cắt theo thứ tự của đề cương: phần mở rộng → độ đẹp trạm mặt đất → E3 → `sim/netem`. Không cắt tập test lũ và phần đánh giá.

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
| `docker/edge-jetson.Dockerfile` | Dựa trên ảnh Ultralytics cho JetPack | Chạy trên Jetson (chỉ kiểm thử được khi có thiết bị) |
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

`tests/` gồm: vòng `georef` đi và về; `confirm` với chuỗi phát hiện định sẵn; outbox khi mất mạng rồi có lại; schema của gói cảnh báo; các phép tính AP/recall (đã có ví dụ tính tay). Thêm GitHub Actions chạy `pytest` mỗi lần push; không cần GPU vì không đụng tới mô hình.

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

Cấu hình tốt nhất của RQ1 × {FP16, INT8} × chế độ công suất. Đo theo từng chặng (cắt ô, suy luận, gộp, `georef`, `confirm`). Đầu ra là đường recall theo FPS, đánh dấu ngưỡng 2 FPS. Jetson nếu chốt mua trước 30/10, không thì Kaggle T4.

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
| 2 | Lab có hỗ trợ mua Jetson không? | Thầy | 30/10 |
| 3 | Có bắt buộc bài báo trước khi bảo vệ không? | Thầy, khoa | 16/10 |
| 4 | Hạn nộp quyển? | Khoa | 16/10 |
| 5 | Có video DJI kèm `.SRT` nào để thử `telemetry` với dữ liệu thật không? | Học viên | 23/10 |
| 6 | Tài khoản Kaggle đã xác minh số điện thoại chưa? | Học viên | 17/10 |
| 7 | Khoảng tin cậy trên tập test lũ lấy mẫu theo video (cluster bootstrap) thay vì theo ảnh? Theo ảnh làm khoảng tin cậy hẹp giả khi nhiều khung cùng video (TECHNICAL 15.3) | Học viên, hỏi thầy | Trước khi khoá tập test (4/11) |
| 8 | `bytetrack`/`bytetrack_cmc`: cho `confirm.py` import tracker của ultralytics, hay đặt bộ bọc tracker trong `detector.py` để giữ quy tắc "ultralytics chỉ trong detector.py"? | Học viên | Trước RQ3 (14/11) |
