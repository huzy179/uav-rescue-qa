# Thuật ngữ và ký hiệu

Bảng chuẩn duy nhất của dự án: tài liệu trong `docs/` và luận văn dùng đúng tên ở cột "Dùng trong tài liệu". Mục "Danh mục thuật ngữ và chữ viết tắt" của luận văn chép từ đây.

## Quy tắc

1. **Lần đầu gặp trong mỗi chương:** viết tiếng Việt, tiếng Anh trong ngoặc, ví dụ "tinh chỉnh (fine-tuning)". Các lần sau chỉ dùng tên ở cột "Dùng trong tài liệu".
2. **"Độ chính xác"** chỉ dùng theo nghĩa chung (phát hiện đúng tới đâu), **không** dùng làm tên chỉ số. Tên chỉ số: AP, AP50, precision, recall.
3. **"Khung"** là một ảnh trong video (frame). Hình chữ nhật bao quanh một người gọi là **box**, lần đầu viết "box (khung bao)".
4. **Trong câu văn viết "khung/giây"**; "FPS" chỉ dùng trong bảng, trục hình và tên đã đặt (ví dụ "bảng recall theo FPS").
5. **Mã thí nghiệm (E0, E2c, …) và tên tuỳ chọn trong mã nguồn (`geo`, `--target-person-px`)** là ký hiệu nội bộ: trong luận văn phải đi kèm tên mô tả ở mục "Ký hiệu nội bộ".

## 1. Thuật ngữ chuẩn của ngành

Ai làm thị giác máy tính hay UAV cũng hiểu; vẫn giải thích một lần khi gặp lần đầu.

| Dùng trong tài liệu | Tiếng Anh | Nghĩa |
|---|---|---|
| câu hỏi nghiên cứu | research question (RQ) | Câu hỏi luận văn trả lời bằng thí nghiệm |
| tinh chỉnh | fine-tuning | Huấn luyện thêm một mô hình đã học sẵn trên dữ liệu của mình |
| mô hình nền | base model, pretrained model | Mô hình đã học sẵn trên COCO, chưa tinh chỉnh (YOLO26s) |
| box (khung bao) | bounding box | Hình chữ nhật bao quanh một đối tượng |
| conf (điểm tin cậy) | confidence score | Điểm mô hình gán cho mỗi box, từ 0 tới 1 |
| IoU | intersection over union | Độ chồng lấn giữa hai box: phần giao chia phần hợp |
| precision | precision | Trong các box mô hình báo, tỉ lệ đúng là người |
| recall | recall | Trong số người thật, tỉ lệ được mô hình tìm thấy |
| AP, AP50, AP50:95 | average precision | Chỉ số tổng hợp precision và recall trên mọi ngưỡng conf; AP50 là AP ở IoU 0,5; AP50:95 là trung bình ở IoU 0,5–0,95 |
| báo nhầm | false positive, false alarm | Mô hình báo có người nhưng không có |
| bỏ sót | false negative, miss | Có người nhưng mô hình không báo |
| NMS | non-maximum suppression | Bỏ các box trùng nhau, giữ box điểm cao nhất |
| khoảng tin cậy | confidence interval | Khoảng chứa giá trị thật với xác suất 95% |
| bootstrap | bootstrap | Lấy mẫu lại có hoàn lại nhiều lần để ước lượng khoảng tin cậy |
| bootstrap theo cụm | cluster bootstrap | Lấy mẫu lại theo video thay vì theo ảnh, vì các khung cùng video không độc lập |
| bootstrap cặp | paired bootstrap | So hai mô hình trên cùng các mẫu lấy lại, để biết chênh lệch có ý nghĩa không |
| thiết bị biên | edge device | Máy tính nhỏ đặt ngay trên UAV, xử lý tại chỗ thay vì gửi về máy chủ |
| trạm mặt đất | ground station | Máy tính của đội cứu hộ, nhận cảnh báo và hiện bản đồ |
| telemetry (dữ liệu bay) | telemetry | Vị trí GPS, độ cao, hướng của UAV theo thời gian |
| GSD | ground sampling distance | Số mét mặt đất ứng với một pixel; bay càng cao GSD càng lớn |
| AGL | above ground level | Độ cao so với mặt đất (mặt nước) ngay bên dưới |
| góc nhìn chéo, ngang, dọc | DFOV, HFOV, VFOV | Góc nhìn của camera theo đường chéo, chiều ngang, chiều dọc ảnh |
| nhìn thẳng xuống | nadir | Camera hướng thẳng đứng xuống đất |
| TensorRT | TensorRT | Công cụ của NVIDIA biên dịch mô hình để chạy nhanh trên GPU NVIDIA |
| FP16, INT8 | half precision, 8-bit integer | Tính bằng số thực 16 bit, số nguyên 8 bit thay cho 32 bit: nhanh hơn, có thể kém chính xác hơn |
| lượng tử hoá | quantization | Đổi mô hình sang số ít bit hơn (FP16, INT8) |
| backbone, neck, head | backbone, neck, head | Ba phần của mạng phát hiện: trích đặc trưng, trộn đặc trưng nhiều tầng, dự đoán box |
| tầng P2, P3, … | feature level, stride | Tầng đặc trưng có độ phân giải bằng 1/4, 1/8, … ảnh vào; số nhỏ thì thấy được vật nhỏ hơn |
| ByteTrack | ByteTrack | Thuật toán theo dõi đối tượng qua các khung, ghép box theo IoU |
| theo dõi đối tượng | object tracking | Gán cùng một mã cho cùng một đối tượng qua nhiều khung |
| bù chuyển động camera | camera motion compensation (CMC) | Trừ đi phần dịch chuyển do camera di chuyển trước khi ghép box giữa hai khung |
| Pareto | Pareto front | Các cấu hình không bị cấu hình nào khác hơn ở mọi tiêu chí (vừa nhanh hơn vừa chính xác hơn) |
| end-to-end (YOLO26) | end-to-end, NMS-free | Mô hình xuất thẳng kết quả cuối, không cần NMS |

## 2. Khái niệm có trong tài liệu khoa học, tên tiếng Việt do dự án đặt

Luôn kèm tên tiếng Anh khi gặp lần đầu, để hội đồng đối chiếu với tài liệu tham khảo.

| Dùng trong tài liệu | Tiếng Anh | Nghĩa | Ghi chú |
|---|---|---|---|
| cắt ô | tiling, slicing | Chia ảnh lớn thành các ô 640 px chồng nhau, phát hiện từng ô rồi gộp | SAHI là một thư viện làm việc này |
| lượt toàn ảnh | full-image pass | Thêm một lần phát hiện trên cả ảnh thu nhỏ, để bắt người to bị cắt đôi giữa các ô | |
| nhánh phát hiện P2 | P2 detection head | Thêm đầu ra ở tầng P2 để thấy vật rất nhỏ | Không viết "đầu dò P2" |
| thu nhỏ theo độ cao bay | altitude-aware rescaling | Dùng độ cao bay ước lượng người to bao nhiêu pixel, thu nhỏ khung về cỡ mô hình làm tốt nhất trước khi phát hiện | Gần với "scale matching" của TinyPerson, nhưng làm lúc chạy theo telemetry; là đóng góp của luận văn |
| tần số theo độ cao | altitude-adaptive frame rate | Đổi số khung xử lý mỗi giây theo độ cao và vận tốc, để mỗi người được nhìn đủ số lần | |
| xác nhận nhiều khung | multi-frame confirmation | Chỉ cảnh báo khi một người được thấy đủ N lần trong một khoảng thời gian | |
| xác nhận theo toạ độ mặt đất | geo-referenced confirmation | Đổi box sang toạ độ GPS rồi gom các lần thấy gần nhau trên mặt đất | Tuỳ chọn `geo`; là đóng góp của luận văn |
| xác nhận theo track | track-based confirmation | Đếm số lần thấy theo mã track của ByteTrack | Tuỳ chọn `bytetrack`, `bytetrack_cmc` |
| vùng bỏ qua | ignore region | Vùng trong ảnh mà box rơi vào không bị tính là báo nhầm (đám đông không gán được từng người) | |
| nhóm kích thước | size group | Chia người theo cạnh ngắn của box: dưới 8, 8–16, 16–32, trên 32 px | COCO chia khác (nhỏ là dưới 32×32); dự án chia mịn hơn vì người rất nhỏ |
| hàng đợi gửi (outbox) | transactional outbox | Lưu cảnh báo vào SQLite trên UAV trước, gửi khi có mạng, gửi lại khi lỗi | Thuật ngữ kỹ thuật phần mềm |
| sự cố | incident | Trạm mặt đất gộp nhiều cảnh báo về cùng một người (gần nhau) thành một sự cố | |
| giả lập thời gian thiết bị | device timing simulation | Pipeline chạy trên máy này nhưng tính thời gian xử lý theo hồ sơ của Jetson | Kết quả là ước lượng, không phải số đo |
| hồ sơ thiết bị | device profile | File ghi thời gian ước lượng mỗi ô, mỗi lượt toàn ảnh của một thiết bị (`configs/devices/`) | |
| rò rỉ dữ liệu | data leakage | Ảnh tập kiểm tra trùng hoặc gần trùng ảnh tập huấn luyện | |
| khoá tập test | test set freeze | Ghi mã băm ảnh và nhãn; sau đó không được sửa | |

## 3. Ký hiệu nội bộ

Chỉ dự án này dùng. Trong luận văn, bảng kết quả ghi tên mô tả; nếu cần mã ngắn thì định nghĩa trong một bảng ở chương thí nghiệm.

### Câu hỏi nghiên cứu

| Mã | Tên mô tả |
|---|---|
| RQ1 | Phát hiện người nhỏ chính xác tới đâu, kỹ thuật nào giúp được bao nhiêu |
| RQ2 | Chạy trên thiết bị biên nhanh tới đâu, đánh đổi bao nhiêu độ chính xác |
| RQ3 | Xác nhận và gửi cảnh báo: báo nhầm, bỏ sót, độ trễ ra sao; cách xác nhận nào chịu được sai số GPS và chuyển động camera |

### Thí nghiệm của câu hỏi 1

| Mã | Tên mô tả | Trạng thái (xem ROADMAP mục 4) |
|---|---|---|
| E0 | Mô hình nền YOLO26s, ảnh 640 px | Xong |
| E1 | Mô hình nền, ảnh 1280 px | Xong |
| E2 | Tinh chỉnh trên VisDrone | Xong |
| E2b | Tinh chỉnh trên VisDrone + C2A | Có cấu hình, không chạy |
| E2c | Tinh chỉnh trên VisDrone + AFO (người dưới nước) | Xong, mô hình chính |
| E2d | Như E2c, thêm HydroVigilance | Có cấu hình |
| E2e | Như E2c, thêm C2A (thêm người cỡ to) | Đang chạy trên Kaggle |
| E3 | Như E2c, thêm nhánh phát hiện P2 | Xong, không đáng chi phí |
| E4 | Mô hình chính + cắt ô (SAHI hoặc bộ cắt ô riêng `E4tiled`) | Xong trên VisDrone và SeaDronesSee |
| E5 | Như E2c nhưng dùng YOLO11s | Có cấu hình |
| E6 | Recall theo số pixel trên người (thu nhỏ ảnh nhiều mức) | Đã chạy thử |

### Bộ dữ liệu và tên viết tắt

| Ký hiệu | Nghĩa |
|---|---|
| VisDrone | Bộ ảnh drone đô thị (Trung Quốc), nhiều người rất nhỏ; không có nước |
| AFO | Aerial dataset of Floating Objects: người và vật nổi trên mặt nước nhìn từ drone |
| C2A | Ảnh thảm hoạ thật có ghép hình người; chỉ dùng để huấn luyện |
| HydroVigilance | Người bơi, đuối nước trên sông |
| SeaDronesSee, SDS | Người bơi trên hồ, có độ cao bay thật từ metadata drone |
| SDS-MOT, `sds_v21` | Phần video có mã track của SeaDronesSee; `v21` là đoạn val-m100-DJI_0001-v21 dùng cho đo tốc độ và demo |
| tập test lũ | 188 khung từ video lũ thật (YouTube và nguồn công khai), tự gán nhãn; tập chính để kết luận về cảnh lũ |

### Tên trong mã nguồn hay gặp trong tài liệu

| Ký hiệu | Nghĩa |
|---|---|
| `geo`, `bytetrack`, `bytetrack_cmc` | Ba cách xác nhận: theo toạ độ mặt đất; theo track; theo track có bù chuyển động camera |
| `--target-person-px` | Thu nhỏ theo độ cao bay: số pixel mong muốn của một người sau khi thu nhỏ |
| `--min-views` | Tần số theo độ cao: số lần muốn nhìn thấy mỗi người |
| `--device-profile` | Giả lập thời gian thiết bị biên |
| `--replay` | Phát lại phát hiện đã lưu thay vì chạy mô hình |
| N, cửa sổ, r | Số lần thấy để xác nhận; khoảng thời gian đếm; bán kính gom (m) |
