# Chương 1. Mở đầu

> **Ghi chú bản nháp (xoá khi đưa vào quyển).** Nháp 7/11/2026 theo `docs/DAN_Y_LUAN_VAN.md` mục chương 1. Nguồn: `docs/TONG_QUAN.md` mục 1, `docs/TECHNICAL.md` mục 1–2, `runs/gsd/m4t_diag82/gsd_table.csv` (bảng số pixel theo độ cao, sinh bằng `scripts/gsd_calc.py`). Cách trình bày câu hỏi con và luận điểm xuyên suốt (mục 1.3) và ba đóng góp (mục 1.4) là **đề xuất ngày 6/11, chờ cô duyệt** (quyết định #16); câu chữ của ba câu hỏi chính phải chép đúng đề cương đã nộp **[ĐỐI CHIẾU ĐỀ CƯƠNG]**. Bối cảnh thực tế (số người mắc kẹt, thiệt hại) cần trích nguồn chính thức **[CẦN NGUỒN]**, không dùng số ước lượng. Thuật ngữ theo `docs/THUAT_NGU.md`.

## 1.1. Bối cảnh

Khi lũ lớn, người mắc kẹt trên mái nhà, bám vào vật nổi hoặc lội trong nước, nhiều khi ở những nơi đội cứu hộ không nhìn thấy từ mặt đất. [CẦN NGUỒN: một hai sự kiện lũ gần đây ở Việt Nam, ví dụ bão Yagi 2024, với số liệu từ cơ quan chính thức.] Máy bay không người lái (UAV) quét được vùng rộng trong thời gian ngắn và đã được dùng trong tìm kiếm cứu nạn. Nhưng một chuyến bay sinh ra hàng chục phút video 4K, trong khi người vận hành vừa phải điều khiển, vừa phải xem màn hình nhỏ ngoài trời, vừa phải báo vị trí cho đội cứu hộ. Người trong video lại rất nhỏ: ở độ cao bay an toàn, một người chỉ chiếm vài chục pixel trên khung hình gần chín triệu pixel. Bỏ sót một người là bỏ sót một mạng sống.

Luận văn xây dựng một hệ thống **tự động phát hiện người trong video UAV, xác định toạ độ GPS của họ và gửi cảnh báo về trạm mặt đất**, chạy ngay trên máy tính nhúng gắn trên UAV. Đội cứu hộ nhận được trên bản đồ những điểm có người, kèm vùng cần tìm và ảnh cắt để xác nhận, thay vì phải xem lại toàn bộ video.

## 1.2. Ba ràng buộc

Ba ràng buộc của bài toán chi phối mọi lựa chọn thiết kế ở các chương sau.

**Người rất nhỏ trong ảnh.** Với camera góc nhìn 82° theo đường chéo (camera góc rộng của DJI Matrice 4T) và video 4K (3840 × 2160), một người rộng khoảng 0,5 m chiếm số pixel như Bảng 1.1. Khi thân đã ngập, chỉ còn đầu người (khoảng 0,2 m) nhô lên, còn nhỏ hơn.

**Bảng 1.1.** Kích thước người trên ảnh theo độ cao bay, camera 82° chéo, video 3840 px, nhìn thẳng xuống (`runs/gsd/m4t_diag82/gsd_table.csv`).

| Độ cao | Bề ngang vùng chụp | Một pixel trên mặt đất | Người (0,5 m) | Đầu người (0,2 m) | Người khi thu ảnh về 640 px |
|---|---|---|---|---|---|
| 30 m | 45,5 m | 1,18 cm | 42,2 px | 16,9 px | 7,0 px |
| 50 m | 75,8 m | 1,97 cm | 25,3 px | 10,1 px | 4,2 px |
| 80 m | 121,2 m | 3,16 cm | 15,8 px | 6,3 px | 2,6 px |
| 100 m | 151,5 m | 3,95 cm | 12,7 px | 5,1 px | 2,1 px |

Các mô hình phát hiện đối tượng phổ biến như YOLO thường thu ảnh về 640 px trước khi xử lý. Với video 4K, bước này chia kích thước đi sáu lần, và người ở 100 m chỉ còn khoảng 2 px (cột cuối), dưới ngưỡng mà mô hình nào cũng thấy được. Vì vậy hệ thống phải giữ độ phân giải gốc, bằng đầu vào lớn hơn hoặc bằng cách cắt ảnh thành ô.

**Thiết bị biên yếu.** Máy tính nhúng gắn được trên UAV (ví dụ dòng NVIDIA Jetson) có công suất dưới vài chục watt. Nó không chạy kịp mô hình trên 30 khung 4K mỗi giây; thực tế chỉ xử lý được vài khung mỗi giây. Câu hỏi đặt ra là vài khung mỗi giây có đủ không. Một người nằm trong vùng chụp trong một khoảng thời gian phụ thuộc độ cao và vận tốc bay: ở 50 m, bay 10 m/s, khoảng 4,3 giây, tức được nhìn tối đa 8 lần nếu xử lý 2 khung mỗi giây (TECHNICAL mục 2.4). Với mỗi lần nhìn mô hình chỉ thấy người với một xác suất nhất định, số lần nhìn này quyết định hệ thống có xác nhận được người hay không.

**Mạng chập chờn.** Vùng lũ thường mất điện và mất sóng di động; đường truyền từ UAV về trạm có thể mất gói, mất hẳn trong vài chục giây. Truyền video về trạm để xử lý là không khả thi. Hệ thống phải xử lý trên UAV và chỉ gửi những gói cảnh báo nhỏ, lưu lại khi mất sóng và gửi bù khi có sóng lại, không được để mất cảnh báo nào.

## 1.3. Câu hỏi nghiên cứu

Luận văn trả lời ba câu hỏi nghiên cứu theo đề cương **[ĐỐI CHIẾU ĐỀ CƯƠNG: chép đúng câu chữ]**:

**Câu hỏi 1 (độ chính xác).** Phát hiện người nhỏ trong ảnh UAV vùng lũ chính xác tới mức nào, và những kỹ thuật nào (độ phân giải đầu vào, cắt ô, tinh chỉnh, nhánh phát hiện P2, thu nhỏ theo độ cao bay) giúp được bao nhiêu, đặc biệt với người dưới 16 px?

**Câu hỏi 2 (tốc độ trên thiết bị biên).** Cấu hình nào đạt tần số xử lý cần thiết (khoảng 2 khung mỗi giây) mà giữ được recall cao nhất?

**Câu hỏi 3 (hệ thống).** Khi ghép phát hiện qua nhiều khung để xác nhận rồi gửi cảnh báo qua mạng chập chờn, hệ thống báo nhầm bao nhiêu, bỏ sót bao nhiêu, cảnh báo tới trạm sau bao lâu; cách xác nhận nào chịu được sai số GPS và chuyển động của camera?

Mỗi câu hỏi được tách thành các câu hỏi con đo được (Bảng 1.2).

**Bảng 1.2.** Câu hỏi con và phép đo trả lời.

| Mã | Câu hỏi con | Trả lời bằng |
|---|---|---|
| RQ1a | Người nhỏ tới đâu thì bị bỏ sót? | Recall theo nhóm cỡ người; khảo sát recall theo số pixel trên người |
| RQ1b | Dữ liệu huấn luyện nào giúp: ảnh UAV đô thị, người dưới nước, ảnh thảm hoạ ghép người? | So các mô hình tinh chỉnh trên cùng các tập đánh giá |
| RQ1c | Cắt ô và nhánh phát hiện P2 giúp người nhỏ bao nhiêu? | Có và không cắt ô; có và không nhánh P2 |
| RQ1d | Thu nhỏ khung theo độ cao bay giúp bao nhiêu? | Cắt ô có và không thu nhỏ trên ảnh 4K có độ cao bay thật |
| RQ1e | Nhiễu riêng của cảnh lũ (loá, vật trôi, nhoè, thời tiết) làm mô hình kém đi bao nhiêu? | Recall theo loại nhiễu trên tập ảnh lũ |
| RQ1f | Mô hình học trên ảnh đô thị và biển dùng được cho cảnh lũ tới đâu? | So cùng mô hình trên ảnh đô thị, biển và tập ảnh lũ |
| RQ2a | Nén mô hình (FP16, INT8) nhanh thêm bao nhiêu và mất bao nhiêu độ chính xác? | Đo trên GPU với TensorRT |
| RQ2b | Cấu hình nào không bị cấu hình khác vượt ở cả tốc độ lẫn độ chính xác? | Bảng recall theo tốc độ |
| RQ2c | Thiết bị yếu có theo kịp tần số cần thiết không; thu nhỏ theo độ cao giúp bao nhiêu? | Giả lập thời gian thiết bị, hiệu chỉnh từ số đo |
| RQ3a | Bao nhiêu khung mỗi giây là đủ, và thay đổi theo độ cao, vận tốc ra sao? | Mô phỏng chuyến bay |
| RQ3b | Gom theo toạ độ mặt đất hay theo dõi trên ảnh tốt hơn khi xử lý ít khung? | Video thật có telemetry và mô phỏng |
| RQ3c | Sai số GPS, độ cao, hướng làm vị trí cảnh báo lệch bao nhiêu? | Mô hình lan truyền sai số và mô phỏng |
| RQ3d | Mất sóng làm cảnh báo tới trễ bao lâu, có mất cảnh báo nào không? | Giả lập mạng |
| RQ3e | Gộp cảnh báo thành sự cố bớt được bao nhiêu cảnh báo lặp? | Gộp ở trạm trên video thật |

Ba câu hỏi có chung một **luận điểm xuyên suốt**: dữ liệu bay sẵn có của UAV (độ cao, GPS, hướng) giúp ở cả ba khâu, chọn cỡ ảnh khi phát hiện (RQ1d), giảm khối lượng tính để máy yếu theo kịp (RQ2c), và xác nhận người khi chỉ xử lý vài khung mỗi giây (RQ3b). Đây không phải câu hỏi thứ tư mà là sợi chỉ nối ba câu hỏi; chương 5, mục 5.4 tổng hợp nó.

## 1.4. Đóng góp

1. **Tập đánh giá ảnh lũ từ UAV và cách đánh giá theo cỡ người.** Chưa có bộ dữ liệu công khai nào gồm ảnh UAV chụp lũ thật có nhãn người. Luận văn tự gán nhãn 188 khung từ 9 nguồn video, rà trùng ảnh với mọi dữ liệu huấn luyện và khoá bằng mã băm trước khi chạy mô hình; mọi kết quả được chia theo nhóm cỡ người (dưới 8, 8–16, 16–32, trên 32 px), khoảng tin cậy lấy mẫu theo video. Tập nhỏ là giới hạn được ghi rõ.
2. **Thu nhỏ khung theo độ cao bay.** Dùng độ cao trong telemetry ước lượng người sẽ to bao nhiêu pixel, rồi thu nhỏ khung trước khi phát hiện: vừa đưa người về cỡ mô hình làm tốt, vừa giảm số ô phải tính trên máy yếu. Đánh giá trên ảnh 4K có độ cao bay thật (SeaDronesSee) và trong mô phỏng; video lũ công khai không có độ cao nên không đánh giá được trên tập ảnh lũ.
3. **Xác nhận theo toạ độ mặt đất khi xử lý ít khung.** Chỉ ra vì sao phương pháp theo dõi đối tượng thông dụng (ByteTrack) gãy khi UAV bay nhanh và chỉ xử lý vài khung mỗi giây, vì sao bù chuyển động camera bằng telemetry chỉ cứu được khi GPS rất ổn định giữa hai khung, và đề xuất gom các phát hiện theo vị trí trên mặt đất để xác nhận người.

Ngoài ba đóng góp, luận văn hiện thực hoá một **hệ thống hoàn chỉnh** từ video tới cảnh báo trên bản đồ: phát hiện, định vị, xác nhận, hàng đợi gửi chịu mất sóng, trạm mặt đất gộp sự cố và xếp ưu tiên, công cụ cho đội cứu hộ; kèm các công cụ giả lập chuyến bay, mạng và thời gian thiết bị biên dùng để đánh giá. Mã nguồn mở, có kiểm thử tự động.

## 1.5. Phạm vi và giới hạn

- Đối tượng là **người** trong ảnh màu (RGB) từ UAV nhìn gần thẳng xuống; không xét ảnh nhiệt, không phân biệt tư thế hay mức độ nguy cấp.
- Không có chuyến bay thật trên vùng lũ và không có thiết bị Jetson: khâu phát hiện được đánh giá trên ảnh có nhãn (đô thị, biển, tập ảnh lũ tự gán); tốc độ đo trên GPU T4 và chỉ so sánh tương đối, thiết bị yếu chỉ ước lượng; phần xác nhận, định vị và gửi được đánh giá trên video biển có telemetry thật và trong mô phỏng. Mọi kết quả mô phỏng hay ước lượng được ghi nhãn như vậy.
- Phần lớn thí nghiệm huấn luyện chạy một lần (một seed) do giới hạn giờ GPU.

## 1.6. Bố cục luận văn

Chương 2 trình bày cơ sở lý thuyết và các nghiên cứu liên quan: phát hiện đối tượng và YOLO, phát hiện vật nhỏ, dữ liệu ảnh UAV, theo dõi đối tượng, nén mô hình cho thiết bị biên, và khoảng trống mà luận văn nhắm tới. Chương 3 mô tả phương pháp: kiến trúc hệ thống, hình học camera và định vị, khâu phát hiện, hai đóng góp phương pháp, khâu gửi cảnh báo và trạm mặt đất, cùng các công cụ giả lập. Chương 4 mô tả dữ liệu, tập ảnh lũ tự gán nhãn, cách đo và các thí nghiệm. Chương 5 trình bày kết quả theo ba câu hỏi nghiên cứu, luận điểm xuyên suốt và phân tích lỗi. Chương 6 kết luận, nêu giới hạn và hướng phát triển.
