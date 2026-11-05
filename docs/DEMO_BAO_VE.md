# Kịch bản demo bảo vệ (15/12/2026)

Mục tiêu: hội đồng thấy bài toán khó ở đâu, hệ thống chạy trọn từ UAV tới trạm mặt đất, và mọi thứ trên màn hình kiểm chứng được. Khoảng 6 phút. Lệnh và cấu hình: README (mục Demo bảo vệ), TECHNICAL mục 14.6.

## Chuẩn bị (trước hôm bảo vệ)

| Việc | Lệnh hoặc cách làm |
|---|---|
| Phát hiện cho mọi khung (một lần, cần GPU) | `scripts/demo_bao_ve.sh chuan-bi sds_v21_goc` và `... chuan-bi sds_v21_px10` |
| Hiệu chỉnh hồ sơ thiết bị sau RQ2 | `tools/fit_device_profile.py` (TECHNICAL 14.6); khi còn `calibrated: false` thì nói rõ là ước lượng chưa hiệu chỉnh |
| Giữ ô bản đồ vùng bay | Diễn tập ít nhất một lần **khi có mạng**, phóng to thu nhỏ quanh vùng bay; ô đã xem nằm trong `runs/ground/tiles` |
| Video so sánh cho slide | `scripts/demo_bao_ve.sh so-sanh sds_v21_goc agx_orin_64gb orin_nano_super`; thêm một lần Orin Nano với `sds_v21_px10` |
| Video dự phòng toàn bộ demo | Quay màn hình một lần chạy `chay`, nhúng vào slide |
| Máy chiếu | Thử độ phân giải thật; phóng to trình duyệt để chữ đọc được từ cuối phòng |
| Mở sẵn trước khi lên | Trình duyệt ở `http://localhost:8000`, terminal đã gõ sẵn lệnh `chay`, slide ở trang demo |

## Kịch bản

| Thời gian | Nội dung | Nói gì |
|---|---|---|
| 0:00–0:45 | Một khung lũ 4K, chưa có khung phát hiện. Hỏi: "Thầy cô thấy bao nhiêu người?". Chờ vài giây, phóng to, rồi hiện khung | Người chỉ vài chục pixel trên ảnh 4K; đó là lý do cần cắt ô và fine-tune |
| 0:45–2:00 | Trước và sau fine-tune trên cùng khung (`runs/edge/demo_truoc_sau.jpg` hoặc khung mới), một hai con số RQ1 từ `docs/results/` | Chỉ dùng số có trong `docs/results/`, đúng mô hình E2c như trong quyển |
| 2:00–4:00 | `scripts/demo_bao_ve.sh chay sds_v21_goc orin_nano_super 20 30`: video bên trái, bản đồ bên phải. Cảnh báo hiện dần, bấm một sự cố xem ảnh cắt và bán kính sai số. Giây 20–30 có banner mất sóng; sau đó cảnh báo được gửi bù | Telemetry thật của drone (SeaDronesSee), không phải giả lập. Outbox giữ cảnh báo khi mất sóng, gửi lại không trùng |
| 4:00–5:15 | Video so sánh: AGX Orin theo kịp 8 khung/giây; Orin Nano Super ở 4K chỉ khoảng một nửa và bỏ khung; Orin Nano với thu nhỏ theo độ cao theo kịp | Thời gian thiết bị là **ước lượng** từ số công bố (TECHNICAL 14.6), không phải đo trên Jetson. Thu nhỏ theo độ cao giảm 32 ô xuống 6 ô mỗi khung |
| 5:15–6:00 | Một trường hợp sai: người bị bỏ sót hoặc báo nhầm (vật nổi, loá), giải thích vì sao | Chủ động nói giới hạn trước khi bị hỏi |

## Điều không nói

- Không nói "chạy thời gian thực trên Jetson". Nói "với độ trễ ước lượng của Orin Nano Super, pipeline đạt X khung/giây".
- Không đưa số nào không có trong `docs/results/` hoặc không đọc được từ `runs/`.
- Không nói video demo là tập test lũ: đoạn SDS v21 thuộc tập val của SeaDronesSee.

## Câu hỏi dễ gặp

| Câu hỏi | Trả lời ngắn | Tài liệu |
|---|---|---|
| Không có Jetson thì sao nói là thiết bị biên? | Đo tương đối trên T4 (RQ2); thời gian Jetson ước lượng từ cùng một bảng benchmark công bố, ghi rõ giả định và đặt ở bảng riêng | TECHNICAL 14.4, 14.6 |
| Ba câu hỏi nghiên cứu có ít không? | Ba câu là mức thường gặp ở luận văn thạc sĩ; mỗi câu chia thành các câu hỏi con đo được (14 câu), nối bằng luận điểm dữ liệu bay giúp cả ba khâu | TONG_QUAN 1.3 |
| Tập test lũ 188 khung có đủ không? | Khoảng tin cậy bootstrap theo video, 9 cụm; khoảng rộng, đã ghi là giới hạn | `docs/results/flood_truoc_khoa.md`, TECHNICAL 15.3 |
| Telemetry trong demo là thật hay giả? | Thật (metadata drone SeaDronesSee); video lũ YouTube không có telemetry, nên thu nhỏ theo độ cao chỉ đánh giá trên SDS | ROADMAP quyết định #13 |
| Vì sao không dùng ByteTrack? | Ở 2 khung/giây box hai khung liền nhau gần như không chồng nhau; gom theo vị trí mặt đất xác nhận được nhiều người hơn trên video thật | `docs/results/sds_mot_confirm.md` |
| Sao có nhiều cảnh báo lặp? | GPS drone trôi làm một người tách thành nhiều cụm; trạm gộp thành sự cố | `docs/results/alert_memory.md` |
| Hình chữ nhật đen trong video? | Có sẵn trong ảnh gốc của SeaDronesSee, không phải do hệ thống | |
| Mất mạng thì bản đồ? | Leaflet đóng gói sẵn, ô bản đồ đã xem được giữ trên đĩa | TECHNICAL 12.5 |
