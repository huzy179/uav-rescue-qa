# Kịch bản demo bảo vệ (15/12/2026)

Mục tiêu: trong khoảng 6 phút, hội đồng thấy ba điều:
- bài toán khó ở đâu (người chỉ vài pixel trong cảnh lũ);
- hệ thống chạy trọn từ UAV tới đội cứu hộ;
- mọi thứ trên màn hình đều kiểm chứng được.

Lệnh và cấu hình: README (mục Demo bảo vệ), TECHNICAL mục 14.6.

## Nguyên tắc

1. **Thật trước, mô phỏng sau, và nói rõ cái nào là cái nào.** Ảnh lũ và video SeaDronesSee là dữ liệu thật. Thời gian Jetson là ước lượng. Chuyến quét Hồ Tây là mô phỏng.
2. **Mỗi con số trên màn hình có nguồn** trong `docs/results/` hoặc `runs/`.
3. **Khung ảnh được chọn theo quy tắc ghi trước, không chọn khung đẹp** (mục "Quy tắc chọn khung"). Phải có ít nhất một khung mô hình làm sai.
4. **Không phụ thuộc mạng, GPU hay một lần chạy trực tiếp.** Phần trực tiếp là phát lại phát hiện đã tính sẵn. Mọi phần đều có video hoặc ảnh dự phòng trong slide.

## Mạch chuyện: ba câu hỏi, một sợi chỉ

Demo đi theo đúng thứ tự ba câu hỏi nghiên cứu, mỗi câu một màn hình:

| Câu hỏi | Màn hình | Ý chính |
|---|---|---|
| Phát hiện | Ảnh lũ: mô hình gốc và mô hình đã tinh chỉnh trên cùng khung | Tinh chỉnh và cắt ô thấy được người vài pixel |
| Tốc độ trên thiết bị | Video hai thiết bị (hoặc hai cấu hình) cạnh nhau | Thiết bị yếu chỉ xử lý được vài khung mỗi giây; biết chỗ chậm nằm ở đâu |
| Xác nhận và gửi | Màn hình điều phối chạy trực tiếp | Với vài khung mỗi giây, vẫn xác nhận được người và đưa vị trí tới đội cứu hộ, kể cả khi mất sóng |

Sợi chỉ nối ba màn hình là **dữ liệu bay** (độ cao, GPS). Nó quyết định thu nhỏ khung bao nhiêu, xử lý bao nhiêu khung mỗi giây, và đặt người lên bản đồ ở đâu.

## Kịch bản

| Thời gian | Màn hình | Nói gì |
|---|---|---|
| 0:00–0:40 | **Mở đầu.** Một khung lũ thật, chưa có đánh dấu (khung `nho_nhat`, xem quy tắc chọn khung). Hỏi: "Thầy cô thấy bao nhiêu người?" Chờ vài giây, rồi chuyển sang ảnh đáp án phóng to (`*_phong_to.png`) | Người chỉ vài chục pixel trên ảnh; đội cứu hộ xem video trực tiếp cũng bỏ sót như vậy |
| 0:40–1:40 | **Câu hỏi 1.** Ảnh so sánh khung `tieu_bieu`: trái là mô hình gốc, phải là E2c. Vòng xanh là thấy, đỏ là bỏ sót, vàng là báo nhầm. Kèm một hai con số trên tập lũ (recall theo cỡ người, khoảng tin cậy) | Khung này được chọn vì recall của nó gần recall chung nhất, tức là khung bình thường chứ không phải khung đẹp. Số chính thức trên toàn tập lũ ở chương 5 |
| 1:40–2:30 | **Câu hỏi 2.** Video `so_sanh_nano_goc_px10.mp4`: cùng Orin Nano Super (giả lập), trái là khung 4K gốc, phải là thu nhỏ theo độ cao | Thời gian Jetson là **ước lượng** từ số đo T4 nhân tỉ lệ công bố. Thu nhỏ theo độ cao giảm số ô mỗi khung từ 32 xuống 6. Theo ước lượng, Nano xử lý được 2,52 khung/giây ở khung gốc và 3,76 khung/giây khi thu nhỏ, vẫn dưới mức 8 khung/giây cần khi bay thấp. Chỗ chậm là bước thu nhỏ khung trên CPU; đã đưa lên GPU (trên máy cá nhân 21,34 → 5,39 ms mỗi khung, `gpu_resize.md`) nhưng chưa đo trên thiết bị biên. Nói giới hạn này trước khi bị hỏi |
| 2:30–4:30 | **Câu hỏi 3, trực tiếp.** `scripts/demo_bao_ve.sh chay sds_v21_goc orin_nano_super 20 30`. Một trang điều phối: video trên drone bên trái, bản đồ ở giữa, sự cố bên phải. Chỉ vào drone trên bản đồ và vùng camera đang nhìn; sự cố hiện dần kèm ảnh cắt; bấm một sự cố xem vùng tìm 95%. Giây 20–30 mất sóng: drone chuyển xám, banner "mất liên lạc", thanh cam "còn kẹt trên drone" tăng dần; có sóng lại thì sự cố bị kẹt hiện ra một loạt. Hết chuyến, bấm **"Đối chiếu đáp án"**: xanh đặc là cảnh báo riêng, vòng xanh là nằm trong vùng tìm, đỏ là bỏ sót, viền đỏ là báo nhầm | Telemetry thật của drone (SeaDronesSee), không phải giả lập; thiết bị là Orin Nano Super giả lập, nên chỉ vài khung mỗi giây được xử lý mà vẫn xác nhận được người. Drone không gửi video, chỉ toạ độ, ảnh cắt nhỏ và trạng thái mỗi giây; outbox giữ cảnh báo khi mất sóng, gửi lại không trùng |
| 4:30–5:15 | **Đội cứu hộ dùng thế nào.** Bấm "Đặt vị trí thuyền", "Gợi ý thứ tự đi cứu"; mở một sự cố xem "Đường từ thuyền"; nút "Tải GPX" | Người vận hành không cần đọc toạ độ. Thứ tự là gợi ý đơn giản (ưu tiên trước, gần trước), theo đường thẳng |
| 5:15–6:00 | **Một trường hợp sai.** Ảnh so sánh khung `loi` (khung E2c bỏ sót nhiều nhất). Chỉ vào chỗ bỏ sót: vì sao (quá nhỏ, loá, bị che, đám đông) | Chủ động nói giới hạn. Khung này cũng chọn theo quy tắc, không chọn tay |

**Nếu còn thời gian hoặc hội đồng hỏi về quét vùng:** chạy `scripts/demo_bao_ve.sh chay hotay_quet orin_nano_super 60 80` với tốc độ phát gấp đôi, khoảng 45 giây. Đây là chuyến bay **mô phỏng** (ảnh tổng hợp, phát hiện giả theo recall đo được) quét bốn đường 300 m ở 50 m. Vùng đã quét lớn dần; mất sóng 20 s rồi được gửi bù. Ý chính: đội cứu hộ biết chỗ nào đã quét mà không có ai.

## Quy tắc chọn khung (ghi trước ngày 10/11, trước khi khoá và trước khi xem kết quả trên tập lũ)

Ảnh của câu hỏi 1 và trường hợp sai lấy từ tập test lũ sau khi khoá, bằng `tools/demo_panels.py`, A là E1 (YOLO26s gốc), B là E2c, conf 0,25, IoU 0,5. Ba quy tắc cố định, không đổi sau khi xem kết quả:

| Tên | Quy tắc | Dùng ở |
|---|---|---|
| `nho_nhat` | Khung có nhiều người nhãn cạnh ngắn dưới 16 px nhất | Mở đầu |
| `tieu_bieu` | Trong các khung có ít nhất 3 người, khung có recall của E2c gần recall chung của E2c nhất | Câu hỏi 1 |
| `loi` | Khung E2c bỏ sót nhiều người nhất | Trường hợp sai |

Hoà thì lấy tên file nhỏ nhất. Đây là chọn ảnh minh hoạ, không phải chọn tham số: không tham số nào của mô hình hay pipeline đổi theo các khung này.

Ảnh tập lũ lấy từ video có bản quyền (YouTube, báo chí): chỉ chiếu trong buổi bảo vệ, không phát hành (quyết định #12).

## Chuẩn bị

| Việc | Lệnh hoặc cách làm | Khi nào |
|---|---|---|
| Ảnh so sánh trên tập lũ | `.venv/bin/python tools/demo_panels.py --images data/processed/flood/images/test --labels data/processed/flood/labels/test --ignore data/processed/flood/ignore/test --run-a runs/flood/E1 --run-b runs/flood/E2c --title-a "YOLO26s gốc" --title-b "Đã tinh chỉnh (E2c)" --output runs/demo/flood_panels` | Ngay sau khi chấm tập lũ (sau 11/11) |
| Phát hiện cho mọi khung SDS (một lần, cần GPU) | `scripts/demo_bao_ve.sh chuan-bi sds_v21_goc` và `... chuan-bi sds_v21_px10` | Đã có |
| Chuyến quét mô phỏng (không cần GPU, khoảng 20 giây) | `scripts/demo_bao_ve.sh chuan-bi hotay_quet` | Đã có |
| Video so sánh thiết bị | `scripts/demo_bao_ve.sh so-sanh sds_v21_goc agx_orin_64gb orin_nano_super`; Nano khung gốc và thu nhỏ: lệnh ghép ở mục "Video Nano" dưới | Làm lại 10/11 theo hồ sơ đã hiệu chỉnh 8/11, dựng lại 13/11 với chữ có dấu (số khung/giây không đổi); làm lại nếu hồ sơ đổi |
| Sân thử cho phần hỏi đáp | `python -m console`, tab Sân thử; chạy trước mặc định và hai câu hỏi hay gặp để bảng so sánh có sẵn vài dòng | Tuần 7/12 |
| Giữ ô bản đồ vùng bay | Diễn tập ít nhất một lần **khi có mạng**, phóng to thu nhỏ quanh vùng bay; ô đã xem nằm trong `runs/ground/tiles` | Đã có, diễn tập lại tuần 7/12 |
| Video dự phòng toàn bộ demo | Quay màn hình một lần chạy `chay`, lưu `runs/edge/demo_bao_ve/du_phong.mp4`, nhúng vào slide | Tuần 7/12 |
| Máy chiếu | Thử độ phân giải thật; phóng to trình duyệt để chữ đọc được từ cuối phòng; ảnh so sánh dùng bản `_phong_to` nếu chữ nhỏ | Hôm trước |
| **Soát lần cuối** | `scripts/demo_bao_ve.sh kiem-tra`: in OK hoặc THIẾU từng mục (dữ liệu phát lại, lớp đáp án, hồ sơ thiết bị, video, ảnh tập lũ, ô bản đồ, thư viện, cổng 8000 và 8001) | Sáng hôm bảo vệ |
| Mở sẵn trước khi lên | Terminal đã gõ sẵn lệnh `chay`; trình duyệt mở link màn hình điều phối (`http://localhost:8000/?video=http://localhost:8001/`), toàn màn hình (F11); slide ở trang demo | Trước khi lên |

**Video Nano:**

```bash
.venv/bin/python -m edge.main --config configs/demo/sds_v21_px10.yaml --replay runs/edge/demo_cache/sds_v21_px10/detections.jsonl \
    --device-profile configs/devices/orin_nano_super.yaml --output runs/edge/demo_bao_ve/nano_px10 --save-video --drain-s 15
.venv/bin/python scripts/ghep_video.py \
    --left runs/edge/demo_bao_ve/so_sanh_sds_v21_goc_agx_orin_64gb_orin_nano_super/orin_nano_super/annotated.mp4 \
    --right runs/edge/demo_bao_ve/nano_px10/annotated.mp4 --left-title "Orin Nano Super, khung 4K gốc" \
    --right-title "Orin Nano Super, thu nhỏ theo độ cao" --output runs/edge/demo_bao_ve/so_sanh_nano_goc_px10.mp4
```

Số khung mỗi giây ước lượng (10/11, hồ sơ hiệu chỉnh 8/11, đọc từ log của hai lệnh trên và `so_sanh_goc.log`):

| Thiết bị, cấu hình | Khung/giây |
|---|---|
| AGX Orin 64GB, khung 4K gốc | 3,76 |
| Orin Nano Super, khung 4K gốc | 2,52 |
| Orin Nano Super, thu nhỏ theo độ cao | 3,76 |

Bản 4/11 (hồ sơ chưa hiệu chỉnh, không có thời gian thu nhỏ khung) cho thấy AGX Orin và Nano thu nhỏ theo kịp 8 khung/giây; điều đó không còn đúng và không được nói. Bản cũ để ở `runs/edge/demo_bao_ve/old_4-11/`.

**Còn mở:** hồ sơ thiết bị tính thời gian thu nhỏ khung theo `cv2` trên CPU. Nếu đo được `--gpu-resize` trên T4 (một biến thể trên Kaggle), hiệu chỉnh lại `resize_ms_per_mpx` rồi dựng lại video. Khi đó thanh bên phải của video Nano mới phản ánh cấu hình cuối.

## Điều không nói

- Không nói "chạy thời gian thực trên Jetson". Nói: "với độ trễ ước lượng của Orin Nano Super, pipeline đạt X khung/giây".
- Không đưa số nào không có trong `docs/results/` hoặc không đọc được từ `runs/`.
- Không nói đoạn SDS v21 là tập test lũ: nó thuộc tập val của SeaDronesSee.
- Không trình bày chuyến quét Hồ Tây như số liệu: ảnh tổng hợp, telemetry mô phỏng, phát hiện giả; toạ độ đặt trên Hồ Tây chỉ để bản đồ nền là mặt nước.
- Không nói ảnh tập lũ được chọn vì đẹp: nói quy tắc chọn.

## Trả lời câu hỏi "nếu… thì sao" ngay tại chỗ

Khi hội đồng hỏi về điều kiện khác (bay cao hơn, mô hình chưa tinh chỉnh, mất sóng lâu, GPS kém, thiết bị yếu, bay nhanh), mở tab **Sân thử**:
1. bấm câu hỏi tương ứng, hoặc chỉnh tham số;
2. đặt tốc độ phát 0 để chạy nhanh, rồi bấm Chạy;
3. so dòng mới với dòng mặc định trong bảng.

Nói rõ đây là mô phỏng, một seed, phát hiện giả theo recall đo được; số chính thức chạy nhiều seed nằm ở `docs/results/` (`rq3_*.md`).

## Câu hỏi dễ gặp

| Câu hỏi | Trả lời ngắn | Tài liệu |
|---|---|---|
| Không có Jetson thì sao nói là thiết bị biên? | Đo trên T4 (câu hỏi 2); thời gian Jetson ước lượng từ số đo T4 nhân tỉ lệ công bố, ghi rõ giả định và đặt ở bảng riêng | TECHNICAL 14.4, 14.6, `rq2_t4.md` |
| Thiết bị yếu không theo kịp thì hệ thống có vô dụng không? | Ở 30–50 m, Nano chỉ được khoảng 4 khung/giây và bỏ sót tăng (0,067 ở 30 m); ở 100 m, 2 khung/giây đã đủ. Chỗ chậm là thu nhỏ khung trên CPU, đã đưa lên GPU, chưa đo trên Jetson | Chương 5 mục 5.2.2, `gpu_resize.md` |
| Thu nhỏ theo độ cao có phải ý tưởng mới? | Không; Messmer và cộng sự (2022), Ahmed và Pizarro (2025) đã làm. Phần của luận văn là đưa vào pipeline theo telemetry từng khung, đo theo cỡ người có khoảng tin cậy, tách chặng đổi cỡ khung, và dùng cùng độ cao cho tần số và xác nhận | Chương 2 mục 2.2, chương 3 mục 3.4, #19 |
| Ba câu hỏi nghiên cứu có ít không? | Ba câu là mức thường gặp ở luận văn thạc sĩ; mỗi câu chia thành các câu hỏi con đo được, nối bằng luận điểm dữ liệu bay giúp cả ba khâu | TONG_QUAN 1.3 |
| Tập test lũ 188 khung có đủ không? | Khoảng tin cậy bootstrap theo video, 9 cụm; khoảng rộng, đã ghi là giới hạn | `flood_truoc_khoa.md`, TECHNICAL 15.3 |
| Ảnh lũ trong demo có phải chọn khung đẹp? | Không: ba quy tắc ghi trước khi khoá (mục "Quy tắc chọn khung"), có một khung mô hình làm sai | Tài liệu này |
| Telemetry trong demo là thật hay giả? | Thật (metadata drone SeaDronesSee); video lũ YouTube không có telemetry, nên thu nhỏ theo độ cao chỉ đánh giá trên SDS | ROADMAP #13 |
| Vì sao không dùng ByteTrack? | Ở 2 khung/giây box hai khung liền nhau gần như không chồng nhau; gom theo vị trí mặt đất xác nhận được nhiều người hơn trên video thật | `sds_mot_confirm.md` |
| Sao có nhiều cảnh báo lặp? | GPS drone trôi làm một người tách thành nhiều cụm; trạm gộp thành sự cố | `alert_memory.md` |
| Sao không dùng video SeaDronesSee có drone bay xa cho phần quét vùng? | Các đoạn drone di chuyển đều quay với camera nghiêng 20–78°, còn phép chiếu giả định nhìn thẳng xuống; đoạn nhìn thẳng xuống (v21) thì drone gần như đứng yên. Nên phần quét vùng dùng mô phỏng | `sim/render.py`, TECHNICAL 11.3 |
| Số "cảnh báo riêng" trên màn hình khác bảng kết quả? | Màn hình đếm theo sự cố đã gộp ở trạm, với thiết bị giả lập (số khung khác). Số chính thức đếm theo cảnh báo trong không gian ảnh bằng `eval/`. Khoảng cách giữa "cảnh báo riêng" và "trong vùng tìm" là do người bơi sát nhau bị gộp thành một sự cố | TECHNICAL 12.6, `sds_mot_confirm.md` |
| Hình chữ nhật đen trong video? | Có sẵn trong ảnh gốc của SeaDronesSee, không phải do hệ thống | |
| Mất mạng thì bản đồ? | Leaflet đóng gói sẵn, ô bản đồ đã xem được giữ trên đĩa | TECHNICAL 12.5 |
