# FloodEye: tổng quan dự án từ đầu đến cuối

Tài liệu này giải thích **toàn bộ dự án theo trình tự các bước**: mỗi bước làm gì, vì sao cần, có cách nào khác và vì sao không chọn, đang ở trạng thái nào. Mục đích là nắm được cả dự án và trình bày lại được cho cô và hội đồng.

Tài liệu không thay cho ba tài liệu kia:

| Tài liệu | Dùng khi |
|---|---|
| **TONG_QUAN.md** (tài liệu này) | Cần hiểu dự án tổng thể, lập luận cho từng lựa chọn, chuẩn bị trả lời câu hỏi |
| [TECHNICAL.md](TECHNICAL.md) | Cần công thức, thuật toán, chi tiết cài đặt. Các chỗ "(T 9.3)" bên dưới là mục 9.3 của TECHNICAL |
| [THUAT_TOAN.md](THUAT_TOAN.md) | Cần hiểu kỹ thuật toán trên UAV: từng bước, ví dụ tính tay, nguồn tham khảo |
| [ROADMAP.md](ROADMAP.md) | Cần lịch theo tuần, các quyết định còn treo |
| [README.md](../README.md) | Cần lệnh cài đặt và chạy |

Mọi con số trong tài liệu này đọc được từ một file trong `runs/` hoặc `docs/results/`; nguồn ghi ngay cạnh số. Trạng thái tính tới ngày **28/10/2026**.

---

## 1. Bài toán

### 1.1. Bối cảnh

Khi lũ lớn, người mắc kẹt trên mái nhà, bám vào vật nổi hoặc lội trong nước. UAV quét nhanh được vùng rộng, nhưng người vận hành không thể nhìn kịp hàng giờ video 4K. Đồ án xây dựng hệ thống **tự động phát hiện người trong video UAV, xác định toạ độ GPS và gửi cảnh báo về trạm mặt đất**, chạy ngay trên máy tính nhúng gắn trên UAV.

### 1.2. Vì sao khó: ba ràng buộc

| Ràng buộc | Con số | Hệ quả cho thiết kế |
|---|---|---|
| **Người rất nhỏ trong ảnh** | Camera 82° chéo, video 4K: người rộng 0,5 m chỉ chiếm 25,3 px ở 50 m và 12,7 px ở 100 m; khi thân đã ngập, đầu người chỉ 5,1–16,9 px (`runs/gsd/m4t_diag82/gsd_table.csv`) | Không được thu ảnh 4K về 640 px như cách dùng YOLO thông thường: ở 100 m người chỉ còn 2,1 px. Phải giữ độ phân giải (ảnh lớn hoặc cắt ô) |
| **Thiết bị biên yếu** | Máy nhúng công suất dưới 25 W | Chỉ xử lý được vài khung mỗi giây; cần chứng minh vài khung mỗi giây là đủ (mục 3.1) |
| **Mạng chập chờn** | Vùng lũ thường mất sóng di động | Không gửi video về được; chỉ gửi gói cảnh báo nhỏ, phải lưu lại và gửi bù khi có sóng |

### 1.3. Ba câu hỏi nghiên cứu và các câu hỏi con

> Ba câu hỏi chính theo đề cương đã nộp; khi trình bày, dùng đúng câu chữ trong đề cương. Các câu hỏi con và luận điểm xuyên suốt là **đề xuất ngày 6/11, chờ cô đồng ý** (quyết định #16 của ROADMAP): đề cương không đổi, chỉ làm rõ mỗi câu được trả lời bằng phép đo nào. Giao diện `python -m console` (tab Hiểu dự án, mục Câu hỏi) đọc thẳng các bảng dưới đây; sửa bảng là giao diện đổi theo. Cột "Trạng thái" bắt đầu bằng "Có", "Có công cụ" hoặc "Chờ".

#### RQ1. Nhìn thấy người nhỏ trong cảnh lũ không? (độ chính xác)

Phát hiện người nhỏ trong ảnh UAV vùng lũ chính xác tới mức nào, và những kỹ thuật nào (độ phân giải đầu vào, cắt ô, tinh chỉnh, nhánh phát hiện P2, thu nhỏ theo độ cao bay) giúp được bao nhiêu, đặc biệt với người dưới 16 px?

| Mã | Câu hỏi con | Trả lời bằng | Khâu | Trạng thái | Nguồn |
|---|---|---|---|---|---|
| RQ1a | Người nhỏ tới đâu thì bị bỏ sót? | Recall theo nhóm kích thước; khảo sát recall theo số pixel trên người (E6) | Phát hiện người | Có trên VisDrone và SeaDronesSee (E6 thử); tập lũ chờ khoá | `visdrone_E2.md`, `e6_sds_pilot.md` |
| RQ1b | Dữ liệu huấn luyện nào giúp: ảnh drone đô thị, người dưới nước, ảnh thảm hoạ ghép người? | So E2, E2c, E2e trên cùng các tập | Phát hiện người | Có (E2, E2c, E2e: thêm C2A kém ở người nhỏ, không hơn có ý nghĩa ở người to) | `visdrone_E2.md`, `E2c.md`, `E2e.md` |
| RQ1c | Cắt ô và nhánh phát hiện P2 giúp người nhỏ bao nhiêu? | Có và không cắt ô (E4); có và không nhánh P2 (E3) | Phát hiện người | Có | `visdrone_baseline.md`, `visdrone_tiled_vs_sahi.md`, `E3.md` |
| RQ1d | Thu nhỏ theo độ cao bay giúp bao nhiêu? | Cắt ô có và không thu nhỏ trên SeaDronesSee 4K (có độ cao thật) | Phát hiện người | Có, sơ bộ (một seed, một tập) | `scale_by_altitude.md` |
| RQ1e | Nhiễu riêng của cảnh lũ (loá, vật trôi, nhoè, thời tiết) làm mô hình kém đi bao nhiêu? | Recall theo thẻ ảnh trên tập lũ | Phát hiện người | Chờ tập lũ | `LABELING.md` |
| RQ1f | Mô hình học trên ảnh đô thị khô và biển dùng được cho cảnh lũ tới đâu? | So kết quả cùng mô hình trên VisDrone, SeaDronesSee và tập lũ | Dữ liệu và cách đánh giá | Chờ tập lũ | `sds_det.md`, `flood_truoc_khoa.md` |

#### RQ2. Máy nhỏ trên drone chạy kịp không? (tốc độ trên thiết bị biên)

Cấu hình nào đạt tần số xử lý cần thiết (khoảng 2 khung mỗi giây) mà giữ được recall cao nhất?

| Mã | Câu hỏi con | Trả lời bằng | Khâu | Trạng thái | Nguồn |
|---|---|---|---|---|---|
| RQ2a | Nén mô hình (FP16, INT8) nhanh thêm bao nhiêu và mất bao nhiêu độ chính xác, nhất là với người nhỏ? | Đo trên Kaggle T4 (TensorRT) | Chạy trên thiết bị biên | Chờ kết quả (đang chạy trên Kaggle 7/11) | `TECHNICAL.md` |
| RQ2b | Cấu hình nào tốt nhất, tức không cấu hình nào khác vừa nhanh hơn vừa chính xác hơn? | Bảng recall theo FPS của RQ2 | Chạy trên thiết bị biên | Chờ kết quả (đang chạy trên Kaggle 7/11) | `TECHNICAL.md` |
| RQ2c | Thiết bị yếu (Orin Nano) theo kịp tần số cần thiết không; thu nhỏ theo độ cao giúp bao nhiêu? | Giả lập thời gian thiết bị, hiệu chỉnh từ số đo T4 (ước lượng) | Chạy trên thiết bị biên | Có công cụ, chờ hiệu chỉnh từ RQ2 | `TECHNICAL.md`, `DEMO_BAO_VE.md` |

#### RQ3. Hệ thống báo đúng về trạm không? (hệ thống)

Khi ghép phát hiện qua nhiều khung để xác nhận rồi gửi cảnh báo qua mạng chập chờn, hệ thống báo nhầm bao nhiêu, bỏ sót bao nhiêu, cảnh báo tới trạm sau bao lâu; cách xác nhận nào chịu được sai số GPS và chuyển động của camera?

| Mã | Câu hỏi con | Trả lời bằng | Khâu | Trạng thái | Nguồn |
|---|---|---|---|---|---|
| RQ3a | Bao nhiêu khung mỗi giây là đủ, và thay đổi theo độ cao, vận tốc ra sao? | Mô phỏng tần số theo độ cao | Camera và lấy khung | Có, mô phỏng | `rq3_adaptive.md`, `rq3_altitude.md`, `rq3_altprofile.md` |
| RQ3b | Gom theo toạ độ mặt đất hay theo dõi trên ảnh (ByteTrack) tốt hơn khi xử lý ít khung? | Video thật SeaDronesSee có telemetry | Xác nhận | Có, sơ bộ (ba đoạn video) | `sds_mot_confirm.md`, `rq3_cmc_cause.md` |
| RQ3c | Sai số GPS và độ cao làm vị trí cảnh báo lệch bao nhiêu? | Mô hình lan truyền sai số, mô phỏng | Định vị | Có, mô phỏng | `rq3_geoerr.md`, `rq3_yawcalib.md`, `rq3_gpsacc.md` |
| RQ3d | Mất sóng làm cảnh báo tới trễ bao lâu, có mất cảnh báo nào không? | Giả lập mạng (mất gói rải rác và theo cụm, mất sóng) | Gửi cảnh báo | Có, mô phỏng | `rq3_network.md`, `rq3_burst.md` |
| RQ3e | Gộp cảnh báo thành sự cố bớt được bao nhiêu cảnh báo lặp? | Gộp theo bán kính ở trạm mặt đất | Trạm mặt đất và bản đồ | Có | `alert_memory.md`, `rq3_group.md` |

#### Luận điểm xuyên suốt

**Dữ liệu bay sẵn có của drone (độ cao, GPS, hướng) giúp ở cả ba khâu**: chọn cỡ ảnh khi phát hiện (RQ1d), giảm khối lượng tính để máy yếu theo kịp (RQ2c), và xác nhận người khi chỉ xử lý vài khung mỗi giây (RQ3b). Đây không phải câu hỏi thứ tư mà là sợi chỉ nối ba câu hỏi; mỗi phần của luận điểm được trả lời bằng câu hỏi con ghi trong ngoặc.

### 1.4. Đóng góp dự kiến

*(Đề xuất 6/11, quyết định #16, chờ cô; bản bốn đóng góp trước đó xem lịch sử git của file này.)*

1. **Tập đánh giá ảnh lũ từ UAV và cách đánh giá theo cỡ người**: 188 khung tự gán nhãn từ 9 nguồn (`flood_truoc_khoa.md`), kết quả chia theo nhóm kích thước (dưới 8, 8–16, 16–32, trên 32 px), khoảng tin cậy lấy mẫu theo video. Chưa có bộ công khai nào chụp người trong lũ từ UAV có nhãn sẵn; tập nhỏ là giới hạn phải ghi rõ.
2. **Thu nhỏ theo độ cao bay** (**7/11: đã có công trình trước** làm đúng ý này, Messmer và cộng sự ICPR 2022, Ahmed và Pizarro OCEANS 2025 trên chính SeaDronesSee; xem `luan_van/tai_lieu_tham_khao.md`, quyết định #19): dùng độ cao ước lượng người sẽ to bao nhiêu pixel rồi thu nhỏ khung trước khi phát hiện, vừa đưa người về cỡ mô hình làm tốt (RQ1d), vừa giảm số ô cần chạy trên máy yếu (RQ2c). Đánh giá trên SeaDronesSee và mô phỏng; không đánh giá được trên tập lũ vì video lũ không có độ cao bay (quyết định #13).
3. **Xác nhận theo toạ độ mặt đất khi xử lý ít khung** (7/11: ghép theo toạ độ thế giới đã có cho theo dõi xe từ drone, MIDDTD 2025; viết hẹp, quyết định #19): chỉ ra vì sao theo dõi thông dụng (ByteTrack) gãy khi UAV xử lý ít khung mỗi giây, và cách gom theo toạ độ mặt đất khắc phục (RQ3b, mục 3.9).

**Hiện thực hoá** (sản phẩm kỹ thuật, không tính là đóng góp khoa học): hệ thống hoàn chỉnh từ video tới cảnh báo trên bản đồ, mã nguồn mở có kiểm thử; giả lập thời gian thiết bị biên; demo bảo vệ chạy không cần GPU và Internet.

---

## 2. Bức tranh tổng thể

```
                    ┌──────────────────────── TRÊN UAV (edge/) ────────────────────────┐
 video 4K, 30 FPS   │                                                                    │
 ─────────────────► │ lấy mẫu ─► phát hiện ─► định vị ─► xác nhận ─► hàng đợi cảnh báo  │
                    │  2 FPS     YOLO26,      pixel→GPS   ≥ N khung   lưu SQLite,        │
 telemetry (GPS,    │            cắt ô                                gửi lại khi lỗi   │
 độ cao, hướng) ──► │                 ▲ telemetry                                │       │
                    └────────────────────────────────────────────────────────────┼───────┘
                                                                     mạng 4G/5G  │ gói toạ độ trước, ảnh cắt sau
                    ┌──────────────────── TRẠM MẶT ĐẤT (ground/) ─────────────────▼───────┐
                    │ nhận, bỏ trùng theo mã cảnh báo, lưu, hiện trên bản đồ               │
                    └──────────────────────────────────────────────────────────────────────┘
```

Đồ án có **hai nửa**, ứng với các câu hỏi nghiên cứu:

| Nửa | Câu hỏi | Bản chất công việc | Dữ liệu cần |
|---|---|---|---|
| **A. Mô hình phát hiện** | RQ1, RQ2 | Thí nghiệm học máy: chọn cấu hình, fine-tune, đo AP và recall, đo tốc độ | Ảnh có nhãn người: VisDrone, AFO, SeaDronesSee, tập test lũ tự gán |
| **B. Hệ thống** | RQ3 | Kỹ thuật hệ thống: định vị, xác nhận, gửi cảnh báo, chịu lỗi | Chuỗi khung theo thời gian kèm telemetry; dùng **mô phỏng** vì không có video lũ thật kèm nhãn theo thời gian |

Hai nửa nối với nhau qua **recall mỗi khung**: RQ1 đo recall của detector; RQ3 dùng recall đó để tính xác suất một người được thấy đủ N khung (T 2.4).

---

## 3. Các bước, theo trình tự

Mỗi bước có cùng bố cục: **Làm gì**, **Vì sao**, **Cách khác** (và vì sao không chọn), **Trạng thái**, **Ở đâu**.

### 3.1. Bước 1: Tính hình học camera

**Làm gì.** Từ góc nhìn camera, độ phân giải và độ cao bay, tính: mỗi pixel ứng với bao nhiêu cm trên mặt đất (GSD), người rộng bao nhiêu pixel, một điểm nằm trong khung bao lâu, giữa hai khung xử lý mặt đất dịch bao nhiêu pixel.

**Vì sao.** Mọi lựa chọn sau đều dựa vào các con số này:
- Người 13–42 px (30–100 m) quyết định phải giữ độ phân giải, không thu về 640.
- Ở 50 m, bay 10 m/s, một điểm nằm trong khung khoảng 4,3 s; xử lý 2 khung mỗi giây là thấy mỗi người tối đa 8 lần (T 2.4). **Đây là lập luận "2 FPS là đủ"**: không cần xử lý 30 khung mỗi giây, nên thiết bị yếu vẫn làm được.
- Giữa hai khung, mặt đất dịch khoảng 254 px trong khi người chỉ 25 px (T 2.5). Con số này giải thích vì sao tracking thông dụng gãy (bước 9).

**Cách khác.** Dùng số "82°" làm góc ngang như đề cương ban đầu. Không chọn vì DJI ghi góc **chéo**; góc ngang thực khoảng 74°, người lớn hơn khoảng 15% so với tính theo 82° ngang (ROADMAP 5.1). Kết luận của đề cương không đổi, chỉ số liệu chính xác hơn.

**Trạng thái.** Xong. **Ở đâu:** `scripts/gsd_calc.py`, kết quả `runs/gsd/m4t_diag82/`.

### 3.2. Bước 2: Chọn mô hình nền

**Làm gì.** Dùng YOLO26s (bản small) của ultralytics, khởi tạo từ trọng số huấn luyện trên COCO.

**Vì sao.**
- Họ YOLO là chuẩn thực tế cho phát hiện thời gian thực, có sẵn công cụ xuất sang TensorRT cho GPU nhúng.
- YOLO26 có thêm đầu ra một-một không cần NMS ("end-to-end"), có thể giảm độ trễ trên thiết bị biên. Đề tài dùng mặc định của Ultralytics 8.4.174 (đầu một-nhiều kèm NMS) cho mọi kết quả; đầu một-một chưa đo.
- Bản `s` cân bằng giữa độ chính xác và tốc độ cho thiết bị dưới 25 W.

**Cách khác.**
| Phương án | Vì sao không chọn làm mô hình chính |
|---|---|
| Mô hình hai giai đoạn (Faster R-CNN) | Chính xác với vật nhỏ nhưng chậm hơn nhiều; không hợp thiết bị biên |
| Transformer (DETR, RT-DETR) | Cần nhiều dữ liệu và tính toán hơn; công cụ xuất sang thiết bị biên kém sẵn có hơn YOLO. Nếu hội đồng hỏi, có thể nêu như hướng mở rộng |
| YOLO11s | Dự kiến làm **đối chứng** (E5), để biết kết quả có phụ thuộc vào đời YOLO không; **cắt 7/11** vì trễ lịch, ghi vào giới hạn |
| Bản lớn hơn (`m`, `l`) | Chậm hơn; nếu RQ2 cho thấy dư tốc độ thì có thể xem lại |

**Trạng thái.** Đã chốt. **Ở đâu:** `yolo26s.pt` (không đưa lên git).

### 3.3. Bước 3: Dữ liệu huấn luyện công khai

**Làm gì.** Chuyển các bộ dữ liệu công khai về **một lớp duy nhất là "person"** theo định dạng YOLO, kiểm tra lại nhãn sau khi chuyển.

| Bộ | Nội dung | Dùng để | Trạng thái |
|---|---|---|---|
| **VisDrone2019-DET** | Ảnh UAV đô thị Trung Quốc; val 548 ảnh, 13.969 người; train 6.471 ảnh, 106.396 người (`runs/data/visdrone_check.json`) | Huấn luyện (train), kiểm định (val), mốc so sánh với nghiên cứu khác | Đã chuyển, đã kiểm tra từng ảnh khớp nhãn gốc |
| **C2A** | 10.215 ảnh thảm hoạ thật (lũ, cháy, nhà sập, tai nạn) có **ghép thêm hình người** (`data/processed/c2a/stats.json`) | Huấn luyện | Đã chuyển; chưa dùng trong lần huấn luyện nào (`E2b_s0.yaml` có cấu hình, chưa chạy) |
| **AFO** | Ảnh drone người và vật trôi trên mặt nước (biển) | Huấn luyện (E2c), đánh giá (test, và test bỏ ảnh chung địa điểm với train) | Đã dùng |
| **SeaDronesSee-MOT** | Video drone 4K người bơi trên biển, nhãn theo track, metadata GPS, độ cao | Đánh giá độc lập người dưới nước (`sds_det.md`); kiểm chứng khối xác nhận trên video thật (`sds_mot_confirm.md`) | Đã dùng |
| **HydroVigilance** | Người bơi nhô đầu trên sông nước đục | Huấn luyện (E2d) | Đã chuyển; E2d không chạy (bỏ 7/11) |
| **FinlandProper** | Người dưới nước, 1920×1024 | Huấn luyện và đánh giá | Tạm bỏ (162 GB, máy chủ không cho tải từng phần) |

**Vì sao gộp về một lớp.** Đề tài chỉ quan tâm "có người hay không". VisDrone tách `pedestrian` (đứng, đi) và `people` (ngồi, nằm); cả hai đều là người cần cứu nên gộp lại. Người đi xe đạp, xe máy bị VisDrone gán vào lớp phương tiện nên bị bỏ (ghi rõ trong luận văn).

**Vì sao cần kiểm tra nhãn sau chuyển.** Mỗi lần huấn luyện tốn khoảng 8 giờ GPU trong hạn mức hằng tuần; phát hiện lỗi nhãn sau khi huấn luyện là mất cả lần đó (T 6.7).

**Vì sao chọn lớp theo tên chứ không theo mã số.** Mỗi bộ đánh số lớp khác nhau (AFO có 9 lớp, trang mô tả không ghi mã số lớp "human"). Đoán sai mã thì mô hình học nhầm lớp mà không có lỗi nào báo (`tools/convert_yolo_subset.py`).

**Cách khác.** Tự gán nhãn toàn bộ dữ liệu huấn luyện: không khả thi với một người trong 2 tháng; công sức gán nhãn dành cho tập test (bước 4), vì đó là nơi quyết định giá trị kết luận.

**Lưu ý về C2A.** Người trong C2A là hình ghép, nên C2A chỉ dùng để **huấn luyện**, không dùng để kết luận về cảnh lũ. Ảnh C2A nhỏ (cạnh dài khoảng 430 px), khi huấn luyện ở 1280 bị phóng to khoảng 3 lần; đo được rằng điều này làm người C2A "to" hơn người VisDrone, hai bộ bù nhau và cùng phủ khoảng 13–42 px của video lũ 4K (`runs/stats/`, T 13.4).

**Ở đâu:** `tools/convert_visdrone.py`, `tools/check_visdrone.py`, `tools/convert_yolo_subset.py`; dữ liệu ở `data/raw/` (gốc) và `data/processed/` (đã chuyển).

### 3.4. Bước 4: Tập test lũ tự gán nhãn

**Làm gì.** Gom video UAV quay cảnh lũ có người, trích 200–300 khung, gán nhãn người bằng CVAT theo một hướng dẫn cố định, rồi **khoá** tập (11/11, lùi từ 4/11) bằng mã băm: sau khi khoá không sửa nhãn, không thêm bớt khung.

**Vì sao.** Đây là **tập quan trọng nhất**: là nơi duy nhất trả lời câu hỏi "trong cảnh lũ thật, mô hình làm được gì". VisDrone là đô thị khô; C2A là ảnh ghép. Khoá tập trước khi chạy thí nghiệm để không ai (kể cả người làm) vô tình chỉnh tập test cho kết quả đẹp.

**Các bước con và lý do:**

| Bước con | Lý do |
|---|---|
| Ghi nguồn từng video vào `sources.csv` | Minh bạch, xử lý bản quyền: luận văn chỉ công bố nhãn và nguồn, không phát hành lại ảnh |
| Trích khung bằng `tools/extract_frames.py`: cách nhau ít nhất 2 s, bỏ khung gần trùng (dHash), tối đa 30 khung mỗi video | Khung liền nhau gần như giống hệt: không thêm thông tin mà làm khoảng tin cậy hẹp giả. Giới hạn 30 khung để không một video nào chi phối kết quả |
| Giữ 10–20% khung không có người | Để đo báo nhầm (sóng, rác trôi, phản chiếu) |
| Gán nhãn theo `docs/LABELING.md`: box sát phần nhìn thấy; vùng `ignore` cho chỗ không chắc; thuộc tính "ngập một phần", "bị che"; thẻ ảnh "lóa", "thời tiết", "nhòe", "vật trôi" | Tập nhỏ nên mỗi nhãn sai kéo lệch kết quả; thuộc tính và thẻ để phân tích recall theo loại nhiễu |
| Gán lại 20 khung sau một tuần, so với lần đầu | Đo độ nhất quán của chính người gán |
| Chuyển nhãn bằng `tools/convert_cvat.py` | Báo lỗi nếu gặp nhãn lạ, thay vì bỏ qua lặng lẽ |
| Kiểm tra rò rỉ bằng `tools/check_leakage.py` với mọi tập huấn luyện | Nền ảnh C2A lấy từ ảnh thảm hoạ trên Internet; nếu trùng video với tập test thì tập test bị "lộ đề" |

**Cách khác.**
| Phương án | Vì sao không chọn |
|---|---|
| Chỉ dùng bộ có sẵn (AFO, SeaDronesSee) làm tập test | Đó là người bơi ngoài biển, không phải cảnh lũ (mái nhà, nước đục, rác); vẫn dùng làm tập đánh giá phụ cho người dưới nước |
| Tự bay UAV quay | Không có thiết bị, không có lũ đúng lúc |

**Trạng thái.** **Chưa bắt đầu gán. Đây là rủi ro lớn nhất của đồ án** (ROADMAP 1.1). Đã trích và lọc tay 212 khung từ 10 video, đóng gói sẵn 10 task CVAT; 4/11 gộp hai video cùng nguồn San Angelo, còn 188 khung; công cụ chuyển nhãn và chấm (`scripts/eval_flood.sh`) đã sẵn sàng. 4 trong 10 video dưới 1080p (hai video 480p, hai video 720p), trái với LABELING mục 1: cần quyết giữ hay tải lại **trước khi** gán các video đó. Phương án dự phòng nếu không kịp: khoá với tối thiểu 150 khung, hoặc lùi khoá tối đa tới 11/11 (quyết định #10, hỏi cô).

**Ở đâu:** `docs/LABELING.md`, `tools/extract_frames.py` (logic ở `eval/frames.py`), `tools/convert_cvat.py`, `tools/check_leakage.py`; dữ liệu ở `data/raw/flood/`, `data/processed/flood/`.

### 3.5. Bước 5: Cách đo độ chính xác

**Làm gì.** Viết công cụ đánh giá riêng thay vì dùng con số mAP mà ultralytics in ra:
- AP và recall **theo nhóm kích thước** người (dưới 8, 8–16, 16–32, trên 32 px, tính theo cạnh ngắn của nhãn).
- Ngưỡng IoU 0,5 cho mọi nhóm, **thêm IoU 0,3 cho nhóm dưới 8 px**.
- Dự đoán rơi vào vùng bỏ qua không bị tính là sai.
- Recall và precision "vận hành" ở conf 0,25, cạnh AP tính ở conf 0,001.
- **Khoảng tin cậy 95% bằng bootstrap** theo ảnh; so sánh hai cấu hình bằng **bootstrap cặp**; tuỳ chọn lấy mẫu theo **video**.

**Vì sao từng điểm:**
| Điểm | Lý do |
|---|---|
| Theo nhóm kích thước | Một con số mAP chung bị người lớn (dễ) chi phối; đề tài quan tâm người nhỏ |
| IoU 0,3 cho người dưới 8 px | Lệch 1–2 px ở người 6 px đã làm IoU tụt dưới 0,5 dù phát hiện đúng chỗ; với cứu hộ, đúng chỗ là đủ |
| Recall ở conf 0,25 | AP gộp mọi ngưỡng; lúc chạy thật phải chọn một ngưỡng. Hai số trả lời hai câu hỏi khác nhau |
| Bootstrap theo ảnh | Tập test nhỏ (200–300 ảnh) nên con số có độ bất định lớn; phải báo khoảng tin cậy. Lấy mẫu theo ảnh chứ không theo box vì các người trong cùng ảnh không độc lập |
| Bootstrap cặp | Hai khoảng tin cậy riêng chồng nhau **không** có nghĩa hai cấu hình như nhau. Ví dụ thật: bộ cắt ô tự viết và SAHI có khoảng tin cậy AP50 riêng gần trùng nhau (0,437–0,470 và 0,444–0,477), nhưng bootstrap cặp cho thấy bộ tự viết kém hơn 0,006, có ý nghĩa thống kê (`docs/results/visdrone_tiled_vs_sahi.md`) |
| Lấy mẫu theo video | 548 ảnh VisDrone val chỉ đến từ 76 video; ảnh cùng video không độc lập. Lấy mẫu theo video, khoảng tin cậy AP50 của E4 rộng gần gấp đôi (0,428–0,489 so với 0,444–0,477; T 15.3). Mặc định vẫn theo ảnh để bảng cũ còn so sánh được; dùng cho tập lũ hay không là quyết định #7 |

**Cách khác.** Dùng `yolo val` của ultralytics: không chia theo kích thước, không có vùng bỏ qua, không có khoảng tin cậy. Vẫn dùng để **đối chiếu**: trên E1 hai cách tính lệch dưới 1% (`docs/results/visdrone_baseline.md`).

**Trạng thái.** Xong, có kiểm thử bằng ví dụ tính tay. **Ở đâu:** `eval/metrics.py`, `eval/eval_by_size.py`, `eval/compare_runs.py`.

### 3.6. Bước 6: Mốc so sánh chưa huấn luyện (E0, E1, E4)

**Làm gì.** Chạy mô hình gốc (chưa fine-tune) trên VisDrone val theo ba cách: thu ảnh về 640 (E0), về 1280 (E1), cắt ô 640 bằng SAHI (E4).

**Vì sao.** Biết điểm xuất phát, và kiểm chứng lập luận ở bước 1 rằng độ phân giải quan trọng.

**Kết quả** (VisDrone val, IoU 0,5, `docs/results/visdrone_baseline.md`):

| Cấu hình | AP50 tất cả | AP50 người < 8 px | AP50 người 8–16 px |
|---|---|---|---|
| E0: ảnh về 640 | 0,277 | 0,050 | 0,255 |
| E1: ảnh về 1280 | **0,497** | **0,167** | **0,507** |
| E4: cắt ô 640 (SAHI) | 0,460 | 0,149 | 0,470 |

Đọc bảng:
- **Tăng độ phân giải gần gấp đôi AP** và gấp ba ở người dưới 8 px: xác nhận lập luận bước 1.
- Cắt ô **không** hơn 1280 trên VisDrone, vì ảnh VisDrone chỉ rộng khoảng 1360 px: ở 1280 đã gần như giữ nguyên độ phân giải. Với video 4K thì khác (1280 phải thu nhỏ 3 lần), nên **E4 phải đo lại trên dữ liệu độ phân giải cao**. Đã đo trên SeaDronesSee 4K với E2c: cắt ô ở độ phân giải gốc lại kém toàn ảnh vì người ở đó to; thu nhỏ theo độ cao rồi cắt ô thì tốt nhất (bước 8, `scale_by_altitude.md`).

**Trạng thái.** Xong.

### 3.7. Bước 7: Bộ cắt ô tự viết

**Làm gì.** Cắt ảnh lớn thành các ô 640 chồng nhau 20%, đưa **cả lô ô vào mô hình trong một lần gọi**, dời box về toạ độ ảnh gốc, gộp các box trùng ở vùng chồng nhau.

**Vì sao không dùng thẳng SAHI.** SAHI chạy mô hình **từng ô một**; trên GPU và TensorRT, chạy theo lô nhanh hơn nhiều. SAHI cũng gắn với cách nạp mô hình riêng, khó dùng với file `.engine` của TensorRT (RQ2).

**Kết quả đối chiếu** (`docs/results/visdrone_tiled_vs_sahi.md`): AP50 0,454 so với 0,460 của SAHI; kém hơn 0,006 có ý nghĩa thống kê, chủ yếu ở người lớn; ở người dưới 8 px thì **tốt hơn**. Với đề tài người nhỏ, mức đánh đổi này chấp nhận được.

**Cách khác đã thử và bỏ.** Hợp nhất toạ độ các box trùng (như SAHI) thay vì chỉ giữ box điểm cao nhất: AP50 tụt dưới 0,05, vì ở ngưỡng conf thấp, box lớn điểm thấp phủ cả nhóm người kéo box của từng người thành box cả nhóm. Lý do được ghi lại trong mã để không ai thử lại.

**Trạng thái.** Xong. **Ở đâu:** `edge/detector.py`, `scripts/run_tiled.py`.

### 3.8. Bước 8: Fine-tune và các thí nghiệm RQ1 (E2–E6)

**Làm gì.**
| Mã | Thí nghiệm | Câu hỏi nó trả lời | Trạng thái |
|---|---|---|---|
| E2 lượt 1 | Fine-tune YOLO26s ở 1280 trên VisDrone, 60 epoch | Fine-tune trên ảnh UAV giúp bao nhiêu so với mô hình COCO? | **Xong 22/10**: nhóm dưới 8 px trên VisDrone val 0,167 → 0,554, nhưng kém mô hình gốc với người dưới nước (`visdrone_E2.md`, `afo_E1_E2.md`) |
| E2c | Như trên, thêm AFO (người dưới nước) | Thêm ảnh người dưới nước có giữ được cảnh nước không? | **Xong 23/10**: AFO test 0,103 → 0,568, VisDrone val chỉ giảm 0,011; **mô hình chính** (`E2c.md`). E2d (+ HydroVigilance) đã có cấu hình |
| E3 | E2c + nhánh phát hiện P2 (thêm tầng phát hiện ở bước nhảy 4 thay vì 8) | Người 8 px chiếm 2×2 ô đặc trưng thay vì 1 ô: có tăng recall người rất nhỏ không, đáng với chi phí tính toán không? | **Xong 28/10, kết quả âm**: dưới 8 px chỉ +0,012 (val) và +0,013 (test-dev) AP50, mất ở IoU 0,3; kém hơn ở người to; 115,0 so với 93,9 GFLOPs. Giữ E2c (`E3.md`) |
| E4 | E2c + cắt ô, trên dữ liệu độ phân giải cao | Cắt ô có lợi khi ảnh thật sự lớn không? | Trên SDS 4K: cắt ô ở độ phân giải gốc **kém** toàn ảnh (0,235 so với 0,468) vì E2c yếu với người to; **thu nhỏ theo độ cao** rồi cắt ô cho 0,531 (`scale_by_altitude.md`). Trên tập lũ: có cấu hình `E4tiled_flood.yaml` (cắt ô không thu nhỏ, vì không có độ cao bay), chờ nhãn |
| E5 | E2c nhưng dùng YOLO11s | Kết quả có phụ thuộc đời mô hình không? | **Cắt 7/11** (thứ tự cắt khi trễ) |
| E6 | Thu nhỏ ảnh theo nhiều mức, vẽ recall theo số pixel trên người | Bay cao tối đa bao nhiêu thì còn phát hiện được? Nối thẳng vào khuyến nghị độ cao bay | **Chạy thử trên SDS** (`e6_sds_pilot.md`): E2c mạnh ở người 6–23 px, tụt với người trên 45 px; dưới 4 px không mô hình nào thấy. Bản chính thức chờ cô duyệt (quyết định #1) |

Cấu hình cuối chạy **3 seed** (khởi tạo ngẫu nhiên khác nhau), báo trung bình ± độ lệch chuẩn: chênh lệch nhỏ hơn độ lệch chuẩn giữa các seed thì không kết luận được.

**Vì sao huấn luyện trên Kaggle.** Không có GPU riêng; Kaggle cho GPU T4 miễn phí, hạn mức khoảng 30 giờ mỗi tuần (cần kiểm tra trên tài khoản). Notebook chỉ là lớp vỏ: lấy mã ở một commit cố định, cài gói, gọi `training/train.py`; mọi logic nằm trong mã có phiên bản, nên kết quả tái lập được.

**Một chi tiết kỹ thuật đã kiểm tra: augmentation `scale`.** Khi huấn luyện, ultralytics phóng to và thu nhỏ ảnh ngẫu nhiên từ 0,5 tới 1,5 lần, rồi **xoá nhãn** của box nhỏ hơn 2 px, trong khi người vẫn còn trong ảnh, nên mô hình học rằng đó là nền. Đo được: ở 1280 hiện tượng này không đáng kể; ở 640 tới 26,9% nhãn bị xoá khi thu nhỏ 0,5 lần (`runs/stats/visdrone_val_640`). Vì vậy giữ 1280 và giữ `scale` mặc định (T 13.4).

**Cách khác.**
| Phương án | Vì sao không chọn |
|---|---|
| Huấn luyện ở 640 cho nhanh | Mất người nhỏ (trên) |
| Huấn luyện trên ô cắt 640 từ ảnh gốc | Hợp lý, giữ độ phân giải với batch lớn; để dành nếu 1280 không đủ bộ nhớ (T 13.2) |
| So E2 với E1 trên VisDrone val | Thiên vị E2 vì `best.pt` được chọn theo chính tập val; bảng chính thức nên dùng VisDrone test-dev (quyết định #11) |

**Ở đâu:** `training/train.py`, `notebooks/kaggle_train.ipynb`, `configs/experiments/E*.yaml`, kết quả ở `runs/train/` và `runs/visdrone/`.

### 3.9. Bước 9: Pipeline trên UAV

**Làm gì.** Năm khối nối tiếp, mỗi khối là một file trong `edge/`:

| Khối | Làm gì | Lựa chọn thiết kế chính |
|---|---|---|
| Lấy mẫu (`sampler.py`) | Đọc video, lấy 2 khung mỗi giây | Thời gian lấy từ **chỉ số khung**, không từ đồng hồ máy, để chạy lại cho cùng kết quả |
| Phát hiện (`detector.py`) | YOLO toàn ảnh hoặc cắt ô; tuỳ chọn thu nhỏ khung theo độ cao trước khi cắt | Bước 7. Đây là file duy nhất dùng thư viện ultralytics; các khối khác test được mà không cần mô hình |
| Định vị (`georef.py`) | Pixel → toạ độ GPS, từ vị trí, độ cao, hướng của UAV | Giả định camera nhìn thẳng xuống; có cả **hàm ngược** GPS → pixel để kiểm thử (đi một vòng phải về đúng điểm cũ) và để mô phỏng |
| Xác nhận (`confirm.py`) | Chỉ cảnh báo khi một người được thấy ở ít nhất N khung; mỗi người chỉ một cảnh báo | Ba chiến lược (dưới) |
| Cảnh báo (`alerts.py`) | Gói toạ độ (vài trăm byte) gửi trước, ảnh cắt gửi sau | Lưu SQLite **trước khi** gửi; lỗi thì gửi lại, chờ lâu dần (1, 2, 4… giây); trạm bỏ trùng theo mã cảnh báo |

**Vì sao cần xác nhận nhiều khung.** Ở một khung, mô hình có thể báo nhầm sóng, rác là người. Báo nhầm ngẫu nhiên hiếm khi lặp lại ở cùng một chỗ N lần; người thật thì có. Đổi lại, detector được phép dùng ngưỡng conf thấp hơn để tăng recall.

**Ba chiến lược xác nhận (trọng tâm RQ3):**
| Chiến lược | Ghép phát hiện giữa các khung bằng | Điểm yếu |
|---|---|---|
| `bytetrack` | Độ trùng box trên ảnh (IoU) và bộ lọc Kalman: cách tracking thông dụng | **Gãy**: mặt đất dịch 254 px giữa hai khung, box người 25 px, IoU bằng 0 |
| `bytetrack_cmc` | Như trên, nhưng trước khi ghép, dời box khung trước theo chuyển động camera tính từ telemetry | Nhạy với sai số GPS |
| `geo` | Khoảng cách **trên mặt đất** sau khi định vị (gom trong bán kính r mét) | Hai người đứng gần hơn r có thể bị gộp |

Ba chiến lược dùng chung bước "đếm N lần thấy", chỉ khác cách ghép, để so sánh công bằng.

**Vì sao gửi gói toạ độ trước, lưu SQLite trước khi gửi.** Khi mất sóng, thông tin quan trọng nhất là **vị trí**; ảnh cắt có thể tới sau. Lưu trước khi gửi để mất điện hay mất mạng giữa chừng không mất cảnh báo. Gửi lại có thể tạo bản trùng, nên trạm bỏ qua mã cảnh báo đã có (cách chuẩn trong hệ thống phân tán khi mạng không tin cậy).

**Cách khác.**
| Phương án | Vì sao không chọn |
|---|---|
| Gửi cả video về trạm, xử lý ở mặt đất | Hàng chục Mbps; vùng lũ không có băng thông đó |
| MQTT thay HTTP | Thêm một máy chủ trung gian phải chạy; HTTP đủ cho demo, cơ chế lưu và gửi lại đã nằm trong outbox |
| Tính chuyển động camera từ ảnh (so khớp điểm đặc trưng) thay vì telemetry | Mặt nước ít đặc trưng, có phản chiếu, dễ sai; để dành nếu còn thời gian |

**Trạng thái.** Xong cả ba chiến lược, có kiểm thử. **Ở đâu:** `edge/`, chạy bằng `python -m edge.main`; cấu hình `configs/edge.yaml`.

### 3.10. Bước 10: Trạm mặt đất

**Làm gì.** Một máy chủ nhỏ nhận cảnh báo, lưu, hiện lên bản đồ (FastAPI + SQLite + Leaflet).

**Vì sao làm tối giản.** Đây là phần minh hoạ cho hệ thống, không phải câu hỏi nghiên cứu. Trạm không dùng thư viện học máy nào, nên cài được trên máy yếu (ảnh Docker 241 MB, không có torch).

**Phần mở rộng (đã làm 2/11).** Gộp cảnh báo từ nhiều drone theo sai số vị trí của cả hai bên, và xếp ưu tiên bằng luật cộng điểm có lý do: thẻ "dưới nước" do người vận hành gắn khi xem ảnh cắt, độ tin cậy, số drone cùng thấy, số người gần nhau, thời gian chờ (T 12.3, 12.4). Trọng số là lựa chọn thiết kế, không học từ dữ liệu vì không có dữ liệu cứu hộ thật.

**Trạng thái.** Xong bản tối giản; có `scripts/demo.sh` chạy cả hai phía bằng một lệnh. Đã thêm **gộp cảnh báo thành sự cố**: cảnh báo mới gắn vào sự cố gần nhất trong 5 m và 300 s, bản đồ hiện sự cố thay cho từng cảnh báo. Lý do là geo lặp cảnh báo khi GPS trôi; chặn lặp ngay trên UAV (`--suppress-s`) làm mất người ở cảnh đông nên tắt, còn gộp ở trạm thì không bỏ cảnh báo nào (`alert_memory.md`). **Ở đâu:** `ground/`.

### 3.11. Bước 11: RQ3 bằng mô phỏng

**Làm gì.** Sinh kịch bản giả lập: UAV bay thẳng, người đứng yên hoặc trôi trên mặt nước, GPS có nhiễu, detector giả lập với recall và tỉ lệ báo nhầm cho trước. Cho kịch bản chạy qua **đúng pipeline thật** (bước 9), rồi chấm: báo nhầm mỗi phút, tỉ lệ bỏ sót, gộp nhầm, tách nhầm, thời gian tới cảnh báo, sai số vị trí, độ trễ giao, tỉ lệ mất cảnh báo. Quét lưới tham số × nhiều seed.

**Vì sao mô phỏng.** RQ3 cần biết **người thật ở đâu, vào lúc nào** để chấm hệ thống; video lũ thật không có nhãn theo thời gian kèm telemetry. Mô phỏng cho phép:
- biết chính xác sự thật để chấm;
- tách riêng từng nguồn sai số (GPS, hướng, nghiêng camera, mạng) và quét hàng trăm kịch bản trong vài phút;
- dùng recall đo ở RQ1 làm đầu vào, nối RQ1 với RQ3.

Giới hạn phải nói rõ: đây là mô phỏng, không phải bay thật.

**Nhiễu GPS mô phỏng thế nào.** GPS thật lệch **chậm**: sai số giữa hai giây gần như giống nhau, không nhảy ngẫu nhiên mỗi khung. Mô phỏng bằng quá trình Gauss–Markov (sai số trôi dần với thời gian tương quan khoảng 30 s), đúng đặc tính này (T 11.3).

**Kết quả chạy thử** (chưa phải kết quả chính thức; 10 người, recall 0,7, 3 seed; `runs/rq3/gps/summary.csv`), tỉ lệ bỏ sót:

| Nhiễu GPS σ | `geo` | `bytetrack` | `bytetrack_cmc` |
|---|---|---|---|
| 0 m | 0,000 | 1,000 | 0,000 |
| 0,5 m | 0,000 | 1,000 | 0,200 |
| 1 m | 0,000 | 1,000 | 0,767 |
| 3 m | 0,033 | 1,000 | 1,000 |

Đọc bảng: tracking thông dụng gãy hoàn toàn ở 2 FPS; bù chuyển động camera cứu được nhưng chỉ khi GPS rất ổn định; gom theo mặt đất gần như không bị ảnh hưởng. **Cơ chế khiến `bytetrack_cmc` bỏ sót đã xác định (26/10, mô phỏng):** độ chênh nhiễu GPS giữa hai khung liên tiếp, không phải sai số tuyệt đối; cùng σ = 0,5 m, GPS nhảy nhanh (τ = 5 s) bỏ sót 0,900, trôi chậm (τ = 300 s) 0,033; geo không bị ảnh hưởng (`docs/results/rq3_cmc_cause.md`).

**Recall theo cỡ người (27/10, mô phỏng).** Detector giả giờ lấy recall theo số pixel trên người từ E6 thử thay cho 0,7 cố định, nên quét được độ cao bay. Tỉ lệ bỏ sót với geo, N = 3 (`runs/rq3/altitude/summary.csv`): E2c 0,567 ở 30 m, 0,033 ở 50 m, 0,000 từ 80 tới 200 m; E1 từ 0,533 tới 0,967 ở mọi độ cao. Bay thấp lại tệ vì người ở ít khung và lại "to", đúng chỗ E2c yếu (`rq3_altitude.md`).

**Tần số xử lý theo độ cao (2/11, mô phỏng).** Thay 2 khung/giây cố định bằng tần số để mỗi người được nhìn khoảng 12 lần (trần 8 khung/giây): không kém cố định ở độ cao nào, ở 30 m bỏ sót 0,033 thay vì 0,567, từ 80 m trở lên chạy ít khung hơn (`rq3_adaptive.md`). Nhìn 6 lần là quá ít với recall mỗi khung khoảng 0,5. Khi độ cao đổi giữa chuyến (120 m rồi hạ 40 m), cách này bỏ sót 0,033 với 137 khung, gần bằng xử lý cố định 8 khung/giây (0 với 480 khung) (`rq3_altprofile.md`).

**Trạng thái.** Công cụ xong; còn chạy đủ lưới tham số (vận tốc, FPS, N, nhiễu hướng, nghiêng camera, mạng), dự kiến 14–20/11. **Ở đâu:** `sim/`, `eval/rq3_metrics.py`, cấu hình `configs/experiments/rq3_*.yaml`.

### 3.12. Bước 12: RQ2, tốc độ

**Làm gì.** Xuất mô hình tốt nhất của RQ1 sang TensorRT (FP16 và INT8), đo thời gian từng chặng (cắt ô, suy luận, gộp, định vị, xác nhận), báo trung vị và phân vị 95%, vẽ recall theo FPS, đánh dấu ngưỡng 2 FPS.

**Vì sao báo phân vị 95% chứ không chỉ trung bình.** Hệ thời gian thực bị giới hạn bởi trường hợp chậm: chọn FPS theo trung bình thì cứ 20 khung có một khung không xử lý kịp.

**Vì sao INT8 phải đo lại recall.** Lượng tử hoá INT8 làm thô tín hiệu yếu, mà người nhỏ chính là tín hiệu yếu. Dữ liệu hiệu chỉnh INT8 phải lấy từ ảnh cùng loại (ảnh UAV), không lấy từ tập test.

**Thay đổi so với đề cương.** **Không có Jetson** (chốt 21/10). Đo trên GPU T4 của Kaggle, báo **thứ hạng tương đối** giữa các cấu hình, không quy đổi ra FPS trên Jetson. Thời gian đo trên Mac chỉ dùng so sánh tương đối; `run_config.json` ghi loại máy để không lẫn.

**Trạng thái.** Mã xong (2/11): `scripts/run_rq2.py` chạy trọn xuất engine, chấm, đo và ghép bảng recall theo FPS; notebook Kaggle `notebooks/kaggle_rq2.ipynb`. INT8 hiệu chỉnh trên ô 640 cắt từ ảnh val, cùng kiểu đầu vào với lúc chạy. Chưa chạy trên T4.

### 3.13. Bước 13: Viết luận văn và demo

Chương 2–4 viết song song với thí nghiệm (ROADMAP 1.3); chương 5 (kết quả RQ1, RQ2, RQ3) từ 7/11; đóng băng mã 28/11; bản thảo đầy đủ 4/12; bảo vệ 15/12. Demo: `scripts/demo.sh` trên một video lũ thật, kèm video quay sẵn phòng khi máy lỗi.

---

## 4. Các thư mục

```
flood-tiny-person/
├── configs/                 cấu hình
│   ├── edge.yaml            mặc định của pipeline UAV
│   └── experiments/         một file cho mỗi thí nghiệm (E0_visdrone.yaml, E2c_s0.yaml, rq3_gps.yaml, ...)
├── shared/                  dùng chung giữa UAV và trạm: kiểu dữ liệu (schema), đọc cấu hình, run_config
├── edge/                    chạy trên UAV: lấy mẫu, phát hiện, định vị, xác nhận, cảnh báo, main.py nối tất cả
├── ground/                  trạm mặt đất: máy chủ + trang bản đồ
├── sim/                     mô phỏng: chuyến bay, kịch bản RQ3, quét lưới, mạng chập chờn
├── eval/                    đánh giá: AP theo kích thước, bootstrap, so sánh cặp, chỉ số RQ3, thời gian, chia tập
├── scripts/                 chạy thí nghiệm: run_baseline (toàn ảnh), run_sahi, run_tiled, gsd_calc, demo.sh
├── tools/                   xử lý dữ liệu: chuyển nhãn, kiểm tra nhãn, trích khung, chia tập, kiểm tra rò rỉ
├── training/                train.py: fine-tune
├── notebooks/               notebook Kaggle (chỉ là lớp vỏ gọi training/train.py)
├── console/                 giao diện thử nghiệm: xem lỗi theo ảnh, chạy thử pipeline, trạm mặt đất
├── tests/                   kiểm thử tự động, chạy không cần mô hình, GPU hay dữ liệu
├── docker/, compose.yaml    đóng gói (ảnh dev và ảnh trạm mặt đất)
├── .github/workflows/       chạy kiểm thử tự động mỗi lần đẩy mã lên GitHub
├── docs/                    tài liệu: TONG_QUAN, THUAT_TOAN, TECHNICAL, ROADMAP, LABELING, results/ (bảng kết quả)
├── data/                    dữ liệu (KHÔNG lên git): raw/ bản gốc, processed/ đã chuyển về YOLO
└── runs/                    kết quả mọi lần chạy (KHÔNG lên git): mỗi lần một thư mục có run_config.json
```

**Ánh xạ bước → thư mục:**

| Bước | Thư mục chính |
|---|---|
| 1. Hình học camera | `scripts/gsd_calc.py` |
| 3–4. Dữ liệu | `tools/`, `data/`, `docs/LABELING.md` |
| 5. Cách đo | `eval/` |
| 6–8. Thí nghiệm RQ1 | `scripts/`, `training/`, `notebooks/`, `configs/experiments/`, `runs/` |
| 9. Pipeline UAV | `edge/`, `configs/edge.yaml` |
| 10. Trạm mặt đất | `ground/` |
| 11. RQ3 | `sim/`, `eval/rq3_metrics.py` |
| 12. RQ2 | `scripts/run_rq2.py`, `notebooks/kaggle_rq2.ipynb`, `eval/timing_summary.py`, `eval/rq2_tradeoff.py`, `scripts/after_rq2.py`, `eval/rq2_report.py` |

---

## 5. Nguyên tắc xuyên suốt

Những nguyên tắc này trả lời câu hỏi "làm sao tin được kết quả":

| Nguyên tắc | Cách thực hiện | Vì sao |
|---|---|---|
| **Tái lập được** | Mỗi lần chạy ghi `run_config.json`: lệnh, tham số, phiên bản thư viện, mã băm trọng số, commit git, loại máy. Phiên bản thư viện ghim chính xác | Bảng số trong luận văn phải chỉ ra được lần chạy nào sinh ra nó |
| **Số liệu chỉ lấy từ `runs/`** | Không ghi số ước lượng hay làm tròn vào tài liệu | Tránh số "nhớ nhầm" lọt vào luận văn |
| **Không rò rỉ dữ liệu** | Chia tập theo video; kiểm tra ảnh gần trùng giữa tập test và tập huấn luyện; mọi lựa chọn tham số làm trên val | Rò rỉ cho kết quả đẹp giả mà không ai thấy |
| **Khoá tập test** | Mã băm toàn bộ ảnh và nhãn; sau khi khoá không sửa | Không vô tình chỉnh tập test theo kết quả |
| **Thống kê đúng** | Khoảng tin cậy, bootstrap cặp, nhiều seed | Tập test nhỏ; chênh lệch nhỏ có thể chỉ là ngẫu nhiên |
| **Kiểm thử tự động** | `pytest` (125 kiểm thử ngày 28/10), chạy mỗi lần đẩy mã | Sửa một chỗ không làm hỏng chỗ khác mà không biết |
| **Đồng hồ mô phỏng** | Pipeline lấy thời gian từ khung hình, không từ đồng hồ máy; ngẫu nhiên có seed | Chạy lại RQ3 cho đúng cùng kết quả; chạy nhanh hơn thời gian thực |

---

## 6. Rủi ro và giới hạn

| Rủi ro, giới hạn | Mức | Cách xử lý |
|---|---|---|
| Tập test lũ chưa gán | **Cao** | Dồn 8–10 giờ mỗi tuần cho gán nhãn tới khi khoá; phương án tối thiểu 150 khung |
| Không có Jetson | Đã chốt | Đo T4, báo thứ hạng tương đối; nêu trong giới hạn |
| Định vị giả định camera nhìn thẳng xuống | Trung bình | Mô phỏng định lượng sai số khi camera nghiêng 1–3°; nêu trong giới hạn |
| Ống kính góc rộng có méo ở mép ảnh, chưa hiệu chỉnh | Trung bình | Nêu trong giới hạn; ước lượng nếu có thông số ống kính |
| RQ3 dựa trên mô phỏng | Trung bình | Ghi rõ là mô phỏng; đã kiểm chứng sơ bộ trên video thật SeaDronesSee (`sds_mot_confirm.md`); nếu kịp, chạy pipeline trên video lũ thật để minh hoạ |
| Mô hình chính (E2c) yếu với người to | Trung bình | Thu nhỏ khung theo độ cao (`scale_by_altitude.md`); thêm toàn bộ C2A (E2e) không giúp có ý nghĩa và làm kém người nhỏ (`E2e.md`); cách khác ở `CAI_TIEN.md` mục 1.1 |
| E2c, E3 mới có một seed | Trung bình | 3 seed cho cấu hình cuối (ROADMAP 1.3, tuần 14–20/11) |
| Video lũ có bản quyền; C2A không ghi giấy phép | Cần hỏi | Chỉ công bố nhãn và nguồn; hỏi cô (quyết định #12) |
| Hạn mức GPU Kaggle | Thấp | Ngân sách theo tuần (ROADMAP 1.4); máy Windows nếu có GPU NVIDIA |

---

## 7. Câu hỏi hội đồng có thể hỏi

| Câu hỏi | Ý trả lời | Chi tiết |
|---|---|---|
| Vì sao không chạy YOLO ở 640 như bình thường? | Ở 640, người ở 100 m chỉ còn 2,1 px; đo được AP50 ở 640 bằng khoảng một nửa ở 1280 | Mục 3.1, 3.6 |
| 2 khung mỗi giây có đủ không? | Ở 50 m, 10 m/s, mỗi người nằm trong khung khoảng 4,3 s, được thấy tối đa 8 lần; xác suất thấy đủ N lần tính được từ recall | T 2.4 |
| Vì sao không dùng ByteTrack như mọi người? | Ở 2 FPS mặt đất dịch 254 px giữa hai khung, box người 25 px, IoU bằng 0; đã chứng minh bằng kiểm thử và mô phỏng | Mục 3.9, 3.11 |
| Tập test có đủ lớn không? | 200–300 khung là nhỏ; vì vậy báo khoảng tin cậy, và cân nhắc lấy mẫu theo video | Mục 3.5 |
| Có rò rỉ giữa train và test không? | Chia theo video, kiểm tra ảnh gần trùng bằng dHash trước khi khoá | Mục 3.4, T 15.6 |
| Sao tin được kết quả mô phỏng RQ3? | Pipeline chạy y nguyên mã thật; mô phỏng chỉ thay video và detector; nhiễu GPS theo mô hình chuẩn; kết luận định tính, ghi rõ giới hạn | Mục 3.11 |
| Không có Jetson thì RQ2 nói được gì? | Thứ hạng tương đối giữa các cấu hình trên cùng GPU, và chặng nào tốn thời gian nhất | Mục 3.12 |
| Sao không thêm nhánh phát hiện P2 cho người nhỏ? | Đã thử (E3): người dưới 8 px chỉ tăng 0,012–0,013 AP50 và mức tăng mất ở IoU 0,3, tức box khít hơn chứ không tìm thêm người; đổi lại kém ở người to, 115,0 so với 93,9 GFLOPs. Thêm dữ liệu tăng nhiều hơn hẳn | `E3.md`, T 3.4 |
| Vì sao tự viết bộ cắt ô thay vì SAHI? | Chạy theo lô, dùng được TensorRT; đã đối chiếu độ chính xác với SAHI bằng bootstrap cặp | Mục 3.7 |

---

## 8. Trạng thái tổng hợp (7/11/2026)

| Bước | Trạng thái |
|---|---|
| 1. Hình học camera | Xong |
| 2. Mô hình nền | Xong |
| 3. Dữ liệu công khai | VisDrone, AFO, C2A, HydroVigilance, SeaDronesSee-MOT đã tải và chuyển; FinlandProper tạm bỏ (162 GB, máy chủ không cho tải từng phần) |
| 4. Tập test lũ | **Chưa gán; gán 7–9/11, khoá 11/11** (quyết định #10; lịch ở LABELING mục 9); giữ 4 video dưới 1080p (#15); khoảng tin cậy theo video (#7); 4/11 gộp hai video cùng nguồn San Angelo (còn 188 khung, 9 nguồn); kiểm tra trùng với 5 thư mục train (kể cả C2A) không thấy cặp nào (`flood_truoc_khoa.md`). Ban đầu 212 khung từ 10 video đã trích, lọc tay, đóng gói zip cho CVAT (`Downloads/floodeye_cvat`); lịch gán ở LABELING mục 9. Gán xong thì `scripts/eval_flood.sh <thư mục file xuất>` chạy trọn: chuyển nhãn, dự đoán mọi `*_flood.yaml`, chấm theo kích thước và theo loại nhiễu (`eval/recall_by_tag.py`) |
| 5. Cách đo | Xong; thêm chấm khối xác nhận theo track trên video thật (`eval/track_confirm_eval.py`) |
| 6. E0, E1, E4 | Xong; 7/11 chạy lại E0, E4 và cắt ô tự viết trên RTX 5060 vì thư mục kết quả trên Mac không còn, kết luận không đổi (`visdrone_baseline.md`, `visdrone_tiled_vs_sahi.md`) |
| 7. Bộ cắt ô | Xong, đã đối chiếu SAHI |
| Cải thiện | `docs/CAI_TIEN.md` (7/11): mỗi điểm yếu đã đo kèm cách sửa, chi phí, cách kiểm chứng, trạng thái. Mới 7/11: số người ước tính mỗi sự cố (`group_size`); định vị theo góc gimbal (`--use-pitch`, tuỳ chọn: tốt hơn khi drone di chuyển với camera nghiêng vừa phải, tính chung chưa tốt hơn, `georef_pitch.md`). Tự hiệu chỉnh lệch la bàn (`--yaw-calib`, mô phỏng: tách nhầm do la bàn lệch 5° ở 100 m từ 5,333 xuống 0,333, `rq3_yawcalib.md`). Bán kính theo độ chính xác GPS bộ thu báo (`--gps-sigma-from-telemetry`, mô phỏng: vùng tìm 95% chứa đủ người cả khi GPS kém đi giữa chuyến, `rq3_gpsacc.md`). Năm thử nghiệm âm 7–8/11, không bật: đầu một-một không NMS của YOLO26 (`nms_free.md`), phóng to khi người dưới 8 px (`upscale_small.md`), thêm lượt toàn ảnh sau khi thu nhỏ (`full_pass.md`), đồng bộ thời gian và làm mượt góc gimbal (`georef_sync.md`), ngưỡng tin cậy theo cỡ box (`conf_by_size.md`). Mất gói theo cụm (`rq3_burst.md`, mô phỏng). Đếm người theo cụm khi người đứng theo nhóm (`--group-count clusters`, `rq3_group.md`, mô phỏng: nhóm 4 người, recall 0,7, đếm đúng 0,303 → 0,524; nhưng video thật SDS v21 kém hơn 0,792 → 0,583 vì cụm tách nhầm, nên không bật, quyết định #18) |
| 8. E2–E6 | E2 (VisDrone) và E2c (+ AFO) xong; **E3 (P2) xong 28/10**: người dưới 8 px chỉ +0,012–0,013 AP50, kém hơn ở người to, không đáng chi phí; giữ E2c (`E3.md`); E2b, E2d (+ HydroVigilance) không chạy, bỏ 7/11; **E5 (YOLO11s) cắt 7/11** theo thứ tự cắt khi trễ; **E2e (E2c + C2A) xong 7/11, kết quả âm**: kém E2c có ý nghĩa ở người nhỏ (VisDrone val < 8 px −0,053 AP50, test-dev tất cả −0,041), tốt hơn trên AFO (+0,057), không hơn có ý nghĩa trên SeaDronesSee (+0,041, khoảng tin cậy −0,167 đến +0,167); giữ E2c (`E2e.md`); **E6 thử trên SDS** (`e6_sds_pilot.md`): E2c mạnh ở người 6–23 px, tụt mạnh với người trên 45 px |
| 9. Pipeline UAV | Xong; demo bảo vệ `scripts/demo_bao_ve.sh` và giao diện `python -m console` (`live_demo.py` cũ bỏ 7/11) |
| 10. Trạm mặt đất | Xong; bản đồ Esri (ô OpenStreetMap không tải được); gộp cảnh báo thành sự cố, bán kính 5 m (`alert_memory.md`), rộng hơn khi hai drone khác nhau; xếp ưu tiên có lý do, người vận hành gắn thẻ và đóng sự cố; demo hai drone |
| 11. RQ3 | Mô phỏng chạy thử; **kiểm chứng sơ bộ trên video thật SeaDronesSee**: ở 2 khung/giây geo xác nhận 12/19 người, ByteTrack 2/19 (`docs/results/sds_mot_confirm.md`); cơ chế `bytetrack_cmc` bỏ sót đã xác định (`rq3_cmc_cause.md`); quét độ cao với recall theo cỡ người (`rq3_altitude.md`); **6/11 sai số vị trí** (`rq3_geoerr.md`: GPS là nguồn chính; vòng 1σ chỉ chứa 0,278 số người khi GPS σ 3 m nên bản đồ vẽ vùng 95%; lệch hướng 5° ở 100 m gây tách nhầm) và **mạng** (`rq3_network.md`: thêm thăm dò đường truyền, không mất cảnh báo nào, độ trễ lớn nhất khi mất một nửa gói từ 41,167 s còn 8,333 s); **7/11 mất theo cụm** (`rq3_burst.md`: cùng tỉ lệ mất 0,5, cụm 30 s cho độ trễ lớn nhất 44,400 s, vẫn không mất cảnh báo khi có thăm dò) |
| 12. RQ2 | Mã xong (2/11): xuất TensorRT FP16/INT8, chấm độ chính xác, đo cả pipeline, bảng recall theo FPS; chạy thử phần PyTorch trên máy cá nhân; **7/11: chạy thử hai biến thể trên Kaggle T4 thành công; lần chạy đủ đầu tiên dừng ở bước xuất INT8 (TensorRT 11 không build được INT8 trên T4), đã ghim TensorRT 10.16 và cho `run_rq2.py` bỏ qua engine lỗi; 8/11 chạy thử xuất INT8 thành công, lần chạy đủ thứ hai đang chạy trên Kaggle**; xử lý sau khi tải về đã sẵn (`scripts/after_rq2.py`, `eval/rq2_report.py`, mô phỏng thiết bị `rq3_device.yaml`); giả lập thời gian thiết bị biên (`--device-profile`, TECHNICAL 14.6), hồ sơ chưa hiệu chỉnh |
| Giao diện thử nghiệm | Xong 3/11 (`python -m console`): xem lỗi từng ảnh (bỏ sót, báo nhầm theo nhóm kích thước và thẻ), chạy thử pipeline, trạm mặt đất; dùng cho phân tích lỗi chương 5 và demo. **7/11: Sân thử** mô phỏng (chỉnh tham số hoặc câu hỏi "nếu… thì sao" dựng sẵn, chạy, xem trên màn hình điều phối, bảng so sánh; TECHNICAL 11.4) |
| Hiểu dự án | Xong 5/11: tab đầu của `python -m console`, nền tối: bản đồ dự án (ví dụ đời thường, kết quả kèm thanh so sánh, 19 câu hỏi tự kiểm tra), đọc tài liệu có giải thích thuật ngữ khi di chuột (`docs/THUAT_NGU.md`), câu hỏi nghiên cứu và câu hỏi con kèm trạng thái (mục 1.3), thẻ ghi nhớ, tìm kiếm, xem mã |
| Demo bảo vệ | Xong 4/11 (`scripts/demo_bao_ve.sh`): phát lại SDS v21 theo thời gian thực với thiết bị giả lập, không cần GPU hay internet; video so hai thiết bị. **6/11: màn hình điều phối** một trang (video trên drone, drone và vùng đã quét trên bản đồ, cảnh báo còn kẹt trên drone khi mất sóng, đoạn đường bay lỡ khi mất sóng được gửi bù; TECHNICAL 10.6, 12.5) và **chuyến quét mô phỏng** có ảnh tổng hợp (`hotay_quet`, `sim/render.py`) để thấy vùng đã quét lớn dần, vì đoạn SeaDronesSee nhìn thẳng xuống thì drone gần như đứng yên; **đối chiếu đáp án** trên bản đồ (người được cảnh báo riêng, nằm trong vùng tìm, bỏ sót, sự cố báo nhầm; TECHNICAL 12.6); **công cụ cho đội đi cứu** (vị trí thuyền, khoảng cách và hướng, thứ tự đi cứu, GPX; TECHNICAL 12.7) |
| 13. Luận văn | Đã báo cáo ý tưởng thuật toán với cô 23/10 (slide 22 trang); dàn ý sáu chương (`DAN_Y_LUAN_VAN.md`); nháp chương 1–5 và khung chương 6 (7–8/11, `docs/luan_van/`; chương 2 còn tra trích dẫn; danh mục tài liệu đã tra `tai_lieu_tham_khao.md`), còn chờ tập lũ (**[CHỜ KHOÁ]**) và câu hỏi 2 (**[CHỜ RQ2]**) |

Kết quả chính tới nay: fine-tune tăng mạnh người nhỏ trên VisDrone (`visdrone_E2.md`); thêm AFO giữ được người dưới nước (`E2c.md`), nhưng trên tập nước độc lập SeaDronesSee chưa hơn mô hình gốc (`sds_det.md`). Lý do một phần là cỡ người: E2c yếu với người to; **thu nhỏ khung theo độ cao bay** (`--target-person-px`) đưa E2c cắt ô trên SDS 4K từ AP50 0,235 lên 0,531, ngang mô hình gốc (`scale_by_altitude.md`). Cảnh báo lặp của geo: chặn ở biên (`--suppress-s`) làm mất người ở cảnh đông nên tắt; gộp thành sự cố ở trạm mặt đất thay thế (`alert_memory.md`).

Lịch chi tiết: [ROADMAP.md](ROADMAP.md) mục 1. Khi một bước đổi trạng thái, cập nhật bảng này cùng lúc với ROADMAP.
