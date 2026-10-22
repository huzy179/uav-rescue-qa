# FloodEye: tổng quan dự án từ đầu đến cuối

Tài liệu này giải thích **toàn bộ dự án theo trình tự các bước**: mỗi bước làm gì, vì sao cần, có cách nào khác và vì sao không chọn, đang ở trạng thái nào. Mục đích là nắm được cả dự án và trình bày lại được cho thầy và hội đồng.

Tài liệu không thay cho ba tài liệu kia:

| Tài liệu | Dùng khi |
|---|---|
| **TONG_QUAN.md** (tài liệu này) | Cần hiểu dự án tổng thể, lập luận cho từng lựa chọn, chuẩn bị trả lời câu hỏi |
| [TECHNICAL.md](TECHNICAL.md) | Cần công thức, thuật toán, chi tiết cài đặt. Các chỗ "(T 9.3)" bên dưới là mục 9.3 của TECHNICAL |
| [ROADMAP.md](ROADMAP.md) | Cần lịch theo tuần, các quyết định còn treo |
| [README.md](../README.md) | Cần lệnh cài đặt và chạy |

Mọi con số trong tài liệu này đọc được từ một file trong `runs/` hoặc `docs/results/`; nguồn ghi ngay cạnh số. Trạng thái tính tới ngày **22/10/2026**.

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

### 1.3. Ba câu hỏi nghiên cứu

> Ghi chú: đây là tóm tắt từ kế hoạch thí nghiệm; khi trình bày, dùng đúng câu chữ trong đề cương đã nộp.

- **RQ1, độ chính xác:** phát hiện người nhỏ trong ảnh UAV vùng lũ chính xác tới mức nào, và những kỹ thuật nào (độ phân giải đầu vào, cắt ô, fine-tune, đầu dò P2) giúp được bao nhiêu, đặc biệt với người dưới 16 px?
- **RQ2, tốc độ trên thiết bị biên:** cấu hình nào đạt tần số xử lý cần thiết (khoảng 2 khung mỗi giây) mà giữ được recall cao nhất?
- **RQ3, hệ thống:** khi ghép phát hiện qua nhiều khung để xác nhận rồi gửi cảnh báo qua mạng chập chờn, hệ thống báo nhầm bao nhiêu, bỏ sót bao nhiêu, cảnh báo tới trạm sau bao lâu; cách xác nhận nào chịu được sai số GPS và chuyển động của camera?

### 1.4. Đóng góp dự kiến

1. Đánh giá phát hiện người **theo nhóm kích thước** (dưới 8, 8–16, 16–32, trên 32 px), có khoảng tin cậy, trên một **tập test lũ tự gán nhãn** (hiện chưa có bộ dữ liệu công khai nào chụp người trong lũ từ UAV có nhãn sẵn).
2. Một pipeline hoàn chỉnh từ video tới cảnh báo trên bản đồ, mã nguồn mở, kiểm thử được.
3. Kết quả về **xác nhận nhiều khung ở tần số khung thấp**: chỉ ra vì sao tracking thông dụng (ByteTrack) gãy khi UAV bay nhanh và xử lý ít khung, và cách gom theo toạ độ mặt đất khắc phục (mục 3.9).

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
| **A. Mô hình phát hiện** | RQ1, RQ2 | Thí nghiệm học máy: chọn cấu hình, fine-tune, đo AP và recall, đo tốc độ | Ảnh có nhãn người: VisDrone, C2A, tập test lũ tự gán |
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
- YOLO26 bỏ được bước NMS ở cuối (đầu ra "end-to-end"), giảm độ trễ và đơn giản hoá việc chạy trên thiết bị biên.
- Bản `s` cân bằng giữa độ chính xác và tốc độ cho thiết bị dưới 25 W.

**Cách khác.**
| Phương án | Vì sao không chọn làm mô hình chính |
|---|---|
| Mô hình hai giai đoạn (Faster R-CNN) | Chính xác với vật nhỏ nhưng chậm hơn nhiều; không hợp thiết bị biên |
| Transformer (DETR, RT-DETR) | Cần nhiều dữ liệu và tính toán hơn; công cụ xuất sang thiết bị biên kém sẵn có hơn YOLO. Nếu hội đồng hỏi, có thể nêu như hướng mở rộng |
| YOLO11s | Giữ làm **đối chứng** (E5), để biết kết quả có phụ thuộc vào đời YOLO không |
| Bản lớn hơn (`m`, `l`) | Chậm hơn; nếu RQ2 cho thấy dư tốc độ thì có thể xem lại |

**Trạng thái.** Đã chốt. **Ở đâu:** `yolo26s.pt` (không đưa lên git).

### 3.3. Bước 3: Dữ liệu huấn luyện công khai

**Làm gì.** Chuyển các bộ dữ liệu công khai về **một lớp duy nhất là "person"** theo định dạng YOLO, kiểm tra lại nhãn sau khi chuyển.

| Bộ | Nội dung | Dùng để | Trạng thái |
|---|---|---|---|
| **VisDrone2019-DET** | Ảnh UAV đô thị Trung Quốc; val 548 ảnh, 13.969 người; train 6.471 ảnh, 106.396 người (`runs/data/visdrone_check.json`) | Huấn luyện (train), kiểm định (val), mốc so sánh với nghiên cứu khác | Đã chuyển, đã kiểm tra từng ảnh khớp nhãn gốc |
| **C2A** | 10.215 ảnh thảm hoạ thật (lũ, cháy, nhà sập, tai nạn) có **ghép thêm hình người** (`data/processed/c2a/stats.json`) | Huấn luyện | Đã tải, đã chuyển |
| **AFO** | Ảnh drone người và vật trôi trên mặt nước (biển) | Huấn luyện | Chưa tải (cần tài khoản Kaggle) |
| **FinlandProper** | Người dưới nước, 1920×1024 | Huấn luyện và đánh giá | Chưa tải |

**Vì sao gộp về một lớp.** Đề tài chỉ quan tâm "có người hay không". VisDrone tách `pedestrian` (đứng, đi) và `people` (ngồi, nằm); cả hai đều là người cần cứu nên gộp lại. Người đi xe đạp, xe máy bị VisDrone gán vào lớp phương tiện nên bị bỏ (ghi rõ trong luận văn).

**Vì sao cần kiểm tra nhãn sau chuyển.** Mỗi lần huấn luyện tốn khoảng 8 giờ GPU trong hạn mức hằng tuần; phát hiện lỗi nhãn sau khi huấn luyện là mất cả lần đó (T 6.7).

**Vì sao chọn lớp theo tên chứ không theo mã số.** Mỗi bộ đánh số lớp khác nhau (AFO có 9 lớp, trang mô tả không ghi mã số lớp "human"). Đoán sai mã thì mô hình học nhầm lớp mà không có lỗi nào báo (`tools/convert_yolo_subset.py`).

**Cách khác.** Tự gán nhãn toàn bộ dữ liệu huấn luyện: không khả thi với một người trong 2 tháng; công sức gán nhãn dành cho tập test (bước 4), vì đó là nơi quyết định giá trị kết luận.

**Lưu ý về C2A.** Người trong C2A là hình ghép, nên C2A chỉ dùng để **huấn luyện**, không dùng để kết luận về cảnh lũ. Ảnh C2A nhỏ (cạnh dài khoảng 430 px), khi huấn luyện ở 1280 bị phóng to khoảng 3 lần; đo được rằng điều này làm người C2A "to" hơn người VisDrone, hai bộ bù nhau và cùng phủ khoảng 13–42 px của video lũ 4K (`runs/stats/`, T 13.4).

**Ở đâu:** `tools/convert_visdrone.py`, `tools/check_visdrone.py`, `tools/convert_yolo_subset.py`; dữ liệu ở `data/raw/` (gốc) và `data/processed/` (đã chuyển).

### 3.4. Bước 4: Tập test lũ tự gán nhãn

**Làm gì.** Gom video UAV quay cảnh lũ có người, trích 200–300 khung, gán nhãn người bằng CVAT theo một hướng dẫn cố định, rồi **khoá** tập (khoảng 4/11) bằng mã băm: sau khi khoá không sửa nhãn, không thêm bớt khung.

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
| Dùng bộ có sẵn (AFO, SeaDronesSee) làm tập test | Đó là người bơi ngoài biển, không phải cảnh lũ (mái nhà, nước đục, rác) |
| Chỉ dùng FinlandProper làm tập test | Là người dưới nước nhưng không phải cảnh lũ đô thị và nông thôn Việt Nam; vẫn dùng làm tập đánh giá thứ hai |
| Tự bay UAV quay | Không có thiết bị, không có lũ đúng lúc |

**Trạng thái.** **Chưa bắt đầu gán. Đây là rủi ro lớn nhất của đồ án** (ROADMAP 1.1). Công cụ trích khung và chuyển nhãn đã sẵn sàng. Phương án dự phòng nếu không kịp: khoá với tối thiểu 150 khung, hoặc lùi khoá tối đa tới 11/11 (quyết định #10, hỏi thầy).

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
| Bootstrap cặp | Hai khoảng tin cậy riêng chồng nhau **không** có nghĩa hai cấu hình như nhau. Ví dụ thật: bộ cắt ô tự viết và SAHI có khoảng tin cậy AP50 riêng gần trùng nhau (0,437–0,469 và 0,443–0,477), nhưng bootstrap cặp cho thấy bộ tự viết kém hơn 0,008, có ý nghĩa thống kê (`docs/results/visdrone_tiled_vs_sahi.md`) |
| Lấy mẫu theo video | 548 ảnh VisDrone val chỉ đến từ 76 video; ảnh cùng video không độc lập. Lấy mẫu theo video, khoảng tin cậy AP50 của E4 rộng gần gấp đôi (0,428–0,489 so với 0,443–0,477; T 15.3). Mặc định vẫn theo ảnh để bảng cũ còn so sánh được; dùng cho tập lũ hay không là quyết định #7 |

**Cách khác.** Dùng `yolo val` của ultralytics: không chia theo kích thước, không có vùng bỏ qua, không có khoảng tin cậy. Vẫn dùng để **đối chiếu**: trên E1 hai cách tính lệch dưới 1% (`docs/results/visdrone_baseline.md`).

**Trạng thái.** Xong, có kiểm thử bằng ví dụ tính tay. **Ở đâu:** `eval/metrics.py`, `eval/eval_by_size.py`, `eval/compare_runs.py`.

### 3.6. Bước 6: Mốc so sánh chưa huấn luyện (E0, E1, E4)

**Làm gì.** Chạy mô hình gốc (chưa fine-tune) trên VisDrone val theo ba cách: thu ảnh về 640 (E0), về 1280 (E1), cắt ô 640 bằng SAHI (E4).

**Vì sao.** Biết điểm xuất phát, và kiểm chứng lập luận ở bước 1 rằng độ phân giải quan trọng.

**Kết quả** (VisDrone val, IoU 0,5, `docs/results/visdrone_baseline.md`):

| Cấu hình | AP50 tất cả | AP50 người < 8 px | AP50 người 8–16 px |
|---|---|---|---|
| E0: ảnh về 640 | 0,276 | 0,050 | 0,254 |
| E1: ảnh về 1280 | **0,497** | **0,167** | **0,507** |
| E4: cắt ô 640 (SAHI) | 0,460 | 0,149 | 0,470 |

Đọc bảng:
- **Tăng độ phân giải gần gấp đôi AP** và gấp ba ở người dưới 8 px: xác nhận lập luận bước 1.
- Cắt ô **không** hơn 1280 trên VisDrone, vì ảnh VisDrone chỉ rộng khoảng 1360 px: ở 1280 đã gần như giữ nguyên độ phân giải. Với video 4K thì khác (1280 phải thu nhỏ 3 lần), nên **E4 phải đo lại trên dữ liệu độ phân giải cao**.

**Trạng thái.** Xong.

### 3.7. Bước 7: Bộ cắt ô tự viết

**Làm gì.** Cắt ảnh lớn thành các ô 640 chồng nhau 20%, đưa **cả lô ô vào mô hình trong một lần gọi**, dời box về toạ độ ảnh gốc, gộp các box trùng ở vùng chồng nhau.

**Vì sao không dùng thẳng SAHI.** SAHI chạy mô hình **từng ô một**; trên GPU và TensorRT, chạy theo lô nhanh hơn nhiều. SAHI cũng gắn với cách nạp mô hình riêng, khó dùng với file `.engine` của TensorRT (RQ2).

**Kết quả đối chiếu** (`docs/results/visdrone_tiled_vs_sahi.md`): AP50 0,452 so với 0,460 của SAHI; kém hơn 0,008 có ý nghĩa thống kê, chủ yếu ở người lớn; ở người dưới 8 px thì **tốt hơn**. Với đề tài người nhỏ, mức đánh đổi này chấp nhận được.

**Cách khác đã thử và bỏ.** Hợp nhất toạ độ các box trùng (như SAHI) thay vì chỉ giữ box điểm cao nhất: AP50 tụt dưới 0,05, vì ở ngưỡng conf thấp, box lớn điểm thấp phủ cả nhóm người kéo box của từng người thành box cả nhóm. Lý do được ghi lại trong mã để không ai thử lại.

**Trạng thái.** Xong. **Ở đâu:** `edge/detector.py`, `scripts/run_tiled.py`.

### 3.8. Bước 8: Fine-tune và các thí nghiệm RQ1 (E2–E6)

**Làm gì.**
| Mã | Thí nghiệm | Câu hỏi nó trả lời | Trạng thái |
|---|---|---|---|
| E2 lượt 1 | Fine-tune YOLO26s ở 1280 trên VisDrone, 60 epoch | Fine-tune trên ảnh UAV giúp bao nhiêu so với mô hình COCO? | **Đang chạy trên Kaggle** (22/10) |
| E2 lượt 2 | Như trên, thêm C2A (`E2b_s0.yaml`) | Thêm ảnh thảm hoạ có giúp không? | Đã có cấu hình; chờ lượt 1 |
| E3 | E2 + đầu dò P2 (thêm tầng phát hiện ở bước nhảy 4 thay vì 8) | Người 8 px chiếm 2×2 ô đặc trưng thay vì 1 ô: có tăng recall người rất nhỏ không, đáng với chi phí tính toán không? | Chưa |
| E4 | E2/E3 + cắt ô, trên dữ liệu độ phân giải cao | Cắt ô có lợi khi ảnh thật sự lớn không? | Chưa |
| E5 | E2 nhưng dùng YOLO11s | Kết quả có phụ thuộc đời mô hình không? | Chưa |
| E6 | Thu nhỏ ảnh theo nhiều mức, vẽ recall theo số pixel trên người | Bay cao tối đa bao nhiêu thì còn phát hiện được? Nối thẳng vào khuyến nghị độ cao bay | Chờ thầy duyệt (quyết định #1) |

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
| Phát hiện (`detector.py`) | YOLO toàn ảnh hoặc cắt ô | Bước 7. Đây là file duy nhất dùng thư viện ultralytics; các khối khác test được mà không cần mô hình |
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

**Cách khác.** Gộp cảnh báo từ nhiều drone, xếp ưu tiên theo mức nguy hiểm: là phần mở rộng, **cắt đầu tiên** nếu trễ (ROADMAP 1.5).

**Trạng thái.** Xong bản tối giản; có `scripts/demo.sh` chạy cả hai phía bằng một lệnh. **Ở đâu:** `ground/`.

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

Đọc bảng: tracking thông dụng gãy hoàn toàn ở 2 FPS; bù chuyển động camera cứu được nhưng chỉ khi GPS rất ổn định; gom theo mặt đất gần như không bị ảnh hưởng. **Cơ chế khiến `bytetrack_cmc` bỏ sót ở σ = 0,5 m chưa được xác nhận** (T 15.4); cần điều tra trước khi viết chương RQ3.

**Trạng thái.** Công cụ xong; còn chạy đủ lưới tham số (độ cao, vận tốc, FPS, N, nhiễu hướng, nghiêng camera, mạng), dự kiến 14–20/11. **Ở đâu:** `sim/`, `eval/rq3_metrics.py`, cấu hình `configs/experiments/rq3_*.yaml`.

### 3.12. Bước 12: RQ2, tốc độ

**Làm gì.** Xuất mô hình tốt nhất của RQ1 sang TensorRT (FP16 và INT8), đo thời gian từng chặng (cắt ô, suy luận, gộp, định vị, xác nhận), báo trung vị và phân vị 95%, vẽ recall theo FPS, đánh dấu ngưỡng 2 FPS.

**Vì sao báo phân vị 95% chứ không chỉ trung bình.** Hệ thời gian thực bị giới hạn bởi trường hợp chậm: chọn FPS theo trung bình thì cứ 20 khung có một khung không xử lý kịp.

**Vì sao INT8 phải đo lại recall.** Lượng tử hoá INT8 làm thô tín hiệu yếu, mà người nhỏ chính là tín hiệu yếu. Dữ liệu hiệu chỉnh INT8 phải lấy từ ảnh cùng loại (ảnh UAV), không lấy từ tập test.

**Thay đổi so với đề cương.** **Không có Jetson** (chốt 21/10). Đo trên GPU T4 của Kaggle, báo **thứ hạng tương đối** giữa các cấu hình, không quy đổi ra FPS trên Jetson. Thời gian đo trên Mac chỉ dùng so sánh tương đối; `run_config.json` ghi loại máy để không lẫn.

**Trạng thái.** Công cụ đo từng chặng xong (`eval/timing_summary.py`); xuất TensorRT và đo thật dự kiến 9–20/11.

### 3.13. Bước 13: Viết luận văn và demo

Chương 2–4 viết song song với thí nghiệm (ROADMAP 1.3); chương 5 (kết quả RQ1, RQ2, RQ3) từ 7/11; đóng băng mã 28/11; bản thảo đầy đủ 4/12; bảo vệ 15/12. Demo: `scripts/demo.sh` trên một video lũ thật, kèm video quay sẵn phòng khi máy lỗi.

---

## 4. Các thư mục

```
flood-tiny-person/
├── configs/                 cấu hình
│   ├── edge.yaml            mặc định của pipeline UAV
│   └── experiments/         một file cho mỗi thí nghiệm (E0_visdrone.yaml, E2b_s0.yaml, rq3_gps.yaml, ...)
├── shared/                  dùng chung giữa UAV và trạm: kiểu dữ liệu (schema), đọc cấu hình, run_config
├── edge/                    chạy trên UAV: lấy mẫu, phát hiện, định vị, xác nhận, cảnh báo, main.py nối tất cả
├── ground/                  trạm mặt đất: máy chủ + trang bản đồ
├── sim/                     mô phỏng: chuyến bay, kịch bản RQ3, quét lưới, mạng chập chờn
├── eval/                    đánh giá: AP theo kích thước, bootstrap, so sánh cặp, chỉ số RQ3, thời gian, chia tập
├── scripts/                 chạy thí nghiệm: run_baseline (toàn ảnh), run_sahi, run_tiled, gsd_calc, demo.sh
├── tools/                   xử lý dữ liệu: chuyển nhãn, kiểm tra nhãn, trích khung, chia tập, kiểm tra rò rỉ
├── training/                train.py: fine-tune
├── notebooks/               notebook Kaggle (chỉ là lớp vỏ gọi training/train.py)
├── tests/                   kiểm thử tự động, chạy không cần mô hình, GPU hay dữ liệu
├── docker/, compose.yaml    đóng gói (ảnh dev và ảnh trạm mặt đất)
├── .github/workflows/       chạy kiểm thử tự động mỗi lần đẩy mã lên GitHub
├── docs/                    tài liệu: TONG_QUAN, TECHNICAL, ROADMAP, LABELING, results/ (bảng kết quả)
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
| 12. RQ2 | `eval/timing_summary.py`, `scripts/benchmark_speed.py` |

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
| **Kiểm thử tự động** | 93 kiểm thử, chạy mỗi lần đẩy mã | Sửa một chỗ không làm hỏng chỗ khác mà không biết |
| **Đồng hồ mô phỏng** | Pipeline lấy thời gian từ khung hình, không từ đồng hồ máy; ngẫu nhiên có seed | Chạy lại RQ3 cho đúng cùng kết quả; chạy nhanh hơn thời gian thực |

---

## 6. Rủi ro và giới hạn

| Rủi ro, giới hạn | Mức | Cách xử lý |
|---|---|---|
| Tập test lũ chưa gán | **Cao** | Dồn 8–10 giờ mỗi tuần cho gán nhãn tới khi khoá; phương án tối thiểu 150 khung |
| Không có Jetson | Đã chốt | Đo T4, báo thứ hạng tương đối; nêu trong giới hạn |
| Định vị giả định camera nhìn thẳng xuống | Trung bình | Mô phỏng định lượng sai số khi camera nghiêng 1–3°; nêu trong giới hạn |
| Ống kính góc rộng có méo ở mép ảnh, chưa hiệu chỉnh | Trung bình | Nêu trong giới hạn; ước lượng nếu có thông số ống kính |
| RQ3 dựa trên mô phỏng | Trung bình | Ghi rõ là mô phỏng; nếu kịp, chạy pipeline trên video lũ thật để minh hoạ |
| Video lũ có bản quyền; C2A không ghi giấy phép | Cần hỏi | Chỉ công bố nhãn và nguồn; hỏi thầy (quyết định #12) |
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
| Vì sao tự viết bộ cắt ô thay vì SAHI? | Chạy theo lô, dùng được TensorRT; đã đối chiếu độ chính xác với SAHI bằng bootstrap cặp | Mục 3.7 |

---

## 8. Trạng thái tổng hợp (22/10/2026)

| Bước | Trạng thái |
|---|---|
| 1. Hình học camera | Xong |
| 2. Mô hình nền | Xong |
| 3. Dữ liệu công khai | VisDrone, C2A xong; AFO, FinlandProper chưa tải |
| 4. Tập test lũ | **Chưa gán**; công cụ sẵn sàng |
| 5. Cách đo | Xong |
| 6. E0, E1, E4 | Xong |
| 7. Bộ cắt ô | Xong, đã đối chiếu SAHI |
| 8. E2–E6 | E2 lượt 1 đang chạy; còn lại chưa |
| 9. Pipeline UAV | Xong |
| 10. Trạm mặt đất | Xong bản tối giản |
| 11. RQ3 | Công cụ xong, đã chạy thử; còn lưới đầy đủ |
| 12. RQ2 | Công cụ đo xong; chưa xuất TensorRT |
| 13. Luận văn | Theo lịch: chương 2 tuần 21–23/10 |

Lịch chi tiết: [ROADMAP.md](ROADMAP.md) mục 1. Khi một bước đổi trạng thái, cập nhật bảng này cùng lúc với ROADMAP.
