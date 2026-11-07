# Cải thiện: điểm yếu đã đo và cách sửa

Mỗi mục: **vấn đề** (kèm bằng chứng đo được, dẫn file trong `docs/results/`), **cách cải thiện**, **chi phí**, **cách kiểm chứng**, **trạng thái**. Số liệu chỉ lấy từ file kết quả; đề xuất chưa làm thì không có số. Dùng tài liệu này để chọn việc khi còn giờ (ROADMAP mục 1.5 vẫn là thứ tự cắt việc khi trễ) và để viết mục "Hướng phát triển" của chương 6.

Trạng thái: **Đã làm** (có mã và kết quả), **Đã làm, tuỳ chọn** (có mã, chưa bật mặc định vì kết quả chưa rõ), **Đề xuất** (chưa làm; ghi rõ cần GPU hay không), **Đã thử, bỏ** (kết quả âm, giữ để khỏi thử lại).

Cập nhật 7/11/2026.

## 1. Phát hiện người (câu hỏi 1)

### 1.1. Mô hình chính yếu với người to (bay thấp)

- **Vấn đề.** E2c mạnh ở người 6–23 px nhưng tụt với người trên 45 px (`e6_sds_pilot.md`). Trên SeaDronesSee, nơi người phần lớn trên 32 px, E2c toàn ảnh 0,468 AP50, chưa hơn mô hình gốc 0,535 (`sds_det.md`).
- **Đã làm: thu nhỏ theo độ cao bay** (`--target-person-px`): đưa người về cỡ mô hình làm tốt trước khi cắt ô. E2c cắt ô trên SDS 4K từ 0,235 lên 0,531 (`scale_by_altitude.md`). Không cần huấn luyện lại; là đóng góp của luận văn.
- **Đã thử, bỏ: thêm C2A (E2e).** Người nhỏ kém rõ trên VisDrone (val −0,029 AP50, < 8 px −0,053, test-dev −0,041, đều có ý nghĩa); SeaDronesSee +0,041 không có ý nghĩa (`E2e.md`).
- **Đề xuất (cần GPU, khoảng 10 giờ Kaggle):** thêm người to mà không làm loãng người nhỏ:
  - lấy mẫu C2A ít hơn (ví dụ một phần ba số ảnh) thay vì toàn bộ, giữ tỉ lệ người nhỏ gần E2c;
  - hoặc fine-tune ngắn từ `E2c/best.pt` thêm vài epoch có C2A với tốc độ học nhỏ, rồi kiểm tra VisDrone < 8 px không tụt;
  - kiểm chứng: so cặp với E2c trên VisDrone val (< 8 px không được kém có ý nghĩa) và SeaDronesSee (> 32 px tăng có ý nghĩa).
- **Đã thử, bỏ (7/11): cắt ô kèm một lượt toàn ảnh** (`--full-pass`). Khi đã thu nhỏ theo độ cao, AP50 không tăng (−0,013, −0,071 đến +0,001), recall người trên 32 px chỉ +0,028, số lần suy luận từ 1.513 lên 1.830 (`full_pass.md`). Không bật trong cấu hình cuối.

### 1.2. Người rất nhỏ (dưới 8 px, bay cao)

- **Vấn đề.** VisDrone val < 8 px: E2c 0,546 AP50, test-dev 0,241 (`E3.md`), thấp hơn hẳn các nhóm khác.
- **Đã thử, bỏ: nhánh phát hiện P2 (E3).** Chỉ +0,012–0,013 AP50 ở < 8 px, mức tăng mất ở IoU 0,3, kém ở người to, tốn thêm tính toán (`E3.md`).
- **Đã làm:** fine-tune trên VisDrone (< 8 px từ 0,167 lên 0,554, `visdrone_E2.md`); cắt ô 640 chồng 0,2.
- **Đã thử, bỏ (7/11): phóng to khi người dự kiến dưới 8 px** (`--min-person-px 8 --max-upscale 2`, tuỳ chọn, mặc định tắt). Trên SeaDronesSee thu nhỏ 2–6 lần, không mức nào cải thiện có ý nghĩa (ví dụ thu nhỏ 6 lần: hiệu AP50 +0,017, −0,043 đến +0,064) mà số ô tăng từ 317 lên 673 (`upscale_small.md`). Người dưới 8 px vẫn là giới hạn dưới; chữa bằng bay thấp hơn.
- **Đề xuất (bay):** hạ độ cao bay khi tìm kiếm chi tiết; mô phỏng cho thấy từ 80 m trở lên E2c không bỏ sót ai còn ở 30 m lại bỏ sót nhiều (`rq3_altitude.md`), nên khuyến nghị độ cao nằm ở khoảng giữa; tần số theo độ cao bù được bay thấp (`rq3_adaptive.md`).

### 1.3. Khác biệt giữa dữ liệu huấn luyện và cảnh lũ

- **Vấn đề.** Chưa đo được: tập test lũ chưa gán (khoá 11/11). Dự kiến các nhiễu riêng của lũ (loá nắng, nước đục, rác trôi, nhoè) làm giảm recall; sẽ đo bằng `eval/recall_by_tag.py` theo thẻ ảnh.
- **Đề xuất (cần GPU):** tăng cường dữ liệu mô phỏng nhiễu lũ khi huấn luyện (loá, đổi màu nước sang phù sa, mờ chuyển động); thêm HydroVigilance (cấu hình `E2d_s0.yaml` có sẵn). Kiểm chứng trên tập lũ **sau khi khoá**, mỗi cấu hình một lần; không chọn tham số trên tập lũ.

### 1.4. Ngưỡng tin cậy

- **Vấn đề.** Pipeline dùng conf 0,1 (để khối xác nhận lọc), bảng recall vận hành dùng 0,25; trên SeaDronesSee E2c cắt ô gốc có precision rất thấp (`scale_by_altitude.md`).
- **Đã thử, bỏ (7/11): ngưỡng theo cỡ box dự đoán** (`eval/conf_by_size.py`, `conf_by_size.md`). Chọn trên VisDrone val (tối đa recall giữ precision của ngưỡng 0,25): ngay trên tập chọn recall chỉ 0,6655 → 0,6657; ngưỡng riêng chỉ chuyển recall từ người 8–16 px sang người dưới 8 px. Trên test-dev recall −0,0019, precision −0,0141 (không có ý nghĩa); trên SeaDronesSee recall +0,0199 nhưng precision −0,0355 (có ý nghĩa). Giữ ngưỡng chung.

### 1.5. Một seed

- **Vấn đề.** E2c, E2e, E3 mỗi cái một seed; hiệu nhỏ như E3 (+0,012) có thể nằm trong dao động giữa các seed.
- **Đề xuất (cần GPU, khoảng 20 giờ):** thêm 2 seed cho mô hình cuối (ROADMAP tuần 14–20/11); không đủ giờ thì ghi vào giới hạn.

## 2. Tốc độ trên thiết bị biên (câu hỏi 2)

- **Đã đo (8/11, `rq2_t4.md`):** chín biến thể trên Kaggle T4. FP16 nhanh hơn PyTorch 1,833–3,028 lần mà độ chính xác gần như giữ; cấu hình đề xuất là FP16 với thu nhỏ theo độ cao (11,58 FPS theo p95 trên khung 4K, recall vận hành 0,580 trên SeaDronesSee). Hồ sơ `configs/devices/` đã hiệu chỉnh từ số đo này (Jetson vẫn là ước lượng, nhân tỉ lệ công bố).
- **Đã làm:** thu nhỏ theo độ cao giảm số ô mỗi khung (khung 4K từ 32 ô xuống 6 ô); tần số xử lý theo độ cao chạy ít khung hơn khi bay cao (`rq3_adaptive.md`); giả lập thời gian thiết bị (`--device-profile`), từ 8/11 có thêm thời gian thu nhỏ khung (`resize_ms_per_mpx`).
- **Điểm yếu mới đo được: đổi cỡ khung 4K tốn hơn suy luận.** Với thu nhỏ theo độ cao, `cv2.resize` (INTER_AREA) trên CPU mất 46,28 ms mỗi khung (trung vị) trên Kaggle, trong tổng 77,34 ms, nhiều hơn suy luận FP16 của 6 ô (30,56 ms). Trên Jetson CPU ARM còn yếu hơn. **Đề xuất (khoảng nửa ngày, chưa làm):** đổi cỡ trên GPU (torch `interpolate` có antialias, hoặc bộ VIC/NVMM của Jetson qua GStreamer), hoặc giải mã video thẳng ở độ phân giải thấp hơn khi bay cao; kiểm chứng bằng bootstrap cặp trên SeaDronesSee val (AP không được giảm) và `timings.jsonl` (chặng `tile_ms`).
- **Điểm yếu mới đo được: INT8 nén độ tin cậy.** Trên VisDrone test-dev, INT8 mất ít AP50 (−0,021) nhưng mất 0,130 recall ở conf 0,25 (dưới 8 px: 0,217 → 0,108); recall tối đa gần như giữ. Ngưỡng 0,25 chọn cho mô hình không nén không hợp với INT8. **Đề xuất (chỉ khi thiết bị cần INT8):** chọn ngưỡng conf riêng cho INT8 trên VisDrone val (không trên test-dev, không trên tập lũ), và hiệu chỉnh INT8 với nhiều ảnh hơn, có ảnh nước. Trên T4 INT8 chỉ nhanh hơn FP16 ít (toàn ảnh 44,58 so với 39,90 FPS theo p95; thu nhỏ 10 px 11,98 so với 11,58) nên hiện không đáng.
- **Đã thử, bỏ (8/11): đầu một-một không cần NMS của YOLO26** (`--nms-free`, `nms_free.md`). Cùng trọng số E2c, recall ở conf 0,25 giảm có ý nghĩa trên VisDrone (val −0,034, dưới 8 px −0,056; test-dev −0,030), AP50 gần như không đổi; trên PyTorch không nhanh hơn (15,2 ms/ảnh ở 1280 cả hai cách). Giữ mặc định có NMS.
- **Đề xuất (chỉ nếu còn giờ T4):** đo thời gian đầu một-một trên TensorRT; nếu nhanh hơn rõ thì chọn lại ngưỡng conf trên val để lấy lại recall.
- **Đã thử, bỏ (8/11): dùng lại kết quả ô không đổi khi drone đứng yên** (`--skip-static-tiles`, `edge/tile_cache.py`, `tile_skip.md`). Bốn đoạn SDS drone đứng yên: chỉ còn chạy 0,518–0,852 số ô nhưng recall giảm 0,035–0,238 (có ý nghĩa ở val v21 và train v9), precision cũng giảm: người bơi vẫn cử động mà ảnh ô thu nhỏ không thấy, box cũ bị dùng lại sai chỗ. Không dùng.

## 3. Xác nhận, định vị, gửi cảnh báo (câu hỏi 3)

### 3.1. Theo dõi thông thường gãy khi xử lý ít khung

- **Vấn đề.** Ở 2 khung/giây, ByteTrack xác nhận 2/19 người trên SDS v21 (`sds_mot_confirm.md`).
- **Đã làm:** xác nhận theo toạ độ mặt đất (`geo`), 12/19 người cùng video. Đóng góp của luận văn.

### 3.2. Vòng sai số trên bản đồ quá hẹp

- **Vấn đề.** Khi GPS σ 3 m đúng giả định, chỉ 0,278 số người nằm trong vòng 1σ (`rq3_geoerr.md`).
- **Đã làm:** bản đồ vẽ vùng tìm 95% (2,448 × 1σ), chứa 1,000 khi GPS σ ≤ 3 m.
- **Đã làm, tuỳ chọn (7/11): bán kính theo độ chính xác GPS do bộ thu báo** (cột `gps_acc_m`, `--gps-sigma-from-telemetry`, TECHNICAL 8.4). Mô phỏng (`rq3_gpsacc.md`): bộ thu báo đúng thì vùng 95% chứa 1,000 ở mọi ô, kể cả GPS kém đi giữa chuyến (σ cố định: 0,763–0,933); GPS tốt thì vùng hẹp lại (50 m, σ 1 m: bán kính 8,069 → 4,141 m). Bộ thu báo lạc quan (nửa σ thật) thì chỉ còn 0,652–0,963. Thẻ drone hiện độ chính xác GPS.
- **Đề xuất:** đọc độ chính xác từ log bay thật (MAVLink `h_acc`, HDOP) và kiểm tra nó với RTK trước khi tin.

### 3.3. La bàn lệch làm một người thành nhiều cảnh báo

- **Vấn đề.** Lệch hướng 5° ở 100 m: tách nhầm 5,333 mỗi kịch bản (ở 50 m: 0,333) (`rq3_geoerr.md`).
- **Đã làm:** trạm gộp cảnh báo gần nhau thành sự cố (`alert_memory.md`).
- **Đã làm, tuỳ chọn (7/11): tự hiệu chỉnh lệch la bàn** (`--yaw-calib`, TECHNICAL 8.4): so hướng di chuyển từ GPS với yaw khi bay thẳng, trừ trung vị. Mô phỏng (`rq3_yawcalib.md`): 100 m, GPS σ 1 m, lệch 5°, bay thẳng: tách nhầm 5,333 → 0,333; quét luống lệch 10°: báo giả mỗi phút 13,667 → 1,333. Khi la bàn không lệch, sai số vị trí tăng nhẹ (1,387 → 1,538 m). Thẻ drone ở trạm hiện lệch đang trừ.
- **Đề xuất:** thử trên log bay thật có drone quét thẳng; ước lượng thêm gió đẩy lệch (mũi máy khác hướng bay).

### 3.4. Cảnh báo chờ lâu sau khi có sóng lại

- **Vấn đề.** Gửi lại có thời gian chờ tăng dần tới 30 s; mất một nửa số gói thì độ trễ lớn nhất 41,167 s và có cảnh báo không tới trạm (`rq3_network.md`).
- **Đã làm:** thăm dò đường truyền mỗi 2 s (quyết định #17, bật mặc định): độ trễ lớn nhất 8,333 s, không mất cảnh báo nào.
- **Đã làm (7/11): mất gói theo cụm** (Gilbert–Elliott, `--net-burst`, TECHNICAL 11.1). Mô phỏng (`rq3_burst.md`), cùng tỉ lệ mất trung bình 0,5, có thăm dò: độ trễ lớn nhất 8,400 s khi mất rải rác, 15,800 s với cụm 10 s, 44,400 s với cụm 30 s; vẫn không mất cảnh báo nào ở mọi ô có thăm dò (không thăm dò: tới 0,180). Phần trễ còn lại là chính độ dài cụm.
- **Đề xuất:** đo mạng thật (radio của drone hoặc 4G) để chọn độ dài cụm; nếu cụm dài là thường, xét đường truyền dự phòng (drone bay về gần trạm khi có cảnh báo chưa gửi được lâu).

### 3.5. Người bơi theo nhóm bị gộp thành một sự cố

- **Vấn đề.** Trên SDS v21, trạm gộp các cảnh báo trong 5 m thành một sự cố; nhiều người trong một nhóm chỉ được tính là một (bản đồ đối chiếu đáp án, TECHNICAL 12.6). Đội cứu hộ không biết cần bao nhiêu phao, xuồng.
- **Đã làm (7/11):** khi xác nhận, UAV đếm số phát hiện cùng khung trong 5 m quanh người đó (`group_size`, `edge/confirm.py`, `shared.schema.GROUP_RADIUS_M`); trạm giữ số lớn nhất của mỗi sự cố, bản đồ hiện "nhóm khoảng N người", GPX ghi kèm. Giới hạn: cộng số người của mọi sự cố thì đếm thừa (một nhóm có thể nằm trong vài sự cố liền nhau, cộng phát hiện nhầm), nên bản đồ không hiện tổng.
- **Đã làm, tuỳ chọn (7/11): đếm theo cụm** (`--group-count clusters`, TECHNICAL 9.4): đếm thêm các cụm còn sống trong 5 m đã thấy ít nhất 2 lần gần đây. Mô phỏng người theo nhóm (`rq3_group.md`): nhóm 4 người, recall 0,7, cảnh báo đúng số người 0,303 → 0,524 (thiếu trung bình 1,040 → 0,494 người); recall 0,9: 0,533 → 0,900; người lẻ không đổi. **Nhưng trên video thật SDS v21 kém hơn**: đúng số người 0,792 → 0,583, đếm thừa 8/24 cảnh báo, vì một người bị tách thành nhiều cụm khi vị trí trôi theo GPS (`eval/group_count_eval.py`). Không bật (quyết định #18).
- **Đã thử (7/11): đếm theo khung trong cửa sổ** (`--group-count frames`: số người thấy cùng lúc ở ít nhất hai khung): hết đếm thừa do tách cụm (v21 thừa 1/24 thay vì 8/24) nhưng đúng số người 0,750, vẫn dưới đếm theo khung xác nhận (0,792); mô phỏng nhóm 4 người, recall 0,7: 0,412. Không bật; giữ đếm theo khung xác nhận.
- **Đề xuất:** chỉ làm tiếp khi có thêm video nhóm người có nhãn.

### 3.6. Camera nghiêng

- **Vấn đề.** Phép chiếu giả định nhìn thẳng xuống; mọi đoạn SeaDronesSee có drone di chuyển đều quay với gimbal nghiêng 20–78°.
- **Đã làm, tuỳ chọn (7/11):** phép chiếu tính góc gimbal (`--use-pitch`, TECHNICAL 8.3, có hàm ngược và test đi một vòng). Kiểm chứng bằng độ tản vị trí của cùng một người qua các khung (`georef_pitch.md`): tốt hơn rõ ở các đoạn drone di chuyển với camera nghiêng vừa phải (v8: 4,982 → 1,301 m), nhưng kém hơn khi camera gần chân trời hoặc drone đứng yên; tính chung chưa tốt hơn (1,336 → 1,603 m), nên chưa bật mặc định.
- **Đã thử, bỏ (7/11): đồng bộ thời gian metadata gimbal và làm mượt góc** (`ShiftedTelemetry`, `SmoothedAngles`). Lưới 11 độ trễ × 4 cửa sổ, chọn trên phần train của SeaDronesSee: ô tốt nhất (trễ +0,3 s, làm mượt 2 s) vẫn kém nhìn thẳng trên train (1,512 so với 1,146 m), trên val chỉ nhỉnh (1,397 so với 1,441 m) (`georef_sync.md`).
- **Đã kiểm tra (8/11): góc nhìn từng camera** (`tools/person_px_check.py`, `person_px_check.md`). Ở khung nhìn thẳng, box người trong nhãn lớn hơn dự kiến 1,8–2,6 lần ở cả Mavic lẫn M100: chủ yếu do cỡ box người bơi, không tách được góc nhìn riêng (bài SeaDronesSee không ghi ống kính từng drone). Giữ 82° và 0,5 m. Hệ quả: mô phỏng thêm `--person-m`; với người 1,0 m, thu nhỏ theo độ cao giảm bỏ sót ở 30 m từ 0,867 xuống 0,400 (mô phỏng).
- **Đề xuất:** quy ước góc gimbal của từng drone và một thước đo thấy được lệch đều (một người đứng yên nhìn từ hai hướng bay); đo lại tỉ số cỡ người trên drone và camera thật.

## 4. Trạm mặt đất và demo

| Điểm yếu | Đã làm | Đề xuất |
|---|---|---|
| Bản đồ chỉ có chấm sự cố, không giúp được người điều phối | Màn hình điều phối: drone, vùng camera nhìn, vùng đã quét, mất liên lạc, cảnh báo còn kẹt trên drone (TECHNICAL 10.6, 12.5) | |
| Mất sóng làm thủng vùng đã quét | Drone gửi bù điểm đường bay khi có sóng lại (`trail`) | |
| Không kiểm chứng được trên màn hình | Đối chiếu đáp án: cảnh báo riêng, trong vùng tìm, bỏ sót, báo nhầm (TECHNICAL 12.6) | |
| Người đi cứu không biết đi đâu trước | Vị trí thuyền, khoảng cách, hướng, thứ tự đi cứu, GPX (TECHNICAL 12.7) | Thứ tự đi cứu tính theo đường thẳng; nếu có bản đồ đường thuỷ hay vật cản thì tính đường đi thật |
| Khó trả lời "nếu… thì sao" tại buổi bảo vệ | Sân thử mô phỏng trong console (TECHNICAL 11.4) | Cho sân thử chạy nhiều seed và vẽ khoảng tin cậy khi có thời gian |
| Đoạn video thật có drone gần như đứng yên | Chuyến quét mô phỏng có ảnh tổng hợp (`hotay_quet`) | Đoạn SDS di chuyển thật khi `--use-pitch` đủ tin cậy (mục 3.6) |
| Ô bản đồ chỉ có cho vùng đã xem | Giữ ô đã xem trên đĩa (TECHNICAL 12.5) | Nguồn ô có giấy phép dùng ngoại tuyến cho triển khai thật |

## 5. Quy trình đo

- **Tập test lũ nhỏ** (188 khung, 9 nguồn): khoảng tin cậy rộng. Không thể sửa trước bảo vệ; nếu sau bảo vệ có thêm video thì gán thêm và khoá phiên bản mới, không sửa phiên bản đã khoá.
- **Sân thử là một seed mỗi lần chạy**: chỉ để thấy xu hướng; số chính thức chạy `sim/sweep_rq3.py` với 3 seed.
- **Mỗi cải thiện mới** cần một dòng trong bảng này: bằng chứng trước, kết quả sau, file kết quả; kết quả âm cũng ghi (mục "Đã thử, bỏ").

## Thứ tự nên làm nếu còn giờ (đề xuất)

1. ~~RQ2 trên T4 rồi hiệu chỉnh hồ sơ thiết bị~~ (8/11, `rq2_t4.md`). Việc mới từ kết quả này: đổi cỡ khung trên GPU (mục 2), khoảng nửa ngày, không cần GPU Kaggle.
2. Hai seed cho E2c (mục 1.5): cần cho chương 5, khoảng 20 giờ GPU.
3. ~~Phóng to khi người dưới 8 px và lượt toàn ảnh cho người to~~ (7/11, cả hai kết quả âm: `upscale_small.md`, `full_pass.md`).
4. ~~Đồng bộ thời gian metadata gimbal~~ (7/11, kết quả âm, `georef_sync.md`); còn lại ở mục 3.6: góc nhìn thật từng camera.
5. Lấy mẫu C2A một phần (mục 1.1): chỉ khi còn khoảng 10 giờ GPU sau mục 1 và 2.
