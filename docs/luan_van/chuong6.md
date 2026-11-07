# Chương 6. Kết luận

> **Ghi chú bản nháp (xoá khi đưa vào quyển).** Khung 8/11/2026 theo `docs/DAN_Y_LUAN_VAN.md` mục chương 6. Chương này **không đưa số mới**: mỗi câu trả lời tóm từ chương 5, số (nếu có) chép từ bảng của chương 5 kèm số bảng. Chỗ **[CHỜ KHOÁ]** điền sau khi chấm tập ảnh lũ (11–13/11), **[CHỜ RQ2]** sau khi có kết quả đo tốc độ trên T4, **[CHỜ #19]** theo quyết định về cách viết đóng góp. Viết lại toàn chương sau khi chương 5 đủ.

## 6.1. Trả lời các câu hỏi nghiên cứu

**Câu hỏi 1: phát hiện người nhỏ trong ảnh UAV vùng lũ chính xác tới mức nào, kỹ thuật nào giúp được bao nhiêu.**

Dữ liệu huấn luyện quyết định nhiều nhất. Tinh chỉnh trên ảnh UAV đô thị (VisDrone) nâng mạnh khả năng thấy người nhỏ; thêm ảnh người dưới nước (AFO) giữ được người bơi mà không mất nhiều ở người nhỏ; trộn thẳng ảnh thảm hoạ ghép người cỡ to (C2A) làm mất người nhỏ (chương 5, mục 5.1.2). Trên ảnh độ phân giải vừa, thay đổi kiến trúc (tầng P2) và cắt ô giúp rất ít so với dữ liệu (mục 5.1.3). Mô hình tinh chỉnh cho người nhỏ lại yếu với người to; trên ảnh 4K có độ cao bay thật, thu nhỏ khung theo độ cao bù được điểm yếu này (mục 5.1.4). Dưới khoảng 6–8 px, không mô hình nào trong luận văn thấy người một cách đáng tin; đây là giới hạn dưới của khâu phát hiện, và cách chữa còn lại là bay thấp hơn. [CHỜ KHOÁ] Mức chính xác trên tập ảnh lũ theo nhóm cỡ người, ảnh hưởng của nhiễu riêng cảnh lũ, và mức chuyển được từ ảnh đô thị, biển sang cảnh lũ (mục 5.1.1, 5.1.5, 5.1.6).

**Câu hỏi 2: cấu hình nào đạt tần số xử lý cần thiết mà giữ recall cao nhất.**

[CHỜ RQ2] Mức nhanh thêm và mức mất độ chính xác của FP16, INT8 so với PyTorch, nhất là ở người nhỏ; cấu hình không bị cấu hình nào khác vượt ở cả tốc độ lẫn recall; thiết bị yếu có theo kịp tần số cần thiết (mục 5.3.1) không, và thu nhỏ theo độ cao giảm khối lượng tính bao nhiêu (ước lượng bằng giả lập thời gian thiết bị).

**Câu hỏi 3: hệ thống báo nhầm, bỏ sót bao nhiêu, cảnh báo tới trạm sau bao lâu; cách xác nhận nào chịu được sai số GPS và chuyển động camera.**

Khi chỉ xử lý vài khung mỗi giây, gom phát hiện theo toạ độ mặt đất bền hơn theo dõi trên ảnh, cả trên ba đoạn video thật có telemetry lẫn trong mô phỏng có nhiễu GPS; bù chuyển động camera bằng telemetry chỉ cứu được theo dõi trên ảnh khi GPS rất ổn định giữa hai khung (mục 5.3.2). Không có một tần số đủ cho mọi độ cao; tính tần số từ độ cao và vận tốc giảm bỏ sót khi bay thấp và giảm tính toán khi bay cao (mục 5.3.1). Vùng tìm 95% chứa người thật khi GPS không tệ hơn giả định; lấy độ chính xác GPS do bộ thu báo giữ được điều đó khi GPS kém đi giữa chuyến, và tự hiệu chỉnh lệch la bàn giảm tách nhầm khi bay cao (mục 5.3.3, mô phỏng). Hàng đợi gửi kèm thăm dò đường truyền không làm mất cảnh báo nào trong mọi kịch bản mất gói, mất sóng, kể cả mất theo cụm; phần trễ còn lại là chính độ dài khoảng mất sóng (mục 5.3.4, mô phỏng). Gộp ở trạm giảm cảnh báo lặp mà không bỏ cảnh báo nào (mục 5.3.5). Phần lớn kết quả câu hỏi 3 là mô phỏng; phần trên video thật dựa vào ba đoạn SeaDronesSee.

**Luận điểm xuyên suốt.** [Viết sau mục 5.4.] Dữ liệu bay sẵn có của UAV giúp ở cả ba khâu: chọn cỡ ảnh khi phát hiện, giảm khối lượng tính để máy yếu theo kịp [CHỜ RQ2], và xác nhận người khi chỉ xử lý vài khung mỗi giây.

## 6.2. Đóng góp

[CHỜ #19: viết theo cách trình bày cô duyệt; bản hiện tại theo chương 1, mục 1.4.]

1. Tập đánh giá ảnh lũ từ UAV tự gán nhãn và cách đánh giá theo cỡ người, khoảng tin cậy theo video. [CHỜ KHOÁ] số khung, số người, phân bố cỡ.
2. Thu nhỏ khung theo độ cao bay trong pipeline thiết bị biên, đo cùng lúc độ chính xác theo cỡ người và khối lượng tính (hướng đã có công trình trước, chương 2, mục 2.2).
3. Phân tích và đo xác nhận theo toạ độ mặt đất so với theo dõi trên ảnh khi xử lý ít khung, cho bài toán cứu nạn.

Kèm theo: hệ thống hoàn chỉnh từ video tới bản đồ, các công cụ giả lập chuyến bay, mạng và thời gian thiết bị, mã nguồn mở có kiểm thử.

## 6.3. Giới hạn

- **Dữ liệu lũ nhỏ.** Tập ảnh lũ có 188 khung từ 9 nguồn, khoảng tin cậy theo nguồn nên rộng; video lũ công khai không có độ cao bay, nên thu nhỏ theo độ cao không đánh giá được trên cảnh lũ.
- **Không bay thật, không có thiết bị biên.** Tốc độ đo trên GPU T4 và chỉ so tương đối; thiết bị yếu là ước lượng từ giả lập. Khâu xác nhận, định vị, gửi phần lớn đánh giá bằng mô phỏng; phần trên video thật gồm ba đoạn biển, drone gần như đứng yên hoặc camera nghiêng.
- **Mô phỏng có thể bỏ qua đúng hiện tượng quyết định kết quả.** Ví dụ ở mục 5.3.5: cách đếm người theo nhóm tốt hơn trong mô phỏng nhưng kém hơn trên video thật, vì mô phỏng không có hiện tượng một người tách thành nhiều cụm khi GPS trôi.
- **Một seed** cho phần lớn thí nghiệm huấn luyện; không có đối chứng đời mô hình (thí nghiệm YOLO11 bị cắt).
- **Giả định hình học:** camera nhìn thẳng xuống, mặt nước phẳng, ống kính không méo; phép chiếu theo góc gimbal đã có nhưng chưa ổn định hơn trên video thật.
- **Giấy phép dữ liệu:** video lũ có bản quyền nên chỉ công bố nhãn và nguồn; giấy phép của AFO cần kiểm tra lại trước khi phát hành mô hình.

## 6.4. Hướng phát triển

- Đo trên thiết bị Jetson thật, gồm điện năng và giảm xung khi nóng; hiệu chỉnh lại giả lập thời gian thiết bị bằng số đo đó.
- Mở rộng tập ảnh lũ, nhất là video có telemetry để đánh giá thu nhỏ theo độ cao trên cảnh lũ.
- Thử đầu ra một-một không cần NMS của YOLO26 để giảm thời gian mỗi khung (`CAI_TIEN.md`).
- Ảnh nhiệt kết hợp ảnh màu cho ban đêm và người bị che khuất.
- Nhiều UAV phối hợp, chia vùng quét; xếp ưu tiên sự cố theo mức nguy cấp.
- Các mục "Đề xuất" còn lại của `docs/CAI_TIEN.md` (ví dụ bỏ qua ô không thay đổi khi UAV gần đứng yên, đọc độ chính xác GPS từ log bay thật).
