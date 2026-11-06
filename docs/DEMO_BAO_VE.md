# Kịch bản demo bảo vệ (15/12/2026)

Mục tiêu: hội đồng thấy bài toán khó ở đâu, hệ thống chạy trọn từ UAV tới trạm mặt đất, và mọi thứ trên màn hình kiểm chứng được. Khoảng 6 phút. Lệnh và cấu hình: README (mục Demo bảo vệ), TECHNICAL mục 14.6.

## Chuẩn bị (trước hôm bảo vệ)

| Việc | Lệnh hoặc cách làm |
|---|---|
| Phát hiện cho mọi khung (một lần, cần GPU) | `scripts/demo_bao_ve.sh chuan-bi sds_v21_goc` và `... chuan-bi sds_v21_px10` |
| Chuyến quét mô phỏng (một lần, không cần GPU, khoảng 20 giây) | `scripts/demo_bao_ve.sh chuan-bi hotay_quet` |
| Sân thử cho phần hỏi đáp | Mở `python -m console`, tab Sân thử; chạy trước mặc định và hai câu hỏi hay gặp để bảng so sánh có sẵn vài dòng; diễn tập một lần bấm câu hỏi rồi Chạy với tốc độ phát 0 (khoảng 15 giây) |
| Lớp đáp án | `chuan-bi` tự sinh `truth_layer.json` (nhãn SDS hoặc đáp án mô phỏng), `chay` tự nạp vào trạm; nếu đã chạy `chuan-bi` SDS trước 6/11 thì chạy `tools/make_truth_layer.py --sds ...` (lệnh trong README) |
| Hiệu chỉnh hồ sơ thiết bị sau RQ2 | `tools/fit_device_profile.py` (TECHNICAL 14.6); khi còn `calibrated: false` thì nói rõ là ước lượng chưa hiệu chỉnh |
| Giữ ô bản đồ vùng bay | Diễn tập ít nhất một lần **khi có mạng**, phóng to thu nhỏ quanh vùng bay; ô đã xem nằm trong `runs/ground/tiles` |
| Video so sánh cho slide | `scripts/demo_bao_ve.sh so-sanh sds_v21_goc agx_orin_64gb orin_nano_super`; thêm một lần Orin Nano với `sds_v21_px10` |
| Video dự phòng toàn bộ demo | Quay màn hình một lần chạy `chay`, nhúng vào slide |
| Máy chiếu | Thử độ phân giải thật; phóng to trình duyệt để chữ đọc được từ cuối phòng |
| Mở sẵn trước khi lên | Terminal đã gõ sẵn lệnh `chay`; trình duyệt mở link màn hình điều phối nó in ra (`http://localhost:8000/?video=http://localhost:8001/`), toàn màn hình (F11); slide ở trang demo |

## Kịch bản

| Thời gian | Nội dung | Nói gì |
|---|---|---|
| 0:00–0:45 | Một khung lũ 4K, chưa có khung phát hiện. Hỏi: "Thầy cô thấy bao nhiêu người?". Chờ vài giây, phóng to, rồi hiện khung | Người chỉ vài chục pixel trên ảnh 4K; đó là lý do cần cắt ô và fine-tune |
| 0:45–2:00 | Trước và sau fine-tune trên cùng khung (`runs/edge/demo_truoc_sau.jpg` hoặc khung mới), một hai con số RQ1 từ `docs/results/` | Chỉ dùng số có trong `docs/results/`, đúng mô hình E2c như trong quyển |
| 2:00–4:00 | `scripts/demo_bao_ve.sh chay sds_v21_goc orin_nano_super 20 30`: một trang điều phối, video trên drone bên trái, bản đồ ở giữa, sự cố bên phải. Chỉ vào drone trên bản đồ và vùng camera đang nhìn; sự cố hiện dần kèm ảnh cắt, bấm một sự cố xem vùng tìm 95%. Giây 20–30: drone trên bản đồ chuyển xám, banner "mất liên lạc", thẻ drone hiện thanh cam "còn kẹt trên drone" tăng dần; có sóng lại thì thanh chuyển xanh, sự cố bị kẹt hiện ra một loạt. Hết chuyến, bấm **"Đối chiếu đáp án"**: người thật hiện lên, xanh đặc là được cảnh báo riêng, vòng xanh là nằm trong vùng tìm (bị gộp với người gần), đỏ là bỏ sót, sự cố báo nhầm có viền đỏ | Telemetry thật của drone (SeaDronesSee), không phải giả lập. Drone không gửi video, chỉ toạ độ, ảnh cắt nhỏ và trạng thái mỗi giây; outbox giữ cảnh báo khi mất sóng, gửi lại không trùng |
| 4:00–4:45 | `scripts/demo_bao_ve.sh chay hotay_quet orin_nano_super 60 80`, phát nhanh gấp đôi: chuyến bay **mô phỏng** quét luống cày bốn đường 300 m ở 50 m. Vùng đã quét lớn dần; giữa chuyến mất sóng 20 s, sau đó cảnh báo kẹt và đoạn đường bay bị lỡ được gửi bù, vùng đã quét liền lại; hết chuyến bản đồ thu về cả vùng | Nói ngay đầu: đây là **mô phỏng**, ảnh tổng hợp và phát hiện giả theo recall đo được của mô hình, để minh hoạ khâu hệ thống; số liệu thật nằm ở phần video SDS và chương 5. Ý chính cho đội cứu hộ: biết chỗ nào đã quét mà không có ai |
| (trong 4:00–4:45, khi hết chuyến) | Bấm "Đặt vị trí thuyền" rồi bấm mép vùng quét, bấm "Gợi ý thứ tự đi cứu": đường đánh số qua mọi sự cố, tổng quãng đường và thời gian; mở một sự cố, "Đường từ thuyền" hiện khoảng cách và hướng; nút "Tải GPX" | Người vận hành không cần đọc toạ độ: thuyền biết đi đâu, theo thứ tự nào; GPX nạp vào máy định vị. Thứ tự là gợi ý đơn giản (ưu tiên trước, gần trước), theo đường thẳng |
| 4:45–5:15 | Video so sánh: AGX Orin theo kịp 8 khung/giây; Orin Nano Super ở 4K chỉ khoảng một nửa và bỏ khung; Orin Nano với thu nhỏ theo độ cao theo kịp | Thời gian thiết bị là **ước lượng** từ số công bố (TECHNICAL 14.6), không phải đo trên Jetson. Thu nhỏ theo độ cao giảm 32 ô xuống 6 ô mỗi khung |
| 5:15–6:00 | Một trường hợp sai: người bị bỏ sót hoặc báo nhầm (vật nổi, loá), giải thích vì sao | Chủ động nói giới hạn trước khi bị hỏi |

## Điều không nói

- Không nói "chạy thời gian thực trên Jetson". Nói "với độ trễ ước lượng của Orin Nano Super, pipeline đạt X khung/giây".
- Không đưa số nào không có trong `docs/results/` hoặc không đọc được từ `runs/`.
- Không nói video demo là tập test lũ: đoạn SDS v21 thuộc tập val của SeaDronesSee.
- Không trình bày chuyến quét Hồ Tây như số liệu: ảnh tổng hợp, telemetry mô phỏng, phát hiện giả; toạ độ đặt trên Hồ Tây chỉ để bản đồ nền là mặt nước.

## Trả lời câu hỏi "nếu… thì sao" ngay tại chỗ

Khi hội đồng hỏi về điều kiện khác (bay cao hơn, mô hình chưa tinh chỉnh, mất sóng lâu, GPS kém, thiết bị yếu, bay nhanh), mở tab **Sân thử**, bấm câu hỏi tương ứng (hoặc chỉnh tham số), đặt tốc độ phát 0 để chạy nhanh, bấm Chạy, rồi so dòng mới với dòng mặc định trong bảng. Nói rõ: mô phỏng, một seed, phát hiện giả theo recall đo được; số chính thức nhiều seed ở `docs/results/` (`rq3_*.md`).

## Câu hỏi dễ gặp

| Câu hỏi | Trả lời ngắn | Tài liệu |
|---|---|---|
| Không có Jetson thì sao nói là thiết bị biên? | Đo tương đối trên T4 (RQ2); thời gian Jetson ước lượng từ cùng một bảng benchmark công bố, ghi rõ giả định và đặt ở bảng riêng | TECHNICAL 14.4, 14.6 |
| Ba câu hỏi nghiên cứu có ít không? | Ba câu là mức thường gặp ở luận văn thạc sĩ; mỗi câu chia thành các câu hỏi con đo được (14 câu), nối bằng luận điểm dữ liệu bay giúp cả ba khâu | TONG_QUAN 1.3 |
| Tập test lũ 188 khung có đủ không? | Khoảng tin cậy bootstrap theo video, 9 cụm; khoảng rộng, đã ghi là giới hạn | `docs/results/flood_truoc_khoa.md`, TECHNICAL 15.3 |
| Telemetry trong demo là thật hay giả? | Thật (metadata drone SeaDronesSee); video lũ YouTube không có telemetry, nên thu nhỏ theo độ cao chỉ đánh giá trên SDS | ROADMAP quyết định #13 |
| Vì sao không dùng ByteTrack? | Ở 2 khung/giây box hai khung liền nhau gần như không chồng nhau; gom theo vị trí mặt đất xác nhận được nhiều người hơn trên video thật | `docs/results/sds_mot_confirm.md` |
| Sao có nhiều cảnh báo lặp? | GPS drone trôi làm một người tách thành nhiều cụm; trạm gộp thành sự cố | `docs/results/alert_memory.md` |
| Sao không dùng video SeaDronesSee có drone bay xa cho phần quét vùng? | Các đoạn drone di chuyển của SeaDronesSee đều quay với camera nghiêng 20–78°, trong khi phép chiếu giả định nhìn thẳng xuống; đoạn nhìn thẳng xuống (v21) thì drone gần như đứng yên. Nên phần quét vùng dùng mô phỏng | `sim/render.py`, TECHNICAL 11.3 |
| Số "cảnh báo riêng" trên màn hình khác bảng kết quả? | Màn hình là minh hoạ trực tiếp: đếm theo sự cố đã gộp ở trạm, với thiết bị giả lập (số khung khác). Số chính thức đếm theo cảnh báo trong không gian ảnh bằng `eval/` (`sds_mot_confirm.md`). Khoảng cách giữa "cảnh báo riêng" và "trong vùng tìm" là do người bơi sát nhau bị gộp thành một sự cố: đội cứu hộ tới vùng đó vẫn gặp cả nhóm | TECHNICAL 12.6 |
| Hình chữ nhật đen trong video? | Có sẵn trong ảnh gốc của SeaDronesSee, không phải do hệ thống | |
| Mất mạng thì bản đồ? | Leaflet đóng gói sẵn, ô bản đồ đã xem được giữ trên đĩa | TECHNICAL 12.5 |
