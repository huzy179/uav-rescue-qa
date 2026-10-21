# Tài liệu kỹ thuật FloodEye

Tài liệu này giải thích **cách hệ thống hoạt động và vì sao được thiết kế như vậy**: cơ sở lý thuyết, phần mã đã có, và thiết kế chi tiết của các phần sẽ làm. Mục đích là để bạn hiểu từng quyết định đủ sâu để tự sửa mã, trả lời hội đồng và viết các chương phương pháp, thực nghiệm của luận văn.

Quy ước trạng thái ở đầu mỗi mục: **[Đã có]** là mã đã chạy và đã kiểm thử; **[Thiết kế]** là đặc tả cho phần sẽ làm, có thể chỉnh khi triển khai. Lịch thực hiện xem [ROADMAP.md](ROADMAP.md); kết quả đã đo xem [results/](results/).

## Mục lục

1. [Bức tranh tổng thể](#1-bức-tranh-tổng-thể)
2. [Hình học camera: từ độ cao bay đến số pixel trên người](#2-hình-học-camera)
3. [Vì sao người nhỏ khó phát hiện: YOLO26 từ bên trong](#3-yolo26-từ-bên-trong)
4. [Cắt ô (SAHI) và chi phí tính toán](#4-cắt-ô-sahi)
5. [Đo độ chính xác: IoU, AP, recall theo nhóm kích thước](#5-đo-độ-chính-xác)
6. [Mã hiện có, từng module](#6-mã-hiện-có)
7. [Pipeline trên UAV (`edge/`)](#7-pipeline-trên-uav)
8. [Định vị: từ pixel ra toạ độ GPS (`georef`)](#8-định-vị-georef)
9. [Xác nhận qua nhiều khung (`confirm`)](#9-xác-nhận-confirm)
10. [Cảnh báo, hàng đợi và gửi bù (`alerts`)](#10-cảnh-báo-alerts)
11. [Giả lập mạng và đồng hồ mô phỏng (`sim/`)](#11-giả-lập-sim)
12. [Trạm mặt đất (`ground/`)](#12-trạm-mặt-đất)
13. [Huấn luyện (`training/`)](#13-huấn-luyện)
14. [Triển khai trên Jetson và đo tốc độ (RQ2)](#14-jetson-và-rq2)
15. [Phương pháp thí nghiệm và thống kê](#15-phương-pháp-thí-nghiệm)
16. [Tái lập, quy ước và đóng gói](#16-tái-lập-và-đóng-gói)
17. [Giới hạn kỹ thuật đã biết](#17-giới-hạn)
18. [Thuật ngữ](#18-thuật-ngữ)

---

## 1. Bức tranh tổng thể

### 1.1. Bài toán trong một câu

Từ video 4K quay thẳng xuống của UAV bay ở 30–100 m, tìm những người chỉ chiếm 5–40 pixel, xác nhận họ là thật qua nhiều khung, tính toạ độ GPS, và gửi về trạm mặt đất một gói tin nhỏ qua đường truyền chập chờn, tất cả chạy trên một máy tính nhúng công suất dưới 25 W.

### 1.2. Luồng dữ liệu

```
                    ┌──────────────────────────── UAV (edge/) ─────────────────────────────┐
 video 4K, 30 FPS   │                                                                       │
 ──────────────────►│ sampler ──► detector ──► georef ──► confirm ──► alerts (outbox SQLite)│
 telemetry          │   2 FPS      YOLO26       pixel→GPS   N khung     toạ độ trước,       │
 (GPS, độ cao,      │              ảnh lớn/                              ảnh cắt sau        │
  hướng bay)  ─────►│ telemetry ──┘ cắt ô      ▲                                    │         │
                    │                           └── telemetry                        │         │
                    └────────────────────────────────────────────────────────────────┼─────────┘
                                                                                     │ 4G/5G (giả lập: sim/netem)
                                                                                     ▼
                    ┌─────────────────────────── Trạm mặt đất (ground/) ───────────────────────┐
                    │ FastAPI ──► SQLite (alerts, crops, incidents) ──► bản đồ Leaflet          │
                    │ bỏ trùng theo alert_id, gộp nhiều drone theo khoảng cách, xếp ưu tiên    │
                    └──────────────────────────────────────────────────────────────────────────┘
```

### 1.3. Ba ràng buộc chi phối mọi thiết kế

| Ràng buộc | Hệ quả thiết kế |
|---|---|
| Người rất nhỏ (mục 2) | Không được thu ảnh về 640; phải dùng ảnh lớn hoặc cắt ô; cân nhắc đầu dò P2 |
| Thiết bị biên yếu (mục 14) | Chỉ xử lý khoảng 2 FPS; TensorRT FP16/INT8; cắt ô chạy theo lô |
| Mạng chập chờn (mục 10–11) | Chỉ gửi gói cảnh báo; outbox lưu và gửi bù; toạ độ trước, ảnh sau |

### 1.4. Hai gói, một hợp đồng

`edge/` (chạy trên UAV) và `ground/` (trạm mặt đất) **không import lẫn nhau**. Chúng chỉ chia sẻ `shared/schema.py`: định nghĩa Pydantic của gói cảnh báo. Lợi ích:
- `edge/` cài lên Jetson không kéo theo FastAPI; `ground/` cài trên laptop không kéo theo torch (khoảng 2 GB).
- Thay đổi giao thức chỉ ở một chỗ, có `schema_version` để hai phía biết đang nói cùng một phiên bản.

---

## 2. Hình học camera

**[Đã có]** trong `scripts/gsd_calc.py`. Phần này là cơ sở cho mục 4 của đề cương và cho kết luận "chỉ cần khoảng 2 FPS".

### 2.1. Mô hình camera lỗ kim

Camera nhìn thẳng xuống (nadir) ở độ cao `h` so với mặt nước. Một điểm trên mặt đất cách điểm ngay dưới camera một khoảng `X` (mét) chiếu lên ảnh tại vị trí cách tâm ảnh `u` pixel:

```
u = f · X / h        ⇔        X = u · h / f
```

`f` là tiêu cự **tính bằng pixel**, suy ra từ góc nhìn ngang (HFOV) và bề rộng ảnh `W` (pixel):

```
f = (W / 2) / tan(HFOV / 2)
```

Từ đó:
- **Bề rộng vùng chụp:** `W_m = 2 · h · tan(HFOV / 2)`
- **GSD** (Ground Sampling Distance, số mét mặt đất ứng với 1 pixel): `GSD = W_m / W = h / f`
- **Kích thước vật trên ảnh:** `s_px = s_m / GSD`

### 2.2. Góc chéo và góc ngang

Hãng camera thường ghi **góc chéo** (DFOV), đo theo đường chéo cảm biến. Với ảnh `W × H` pixel:

```
tan(HFOV / 2) = tan(DFOV / 2) · W / √(W² + H²)
tan(VFOV / 2) = tan(DFOV / 2) · H / √(W² + H²)
```

Matrice 4T ghi 82° và tiêu cự tương đương 24 mm. Trên khổ full-frame (36 × 24 mm, đường chéo 43,3 mm), 24 mm ứng với DFOV = 2·atan(21,6/24) ≈ 84°, HFOV = 2·atan(18/24) ≈ 74°. Vì vậy 82° gần như chắc chắn là góc chéo. Với video 16:9 (giả định không cắt khung thêm):

| Đại lượng | Giá trị |
|---|---|
| HFOV | 74,3° |
| VFOV | 46,2° |
| `f` cho video 3840 px | 1920 / tan(37,15°) ≈ 2.534 px |

Thực tế khi quay 4K, camera có thể cắt bớt cảm biến 4:3, làm góc ngang còn 70–74°. Thông số chính xác cần lấy từ metadata video thật hoặc tài liệu hãng.

### 2.3. Bảng tham chiếu (82° góc chéo, video 3840×2160)

```bash
python scripts/gsd_calc.py     # mặc định đúng cấu hình này
```

| Độ cao | Bề ngang vùng chụp | GSD | Người (0,5 m) | Đầu (0,2 m) | Người ở imgsz 640 | Người ở imgsz 1280 |
|---|---|---|---|---|---|---|
| 30 m | 45,5 m | 1,18 cm | 42 px | 17 px | 7,0 px | 14,1 px |
| 50 m | 75,8 m | 1,97 cm | 25 px | 10 px | 4,2 px | 8,4 px |
| 80 m | 121,2 m | 3,16 cm | 16 px | 6 px | 2,6 px | 5,3 px |
| 100 m | 151,5 m | 3,95 cm | 13 px | 5 px | 2,1 px | 4,2 px |

Cột "ở imgsz N" là kích thước sau khi ảnh 3840 px bị thu nhỏ theo tỉ lệ `N / 3840` để đưa vào mô hình (mục 3.3).

### 2.4. Thời gian người nằm trong khung và số lần nhìn thấy

UAV bay với vận tốc `v` theo chiều dọc ảnh. Chiều dọc vùng chụp là `L_v = 2h · tan(VFOV/2)`. Một điểm trên mặt đất đi từ mép trên xuống mép dưới ảnh trong thời gian:

```
T_dwell = L_v / v
```

Ở tần số xử lý `F` khung/giây, điểm đó được nhìn thấy tối đa:

```
K_max = ⌊T_dwell · F⌋ = ⌊2h · tan(VFOV/2) · F / v⌋
```

| Độ cao | `L_v` | `T_dwell` @10 m/s | `K_max` @2 FPS, 10 m/s | `K_max` @2 FPS, 5 m/s |
|---|---|---|---|---|
| 30 m | 25,6 m | 2,6 s | 5 | 10 |
| 50 m | 42,6 m | 4,3 s | 8 | 17 |
| 80 m | 68,2 m | 6,8 s | 13 | 27 |
| 100 m | 85,2 m | 8,5 s | 17 | 34 |

**Hệ quả cho RQ3:** số khung xác nhận `N` phải nhỏ hơn `K_max`, và nhỏ hơn đáng kể vì mô hình không phát hiện được người ở mọi khung (recall mỗi khung < 1). Nếu recall mỗi khung là `r` và các khung độc lập, xác suất thấy người ở ít nhất `N` trong `K` khung là phân phối nhị thức:

```
P(xác nhận) = Σ_{k=N..K} C(K,k) · r^k · (1−r)^(K−k)
```

Ví dụ ở 50 m, 10 m/s (`K = 8`), `r = 0,5`: `N = 3` cho P ≈ 0,86; `N = 5` cho P ≈ 0,36. Công thức này cho phép dự đoán trước kết quả RQ3 từ recall đo ở RQ1, rồi kiểm chứng bằng mô phỏng. Đây là một điểm nên đưa vào luận văn: nó nối RQ1 với RQ3.

### 2.5. Dịch chuyển giữa hai khung

Giữa hai khung cách nhau `Δt = 1/F`, mặt đất dịch `v · Δt` mét, tức `v · Δt / GSD` pixel. Ở 50 m, 10 m/s, 2 FPS: 5 m / 0,0197 m ≈ **254 px**, trong khi người chỉ khoảng 25 px. Đây là lý do ByteTrack gãy (mục 9).

### 2.6. Tốc độ quét

Diện tích quét mỗi giờ (không chồng dải): `A = W_m · v · 3600`. Ở 50 m, 10 m/s: 75,8 × 10 × 3600 ≈ 2,7 km²/giờ. Bay cao hơn quét nhanh hơn tuyến tính theo `h`, nhưng người nhỏ đi tỉ lệ nghịch với `h`. Đường cong recall theo số pixel (E6) cộng với công thức này cho ra khuyến nghị độ cao: **độ cao lớn nhất mà recall vẫn trên ngưỡng chấp nhận**.

---

## 3. YOLO26 từ bên trong

### 3.1. Cấu trúc

YOLO26 là bộ phát hiện một giai đoạn (one-stage), gồm ba phần. Đọc trực tiếp từ `ultralytics/cfg/models/26/yolo26.yaml`:

| Phần | Vai trò | Chi tiết |
|---|---|---|
| Backbone | Trích đặc trưng, giảm dần độ phân giải | Chuỗi Conv stride 2: P1/2, P2/4, P3/8, P4/16, P5/32; khối C3k2, SPPF, C2PSA (attention) |
| Neck | Trộn đặc trưng nhiều tầng | Kiểu FPN + PAN: upsample P5 ghép với P4, P3; rồi downsample ngược lại |
| Head | Dự đoán box và lớp | `Detect` trên P3 (stride 8), P4 (16), P5 (32) |

Hai thay đổi đáng chú ý so với YOLO11, thấy trực tiếp trong file cấu hình:
- `end2end: True`: mô hình xuất kết quả cuối mà **không cần NMS** khi suy luận. Bớt một bước hậu xử lý, có lợi cho thiết bị biên và cho xuất TensorRT.
- `reg_max: 1`: bỏ DFL (Distribution Focal Loss); box được hồi quy trực tiếp. Đầu ra đơn giản hơn, dễ lượng tử hoá hơn.

Theo tài liệu của Ultralytics, YOLO26 còn có ProgLoss và STAL (gán nhãn có lưu ý vật thể nhỏ), được giới thiệu là cải thiện vật thể nhỏ. Đây là tuyên bố của nhà phát triển; E5 (so với YOLO11s) là cách đề tài kiểm chứng nó.

Kích thước bản `s`: 10,0 triệu tham số, 22,8 GFLOPs ở ảnh 640. GFLOPs tăng theo bình phương cạnh ảnh: ở 1280 khoảng 91 GFLOPs.

### 3.2. Vì sao người nhỏ bị mất

Tầng phát hiện mịn nhất là P3, **stride 8**: mỗi ô trên bản đồ đặc trưng ứng với một vùng 8×8 pixel của ảnh đầu vào. Một người 4 pixel chỉ chiếm một nửa ô, đặc trưng của họ bị trộn với nền ngay từ mấy lớp Conv đầu. Có ba cơ chế cùng gây hại:

1. **Mất thông tin do lấy mẫu xuống.** Sau 3 lần stride 2, chi tiết nhỏ hơn 8 px gần như không còn biểu diễn riêng.
2. **Gán nhãn khi huấn luyện.** Bộ gán nhãn chọn các ô "dương" cho mỗi box; box rất nhỏ có rất ít ô ứng viên, nên tín hiệu học yếu. STAL được thiết kế để giảm vấn đề này.
3. **IoU khắc nghiệt với box nhỏ** (mục 5.2): box dự đoán đúng chỗ nhưng lệch 2 px vẫn bị tính là sai.

### 3.3. imgsz và letterbox

Khi gọi `model.predict(img, imgsz=N)`, ultralytics thu ảnh sao cho **cạnh dài bằng N**, giữ tỉ lệ, rồi đệm viền xám cho chia hết cho stride lớn nhất (letterbox; với ảnh đơn và mô hình `.pt` dùng chế độ "rect", đệm tối thiểu). Box dự đoán được quy đổi ngược về toạ độ ảnh gốc. Vì vậy:

```
kích thước người khi vào mô hình = kích thước gốc × N / max(W, H)
```

Video 3840 px với imgsz 1280 bị thu 3 lần: người 25 px còn 8,4 px, khoảng một ô P3. Với imgsz 640: 4,2 px, nửa ô. Đây là cơ chế đằng sau con số AP tăng gấp đôi từ E0 lên E1.

Thu ảnh lớn hơn (1920, 3840) giữ được người nhưng chi phí tăng theo bình phương: 3840 tốn khoảng 36 lần so với 640.

### 3.4. Đầu dò P2

`yolo26-p2.yaml` có sẵn trong ultralytics: thêm tầng phát hiện ở **stride 4**. Người 8 px giờ chiếm 2×2 ô thay vì một ô. Cái giá:
- Bản đồ đặc trưng P2 có số ô gấp 4 lần P3, nên phần neck và head tốn thêm tính toán và bộ nhớ đáng kể.
- Phải huấn luyện lại; không dùng được trọng số COCO cho phần đầu mới (backbone vẫn tận dụng được).

E3 đo xem mức tăng recall có đáng với chi phí đó không, và RQ2 đo chi phí đó trên thiết bị biên.

### 3.5. Ngưỡng tin cậy

Mỗi box có điểm `conf` từ 0 đến 1. Kết quả VisDrone cho thấy một điều quan trọng: ở conf 0,25, mô hình COCO chỉ bắt 30% người 8–16 px, nhưng nếu giữ mọi box thì bắt được tới 75%. Mô hình **có thấy** người nhỏ, nhưng không tự tin. Hai hệ quả:
- Fine-tune (E2) chủ yếu là dạy mô hình tự tin hơn với người nhỏ nhìn từ trên cao.
- Trong cứu hộ, ngưỡng nên chọn theo **recall mục tiêu**, rồi để bước xác nhận nhiều khung (mục 9) lọc báo nhầm, thay vì dùng 0,25 mặc định.

---

## 4. Cắt ô (SAHI)

**[Đã có]** qua thư viện SAHI trong `scripts/run_sahi.py`. **[Thiết kế]** bộ cắt ô riêng trong `edge/detector.py`.

### 4.1. Nguyên lý

Thay vì thu nhỏ cả ảnh 3840 px về 640, cắt ảnh thành các ô 640×640 **giữ nguyên độ phân giải**, chạy mô hình trên từng ô, rồi ghép kết quả. Người 25 px vẫn là 25 px khi vào mô hình.

### 4.2. Số ô

Với ô cạnh `s`, độ chồng `o`, bước nhảy `step = s · (1 − o)`. Số ô theo một chiều dài `L`:

```
n = ⌈(L − s) / step⌉ + 1
```

Ảnh 3840×2160, `s = 640`, `o = 0,2` (bước 512): `n_x = ⌈3200/512⌉ + 1 = 8`, `n_y = ⌈1520/512⌉ + 1 = 4`, tổng **32 ô** (đã kiểm tra bằng `sahi.slicing.get_slice_bboxes`). Ảnh VisDrone 1360×765 chỉ cần 6 ô.

SAHI mặc định (`perform_standard_pred=True`) chạy thêm **một lượt toàn ảnh** ở imgsz của mô hình, để bắt người lớn bị cắt đôi giữa các ô. Tổng: 33 lần suy luận cho mỗi khung 4K.

### 4.3. Ghép kết quả

Box từ các ô được dời về toạ độ ảnh gốc, rồi gộp các box trùng. Tham số mặc định của SAHI 0.12.8:

| Tham số | Giá trị | Ý nghĩa |
|---|---|---|
| `postprocess_type` | `GREEDYNMM` | Gộp tham lam: box điểm cao "nuốt" box trùng, hợp nhất toạ độ thay vì chỉ xoá |
| `postprocess_match_metric` | `IOS` | Intersection over Smaller: giao chia diện tích box nhỏ hơn. Bắt được trường hợp một box bị cắt nằm gọn trong box đầy đủ |
| `postprocess_match_threshold` | 0,5 | |

Vì sao IOS chứ không phải IoU: người nằm ở mép ô bị cắt thành box nửa người. Box nửa người và box đầy đủ (từ ô bên cạnh) có IoU chỉ khoảng 0,5, nhưng IOS gần 1.

### 4.4. Vì sao SAHI không thắng trên VisDrone

Kết quả E4: AP50 0,460, thấp hơn E1 (imgsz 1280) là 0,497, lại chậm gấp 4 lần. 75% ảnh VisDrone val rộng 1360 px, nên imgsz 1280 đã gần như giữ nguyên độ phân giải gốc: cắt ô không thêm chi tiết, chỉ thêm box bị cắt ở mép ô làm giảm precision (0,78 so với 0,83). Với video 4K tình hình đảo ngược: imgsz 1280 thu nhỏ 3 lần, còn cắt ô giữ nguyên. **E4 phải được đánh giá lại trên dữ liệu độ phân giải cao.**

### 4.5. Bộ cắt ô riêng trong `edge/detector.py` [Đã có]

Đã cài đủ 6 bước (gộp bằng NMS tham lam theo IOS, ngưỡng 0,5, viết bằng numpy; lượt toàn ảnh bật bằng `full_pass`). Đã đối chiếu với SAHI trên VisDrone val bằng bootstrap cặp (mục 15.3): AP50 thấp hơn 0,008 (khoảng tin cậy −0,011 đến −0,003), chủ yếu ở người trên 32 px; ở người dưới 8 px thì cao hơn; ở IoU 0,3 cao hơn 0,016. Box tìm đúng chỗ nhưng kém khít hơn. Xem [results/visdrone_tiled_vs_sahi.md](results/visdrone_tiled_vs_sahi.md). Hợp nhất toạ độ kiểu NMM đã thử và bỏ (AP50 tụt dưới 0,05).

SAHI gọi mô hình từng ô một và gắn với cách nạp mô hình của nó. Bộ cắt ô riêng:

1. Tính danh sách ô như mục 4.2; ô cuối mỗi hàng, cột được kéo sát mép ảnh để không có ô thừa ra ngoài.
2. Cắt bằng slicing numpy (không sao chép dữ liệu ảnh), đưa **cả lô ô** vào một lần gọi `model.predict(list_of_tiles, imgsz=s)`. Trên GPU và TensorRT, chạy theo lô tận dụng song song tốt hơn nhiều so với 32 lần gọi riêng.
3. Cộng offset của từng ô vào box.
4. Gộp: NMS không phân lớp theo IoU (hoặc gộp kiểu IOS như SAHI). Có thể dùng `torchvision.ops.nms` trên edge; trên Jetson không có torchvision thì dùng `cv2.dnn.NMSBoxes`.
5. Tuỳ chọn: lượt toàn ảnh ở độ phân giải thấp cho người lớn.
6. Trả về `list[Detection]` cùng thời gian từng phần (cắt, suy luận, gộp) cho RQ2.

YOLO26 không cần NMS **trong** từng ô, nhưng vẫn cần gộp **giữa** các ô vì cùng một người xuất hiện ở vùng chồng của hai ô.

Tối ưu tiềm năng (nếu RQ2 cần): chỉ chạy ô có nước hoặc có khả năng có người (lọc bằng mô hình phân vùng nước rẻ, hoặc bằng lượt toàn ảnh độ phân giải thấp với ngưỡng rất thấp), ô không thay đổi so với khung trước thì bỏ qua.

---

## 5. Đo độ chính xác

**[Đã có]** trong `eval/metrics.py` và `eval/eval_by_size.py`; đã đối chiếu với `yolo val` của ultralytics (lệch dưới 1%).

### 5.1. IoU

```
IoU(A, B) = diện tích(A ∩ B) / diện tích(A ∪ B)
```

Một dự đoán được coi là đúng (TP) nếu IoU với một nhãn chưa được ghép đạt ngưỡng (thường 0,5).

### 5.2. IoU khắc nghiệt với box nhỏ

Dự đoán lệch 2 px theo cả hai chiều so với nhãn:

| Kích thước box | Giao | Hợp | IoU |
|---|---|---|---|
| 8×8 | 6×6 = 36 | 128 − 36 = 92 | **0,39** (bị tính là sai) |
| 16×16 | 14×14 = 196 | 512 − 196 = 316 | 0,62 |
| 32×32 | 30×30 = 900 | 2048 − 900 = 1148 | 0,78 |

Cùng một sai lệch 2 px, người 8 px bị tính là bỏ sót, người 32 px thì không. Mà chính người gán nhãn cũng khó đặt box chính xác tới 1–2 px cho người 8 px. Vì vậy đề cương báo cáo thêm IoU 0,3 cho nhóm dưới 8 px. Kết quả VisDrone xác nhận: hạ IoU xuống 0,3 làm AP nhóm dưới 8 px tăng gấp đôi (0,167 → 0,342 với E1). Hướng nghiên cứu liên quan: NWD (Normalized Wasserstein Distance) thay IoU bằng khoảng cách giữa hai phân phối Gauss.

### 5.3. Ghép dự đoán với nhãn

`match_image` trong `eval/metrics.py`, cho một ảnh:
1. Sắp dự đoán theo conf giảm dần.
2. Với mỗi dự đoán, tìm các nhãn chưa bị lấy có IoU ≥ ngưỡng; chọn nhãn tốt nhất; đánh dấu đã lấy.
3. Không khớp nhãn nào thì là FP.

Đây là cách ghép tham lam chuẩn của COCO và Pascal VOC.

### 5.4. Đường precision-recall và AP

Gộp mọi dự đoán của mọi ảnh, sắp theo conf giảm dần. Hạ dần ngưỡng conf, tại mỗi bước:

```
precision = TP / (TP + FP)        recall = TP / số nhãn
```

**AP** là diện tích dưới đường precision-recall, tính theo kiểu COCO:
1. Lấy "bao lồi" precision: tại mỗi mức recall, precision bằng giá trị lớn nhất ở mọi mức recall lớn hơn hoặc bằng (làm đường cong đơn điệu giảm).
2. Lấy mẫu tại 101 mức recall 0; 0,01; …; 1; mức nào chưa đạt được thì precision bằng 0.
3. AP là trung bình 101 giá trị.

AP50 là AP ở IoU 0,5; AP50:95 là trung bình AP ở 10 ngưỡng IoU từ 0,5 đến 0,95 (đánh giá cả độ chính xác định vị).

Vì sao tính AP với conf 0,001: AP cần cả đường cong, tức cần cả những dự đoán điểm thấp. Cắt ở 0,25 sẽ chặt đuôi đường cong và làm AP thấp giả tạo. Ngược lại, **recall vận hành** báo ở conf 0,25 (ngưỡng triển khai thật). `recall_max` là recall khi giữ mọi dự đoán: trần mà việc hạ ngưỡng có thể đạt.

### 5.5. Theo nhóm kích thước

Nhóm theo **cạnh ngắn của nhãn** trên ảnh gốc: <8, 8–16, 16–32, >32 px. Dùng cạnh ngắn thay vì diện tích vì nhìn từ trên xuống, người có dạng elip dẹt; cạnh ngắn phản ánh "độ mảnh" quyết định khả năng phát hiện.

Cách tính theo nhóm theo quy ước của COCO (hàm `match_image` với `size_range`):
- Nhãn trong nhóm là đối tượng cần tìm; nhãn ngoài nhóm được **bỏ qua**.
- Dự đoán khớp nhãn bị bỏ qua: không tính.
- Dự đoán không khớp gì: chỉ tính là FP nếu **chính nó** nằm trong nhóm.

Nếu không làm vậy, một dự đoán đúng cho người 40 px sẽ bị tính là FP khi đánh giá nhóm dưới 8 px.

**Lỗi biên đã sửa.** Nhãn YOLO lưu toạ độ chuẩn hoá 6 chữ số. Box VisDrone rộng đúng 8 px (rất phổ biến, vì VisDrone ghi kích thước bằng số nguyên) khi đọc lại thành 7,99999 px và rơi sang nhóm "<8". Lỗi này làm nhóm dưới 8 px bị đếm thừa khoảng 30%. Sửa bằng cách làm tròn cạnh ngắn tới 0,01 px trước khi chia nhóm (`_short_side`), có kiểm thử riêng.

### 5.6. Vùng bỏ qua

VisDrone đánh dấu một số vùng là "ignored" (đám đông quá dày, vùng mờ không gán nhãn được). Dự đoán rơi vào đó có thể là người thật nhưng không có nhãn. Nếu tính là FP, precision bị đánh giá thấp oan. `match_image` nhận thêm `ignore_regions`: dự đoán không khớp nhãn nào mà có ít nhất 50% diện tích nằm trong một vùng bỏ qua (IoA, Intersection over Area của dự đoán) thì không tính. Ultralytics bỏ hẳn các vùng này khi chuyển nhãn, nên AP của nó thấp hơn một chút (0,490 so với 0,497).

### 5.7. Recall theo loại nhiễu [Thiết kế]

**[Đã có]** phần dữ liệu: `tools/convert_cvat.py` ghi `boxes_<split>.csv` (thuộc tính từng người) và `tags_<split>.csv` (thẻ từng ảnh). **[Thiết kế]** phần tính recall theo tập con.

Tập test lũ được gắn thẻ nhiễu (lóa nước, rác trôi, ngập một phần, che khuất, thời tiết, nhòe). Hai mức gắn thẻ:
- **Theo ảnh** (lóa, thời tiết, nhòe): tính recall trên tập con các ảnh có thẻ.
- **Theo box** (ngập một phần, che khuất): thêm một cột thẻ cho từng nhãn, tính recall trên tập con các nhãn có thẻ.

Báo động giả do rác trôi đo bằng số FP trên ảnh có thẻ "vật nổi". Mỗi tập con nhỏ nên phải báo khoảng tin cậy (mục 15.3).

---

## 6. Mã hiện có

### 6.1. Bản đồ module [Đã có]

Xếp theo đường đi của dữ liệu. Mũi tên là "đưa kết quả cho".

**Trên UAV (`edge/`), một khung đi qua:**

```
sampler ──(frame_id, t, ảnh)──► detector ──Detection──► georef ──Detection có lat/lon──► confirm ──Confirmation──► alerts ──HTTP──► ground
    ▲                                                     ▲                                                           │
    └── video/thư mục khung          telemetry.at(t) ─────┘                                              outbox SQLite, gửi lại khi mất mạng
```

| File | Vai trò | Kỹ thuật chính (mục) |
|---|---|---|
| `edge/sampler.py` | Đọc video/thư mục ảnh; `iter_timed_frames` lấy mẫu ở F FPS, `t` tính từ chỉ số khung | Đồng hồ mô phỏng (11.2) |
| `edge/telemetry.py` | `SampledTelemetry` từ CSV hoặc `.SRT` DJI, nội suy theo `t`; `python -m edge.telemetry file.SRT` để kiểm tra file | Nội suy góc theo đường ngắn nhất (7.3) |
| `edge/detector.py` | `YoloDetector` toàn ảnh hoặc cắt ô theo lô, gộp NMS theo IOS; `ReplayDetector` đọc lại `detections.jsonl`; `ByteTracker` bọc tracker của ultralytics. Nơi duy nhất import ultralytics | Cắt ô (4.5), ByteTrack (9.2) |
| `edge/georef.py` | `pixel_to_gps`, `gps_to_pixel` (hàm ngược), `Camera.from_fov`, `frame_motion` (chuyển động mặt đất giữa hai khung) | Chiếu nadir (8), bù chuyển động (9.3) |
| `edge/confirm.py` | `GeoConfirmer` (gom theo vị trí mặt đất), `TrackConfirmer` (theo track ByteTrack, có hoặc không bù chuyển động camera) | Xác nhận N khung (9) |
| `edge/alerts.py` | `Outbox` SQLite, `HttpTransport`, `FakeTransport`, cắt ảnh JPEG | Outbox, gửi lại lùi theo hàm mũ (10) |
| `edge/main.py` | Nối các khối, ghi log JSONL; không chứa logic | (7.5) |
| `edge/device.py` | Chọn thiết bị: CUDA → MPS → CPU | |

**Trạm mặt đất (`ground/`):** `app.py` (FastAPI: nhận cảnh báo, bỏ trùng theo `alert_id`, lưu SQLite), `map.html` (bản đồ Leaflet). Chỉ import `shared/`.

**Giả lập (`sim/`):** `flight.py` (`StraightFlight`, telemetry giả lập), `scenario.py` (người, nhãn theo thời gian, nhiễu GPS, detector giả), `make_rq3.py` (sinh trọn một kịch bản RQ3), `netem.py` (`NetemTransport`, mạng mất gói và mất sóng, có seed).

**Dùng chung (`shared/`):** `schema.py` (`Telemetry`, `Detection`, `Confirmation`, `Alert`, `AlertCrop`), `config.py` (`--config file.yaml`), `provenance.py` (`run_config.json` có commit git và máy chạy).

**Đánh giá (`eval/`), chạy sau, đọc kết quả đã lưu:**

| File | Vai trò |
|---|---|
| `eval/eval_by_size.py` | AP, recall, precision theo nhóm kích thước, khoảng tin cậy bootstrap (theo ảnh hoặc theo video), biểu đồ PR |
| `eval/compare_runs.py` | So sánh hai lần chạy bằng bootstrap cặp (15.3) |
| `eval/metrics.py` | IoU, IoA, ghép, AP, điểm vận hành, `bootstrap_ci`, `paired_bootstrap` (5, 15.3) |
| `eval/splits.py` | Nhóm theo video, chia tập, dHash tìm ảnh gần trùng (15.6) |
| `eval/rq3_metrics.py` | Chỉ số RQ3 từ log pipeline và nhãn theo thời gian (15.4) |
| `eval/report.py`, `eval/draw.py` | Ghi CSV, tóm tắt, histogram; vẽ box |

**Script thí nghiệm (`scripts/`):** `run_baseline.py` (toàn ảnh), `run_sahi.py` (SAHI), `run_tiled.py` (bộ cắt ô riêng, cùng định dạng đầu ra), `gsd_calc.py` (mục 2), `benchmark_speed.py` (tốc độ `.pt`, `.onnx`, `.engine`).

**Công cụ dữ liệu (`tools/`):** `convert_visdrone.py` (VisDrone → YOLO một lớp, kèm vùng bỏ qua), `convert_cvat.py` (nhãn tập lũ từ CVAT → YOLO, vùng bỏ qua, CSV thuộc tính và thẻ), `split_by_video.py` (chia tập theo video), `check_leakage.py` (rò rỉ giữa các tập), `label_size_stats.py` (kích thước người khi huấn luyện, 13.4).

**Huấn luyện (`training/`):** `train.py`, notebook Kaggle mỏng (13).

**Kiểm thử (`tests/`):** chạy không cần mô hình, GPU hay `data/`; mỗi khối thuần có test (georef đi–về, outbox khi mất mạng, AP tính tay, bootstrap…).

### 6.2. Định dạng dữ liệu trao đổi

**`boxes.csv`**: mỗi dòng một box, toạ độ pixel trên **ảnh gốc**:

```
image, method, imgsz, conf, width_px, height_px, x1, y1, x2, y2
```

`method` là `full`, `sahi` hoặc `tiled`; với SAHI và `tiled`, `imgsz` là kích thước ô. Thiết kế này cho phép nối CSV của nhiều lần chạy rồi so sánh bằng pandas.

**`per_image.csv`**: `image, method, imgsz, n_persons, infer_ms`. `eval_by_size.py` dùng file này để biết **ảnh nào đã được xử lý**: ảnh không có dự đoán vẫn phải tính vào mẫu số của recall.

**`run_config.json`** (`shared/provenance.py`): lệnh chạy, toàn bộ tham số, phiên bản Python, ultralytics, torch, sahi, opencv, numpy, tên và **mã băm SHA-256 của file trọng số**, thiết bị, hệ điều hành, kiến trúc máy (`machine`: `arm64` là Mac, `aarch64` là Jetson), **commit git** và cờ `dirty` (còn sửa chưa commit). Lần chạy cho số liệu chính thức phải có `dirty: false`, nếu không thì không biết chính xác mã nào sinh ra số. Mã băm quan trọng vì `yolo26s.pt` có thể được Ultralytics cập nhật mà giữ nguyên tên.

### 6.3. Đo thời gian

`infer_ms` đo bằng `time.perf_counter()` quanh một lần gọi `predict`: gồm tiền xử lý (letterbox, chuẩn hoá), suy luận và hậu xử lý; không gồm đọc ảnh từ đĩa. Lần gọi đầu ở mỗi imgsz bị bỏ (làm nóng): lần đầu chậm bất thường do khởi tạo kernel và cấp phát bộ nhớ. Trên MPS, ảnh có kích thước mới cũng gây chậm ở lần đầu, nên ảnh đầu tiên của mỗi độ phân giải có thể có thời gian cao bất thường.

### 6.4. Cấu hình

`shared/config.py` dùng hai lượt parse: lượt đầu chỉ đọc `--config`, nạp YAML, đặt làm giá trị mặc định cho parser; lượt hai parse đầy đủ, nên tham số gõ trên dòng lệnh luôn thắng. Khoá không có trong parser bị báo lỗi ngay. Mỗi thí nghiệm có một file trong `configs/experiments/` (ví dụ `E1_visdrone.yaml`).

### 6.5. Chuyển nhãn VisDrone

Mỗi dòng nhãn gốc: `trái, trên, rộng, cao, score, category, truncation, occlusion`. Quy tắc:
- `category` 1 (pedestrian) và 2 (people) → lớp 0 `person`. VisDrone tách người đi bộ và người đứng/ngồi; với bài toán này cả hai là người.
- `category` 0 (vùng bỏ qua) và mọi box có `score` = 0 → `ignore/`.
- Người đi xe đạp, xe máy (VisDrone gán vào lớp phương tiện) bị bỏ, khớp với định nghĩa "người" của đề tài; cần ghi rõ trong luận văn.
- Ảnh được tạo hard link thay vì sao chép, không tốn thêm dung lượng.

### 6.6. Đóng gói

`pyproject.toml` định nghĩa gói `floodeye` gồm `shared`, `edge`, `ground`, `sim`, `eval`, với ba nhóm phụ thuộc. `pip install -e ".[dev]"` cài ở chế độ editable: sửa mã có hiệu lực ngay, và script chạy được từ bất kỳ thư mục nào mà không cần chỉnh `sys.path`. Phiên bản thư viện được ghim chính xác để tái lập.

---

## 7. Pipeline trên UAV

**[Đã có]** `schema` (`Telemetry`, `Detection`, `Confirmation`, `Alert`, `AlertCrop`), `sampler.iter_timed_frames`, `SampledTelemetry` (CSV và SRT), `YoloDetector`, `ReplayDetector` (đọc lại `detections.jsonl`) và `main.py` đủ các chặng tới gửi cảnh báo. Khác thiết kế: `Alert` mang `t` (giây theo đồng hồ chuyến bay) thay cho `time: datetime`, vì pipeline không đọc đồng hồ máy; `alert_id` và `uav_id` chỉ nhận chữ, số, `_`, `.`, `-`.

### 7.1. Kiểu dữ liệu chính (`shared/schema.py`)

```python
class Telemetry(BaseModel):
    t: float                 # giây, theo đồng hồ của chuyến bay
    lat: float; lon: float   # độ, WGS84
    alt_agl_m: float         # độ cao so với mặt đất/mặt nước, KHÔNG phải so với mực nước biển
    yaw_deg: float           # hướng của đỉnh ảnh, 0 = Bắc, theo chiều kim đồng hồ
    pitch_deg: float = -90   # -90 = nhìn thẳng xuống
    roll_deg: float = 0

class Detection(BaseModel):
    frame_id: int; t: float
    box_px: tuple[float, float, float, float]   # x1, y1, x2, y2 trên ảnh gốc
    conf: float
    lat: float | None = None; lon: float | None = None   # điền bởi georef

class Alert(BaseModel):
    schema_version: int = 1
    alert_id: str            # "<uav_id>-<số thứ tự>", duy nhất, dùng để bỏ trùng
    uav_id: str; time: datetime
    lat: float; lon: float; position_error_m: float
    altitude_m: float; cluster_id: int
    confidence: float; frames_confirmed: int
    box_px: tuple[int, int, int, int]; model: str
```

Ảnh cắt là một thông điệp riêng `AlertCrop(alert_id, jpeg_base64)` (mục 10).

### 7.2. `sampler.py`

Video DJI thường 30 FPS. Để xử lý `F` FPS, lấy một khung sau mỗi `stride = round(fps_video / F)` khung. Mỗi khung mang `frame_id` và `t = chỉ số khung / fps_video`. Thời gian này là khoá để tra telemetry, nên phải lấy từ chỉ số khung chứ không phải đồng hồ máy.

Khi chạy thật trên UAV, sampler đọc luồng camera và bỏ khung nếu pipeline chưa xử lý xong khung trước (luôn xử lý khung mới nhất, không xếp hàng). Khi phát lại video cho thí nghiệm, không bỏ khung nào để kết quả tái lập được.

### 7.3. `telemetry.py`

Một giao diện, nhiều nguồn:

| Nguồn | Mô tả | Trạng thái |
|---|---|---|
| `SampledTelemetry.from_csv` | File CSV `t, lat, lon, alt_agl_m, yaw_deg, …` | Đã có |
| `SyntheticFlight` (`sim/flight.py`) | Sinh đường bay: thẳng hoặc zig-zag (lawnmower) theo độ cao, vận tốc, khoảng cách dải; có thể cộng nhiễu | Làm trước |
| `SampledTelemetry.from_srt` | File phụ đề `.SRT` đi kèm video DJI | Đã có, theo định dạng Mavic 3/Mini/M30 và Phantom 4; chưa thử với file thật. Kiểm tra file mới bằng `python -m edge.telemetry file.SRT`. Cần xác minh `gb_yaw` là hướng tuyệt đối (so với Bắc) hay so với thân máy bay trên dòng máy dùng thật |
| `MavlinkTelemetry` | Bộ điều khiển bay PX4/ArduPilot | Hướng phát triển |

Truy vấn `at(t)` nội suy tuyến tính giữa hai mẫu gần nhất; riêng góc hướng nội suy theo đường ngắn nhất trên vòng tròn (từ 359° sang 1° là +2°, không phải −358°).

File SRT của DJI là phụ đề, mỗi khung (hoặc mỗi nhóm khung) có một khối chữ chứa vĩ độ, kinh độ, độ cao tương đối và tuyệt đối, đôi khi cả góc gimbal. **Định dạng khác nhau giữa các dòng máy**, nên bộ đọc dùng biểu thức chính quy linh hoạt và phải được kiểm thử với file thật. Lưu ý dùng độ cao tương đối (so với điểm cất cánh) làm `alt_agl_m`, và hiệu chỉnh nếu mặt nước thấp hoặc cao hơn điểm cất cánh.

### 7.4. `detector.py`

```python
class YoloDetector:
    def __init__(self, model_path: str, mode: Literal["full", "tiled"], imgsz: int,
                 tile: int = 640, overlap: float = 0.2, conf: float = 0.1, device: str | None = None): ...
    def detect(self, frame: np.ndarray) -> tuple[list[Detection], dict[str, float]]: ...
```

- `model_path` nhận `.pt`, `.onnx`, `.engine`. Ultralytics tự chọn backend theo đuôi file. `.engine` có kích thước đầu vào và batch cố định lúc xuất, nên cấu hình phải khớp với lúc xuất.
- `mode="full"`: một lần `predict` ở `imgsz`.
- `mode="tiled"`: bộ cắt ô ở mục 4.5.
- Trả về thêm dict thời gian từng phần cho RQ2.
- Ultralytics chỉ được import trong file này; các module khác làm việc với `Detection`.

### 7.5. `main.py` [Đã có]

Vòng lặp chính, nối các khối qua giao diện (`Detector`, `TelemetrySource`, `Transport` đều là `Protocol`, có bản giả để kiểm thử):

```python
for frame_id, t, frame in iter_timed_frames(source, fps):      # t = frame_id / fps_video
    tel = telemetry.at(t)                                       # CSV, SRT hoặc StraightFlight
    dets, timings = detector.detect(frame, frame_id, t)         # YOLO hoặc ReplayDetector
    dets = [locate(d, tel, cam) for d in dets]                  # điền lat/lon
    for c in confirmer.update(dets, t):                         # cụm vừa đủ N lần thấy
        outbox.enqueue(make_alert(c, ...), crop_jpeg(frame, c.box_px), t)
    outbox.pump(t)                                              # gửi những gì đến hạn
    ghi detections.jsonl, confirmations.jsonl, alerts.jsonl, alerts_sent.jsonl, timings.jsonl
sau khung cuối: pump thêm mỗi giây, tối đa --drain-s giây, để gửi bù phần còn lại
```

Mọi khối nhận thời gian `t` từ ngoài vào, không tự gọi đồng hồ (mục 11.2). Thời gian xử lý thật đo bằng `perf_counter` và chỉ ghi vào `timings.jsonl`.

Ba chế độ chạy thường dùng:

| Mục đích | Lệnh (thêm `--config configs/edge.yaml --source video.mp4`) | Ghi chú |
|---|---|---|
| Demo đủ hai phía | `--ground-url http://localhost:8000 --save-video` | Không có `--telemetry` thì video có dòng "TELEMETRY GIA LAP" |
| Thử mạng chập chờn | `--net-loss 0.2 --net-outage 30 90 --seed 1` | `NetemTransport` bọc ngoài transport |
| Quét tham số RQ3 không cần GPU | `--replay runs/.../detections.jsonl --confirm bytetrack_cmc --n-confirm 5` | Phát hiện đọc lại từ lần chạy trước; georef, confirm, alerts chạy lại |

## 8. Định vị (georef)

**[Đã có]** mục 8.1–8.2 trong `edge/georef.py`, kiểm thử trong `tests/test_georef.py`. Hàm thuần, không trạng thái, kiểm thử được bằng tay.

### 8.1. Pixel → mặt đất, camera nhìn thẳng xuống

Ký hiệu: ảnh `W × H`, tâm `(c_x, c_y) = (W/2, H/2)`, tiêu cự pixel `f` (mục 2.1), độ cao `h`, hướng `ψ` (hướng của đỉnh ảnh, đo từ Bắc theo chiều kim đồng hồ). Điểm ảnh `(u, v)` (u sang phải, v xuống dưới) lấy ở **tâm đáy box**: với người đứng, đó là chân; với người nhìn từ trên xuống, tâm box và tâm đáy gần như trùng nhau.

Bước 1, toạ độ trong hệ của UAV (mét): tiến về phía đỉnh ảnh, phải theo chiều u:

```
forward = −(v − c_y) · h / f
right   =  (u − c_x) · h / f
```

Bước 2, xoay theo hướng bay sang hệ Bắc–Đông:

```
north = forward · cos ψ − right · sin ψ
east  = forward · sin ψ + right · cos ψ
```

Kiểm tra: ψ = 0 thì north = forward, east = right; ψ = 90° (đỉnh ảnh hướng Đông) thì east = forward, north = −right (bên phải là phía Nam). Đúng.

Bước 3, cộng vào toạ độ UAV (xấp xỉ mặt phẳng cục bộ, sai số không đáng kể trong vài km):

```
lat = lat_uav + north / R ·(180/π)
lon = lon_uav + east / (R · cos(lat_uav)) ·(180/π)        R = 6.378.137 m
```

### 8.2. Hàm ngược: GPS → pixel

Làm ngược ba bước trên. Hàm ngược có hai công dụng:
- **Kiểm thử:** pixel → GPS → pixel phải ra đúng điểm cũ (sai số dưới 0,01 px).
- **Giả lập:** đặt "người thật" tại toạ độ cố định trên mặt nước; với mỗi khung của chuyến bay giả lập, hàm ngược cho biết người đó ở pixel nào (hoặc nằm ngoài khung). Đó là nhãn theo thời gian cho RQ3 (mục 15.5), và là cách bù chuyển động camera cho `bytetrack_cmc` (mục 9.3).

### 8.3. Khi camera nghiêng [Thiết kế mở rộng]

Đề tài giả định nhìn thẳng xuống, nhưng cần định lượng sai số khi giả định sai. Tổng quát: tia từ tâm camera qua pixel `(u, v)` có hướng `d_cam = ((u − c_x)/f, (v − c_y)/f, 1)` trong hệ camera. Xoay bằng ma trận `R = R_yaw · R_pitch · R_roll` sang hệ thế giới, rồi giao với mặt phẳng `z = 0`:

```
P = C + λ · R · d_cam,     λ = −C_z / (R · d_cam)_z
```

Với camera nadir, R chỉ còn phép xoay quanh trục đứng và công thức thu về mục 8.1.

### 8.4. Lan truyền sai số

Điểm cách nadir một khoảng `d` trên mặt đất:

| Nguồn sai số | Sai số vị trí | Ví dụ ở 50 m, mép ảnh (d ≈ 38 m) |
|---|---|---|
| GPS của UAV, σ_GPS | σ_GPS (cộng trực tiếp) | 2–5 m với GPS thường; dưới 0,1 m với RTK |
| Độ cao, δh | d · δh / h | δh = 2 m → 1,5 m |
| Hướng bay, δψ (radian) | d · δψ | δψ = 2° → 1,3 m |
| Nghiêng camera, δθ | ≈ h · tan δθ (ở tâm), lớn hơn ở mép | δθ = 1° → 0,9 m |
| Box lệch 2 px | 2 · GSD | 0,04 m (không đáng kể) |

Tổng gần đúng (các nguồn độc lập): căn bậc hai của tổng bình phương. Với GPS thường, **GPS chiếm phần lớn sai số**. Con số này quyết định bán kính gom của `confirm` (mục 9.4) và được ghi vào trường `position_error_m` của cảnh báo.

Một tinh tế: GPS thường lệch **chậm** (sai số tương quan theo thời gian), nên giữa hai khung liên tiếp, vị trí của cùng một người gần như lệch cùng chiều. Điều này có lợi cho `confirm` kiểu `geo`: bán kính gom có thể nhỏ hơn sai số tuyệt đối. Mô phỏng nên dùng nhiễu GPS dạng quá trình ngẫu nhiên tương quan (ví dụ Gauss–Markov bậc 1), không phải nhiễu trắng độc lập mỗi khung.

---

## 9. Xác nhận (confirm)

**[Đã có]** cả ba chiến lược trong `edge/confirm.py`, chọn bằng `--confirm geo|bytetrack|bytetrack_cmc`. Mục tiêu: chỉ cảnh báo khi một người được thấy ở ít nhất `N` khung, để lọc báo nhầm ngẫu nhiên (sóng nước, rác), và mỗi người chỉ sinh **một** cảnh báo.

### 9.1. Giao diện chung

```python
class Confirmer(Protocol):
    def update(self, dets: list[Detection], t: float) -> list[Confirmation]: ...
```

`update` trả về những cụm **vừa đủ điều kiện** ở khung này (mỗi cụm chỉ trả về một lần).

Để so sánh công bằng trong RQ3, ba chiến lược **chỉ khác nhau ở cách ghép** một phát hiện mới vào cụm/track nào. Phần còn lại dùng chung một hàm (`_newly_confirmed`): đếm số lần thấy trong cửa sổ `T_win`, đủ `N` thì xác nhận, toạ độ cảnh báo là trung bình có trọng số conf của các lần thấy.

| Chiến lược | Ghép bằng | Lớp | Cần gì |
|---|---|---|---|
| `geo` | Khoảng cách mặt đất ≤ `r`, một-một | `GeoConfirmer` | lat/lon từ georef |
| `bytetrack` | IoU của box trên ảnh, Kalman, hai vòng | `TrackConfirmer(ByteTracker())` | Chỉ box |
| `bytetrack_cmc` | Như trên, sau khi dời track theo chuyển động camera | `TrackConfirmer(ByteTracker(), motion=…)` | Box + telemetry hai khung |

### 9.2. `bytetrack`: mốc so sánh

ByteTrack: mỗi track có bộ lọc Kalman (vận tốc không đổi) dự đoán vị trí box ở khung sau; ghép box mới với dự đoán bằng IoU và thuật toán Hungary; hai vòng ghép (box điểm cao trước, box điểm thấp sau để cứu track bị che). Dùng `ultralytics.trackers.byte_tracker.BYTETracker` như thư viện độc lập.

**Cài đặt** (`edge/detector.py`, lớp `ByteTracker`): bọc `BYTETracker` ở `detector.py` để ultralytics vẫn chỉ được import ở một file (quyết định #8); `confirm.py` dùng qua giao diện `Tracker` nên test được bằng tracker giả. Hai điểm đã chỉnh so với dùng thẳng:
- Đầu ra mặc định của `BYTETracker` bỏ **lần thấy đầu tiên** của track mới (track chưa "kích hoạt" cho tới khi được ghép ở khung sau). Giữ nguyên thì `bytetrack` cần `N + 1` khung trong khi `geo` cần `N`, so sánh sai. Bộ bọc trả mọi track được thấy ở khung hiện tại.
- Tham số giữ như `bytetrack.yaml` của ultralytics: chỉ phát hiện conf ≥ 0,25 mới **tạo** track; phát hiện 0,1–0,25 chỉ nối dài track có sẵn. `geo` thì nhận mọi phát hiện ≥ conf của detector (0,1). Đây là khác biệt do thiết kế của ByteTrack; khi chạy RQ3 cần quyết giữ nguyên (đúng bài báo gốc) hay hạ ngưỡng tạo track về bằng conf detector (cùng đầu vào với `geo`).

Vì sao gãy ở đây: giữa hai khung, box dịch khoảng 254 px (mục 2.5) trong khi box chỉ 25 px, nên IoU giữa dự đoán và box mới bằng 0. Kalman không cứu được vì chuyển động do **camera** gây ra, không phải do người; ở khung đầu tiên của track, Kalman chưa biết vận tốc.

**Đã kiểm chứng** bằng `tests/test_confirm.py::test_bytetrack_breaks_at_2fps_and_camera_motion_compensation_fixes_it` (ByteTrack thật, không cần mô hình): một người đứng yên, UAV bay 10 m/s ở 50 m, 2 FPS, camera 4K 74,3°, 6 khung. `bytetrack` không xác nhận được (mỗi khung một track mới); `bytetrack_cmc` và `geo` cùng xác nhận ở khung thứ 3. Đây là ví dụ dựng tay để minh hoạ cơ chế; số liệu RQ3 phải lấy từ chạy thật.

### 9.3. `bytetrack_cmc`: bù chuyển động camera

Trước khi ghép, dời mọi track của khung trước theo chuyển động camera. Với camera nadir, chuyển động mặt đất trên ảnh giữa hai khung là phép tịnh tiến cộng xoay (do thay đổi hướng) cộng co giãn (do thay đổi độ cao). Hai cách tính:
- **Từ telemetry [Đã có]** (`georef.frame_motion`): lấy 4 góc ảnh, `pixel → GPS` bằng telemetry khung trước, rồi `GPS → pixel` bằng telemetry khung này, khớp một phép affine 2×3. Chính xác nếu telemetry chính xác; không tốn tính toán. Ví dụ: bay 5 m về phía đỉnh ảnh ở 50 m với tiêu cự 1920 px, mặt đất dịch xuống đúng 192 px (có test).
- **Từ ảnh (nếu còn thời gian):** ước lượng phép biến đổi giữa hai khung bằng điểm đặc trưng (ORB + RANSAC) hoặc `cv2.findTransformECC`. Không cần telemetry, nhưng mặt nước ít đặc trưng và có phản chiếu nên dễ sai.

Sau khi bù, box của cùng một người ở hai khung gần trùng nhau và ByteTrack hoạt động bình thường.

Áp phép bù vào trạng thái Kalman: trạng thái của `BYTETracker` là `(x, y, a, h, vx, vy, va, vh)` với `a` là tỉ lệ khung. `multi_gmc` có sẵn trong ultralytics xoay cả cặp `(a, h)` như thể là toạ độ, sai với dạng trạng thái này (chính ultralytics ghi chú như vậy). `_warp_tracks` chỉ dời và xoay `(x, y)`, xoay `(vx, vy)`, để nguyên `(a, h)`. Co giãn do đổi độ cao giữa hai khung chỉ vài phần trăm nên bỏ qua với `h`.

Giới hạn: bù bằng telemetry kế thừa mọi sai số của telemetry (mục 8.4). Lệch hướng 2° ở mép ảnh 4K làm điểm lệch khoảng 1920 × tan 2° ≈ 67 px, lớn hơn box người 25 px, nên `bytetrack_cmc` nhạy với sai số hướng hơn `geo` (bán kính gom tính bằng mét). RQ3 đo đúng điều này qua biến nhiễu telemetry.

### 9.4. `geo`: gom theo vị trí mặt đất [Đã có]

Cài trong `edge/confirm.py` (`GeoConfirmer`). Khác thiết kế: bước 2 ghép tham lam theo khoảng cách tăng dần thay cho thuật toán Hungary, vì chưa có scipy.

Thuật toán trực tuyến:

```
Mỗi cụm: tâm (lat, lon), danh sách lần thấy (t, conf), trạng thái {đang theo dõi, đã cảnh báo}.

Với mỗi khung tại thời điểm t:
  1. Ma trận khoảng cách mặt đất giữa phát hiện mới và tâm các cụm còn sống.
  2. Ghép một-một bằng thuật toán Hungary, chỉ chấp nhận cặp có khoảng cách ≤ r.
     (Một-một để hai người đứng cạnh nhau trong cùng khung không bị nhập vào một cụm.)
  3. Phát hiện được ghép: thêm lần thấy, cập nhật tâm (trung bình có trọng số theo conf).
     Phát hiện không ghép: tạo cụm mới.
  4. Cụm có ≥ N lần thấy trong cửa sổ T_win giây và chưa cảnh báo: trả về Confirmation.
  5. Cụm không được thấy quá T_exp giây: xoá.
```

Tham số và cách chọn:

| Tham số | Ý nghĩa | Gợi ý ban đầu |
|---|---|---|
| `r` | Bán kính gom | 2–3 lần sai số định vị tương đối giữa hai khung; quét 1, 2, 3, 5, 8 m trong RQ3 |
| `N` | Số lần thấy để xác nhận | 1, 3, 5, 10 (RQ3); bị chặn bởi `K_max` ở mục 2.4 |
| `T_win` | Cửa sổ đếm | Bằng `T_dwell` ở độ cao đang bay |
| `T_exp` | Thời gian xoá cụm | Lớn hơn `T_dwell` một chút |

Rủi ro: hai người cách nhau dưới `r` (một gia đình trên mái nhà) bị gộp thành một cảnh báo. RQ3 đo cả **gộp nhầm** và **tách nhầm** theo `r`. Trong cứu hộ, gộp nhầm ít nguy hiểm hơn bỏ sót, vì đội cứu hộ tới nơi vẫn thấy cả nhóm, nhưng sẽ làm sai số đếm người; trạm mặt đất có thể hiển thị "có thể nhiều người" khi cụm có nhiều box gần nhau trong cùng khung.

### 9.5. Lựa chọn conf cho từng tầng

Vì xác nhận nhiều khung lọc được báo nhầm ngẫu nhiên, `detector` có thể dùng ngưỡng conf **thấp hơn** (ví dụ 0,1) để tăng recall mỗi khung. Đây là đánh đổi chính của RQ3: ngưỡng thấp + `N` lớn hay ngưỡng cao + `N` nhỏ. Công thức nhị thức ở mục 2.4 giúp dự đoán trước.

---

## 10. Cảnh báo (alerts)

**[Đã có]** trong `edge/alerts.py` (`Outbox`, `FakeTransport`, `HttpTransport`), kiểm thử trong `tests/test_alerts.py`. Cơ chế "lưu và gửi bù, toạ độ trước, ảnh sau" của đề cương. Ảnh cắt chỉ được gửi sau khi gói toạ độ cùng `alert_id` đã được ack; lượt gửi dừng ở lần thất bại đầu tiên. Chưa có giới hạn băng thông.

### 10.1. Mẫu outbox

Mọi thông điệp được ghi vào SQLite **trước khi** gửi. Mất điện hay mất mạng giữa chừng không làm mất cảnh báo.

```sql
CREATE TABLE outbox (
  msg_id      TEXT PRIMARY KEY,     -- "<alert_id>:coords" hoặc "<alert_id>:crop"
  alert_id    TEXT NOT NULL,
  kind        TEXT NOT NULL,        -- 'coords' | 'crop'
  priority    INTEGER NOT NULL,     -- coords = 0 (cao), crop = 1
  payload     BLOB NOT NULL,        -- JSON
  status      TEXT NOT NULL,        -- 'pending' | 'acked'
  attempts    INTEGER NOT NULL DEFAULT 0,
  next_try_t  REAL NOT NULL,        -- thời điểm được thử lại (đồng hồ mô phỏng)
  created_t   REAL NOT NULL,
  acked_t     REAL
);
```

Bật chế độ WAL của SQLite để ghi nhanh và an toàn khi có sự cố.

### 10.2. Vòng gửi

```
pump(now):
  lấy các dòng status='pending' và next_try_t ≤ now, sắp theo (priority, created_t)
  với mỗi dòng:
     gửi qua Transport
     thành công (nhận ack) → status='acked', acked_t=now
     thất bại → attempts += 1; next_try_t = now + min(cap, base · 2^attempts) · (1 + jitter)
```

- **Lùi theo hàm mũ có nhiễu** (exponential backoff with jitter): tránh dội liên tục khi mất sóng, và tránh nhiều drone cùng thử lại một lúc khi sóng có lại.
- **Toạ độ trước:** `priority` bảo đảm mọi gói toạ độ đang chờ được gửi trước bất kỳ ảnh cắt nào. Khi sóng yếu, trạm vẫn có vị trí người ngay.
- **Giới hạn băng thông:** có thể đặt ngân sách byte mỗi giây; ảnh cắt chỉ gửi khi còn ngân sách.

### 10.3. Bảo đảm giao nhận

Cơ chế trên cho bảo đảm **ít nhất một lần** (at-least-once): một thông điệp có thể đến trạm hai lần (ack bị mất trên đường về nên edge gửi lại). Trạm mặt đất biến nó thành **đúng một lần về mặt hiệu ứng** bằng cách bỏ qua `msg_id` đã có (khoá chính). Đây là cách chuẩn trong hệ thống phân tán khi không có mạng tin cậy.

### 10.4. Kích thước gói

| Thành phần | Ước tính |
|---|---|
| Gói toạ độ (JSON) | 300–500 byte |
| Ảnh cắt 256×256 JPEG chất lượng 80 | khoảng 10–25 KB; base64 làm tăng 4/3 |
| Luồng video 4K nén | hàng chục Mbps |

Con số thật đo trong RQ3. Ảnh cắt có thể gửi dạng nhị phân (multipart) thay vì base64 để bớt 25%.

### 10.5. Transport

```python
class Transport(Protocol):
    def send(self, msg: OutboxMessage, now: float) -> bool: ...   # True nếu nhận được ack
```

- `HttpTransport`: `POST` tới `ground/`; HTTP 200 kèm `msg_id` là ack. Đơn giản, dễ demo.
- MQTT (QoS 1) là lựa chọn tự nhiên cho IoT, nhưng thêm một broker cần chạy; chỉ làm nếu thầy yêu cầu.
- `FakeTransport` cho kiểm thử; `NetemTransport` (mục 11) bọc bên ngoài cả hai.

---

## 11. Giả lập (sim/)

### 11.1. `netem.py`: mạng chập chờn [Đã có một phần]

Đã có mất gói Bernoulli và khoảng mất sóng. Chưa có Gilbert–Elliott, độ trễ, băng thông.

`NetemTransport(inner, …)` bọc một Transport và quyết định mỗi lần gửi có thành công không, trễ bao lâu:

| Hiện tượng | Mô hình |
|---|---|
| Mất gói rải rác | Bernoulli với xác suất `p_loss` |
| Mất gói theo cụm | Mô hình Gilbert–Elliott: hai trạng thái Tốt/Xấu, xác suất chuyển trạng thái mỗi lần gửi; trạng thái Xấu có tỉ lệ mất cao. Thực tế hơn Bernoulli vì sóng yếu thường kéo dài |
| Mất sóng hoàn toàn | Danh sách khoảng thời gian `[(t_start, t_end), …]` mọi lần gửi đều thất bại |
| Độ trễ | Phân phối đều hoặc log-normal trong `[d_min, d_max]` |
| Băng thông | Thời gian gửi cộng thêm `kích thước / băng thông` |

Mọi ngẫu nhiên lấy từ một `random.Random(seed)` riêng, nên cùng seed thì cùng chuỗi sự kiện mạng.

### 11.2. Đồng hồ mô phỏng

Toàn bộ pipeline nhận thời gian từ khung hình (`t = frame_id / fps`), không gọi `time.time()`. Netem tính "lúc nào thông điệp tới nơi" theo đồng hồ này. Hệ quả:
- **Tái lập:** cùng video, cùng cấu hình, cùng seed thì cùng kết quả từng byte.
- **Nhanh hơn thời gian thực:** RQ3 quét lưới N × chiến lược × độ cao × vận tốc × kịch bản mạng. Nếu phát video theo thời gian thực sẽ mất hàng ngày; theo đồng hồ mô phỏng, chạy với `FakeDetector` đọc lại kết quả phát hiện đã lưu, chỉ mất vài phút.

Mẹo quan trọng: **tách phát hiện khỏi phần còn lại**. Chạy detector một lần cho mỗi video (tốn GPU), lưu `detections.jsonl`; mọi thí nghiệm RQ3 sau đó đọc lại file này thay vì chạy lại mô hình.

Thời gian xử lý thật (cho RQ2 và cho demo) đo riêng bằng `perf_counter`, ghi vào `timings.jsonl`. Khi demo trực tiếp, có chế độ "thời gian thực" chờ đúng nhịp khung.

### 11.3. `flight.py`, `scenario.py`: chuyến bay và kịch bản giả lập [Đã có một phần]

**[Đã có]** `sim/flight.py` (`StraightFlight`), `sim/scenario.py`, `sim/make_rq3.py`: bay thẳng; người đứng yên hoặc trôi; nhiễu GPS Gauss–Markov; phát hiện giả theo recall cố định và báo nhầm Poisson. **[Thiết kế]** đường zig-zag, nhiễu độ cao, nhiễu hướng, nghiêng camera, recall theo kích thước người.

**Luồng một kịch bản RQ3 hoàn toàn giả lập:**

```
sim/make_rq3.py ──► ground_truth.json   (người thật, ai ở khung nào: theo đường bay THẬT)
                ├─► telemetry.csv       (đường bay thật + nhiễu GPS: thứ UAV THẤY)
                ├─► detections.jsonl    (detector giả: recall, báo nhầm)
                └─► frames.mp4          (khung đen đúng kích thước camera, để pipeline chạy y nguyên)
edge/main.py --telemetry telemetry.csv --replay detections.jsonl --confirm ... ──► alerts.jsonl, alerts_sent.jsonl
eval/rq3_metrics.py --run ... --truth ground_truth.json ──► rq3_eval/rq3_metrics.json
```

Ba lớp tách riêng (sự thật, cảm biến, detector) vì mỗi lớp là một nguồn sai số riêng của RQ3. Pipeline không biết mình đang chạy trên dữ liệu giả: cùng mã `edge/` sẽ chạy trên video thật.

**Nhiễu GPS Gauss–Markov** (`GaussMarkovGps`): `e(t+dt) = e(t)·exp(−dt/τ) + σ·√(1 − exp(−2dt/τ))·N(0,1)` cho mỗi trục. Độ lệch chuẩn dài hạn là σ, nhưng giữa hai khung cách `dt` chỉ thay đổi khoảng `σ·√(1 − exp(−2dt/τ))`. Với σ = 3 m, τ = 30 s, dt = 0,5 s, thay đổi giữa hai khung khoảng 0,55 m.

- Đường bay thẳng hoặc zig-zag, tham số: điểm bắt đầu, độ cao, vận tốc, hướng, khoảng cách dải, tần số mẫu telemetry.
- Nhiễu: GPS Gauss–Markov (mục 8.4), nhiễu độ cao, nhiễu hướng, nghiêng camera cố định.
- Kịch bản người: danh sách toạ độ người (đứng yên hoặc trôi chậm theo dòng nước) và kích thước. Dùng hàm ngược `gps_to_pixel` để sinh nhãn theo thời gian: ở khung nào, pixel nào, ai đang trong tầm nhìn.

Hai cách dùng:
1. **Chỉ telemetry:** gắn telemetry giả lập vào video thật (video lũ, FinlandProper). Nhãn người lấy từ nhãn có sẵn.
2. **Hoàn toàn giả lập cho RQ3:** sinh chuỗi phát hiện giả theo recall và tỉ lệ báo nhầm đo được ở RQ1 (ví dụ mỗi người thật được phát hiện với xác suất `r(kích thước)`, cộng báo nhầm theo phân phối Poisson). Cho phép quét rất nhiều kịch bản và đối chiếu với công thức nhị thức. Phải ghi rõ là mô phỏng.

---

## 12. Trạm mặt đất

**[Đã có]** `ground/app.py` và `ground/map.html`: API mục 12.1 trừ `/api/stream` (trang bản đồ hỏi lại mỗi 2 giây), bảng `alerts` và `crops`. **[Thiết kế]** bảng `incidents`, gộp nhiều drone (12.3), xếp ưu tiên (12.4). Tối giản: FastAPI + SQLite + một trang Leaflet.

### 12.1. API

| Phương thức | Đường dẫn | Việc |
|---|---|---|
| `POST` | `/api/alerts` | Nhận gói toạ độ; trả `{"ack": msg_id}`; trùng `msg_id` vẫn trả ack nhưng không ghi lại |
| `POST` | `/api/alerts/{alert_id}/crop` | Nhận ảnh cắt |
| `GET` | `/api/alerts?since=…` | Danh sách cảnh báo (cho bản đồ) |
| `GET` | `/api/alerts/{alert_id}/crop` | Ảnh cắt |
| `GET` | `/api/stream` | Server-Sent Events: đẩy cảnh báo mới tới trình duyệt ngay khi tới |
| `GET` | `/` | Trang bản đồ |

### 12.2. Lưu trữ

```sql
alerts(alert_id PK, uav_id, time, lat, lon, position_error_m, confidence,
       frames_confirmed, model, received_at, incident_id)
crops(alert_id PK, jpeg BLOB, received_at)
incidents(incident_id PK, lat, lon, first_seen, last_seen, n_alerts, n_uavs, priority)
```

### 12.3. Gộp nhiều drone

Hai drone có thể cảnh báo cùng một người. Khi một cảnh báo mới tới: tìm `incident` có khoảng cách ≤ `r_merge` (gắn với tổng `position_error_m` của hai cảnh báo) và thời gian gần; có thì gắn vào, không thì tạo mới. Bản đồ hiển thị incident, không hiển thị từng cảnh báo.

### 12.4. Xếp ưu tiên (luật đơn giản, giải thích được)

Điểm ưu tiên là tổng có trọng số: người dưới nước (vị trí nằm trên mặt nước theo bản đồ hoặc theo thẻ của mô hình) cao hơn người trên mái nhà; nhóm đông (nhiều box gần nhau) cao hơn; độ tin cậy cao hơn; chờ lâu chưa được xử lý cao hơn. Trọng số ghi trong cấu hình và được giải thích trong luận văn. Phân biệt "dưới nước" và "trên mái" cần thêm thông tin; phương án đơn giản nhất là người vận hành gắn thẻ khi xem ảnh cắt.

### 12.5. Bản đồ

Leaflet hiển thị incident theo màu ưu tiên, bấm để xem ảnh cắt và lịch sử; bảng bên cạnh hiện FPS, băng thông, số cảnh báo đang chờ của mỗi drone. Ô bản đồ lấy từ OpenStreetMap cần internet; trong ngữ cảnh lũ mất mạng thì cần ô bản đồ ngoại tuyến (tải trước cho khu vực, phục vụ từ chính trạm). Đây là giới hạn cần ghi nếu không làm.

---

## 13. Huấn luyện

**[Đã có]** `training/train.py` và notebook Kaggle. **[Thiết kế]** `tools/make_tiles.py` (13.2).

### 13.1. Dữ liệu huấn luyện

Mọi bộ được chuyển về YOLO một lớp (như `tools/convert_visdrone.py`). Ultralytics nhận nhiều thư mục trong một `data.yaml`:

```yaml
path: /kaggle/input
train: [visdrone/images/train, finland/images/train, c2a/images/train]
val:   [visdrone/images/val, finland/images/val]
names: {0: person}
```

Chia theo video hoặc địa điểm (FinlandProper là khung trích từ video: các khung liền nhau gần như giống hệt, chia ngẫu nhiên sẽ làm rò rỉ val vào train và cho kết quả đẹp giả). Công cụ: `tools/split_by_video.py` và `tools/check_leakage.py` (mục 15.6).

### 13.2. Hai cách đưa người nhỏ vào mô hình khi huấn luyện

| Cách | Làm gì | Ưu, nhược |
|---|---|---|
| Ảnh lớn | Huấn luyện toàn ảnh ở imgsz 1280 | Đơn giản; tốn bộ nhớ GPU gấp 4 lần so với 640, batch nhỏ |
| Mảnh cắt | `tools/make_tiles.py` cắt ảnh gốc thành mảnh 640 có chồng lấn, giữ nguyên độ phân giải; huấn luyện ở 640 | Người giữ nguyên kích thước, batch lớn; phải dùng cắt ô khi suy luận cho khớp |

Quy tắc khi cắt mảnh: box bị cắt còn dưới 50% diện tích thì bỏ (hoặc đưa vào vùng bỏ qua); giữ một tỉ lệ mảnh không có người để mô hình học nền (sóng, rác, mái nhà).

### 13.3. Siêu tham số khởi đầu

```bash
yolo detect train model=yolo26s.pt data=data.yaml imgsz=1280 epochs=100 patience=20 \
     batch=8 seed=0 deterministic=True cos_lr=True close_mosaic=10 project=runs/train name=E2_s0
```

- `mosaic` (ghép 4 ảnh) mặc định bật, có lợi cho vật thể nhỏ; tắt ở 10 epoch cuối (`close_mosaic`) để mô hình quen với ảnh thật.
- Tăng cường dữ liệu nên thêm: xoay 90°/180° (nhìn từ trên xuống không có "chiều đứng"), lật dọc (`flipud=0.5`), thay đổi màu nhẹ (mặt nước đục, phản chiếu).
- E3 dùng `model=yolo26s-p2.yaml` khởi tạo từ trọng số `yolo26s.pt` (ultralytics chuyển phần khớp).

### 13.4. Thang kích thước khi huấn luyện và augmentation `scale`

**Vấn đề hay bị bỏ qua:** mô hình học tốt nhất ở những kích thước người nó đã thấy khi huấn luyện. Phân bố kích thước người **khi vào mô hình** lúc huấn luyện nên phủ phân bố lúc triển khai. Ý tưởng này là "scale match" trong bài TinyPerson (Yu và cộng sự, WACV 2020).

Ultralytics biến đổi kích thước hai lần:
1. `load_image`: đưa cạnh dài ảnh về `imgsz` (ảnh VisDrone 1360 px ở imgsz 1280 nhân 0,94).
2. `RandomPerspective`: nhân hệ số ngẫu nhiên `s` trong `[1 − scale, 1 + scale]`; mặc định `scale = 0.5`, tức `s` từ 0,5 đến 1,5.

Sau đó box có cạnh dưới 2 px bị **xoá nhãn** (`box_candidates`, `wh_thr = 2`) nhưng người vẫn còn trong ảnh, nên mô hình học rằng chỗ đó là nền. Đây là nhãn sai do augmentation sinh ra.

Đo bằng `tools/label_size_stats.py` trên nhãn VisDrone val (thay cho train, cùng bộ dữ liệu; `runs/stats/visdrone_val_*/size_stats.csv`):

| imgsz | Hệ số s | Mất nhãn (<2 px) | 2–4 px | 4–8 px | 8–16 px | 16–32 px | >32 px |
|---|---|---|---|---|---|---|---|
| 1280 | 0,5 | 3,2% | 23,7% | 44,4% | 25,0% | 3,5% | 0,2% |
| 1280 | 1,0 | 0,1% | 3,1% | 23,7% | 44,4% | 25,0% | 3,7% |
| 1280 | 1,5 | 0,0% | 0,2% | 7,1% | 39,9% | 37,6% | 15,1% |
| 640 | 0,5 | **26,9%** | 44,4% | 25,0% | 3,5% | 0,2% | 0,0% |
| 640 | 1,0 | 3,2% | 23,7% | 44,4% | 25,0% | 3,5% | 0,2% |

Lúc triển khai (cắt ô ở độ phân giải gốc, video 4K, camera 82° chéo, `runs/gsd/m4t_diag82/gsd_table.csv`): người 42,2 px ở 30 m xuống 12,7 px ở 100 m; đầu người (thân đã ngập) 16,9 px xuống 5,1 px.

Kết luận:
- **E2 ở imgsz 1280 giữ `scale = 0.5`**: khoảng s từ 0,5 tới 1,5 phủ được từ đầu người 5 px tới người 42 px; mất nhãn chỉ đáng kể ở đầu dưới của khoảng s.
- **Không huấn luyện ở imgsz 640 với `scale` mặc định**: tới 26,9% nhãn bị xoá ở s = 0,5. Nếu cần 640 (để batch lớn) thì dùng mảnh cắt (13.2), không thu cả ảnh.
- `train.py` có `--scale` để giá trị này được ghi vào `run_config.json`; muốn thử giá trị khác thì tạo file cấu hình mới, không sửa E2_s0.

### 13.5. Kaggle

- GPU T4 16 GB; hạn mức theo tuần (khoảng 30 giờ, cần kiểm tra), mỗi phiên tối đa khoảng 12 giờ.
- Lưu checkpoint vào `/kaggle/working` và dùng `resume=True` khi phiên bị ngắt.
- Notebook chỉ clone kho mã ở một commit cố định, cài gói, gọi `training/train.py`. Mọi logic nằm trong mã có phiên bản.
- Kết quả (trọng số, `results.csv`, `run_config.json`) lưu thành Kaggle Dataset có phiên bản, rồi tải về `runs/train/`.

### 13.6. E6: recall theo số pixel trên người

`tools/rescale_dataset.py`: thu nhỏ ảnh và nhãn theo các tỉ lệ 1, 1/1,5, 1/2,1, 1/3, 1/4 bằng `cv2.INTER_AREA` (nội suy theo diện tích, mô phỏng đúng việc cảm biến có ít điểm ảnh hơn, tránh răng cưa). Tuỳ chọn mô phỏng camera thật ở mỗi mức: làm mờ Gauss nhẹ, nén JPEG ở chất lượng tương đương video. Chạy cùng mô hình, vẽ recall theo kích thước người tính bằng pixel. Giới hạn: không tái tạo được nhiễu cảm biến và đặc tính ống kính.

---

## 14. Jetson và RQ2

**[Thiết kế]**

### 14.1. TensorRT

TensorRT biên dịch mô hình thành "engine" tối ưu cho đúng GPU đó: gộp lớp, chọn kernel nhanh nhất, giảm độ chính xác số.

```bash
yolo export model=best.pt format=engine half=True imgsz=640 batch=32 device=0          # FP16, lô 32 ô
yolo export model=best.pt format=engine int8=True data=calib.yaml imgsz=640 device=0   # INT8
```

Những điều phải biết:
- **Engine không mang sang máy khác được.** Engine xây trên T4 của Kaggle không chạy trên Jetson; phải xuất lại ngay trên Jetson (hoặc cùng phiên bản TensorRT và cùng kiến trúc GPU).
- Kích thước ảnh và batch được cố định lúc xuất. Chế độ cắt ô cần engine có batch bằng số ô (32 cho 4K, ô 640, chồng 0,2), hoặc engine batch động.
- **INT8** cần dữ liệu hiệu chỉnh (vài trăm ảnh đại diện, lấy từ tập train, không lấy từ tập test) để đo dải giá trị kích hoạt. INT8 thường làm hại vật thể nhỏ nhiều nhất (tín hiệu yếu bị lượng tử hoá thô), nên phải đo lại recall theo nhóm kích thước sau khi lượng tử hoá.
- `end2end` của YOLO26 giúp engine trả thẳng kết quả cuối, không cần NMS chạy ngoài.

### 14.2. Đo đúng cách trên Jetson

- **Chế độ công suất:** `sudo nvpmodel -m <mode>` chọn mức (7 W, 15 W, 25 W tuỳ phiên bản JetPack); `sudo jetson_clocks` khoá xung nhịp tối đa để số đo ổn định. Ghi rõ chế độ trong mỗi bảng.
- **Làm nóng và thời lượng:** bỏ vài chục lần đầu; đo ít nhất 60 giây liên tục để thấy hiện tượng giảm xung do nóng (thermal throttling).
- **Báo cáo phân vị:** p50 và p95 độ trễ, không chỉ trung bình; hệ thống thời gian thực bị giới hạn bởi trường hợp chậm.
- **Điện năng:** `tegrastats` in công suất các đường nguồn (dòng tổng thường tên `VDD_IN`). Năng lượng mỗi khung = công suất trung bình × thời gian mỗi khung.
- **Đo từng chặng:** đọc khung, cắt ô, suy luận, gộp, georef, confirm, ghi outbox. Thường suy luận chiếm phần lớn, nhưng với cắt ô, bước cắt và gộp trên CPU yếu của Jetson có thể đáng kể.

### 14.3. Đường cong recall theo FPS

Mỗi cấu hình (mô hình × imgsz hoặc cắt ô × FP16/INT8 × chế độ công suất) là một điểm (FPS, recall nhóm dưới 16 px). Vẽ tất cả, đánh dấu đường ngưỡng 2 FPS, và tô **biên Pareto** (những cấu hình không bị cấu hình nào khác vượt cả về FPS lẫn recall). Khuyến nghị cấu hình theo độ cao bay lấy từ biên này.

### 14.4. Khi không có Jetson

Đo trên T4 bằng TensorRT, báo cáo **thứ hạng tương đối** giữa các cấu hình (cấu hình nào nhanh hơn bao nhiêu lần), không quy đổi thẳng ra FPS trên Jetson. Có thể tham khảo số liệu công bố (ví dụ bài đo YOLO trên Orin Nano Super mà đề cương đã dẫn) để ước lượng bậc độ lớn, ghi rõ là ước lượng.

---

## 15. Phương pháp thí nghiệm

### 15.1. Ba tập đánh giá

| Tập | Vai trò | Lưu ý |
|---|---|---|
| VisDrone val | Mốc so sánh với các nghiên cứu khác | Đô thị, không có nước; ảnh độ phân giải thấp |
| FinlandProper test | Người dưới nước, độ phân giải 1920×1024 | Chia theo video |
| Tập test lũ | **Tập chính** cho kết luận về cảnh lũ | Khoá bằng mã băm trước khi chạy E3; không dùng để chọn tham số |

Mọi lựa chọn (ngưỡng conf, epoch, siêu tham số) làm trên val. Tập test lũ chỉ chạy một lần cho mỗi cấu hình cuối cùng.

### 15.2. Lặp và seed

Huấn luyện có ngẫu nhiên (khởi tạo, thứ tự dữ liệu, tăng cường). Mỗi cấu hình huấn luyện chạy ít nhất 3 seed, báo trung bình ± độ lệch chuẩn. Chênh lệch giữa hai cấu hình nhỏ hơn độ lệch chuẩn thì không kết luận được cấu hình nào tốt hơn.

### 15.3. Khoảng tin cậy bootstrap

Tập test lũ nhỏ (200–300 ảnh), nên một con số recall có độ bất định lớn. Bootstrap theo **ảnh**: lấy mẫu có hoàn lại 300 ảnh từ 300 ảnh, tính lại recall, lặp 1.000 lần, lấy phân vị 2,5% và 97,5% làm khoảng tin cậy 95%. Lấy mẫu theo ảnh chứ không theo box, vì các box trong cùng ảnh không độc lập (cùng điều kiện ánh sáng, độ cao). **[Đã có]** trong `eval/metrics.py` (`bootstrap_ci`), cột `_lo`, `_hi` của `eval_by_size.csv`.

**So sánh hai cấu hình: bootstrap cặp.** **[Đã có]** `eval/metrics.py` (`paired_bootstrap`) và `eval/compare_runs.py`.

Sai lầm hay gặp: thấy hai khoảng tin cậy riêng chồng nhau rồi kết luận "không khác nhau". Hai khoảng riêng mang cả độ bất định **chung** của tập ảnh: ảnh khó thì khó cho cả hai cấu hình, nên AP của hai cấu hình lên xuống cùng nhau giữa các mẫu bootstrap. Phần dao động chung này không liên quan tới câu hỏi "cấu hình nào tốt hơn".

Bootstrap cặp loại phần chung đó:

```
lặp 1000 lần:
    rút có hoàn lại n ảnh từ n ảnh        (cùng một bộ cho cả A và B)
    hiệu = chỉ_số(B trên bộ đó) − chỉ_số(A trên bộ đó)
khoảng tin cậy 95% của hiệu = phân vị 2,5% và 97,5% của 1000 hiệu
p (hai phía) = 2 × tỉ lệ hiệu trái dấu với hiệu quan sát
```

Khoảng tin cậy của hiệu không chứa 0 thì chênh lệch có ý nghĩa ở mức 5%. Ví dụ thật trên VisDrone val (E4 SAHI và bộ cắt ô riêng): hai khoảng tin cậy AP50 riêng là 0,443–0,477 và 0,437–0,469, chồng nhau gần hết; nhưng khoảng tin cậy của hiệu là −0,011 đến −0,003, tức bộ cắt ô riêng kém hơn một chút và ổn định ([results/visdrone_tiled_vs_sahi.md](results/visdrone_tiled_vs_sahi.md)).

Ba lưu ý:
- "Có ý nghĩa thống kê" khác "đáng kể trong thực tế": hiệu 0,008 AP có ý nghĩa thống kê trên 548 ảnh nhưng có thể không đáng để đổi lấy tốc độ. Luận văn nên báo cả hiệu số lẫn khoảng tin cậy, không chỉ báo "có ý nghĩa".
- So nhiều cặp cùng lúc (5 nhóm kích thước × 2 chỉ số × nhiều cấu hình) thì vài cặp sẽ "có ý nghĩa" do ngẫu nhiên. Kết luận chính nên dựa trên nhóm "tất cả" và nhóm người nhỏ đã định trước, không chọn sau khi thấy kết quả.
- Bootstrap cặp xử lý độ bất định do **chọn ảnh**; độ bất định do **seed huấn luyện** (mục 15.2) là nguồn khác và phải báo riêng.

**Ảnh không độc lập: cluster bootstrap.** **[Đã có]** tuỳ chọn `--cluster-pattern` của `eval_by_size.py` và `compare_runs.py`.

Bootstrap theo ảnh giả định các ảnh độc lập. Nhưng VisDrone val có 548 ảnh mà chỉ từ **76 video** (`runs/leakage/visdrone_val`); ảnh cùng video cùng cảnh, cùng ánh sáng, cùng độ cao, nên lỗi của mô hình trên chúng đi cùng nhau. Coi 548 ảnh là 548 mẫu độc lập làm khoảng tin cậy **hẹp giả**. Cluster bootstrap rút có hoàn lại theo **video**: video được rút k lần thì mọi ảnh của nó vào mẫu k lần.

Ví dụ thật, AP50 của E4 (SAHI) trên VisDrone val: theo ảnh 0,443–0,477 (rộng 0,034), theo video 0,428–0,489 (rộng 0,061), rộng gần gấp đôi (`runs/visdrone/E4/eval_iou0.5`, `runs/visdrone/eval_iou0.5_cluster`). Hiệu số trong bootstrap cặp thì gần như không đổi (−0,011 đến −0,003 theo video, `runs/visdrone/compare_E4_E4tiled_iou0.5_cluster`), vì phần tương quan theo video triệt tiêu khi lấy hiệu.

Tập test lũ lấy tối đa 30 khung mỗi video (docs/LABELING.md), nên cùng vấn đề. **Mặc định hiện vẫn là theo ảnh** để các bảng cũ còn so sánh được; chuyển sang theo video cho tập test lũ là thay đổi quy ước đo, cần chốt trước khi chạy bảng chính.

### 15.4. Định nghĩa chỉ số RQ3

**[Đã có]** `eval/rq3_metrics.py` (hàm thuần `compute_metrics`, có ví dụ tính tay trong `tests/test_rq3.py`). Kết quả ghi vào `<run>/rq3_eval/`, không ghi đè `run_config.json` của pipeline.

Cho một video với nhãn theo thời gian (mỗi người thật có khoảng thời gian xuất hiện `[t_in, t_out]` và toạ độ):

| Chỉ số | Định nghĩa |
|---|---|
| Báo động giả mỗi phút | Số cảnh báo không ứng với người thật nào (khoảng cách tới người thật gần nhất > `r_eval`) / thời lượng video (phút) |
| Thời gian tới cảnh báo | Với mỗi người được cảnh báo: thời điểm cảnh báo đầu tiên − `t_in` |
| Tỉ lệ bỏ sót hoàn toàn | Số người thật không có cảnh báo nào trong `[t_in, t_out + Δ]` / tổng số người |
| Gộp nhầm | Số cảnh báo ứng với từ hai người thật trở lên |
| Tách nhầm | Số người thật nhận từ hai cảnh báo trở lên |
| Độ trễ giao | Thời điểm trạm nhận gói toạ độ − thời điểm tạo cảnh báo |
| Tỉ lệ mất | Cảnh báo không bao giờ tới trạm (khi kết thúc mô phỏng) / tổng cảnh báo |
| KB mỗi cảnh báo | Tổng byte gửi (gồm cả gửi lại) / số cảnh báo |

Cách ghép cảnh báo với người thật: tại thời điểm cảnh báo, tính khoảng cách mặt đất tới vị trí lúc đó của mọi người thật (người trôi thì lấy vị trí đã trôi); cảnh báo thuộc về người gần nhất trong `r_eval`.

Giới hạn của định nghĩa, cần ghi trong luận văn:
- **Hai người đứng gần nhau hơn `r_eval`** thì mọi cảnh báo về họ đều bị tính là gộp nhầm, kể cả khi hệ thống cảnh báo đúng từng người. Chọn `r_eval` nhỏ hơn khoảng cách thường gặp giữa các nhóm người, và báo kết quả ở vài giá trị `r_eval`.
- **Sai số vị trí có một phần cố định**: `georef.locate` lấy tâm đáy box (chân người đứng), còn mô phỏng đặt người ở tâm box, nên dù không nhiễu vẫn lệch nửa bề ngang người (0,25 m). Với người nhìn từ trên xuống, phần lệch này nhỏ so với sai số GPS.

**Chạy thử (không phải kết quả RQ3)**: một kịch bản 60 s, 10 người, recall 0,7, 0,5 báo nhầm mỗi khung, seed 0, quét σ GPS (`runs/rq3/smoke_gps*`, `runs/rq3/sweep_gps*`). `geo` bắt đủ 10/10 người ở mọi σ đã thử (0 đến 3 m); `bytetrack` không bắt được ai; `bytetrack_cmc` bắt đủ tới σ = 0,25 m, bỏ sót 20% ở 0,5 m, 90% ở 1 m, 100% ở 3 m. Đúng với lập luận ở mục 9.3: bù chuyển động bằng telemetry cần GPS dao động giữa hai khung nhỏ hơn bề ngang người (cỡ GPS RTK). Báo nhầm ngẫu nhiên không thành cảnh báo nào nhờ yêu cầu 3 lần thấy. Kết luận chính thức phải chạy đủ lưới tham số ở ROADMAP mục 4, nhiều seed.

### 15.5. Nhãn theo thời gian cho RQ3

Hai nguồn:
1. Chuỗi khung của FinlandProper, nếu nhãn được gán liên tục và có định danh người qua các khung (cần kiểm tra khi tải về).
2. Mô phỏng (mục 11.3): người đặt tại toạ độ cố định, nhãn suy ra bằng `gps_to_pixel`. **[Đã có]** `sim/make_rq3.py`.

Nếu tự gán nhãn vài đoạn video lũ cho RQ3, gán ở 2 FPS và gán thêm định danh người (cùng một người giữ cùng một số qua các khung); CVAT hỗ trợ chế độ gán nhãn theo track.

---

### 15.6. Rò rỉ dữ liệu giữa các tập [Đã có]

Rò rỉ là khi tập đánh giá chứa ảnh giống ảnh huấn luyện; kết quả đẹp giả mà không ai thấy. Ba dạng hay gặp trong đề tài này:

| Dạng | Ví dụ | Cách chặn |
|---|---|---|
| Khung liền nhau bị chia vào hai tập | FinlandProper chia ngẫu nhiên theo khung | `tools/split_by_video.py`: gom ảnh theo mã video (regex trên tên file), gán **cả video** vào một tập; cùng seed thì cùng kết quả |
| Cùng cảnh, khác tên | Một video lũ tải về hai lần từ hai nguồn, hoặc cắt lại | `tools/check_leakage.py`: so dHash mọi cặp ảnh đánh giá–huấn luyện |
| Chọn tham số trên tập test | Chỉnh ngưỡng conf cho tới khi recall trên test đẹp | Quy trình: mọi lựa chọn làm trên val (15.1) |

**dHash** (difference hash): thu ảnh xám về 9×8 điểm, so từng điểm với điểm bên phải, được 64 bit. Hai ảnh gần giống nhau (khác kích thước, nén, độ sáng) có hash khác nhau vài bit; hai cảnh khác nhau khác khoảng 32 bit. Ngưỡng mặc định 5 bit. dHash không bắt được ảnh bị cắt mạnh hay xoay; đủ cho trường hợp tải lại cùng một video.

Chạy `check_leakage.py` với một tập (không có `--train`) thì tìm ảnh gần trùng **bên trong** tập đó: trên VisDrone val tìm được 4 cặp liên quan 7 ảnh (`runs/leakage/visdrone_val/near_duplicates.csv`), không đáng kể. Với tập test lũ, phải chạy trước khi khoá (cùng với `train` của mọi bộ đã dùng để huấn luyện), và lưu kết quả cạnh `MANIFEST.sha256`.

## 16. Tái lập và đóng gói

### 16.1. Quy ước

- Mỗi lần chạy ghi `run_config.json` (mục 6.2). Bảng trong luận văn ghi rõ file cấu hình và commit git sinh ra nó.
- Dữ liệu thô trong `data/raw/` không bao giờ bị sửa; mọi thứ trong `data/processed/` sinh ra bằng script trong `tools/`.
- Tập test lũ có `MANIFEST.sha256`; script đánh giá kiểm tra mã băm trước khi chạy.
- `docs/results/` chứa bảng và biểu đồ đã chốt (đưa lên git); `runs/` chứa đầu ra thô (không đưa lên git).

### 16.2. Kiểm thử

`pytest` chạy trong vài giây, không cần mô hình hay GPU:
- **Đã có:** AP bằng ví dụ tính tay; nhóm kích thước; vùng bỏ qua; lỗi biên làm tròn.
- **Sẽ thêm:** georef đi và về; nội suy góc hướng; confirm với chuỗi phát hiện định sẵn (hai người gần nhau, một người biến mất rồi xuất hiện lại); outbox khi mất mạng rồi có lại (không mất, không trùng); netem với seed cố định cho cùng chuỗi sự kiện; schema JSON của gói cảnh báo.

GitHub Actions chạy `pytest` mỗi lần push.

### 16.3. Docker

| Ảnh | Nội dung | Trạng thái |
|---|---|---|
| `docker/dev.Dockerfile` | Python 3.13 slim, torch CPU, `.[dev]` | Đã có |
| `docker/ground.Dockerfile` | Python slim + `.[ground]`, không torch | Đã có (dịch vụ `ground` trong `compose.yaml`) |
| `docker/edge.Dockerfile` | torch CPU + `.[edge]`, phát lại video | Thiết kế |
| `docker/edge-jetson.Dockerfile` | Dựa trên ảnh Ultralytics cho JetPack | Thiết kế, cần thiết bị để thử |

`compose.yaml` cho demo: một dịch vụ `ground` và 2–3 dịch vụ `edge`, mỗi dịch vụ phát lại một video với telemetry riêng, cùng gửi về `ground`. Một lệnh `docker compose up` dựng toàn bộ kịch bản nhiều drone. Cài torch bản CPU từ `download.pytorch.org` để ảnh không kéo bản CUDA nặng vài GB. Container trên macOS không dùng được GPU Apple Silicon, nên ảnh `edge` chỉ dùng để demo luồng hệ thống, không dùng để đo tốc độ.

---

## 17. Giới hạn

| Giới hạn | Ảnh hưởng | Cách xử lý trong luận văn |
|---|---|---|
| Không bay thật; telemetry giả lập | Sai số định vị và RQ3 dựa trên mô hình | Phân tích độ nhạy theo nhiễu (mục 8.4); ghi rõ |
| Giả định nadir và mặt nước phẳng | Sai lệch khi camera nghiêng hoặc gió làm rung | Định lượng sai số theo góc nghiêng |
| Thông số camera lấy từ tài liệu | Bảng GSD có thể lệch 5–10% | Tính từ metadata thật khi có |
| VisDrone không có nước | Không kết luận được về cảnh lũ | Chỉ dùng làm mốc |
| Tập test lũ nhỏ, ảnh từ nguồn công khai | Độ bất định lớn; không phân phối lại được ảnh | Bootstrap; chỉ công bố nhãn và nguồn |
| E6 bằng thu nhỏ ảnh | Không tái tạo nhiễu cảm biến | Gọi là mô phỏng |
| Không có Jetson (nếu không mua) | RQ2 chỉ là thứ hạng tương đối | Phương án B của đề cương |
| Bản đồ cần internet | Không đúng ngữ cảnh mất mạng | Ô bản đồ ngoại tuyến hoặc ghi giới hạn |

---

## 18. Thuật ngữ

| Thuật ngữ | Nghĩa |
|---|---|
| AGL | Above Ground Level: độ cao so với mặt đất (hoặc mặt nước) ngay bên dưới |
| AP, AP50, AP50:95 | Average Precision: diện tích dưới đường precision-recall; ở IoU 0,5; trung bình ở IoU 0,5–0,95 |
| Backbone, neck, head | Ba phần của mạng phát hiện: trích đặc trưng, trộn đặc trưng nhiều tầng, dự đoán |
| Bootstrap | Lấy mẫu lại có hoàn lại để ước lượng độ bất định của một chỉ số |
| CMC | Camera Motion Compensation: bù chuyển động camera |
| conf | Điểm tin cậy của một box |
| DFOV, HFOV, VFOV | Góc nhìn chéo, ngang, dọc |
| Edge | Thiết bị biên: máy tính đặt tại nơi thu dữ liệu (trên UAV) thay vì máy chủ xa |
| End-to-end (YOLO26) | Mô hình xuất kết quả cuối, không cần NMS |
| FP16, INT8 | Số thực 16 bit, số nguyên 8 bit: giảm độ chính xác số để chạy nhanh hơn |
| GSD | Ground Sampling Distance: số mét mặt đất ứng với 1 pixel |
| IoU, IoA, IOS | Giao trên hợp; giao trên diện tích của một box; giao trên diện tích box nhỏ hơn |
| Letterbox | Thu ảnh giữ tỉ lệ rồi đệm viền cho vừa kích thước đầu vào |
| NMS | Non-Maximum Suppression: xoá các box trùng, giữ box điểm cao nhất |
| Outbox | Bảng lưu thông điệp trước khi gửi, để không mất khi mất mạng |
| P2, P3, … | Tầng đặc trưng có stride 4, 8, …: số càng nhỏ, độ phân giải càng cao |
| Pareto | Tập các phương án không bị phương án nào khác vượt trên mọi tiêu chí |
| Recall, precision | Tỉ lệ người thật được phát hiện; tỉ lệ phát hiện là người thật |
| SAHI | Slicing Aided Hyper Inference: suy luận theo ô ảnh |
| Stride | Hệ số giảm độ phân giải của một tầng so với ảnh đầu vào |
| TensorRT | Bộ biên dịch và chạy mô hình tối ưu cho GPU NVIDIA |
| Telemetry | Dữ liệu trạng thái chuyến bay: vị trí, độ cao, hướng, thời gian |
