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
- **Đề xuất (không cần GPU huấn luyện):** chọn ngưỡng theo nhóm cỡ người (người nhỏ ngưỡng thấp, người to ngưỡng cao) trên VisDrone val và SeaDronesSee, không trên tập lũ; kiểm chứng bằng báo nhầm mỗi phút và bỏ sót trong mô phỏng RQ3 với recall đo được.

### 1.5. Một seed

- **Vấn đề.** E2c, E2e, E3 mỗi cái một seed; hiệu nhỏ như E3 (+0,012) có thể nằm trong dao động giữa các seed.
- **Đề xuất (cần GPU, khoảng 20 giờ):** thêm 2 seed cho mô hình cuối (ROADMAP tuần 14–20/11); không đủ giờ thì ghi vào giới hạn.

## 2. Tốc độ trên thiết bị biên (câu hỏi 2)

- **Vấn đề.** Chưa đo TensorRT FP16/INT8 trên T4 (notebook `kaggle_rq2.ipynb` sẵn sàng). Hồ sơ Jetson trong `configs/devices/` là ước lượng chưa hiệu chỉnh.
- **Đã làm:** thu nhỏ theo độ cao giảm số ô mỗi khung (khung 4K từ 32 ô xuống 6 ô, `DEMO_BAO_VE.md`); tần số xử lý theo độ cao chạy ít khung hơn khi bay cao (`rq3_adaptive.md`); giả lập thời gian thiết bị (`--device-profile`).
- **Đề xuất (cần GPU T4, khoảng 2 giờ):** chạy RQ2, rồi hiệu chỉnh hồ sơ bằng `tools/fit_device_profile.py`.
- **Đề xuất (không cần GPU):** bỏ qua ô không có gì thay đổi so với khung trước khi drone gần như đứng yên (so độ khác biệt ảnh trên ô đã căn theo telemetry); kiểm chứng: số ô chạy và recall trên SDS v21 (drone gần như đứng yên).

## 3. Xác nhận, định vị, gửi cảnh báo (câu hỏi 3)

### 3.1. Theo dõi thông thường gãy khi xử lý ít khung

- **Vấn đề.** Ở 2 khung/giây, ByteTrack xác nhận 2/19 người trên SDS v21 (`sds_mot_confirm.md`).
- **Đã làm:** xác nhận theo toạ độ mặt đất (`geo`), 12/19 người cùng video. Đóng góp của luận văn.

### 3.2. Vòng sai số trên bản đồ quá hẹp

- **Vấn đề.** Khi GPS σ 3 m đúng giả định, chỉ 0,278 số người nằm trong vòng 1σ (`rq3_geoerr.md`).
- **Đã làm:** bản đồ vẽ vùng tìm 95% (2,448 × 1σ), chứa 1,000 khi GPS σ ≤ 3 m.
- **Đề xuất (không cần GPU):** GPS thật kém hơn giả định (σ 5 m) thì vùng 95% chỉ còn chứa 0,763–0,833: lấy độ chính xác do bộ thu GPS báo (HDOP hoặc độ chính xác ngang trong log bay DJI) thay cho `--gps-sigma-m` cố định. Kiểm chứng: `rq3_geoerr.yaml` với σ đổi theo thời gian.

### 3.3. La bàn lệch làm một người thành nhiều cảnh báo

- **Vấn đề.** Lệch hướng 5° ở 100 m: tách nhầm 5,333 mỗi kịch bản (ở 50 m: 0,333) (`rq3_geoerr.md`).
- **Đã làm:** trạm gộp cảnh báo gần nhau thành sự cố (`alert_memory.md`).
- **Đề xuất (không cần GPU):** ước lượng lệch la bàn khi bay thẳng bằng cách so hướng di chuyển từ GPS với hướng ghi trong telemetry, rồi hiệu chỉnh; kiểm chứng bằng `rq3_geoerr.yaml` có `yaw_bias_deg`.

### 3.4. Cảnh báo chờ lâu sau khi có sóng lại

- **Vấn đề.** Gửi lại có thời gian chờ tăng dần tới 30 s; mất một nửa số gói thì độ trễ lớn nhất 41,167 s và có cảnh báo không tới trạm (`rq3_network.md`).
- **Đã làm:** thăm dò đường truyền mỗi 2 s (quyết định #17, bật mặc định): độ trễ lớn nhất 8,333 s, không mất cảnh báo nào.
- **Đề xuất:** mất gói theo cụm (Gilbert–Elliott) trong giả lập mạng, để kiểm tra trường hợp sóng yếu kéo dài (TECHNICAL 11.1).

### 3.5. Người bơi theo nhóm bị gộp thành một sự cố

- **Vấn đề.** Trên SDS v21, trạm gộp các cảnh báo trong 5 m thành một sự cố; nhiều người trong một nhóm chỉ được tính là một (bản đồ đối chiếu đáp án, TECHNICAL 12.6). Đội cứu hộ không biết cần bao nhiêu phao, xuồng.
- **Đã làm (7/11):** khi xác nhận, UAV đếm số phát hiện cùng khung trong 5 m quanh người đó (`group_size`, `edge/confirm.py`, `shared.schema.GROUP_RADIUS_M`); trạm giữ số lớn nhất của mỗi sự cố, bản đồ hiện "nhóm khoảng N người", GPX ghi kèm. Giới hạn: cộng số người của mọi sự cố thì đếm thừa (một nhóm có thể nằm trong vài sự cố liền nhau, cộng phát hiện nhầm), nên bản đồ không hiện tổng.
- **Đề xuất (không cần GPU):** đếm số người riêng biệt quanh mỗi sự cố bằng cách gom các cụm còn sống cùng lúc trên UAV, thay vì đếm phát hiện của một khung; kiểm chứng với lớp đáp án trên SDS v21 và chuyến quét mô phỏng.

### 3.6. Camera nghiêng

- **Vấn đề.** Phép chiếu giả định nhìn thẳng xuống; mọi đoạn SeaDronesSee có drone di chuyển đều quay với gimbal nghiêng 20–78°.
- **Đã làm, tuỳ chọn (7/11):** phép chiếu tính góc gimbal (`--use-pitch`, TECHNICAL 8.3, có hàm ngược và test đi một vòng). Kiểm chứng bằng độ tản vị trí của cùng một người qua các khung (`georef_pitch.md`): tốt hơn rõ ở các đoạn drone di chuyển với camera nghiêng vừa phải (v8: 4,982 → 1,301 m), nhưng kém hơn khi camera gần chân trời hoặc drone đứng yên; tính chung chưa tốt hơn (1,336 → 1,603 m), nên chưa bật mặc định.
- **Đề xuất (không cần GPU):** tìm độ trễ giữa metadata gimbal và khung ảnh (`tools/shift_telemetry.py`) và góc nhìn thật của từng camera; làm mượt góc gimbal theo thời gian; thêm thước đo thấy được lệch đều (một người đứng yên nhìn từ hai hướng bay). Nếu ổn, bật cho các đoạn camera nghiêng và dùng một đoạn drone di chuyển thật cho phần quét vùng của demo thay cho mô phỏng.

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

1. RQ2 trên T4 rồi hiệu chỉnh hồ sơ thiết bị (mục 2): mở khoá câu hỏi 2, khoảng 2 giờ GPU.
2. Hai seed cho E2c (mục 1.5): cần cho chương 5, khoảng 20 giờ GPU.
3. ~~Phóng to khi người dưới 8 px và lượt toàn ảnh cho người to~~ (7/11, cả hai kết quả âm: `upscale_small.md`, `full_pass.md`).
4. Đồng bộ thời gian metadata gimbal (mục 3.6): không cần GPU; mở được video thật cho phần quét vùng.
5. Lấy mẫu C2A một phần (mục 1.1): chỉ khi còn khoảng 10 giờ GPU sau mục 1 và 2.
