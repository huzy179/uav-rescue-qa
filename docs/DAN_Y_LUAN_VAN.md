# Dàn ý luận văn

Khung sáu chương theo đề xuất ngày 6/11 (quyết định #16 của ROADMAP: giữ ba câu hỏi của đề cương, thêm câu hỏi con và luận điểm xuyên suốt; chờ cô). Mỗi mục ghi: viết gì, lấy nội dung từ tài liệu nào của dự án, dùng kết quả nào và kết quả đó **đã có** hay **còn chờ**. Lịch viết theo ROADMAP mục 1.3: chương 4 và 5 từ 7/11, bản thảo đầy đủ 4/12. Thuật ngữ dùng theo `THUAT_NGU.md`; mục "Danh mục thuật ngữ và chữ viết tắt" ở đầu quyển chép từ đó.

Ký hiệu trạng thái: **Có** (có file kết quả), **Chờ** (chưa chạy hoặc chờ tập lũ), **Viết** (không cần số liệu, chỉ cần viết), **Nháp** (đã có bản nháp trong `docs/luan_van/`).

## Phần đầu quyển

| Mục | Nguồn | Trạng thái |
|---|---|---|
| Danh mục thuật ngữ và chữ viết tắt | `THUAT_NGU.md` (ba nhóm: ngành, dự án đặt tên, ký hiệu nội bộ) | Viết |
| Danh mục bảng, hình | Sinh khi dàn trang | Viết |

## Chương 1. Mở đầu

Nháp 7/11: `docs/luan_van/chuong1.md` (1.1–1.6; thêm 1.5 phạm vi và giới hạn; còn **[CẦN NGUỒN]** cho số liệu lũ thực tế và **[ĐỐI CHIẾU ĐỀ CƯƠNG]** cho câu chữ ba câu hỏi).

| Mục | Viết gì | Nguồn | Trạng thái |
|---|---|---|---|
| 1.1 Bối cảnh | Người mắc kẹt trong lũ; UAV quét nhanh nhưng người vận hành không xem kịp video | TONG_QUAN 1.1 | Nháp |
| 1.2 Ba ràng buộc | Người rất nhỏ trong ảnh; thiết bị biên yếu; mạng chập chờn. Kèm bảng số pixel theo độ cao | TONG_QUAN 1.2, TECHNICAL mục 2 (bảng GSD) | Nháp |
| 1.3 Câu hỏi nghiên cứu | Ba câu theo đề cương, 14 câu hỏi con, luận điểm "dữ liệu bay giúp cả ba khâu" | TONG_QUAN 1.3 | Nháp (chờ cô duyệt cách trình bày) |
| 1.4 Đóng góp | Ba đóng góp và phần hiện thực hoá | TONG_QUAN 1.4 | Nháp |
| 1.5 Bố cục luận văn | Một đoạn giới thiệu sáu chương | Dàn ý này | Nháp |

## Chương 2. Cơ sở lý thuyết và nghiên cứu liên quan

Nháp 8/11: `docs/luan_van/chuong2.md`, trích dẫn theo `luan_van/tai_lieu_tham_khao.md`; còn **[TRA]** (TensorRT, Blackman, Bar-Shalom), **[ĐỌC TOÀN VĂN]** (SAHI, Adaptive Resizing, Altitude-Aware Dynamic Tiling, MIDDTD, hai bài tổng quan), mục 2.6 chờ quyết định #19.

| Mục | Viết gì | Nguồn | Trạng thái |
|---|---|---|---|
| 2.1 Phát hiện đối tượng và YOLO26 | Backbone, neck, head; đầu một-một không cần NMS (tuỳ chọn; đề tài dùng mặc định có NMS); vì sao người nhỏ bị mất qua các tầng | TECHNICAL mục 3, THUAT_TOAN mục 7 (nguồn tham khảo) | Nháp |
| 2.2 Phát hiện vật nhỏ | Cắt ô (SAHI), tầng P2, khớp tỉ lệ (TinyPerson), đổi cỡ ảnh theo độ cao (Messmer và cộng sự 2022; Ahmed, Pizarro 2025) | TECHNICAL mục 4, `luan_van/tai_lieu_tham_khao.md` | Nháp |
| 2.3 Ảnh từ UAV và bộ dữ liệu | VisDrone, AFO, C2A, SeaDronesSee, HydroVigilance; vì sao chưa có bộ ảnh lũ có nhãn | TONG_QUAN 3.3, TECHNICAL 13.1 | Nháp |
| 2.4 Theo dõi đối tượng qua nhiều khung | ByteTrack, bù chuyển động camera; giả định tần số khung cao | TECHNICAL mục 9 | Nháp |
| 2.5 Thiết bị biên và nén mô hình | TensorRT, FP16, INT8; Jetson | TECHNICAL mục 14 | Nháp |
| 2.6 Khoảng trống nghiên cứu | Chưa có đánh giá theo cỡ người trong cảnh lũ; theo dõi thông dụng không hợp với xử lý ít khung; đổi cỡ ảnh theo độ cao đã có nhưng chưa được đo cùng khối lượng tính và khâu xác nhận trong một pipeline thiết bị biên | Tổng hợp 2.1–2.5 | Nháp |

## Chương 3. Phương pháp

Nháp đầy đủ 7/11: `docs/luan_van/chuong3.md` (3.1–3.8 và tóm tắt; còn **[CHỜ RQ2]** cho hồ sơ thiết bị đã hiệu chỉnh ở 3.8.3, hình 3.1 vẽ khi dàn trang). Thêm mục 3.8 (công cụ giả lập) so với dàn ý ban đầu.

| Mục | Viết gì | Nguồn | Trạng thái |
|---|---|---|---|
| 3.1 Kiến trúc hệ thống | Sơ đồ sáu khâu từ camera tới bản đồ; trên UAV và ở trạm | TONG_QUAN mục 2, THUAT_TOAN mục 2–3 | Nháp |
| 3.2 Hình học camera và định vị | Pixel → GPS, hàm ngược, lan truyền sai số | TECHNICAL mục 2, 8; THUAT_TOAN ví dụ tính tay | Nháp |
| 3.3 Phát hiện: tinh chỉnh và cắt ô | Dữ liệu trộn, bộ cắt ô riêng, gộp theo IOS | TECHNICAL mục 4, 13 | Nháp |
| 3.4 Thu nhỏ theo độ cao bay (có công trình trước, quyết định #19) | Công thức số pixel dự kiến, hệ số thu nhỏ, ảnh hưởng tới số ô | THUAT_TOAN bước 2d, `scale_by_altitude.md`, TECHNICAL 14.6 | Nháp |
| 3.5 Tần số theo độ cao | Số lần nhìn mỗi người, công thức tần số | TECHNICAL 7.5, THUAT_TOAN | Nháp |
| 3.6 **Đóng góp: xác nhận theo toạ độ mặt đất** | Gom theo vị trí mặt đất, N lần trong cửa sổ; vì sao ByteTrack gãy ở 2 khung/giây | TECHNICAL mục 9, THUAT_TOAN | Nháp |
| 3.7 Gửi cảnh báo và trạm mặt đất | Hàng đợi gửi, gửi lại, gộp sự cố, xếp ưu tiên | TECHNICAL mục 10, 12 | Nháp |

## Chương 4. Dữ liệu và thiết lập thí nghiệm

Nháp đầy đủ 7/11: `docs/luan_van/chuong4.md` (còn chỗ **[CHỜ KHOÁ]** cho thống kê tập ảnh lũ và kết quả gán lại, **[CẬP NHẬT]** cho seed).

| Mục | Viết gì | Nguồn | Trạng thái |
|---|---|---|---|
| 4.1 Dữ liệu huấn luyện | Bốn bộ, cách chuyển về một lớp người, thống kê cỡ người | TONG_QUAN 3.3, TECHNICAL 13.1, 13.4 | Có |
| 4.2 **Đóng góp: tập ảnh lũ tự gán nhãn** | Chọn video, trích khung, quy tắc gán, rà trùng ảnh, gộp nguồn San Angelo, khoá bằng mã băm | `LABELING.md`, `flood_truoc_khoa.md` | Có (rà); **Chờ** (gán 7–9/11, khoá 11/11) |
| 4.3 Cách đo | AP, recall theo nhóm kích thước; IoU 0,5 và 0,3; vùng bỏ qua; bootstrap theo video; bootstrap cặp | TECHNICAL mục 5, 15 | Có |
| 4.4 Các thí nghiệm | Bảng mã thí nghiệm E0–E6 với tên mô tả; RQ2 trên T4; RQ3 bằng mô phỏng và video thật | `THUAT_NGU.md` mục 3, ROADMAP mục 4 | Viết |
| 4.5 Môi trường | Kaggle T4, máy cá nhân chỉ để so tương đối; ghim phiên bản, commit | TECHNICAL mục 16 | Viết |

## Chương 5. Kết quả và thảo luận

Theo ba câu hỏi; mỗi câu hỏi con một tiểu mục ngắn: bảng, hình, nhận xét. Kết quả âm (nhánh P2) và kết quả sơ bộ giữ nguyên nhãn.

Nháp 7/11: `docs/luan_van/chuong5.md`. Đã viết đủ RQ1a–d (phần SeaDronesSee và VisDrone), RQ3a–e, mục 5.6; còn chỗ **[CHỜ KHOÁ]** (RQ1a phần lũ, RQ1e, RQ1f, 5.5), **[CHỜ RQ2]** (5.2, một ý ở 5.3.1 và 5.4); 5.4 và tóm tắt chương mới có khung.

| Mục | Câu hỏi con | Kết quả | Trạng thái |
|---|---|---|---|
| 5.1 Câu hỏi 1 | RQ1a cỡ người và bỏ sót | `visdrone_E2.md`, `e6_sds_pilot.md`; tập lũ | Có một phần; tập lũ **Chờ** |
| | RQ1b dữ liệu huấn luyện | `visdrone_E2.md`, `E2c.md`, `afo_E1_E2.md`, `E2e.md` (kết quả âm: thêm người to làm kém người nhỏ) | Có |
| | RQ1c cắt ô, nhánh P2 | `visdrone_baseline.md`, `visdrone_tiled_vs_sahi.md`, `E3.md`; ngưỡng theo cỡ (âm, `conf_by_size.md`) | Có |
| | RQ1d thu nhỏ theo độ cao | `scale_by_altitude.md`; biến thể âm: `upscale_small.md`, `full_pass.md` | Có, sơ bộ |
| | RQ1e nhiễu của cảnh lũ | recall theo thẻ ảnh trên tập lũ | **Chờ** tập lũ |
| | RQ1f chuyển sang cảnh lũ | `sds_det.md` và tập lũ | **Chờ** tập lũ |
| 5.2 Câu hỏi 2 | RQ2a, RQ2b nén mô hình, cấu hình tốt nhất | Bảng recall theo FPS trên T4 (`rq2_t4.md`, bảng in sẵn bởi `scripts/after_rq2.py`) | **Đang chạy** trên Kaggle (7/11) |
| | RQ2c thiết bị yếu | Giả lập thời gian thiết bị, hiệu chỉnh từ RQ2 (ước lượng, bảng riêng; mô phỏng `rq3_device.yaml`) | **Chờ** hiệu chỉnh |
| 5.3 Câu hỏi 3 | RQ3a số khung mỗi giây | `rq3_adaptive.md`, `rq3_altitude.md`, `rq3_altprofile.md` | Có, mô phỏng |
| | RQ3b xác nhận | `sds_mot_confirm.md`, `rq3_cmc_cause.md` | Có, sơ bộ |
| | RQ3c sai số GPS | `rq3_geoerr.md`, `rq3_yawcalib.md`, `rq3_gpsacc.md`; video thật: `georef_pitch.md`, `georef_sync.md` (âm) | Có, mô phỏng |
| | RQ3d mất sóng | `rq3_network.md`, `rq3_burst.md` (mất theo cụm) | Có, mô phỏng |
| | RQ3e gộp sự cố, số người mỗi sự cố | `alert_memory.md`, `rq3_group.md` (mô phỏng tốt, video thật kém: không bật) | Có |
| 5.4 Luận điểm xuyên suốt | Nối RQ1d, RQ2c, RQ3b | Các mục trên | Viết sau khi đủ 5.1–5.3 |
| 5.5 Phân tích lỗi | Ảnh bỏ sót, báo nhầm tiêu biểu theo nhóm cỡ và thẻ ảnh | Báo cáo phân tích lỗi của giao diện (`python -m console`) | **Chờ** tập lũ |
| 5.6 Demo hệ thống | Ảnh chụp bản đồ, video so hai thiết bị | `DEMO_BAO_VE.md` | Có công cụ |

## Chương 6. Kết luận

| Mục | Viết gì | Nguồn | Trạng thái |
|---|---|---|---|
| 6.1 Trả lời ba câu hỏi | Mỗi câu một đoạn, dẫn số chính | Chương 5 | Viết sau chương 5 |
| 6.2 Giới hạn | Tập lũ nhỏ (188 khung, 9 cụm), không bay thật, không có Jetson, video lũ không có độ cao, một seed cho phần lớn thí nghiệm, không có đối chứng đời mô hình (YOLO11s cắt 7/11) | TECHNICAL mục 17, TONG_QUAN mục 6 | Viết |
| 6.3 Hướng phát triển | Đo trên Jetson thật; nhiều drone phối hợp; phân biệt người cần cứu gấp; ảnh nhiệt; các mục "Đề xuất" của `CAI_TIEN.md` | DEMO_BAO_VE (câu hỏi dễ gặp), TONG_QUAN mục 6, `CAI_TIEN.md` | Viết |

## Việc còn thiếu để viết đủ

1. Gán và khoá tập ảnh lũ (11/11), rồi chấm mọi mô hình: mở khoá RQ1a (phần lũ), RQ1e, RQ1f, mục 5.5.
2. ~~E2e phiên 2, rồi chấm trên SeaDronesSee~~ (xong 7/11, `E2e.md`): RQ1b đủ.
3. Chạy RQ2 trên T4 (đang chạy 7/11, lần đầu lỗi INT8 với TensorRT 11, đã ghim TensorRT 10): RQ2a, RQ2b; sau đó `scripts/after_rq2.py` hiệu chỉnh giả lập thiết bị và `rq3_device.yaml`: RQ2c.
4. ~~Một lần chạy tổng hợp sai số GPS và mất sóng thành bảng: RQ3c, RQ3d~~ (xong 6/11, `rq3_geoerr.md`, `rq3_network.md`).
5. Ba seed cho mô hình cuối (tuần 14–20/11) nếu còn giờ GPU; không đủ thì ghi một seed vào giới hạn.
