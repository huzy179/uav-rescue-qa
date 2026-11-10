# Chương 3. Phương pháp

> **Ghi chú bản nháp (xoá khi đưa vào quyển).** Nháp 7/11/2026 theo `docs/DAN_Y_LUAN_VAN.md` mục chương 3. Nguồn: `docs/TECHNICAL.md` mục 2, 4, 7–12, 14.6; `docs/THUAT_TOAN.md` (thuật toán từng bước, ví dụ tính tay); mã trong `edge/`, `ground/`, `sim/`. Chương này mô tả **cách làm**; số đo nằm ở chương 5, ở đây chỉ dẫn vài con số làm động lực, mỗi số ghi file nguồn trong `docs/results/`. Thuật ngữ theo `docs/THUAT_NGU.md`. Tham số ghi là giá trị mặc định trong `configs/edge.yaml`. Số hình, số bảng đánh lại khi dàn trang.

Chương này trình bày hệ thống phát hiện và báo vị trí người trong vùng ngập từ UAV: kiến trúc tổng thể (3.1), hình học camera và cách đổi vị trí trên ảnh sang toạ độ mặt đất (3.2), khâu phát hiện (3.3) cùng bước thu nhỏ khung theo độ cao bay (3.4), tần số xử lý theo độ cao (3.5), đóng góp xác nhận theo toạ độ mặt đất (3.6), và khâu gửi cảnh báo cùng trạm mặt đất (3.7). Mục 3.8 mô tả các công cụ giả lập dùng để đánh giá những phần không đo được trên thiết bị và chuyến bay thật.

Xuyên suốt chương là một ý: **dữ liệu bay sẵn có của UAV (độ cao, GPS, hướng) được đưa vào cả ba khâu**, phát hiện, tính toán và xác nhận, thay cho các giả định cố định.

## 3.1. Kiến trúc hệ thống

Hệ thống gồm hai phía (Hình 3.1).

**Trên UAV (thiết bị biên)**, mỗi khung được chọn đi qua năm bước:

1. **Lấy mẫu:** lấy một khung từ video và telemetry tại đúng thời điểm đó.
2. **Phát hiện:** cắt khung thành các ô, chạy mô hình YOLO26 trên mọi ô trong một lô, gộp các box trùng.
3. **Định vị:** đổi mỗi box sang toạ độ GPS trên mặt đất.
4. **Xác nhận:** gom các phát hiện theo vị trí mặt đất qua nhiều khung; vị trí nào được thấy đủ N lần trong một cửa sổ thời gian thì thành cảnh báo, mỗi người một lần.
5. **Gửi:** ghi cảnh báo vào hàng đợi trên đĩa, gửi toạ độ trước và ảnh cắt sau, gửi lại khi lỗi.

**Ở trạm mặt đất**, cảnh báo được gộp thành sự cố, xếp ưu tiên và hiện trên bản đồ cho đội cứu hộ.

**Hình 3.1.** [Vẽ khi dàn trang] Sơ đồ hai phía: camera và telemetry → lấy mẫu → phát hiện → định vị → xác nhận → hàng đợi gửi → (mạng chập chờn) → trạm: gộp sự cố, xếp ưu tiên, bản đồ.

Ba nguyên tắc thiết kế đi kèm, vì chúng quyết định cách đánh giá ở chương 4:

- **Mỗi khâu là một giao diện có bản giả.** Khâu phát hiện, nguồn telemetry và đường truyền đều có bản giả để kiểm thử và mô phỏng. Nhờ đó cùng một mã xác nhận, gửi và trạm chạy được với mô hình thật, với phát hiện đọc lại từ lần chạy trước, hay với detector giả trong chuyến bay mô phỏng.
- **Thời gian lấy từ khung hình, không từ đồng hồ máy.** Thời điểm của khung là chỉ số khung chia cho số khung mỗi giây của video. Chạy lại cùng dữ liệu cho đúng cùng kết quả, kể cả phần mạng giả lập (dùng seed cố định); mô phỏng chạy nhanh hơn thời gian thực được. Thời gian xử lý thật đo riêng và chỉ ghi vào nhật ký.
- **Mỗi khâu ghi nhật ký; chỉ số tính sau.** Pipeline không tự tính độ chính xác. Mọi chỉ số ở chương 5 được tính lại từ nhật ký bằng các script đánh giá riêng, nên có thể đổi cách tính mà không chạy lại pipeline.

## 3.2. Hình học camera và định vị

### 3.2.1. Mô hình camera

Dùng mô hình camera lỗ kim với giả định **camera nhìn thẳng xuống** (nadir) ở độ cao h so với mặt nước. Tiêu cự tính bằng pixel suy ra từ góc nhìn ngang (HFOV) và bề rộng ảnh W:

```
f = (W / 2) / tan(HFOV / 2)
```

Hãng camera thường ghi góc nhìn theo đường chéo (DFOV); với ảnh W × H, góc ngang suy ra bằng `tan(HFOV/2) = tan(DFOV/2) · W / √(W² + H²)`. Với camera 82° chéo và video 3840 × 2160, HFOV khoảng 74,3° và f khoảng 2.534 px.

Kích thước một pixel trên mặt đất (GSD) là `h / f`, nên một người rộng khoảng 0,5 m chiếm

```
px_người = 0,5 · f / h
```

pixel trên ảnh: khoảng 42 px ở 30 m, 25 px ở 50 m, 13 px ở 100 m (TECHNICAL mục 2.3). Đây là con số nối độ cao bay với khâu phát hiện ở mục 3.4.

### 3.2.2. Từ pixel sang toạ độ mặt đất

Với điểm ảnh (u, v) (u sang phải, v xuống dưới), tâm ảnh (c_x, c_y), độ cao h và hướng ψ của đỉnh ảnh (đo từ hướng Bắc theo chiều kim đồng hồ):

```
phía trước = −(v − c_y) · h / f          bên phải = (u − c_x) · h / f
Bắc  = phía trước · cos ψ − bên phải · sin ψ
Đông = phía trước · sin ψ + bên phải · cos ψ
vĩ độ  = vĩ độ UAV  + Bắc / R · 180/π
kinh độ = kinh độ UAV + Đông / (R · cos(vĩ độ UAV)) · 180/π        (R = 6.378.137 m)
```

Bước cuối là xấp xỉ mặt phẳng cục bộ, đủ chính xác trong phạm vi vài km quanh UAV. Điểm lấy trên box là **tâm cạnh dưới** (chân người khi đứng; nhìn từ trên xuống thì gần trùng tâm box).

**Hàm ngược** (GPS → pixel) làm ngược ba bước trên. Nó có hai công dụng: kiểm thử (pixel → GPS → pixel phải ra đúng điểm cũ, sai dưới 0,01 px) và mô phỏng (biết người đặt ở toạ độ nào thì biết họ hiện ở pixel nào trong mỗi khung, mục 3.8).

Telemetry thường ghi ở tần số khác video nên giá trị tại thời điểm của khung được **nội suy** từ hai mẫu gần nhất; riêng góc hướng nội suy theo đường ngắn nhất trên vòng tròn (từ 359° sang 1° là tăng 2°).

### 3.2.3. Sai số vị trí

Mỗi cảnh báo mang một **sai số vị trí ước lượng** (1σ), tính từ vị trí của người trong ảnh và độ cao, bằng cách cộng theo căn bậc hai tổng bình phương các nguồn độc lập (Bảng 3.1).

**Bảng 3.1.** Nguồn sai số định vị, với d là khoảng cách trên mặt đất từ điểm ngay dưới UAV tới người.

| Nguồn | Sai số vị trí | Mặc định (giả định GPS thường) |
|---|---|---|
| GPS của UAV, σ_GPS | σ_GPS | 3 m |
| Độ cao, δh | d · δh / h | 2 m |
| Hướng bay, δψ (radian) | d · δψ | 2° |
| Nghiêng camera, δθ | h · (1 + d²/h²) · δθ | 1° |

Với GPS thường, GPS chiếm phần lớn sai số. Sai số trên mặt đất có hai chiều: nếu mỗi trục là phân phối chuẩn với độ lệch σ thì khoảng cách tới vị trí đúng theo phân phối Rayleigh, và vòng bán kính 1σ chỉ chứa khoảng 39% trường hợp. Vì vậy bản đồ ở trạm vẽ **vùng tìm 95%**, bán kính

```
r_95 = √(−2 ln 0,05) · σ ≈ 2,448 σ
```

Mô phỏng ở chương 5 xác nhận điều này: khi GPS σ 3 m đúng như giả định, chỉ 0,278 số người nằm trong vòng 1σ, còn vùng 95% chứa 1,000 (`rq3_geoerr.md`).

Hai phần mở rộng tuỳ chọn dùng chính telemetry để sửa telemetry (chi tiết ở TECHNICAL mục 8.4; kết quả mô phỏng ở chương 5, mục 5.3.3):

- **Sai số GPS theo độ chính xác bộ thu tự báo:** khi telemetry có trường độ chính xác ngang của bộ thu, σ_GPS của cảnh báo lấy theo giá trị tại thời điểm phát hiện thay cho hằng số, nên vùng tìm co giãn theo chất lượng GPS lúc đó.
- **Tự hiệu chỉnh lệch la bàn:** khi UAV bay thẳng với vận tốc đủ lớn, hướng di chuyển tính từ hai điểm GPS là một phép đo độc lập của hướng mũi máy; trung vị của hiệu (hướng la bàn − hướng di chuyển) trên nhiều đoạn bay thẳng ước lượng được độ lệch cố định của la bàn, và được trừ trước khi định vị.

Giả định nhìn thẳng xuống được giữ làm mặc định. Phép chiếu tổng quát theo góc nghiêng gimbal đã được cài (tia từ tâm camera qua pixel, xoay theo góc nghiêng rồi giao với mặt nước), có hàm ngược và kiểm thử đi một vòng, nhưng trên video thật nó chưa cho vị trí ổn định hơn tính chung (`georef_pitch.md`), nên để tuỳ chọn.

## 3.3. Phát hiện người: tinh chỉnh và cắt ô

### 3.3.1. Mô hình và dữ liệu tinh chỉnh

Mô hình là YOLO26s (Ultralytics 8.4.174). YOLO26 có hai đầu dự đoán: đầu một-nhiều cần bước loại bỏ box trùng (NMS) và đầu một-một cho kết quả cuối không cần NMS; luận văn dùng mặc định của thư viện, đầu một-nhiều kèm NMS, cho cả lần chạy PyTorch lẫn TensorRT, nên kết quả hai bên so được trực tiếp. Mô hình được **tinh chỉnh** từ trọng số học trên COCO, với một lớp duy nhất là người, ở đầu vào 1280 px. Dữ liệu tinh chỉnh trộn hai nguồn bù nhau: VisDrone (người rất nhỏ nhìn từ trên cao, đô thị) và AFO (người dưới nước). Mô hình này (E2c) là mô hình chính của luận văn; lý do chọn và các phương án đã thử (thêm tầng P2, thêm ảnh thảm hoạ C2A) ở chương 5, mục 5.1.2.

### 3.3.2. Cắt ô theo lô

Mô hình YOLO thu ảnh về cỡ đầu vào trước khi xử lý. Khung 3840 px thu về 640 px là chia 6: người 25 px còn khoảng 4 px và gần như biến mất. **Cắt ô** giữ nguyên độ phân giải: chia khung thành các ô 640 × 640 chồng nhau 20%, chạy mô hình ở đầu vào 640 để một pixel ảnh đúng bằng một pixel vào mạng. Số ô theo một chiều dài L là

```
n = ⌈(L − 640) / 512⌉ + 1
```

nên khung 3840 × 2160 có 8 × 4 = 32 ô. Ô cuối mỗi hàng, mỗi cột kéo sát mép ảnh.

Khác thư viện SAHI (chạy mô hình từng ô một), luận văn dùng **bộ cắt ô riêng chạy mọi ô trong một lô**: GPU xử lý song song nhiều ô một lượt, và mô hình xuất được sang TensorRT với kích thước lô động (số ô thay đổi khi khung bị thu nhỏ, mục 3.4).

### 3.3.3. Gộp box giữa các ô

Người nằm ở vùng hai ô chồng nhau cho hai box gần trùng; người ở mép ô có thể cho một box đủ (ô này) và một box nửa người (ô bên cạnh). Box được đổi về toạ độ ảnh gốc rồi gộp:

```
sắp box theo conf giảm dần;
lặp: giữ box conf cao nhất còn lại; bỏ mọi box còn lại có IOS với nó > 0,5
IOS = diện tích phần giao / diện tích box nhỏ hơn
```

Dùng IOS (giao trên box nhỏ) thay IoU vì box nửa người nằm gọn trong box đủ nên IOS gần 1, trong khi IoU của chúng chỉ khoảng 0,5. Gộp bằng cách **giữ box điểm cao nhất**, không hợp nhất toạ độ như SAHI: hợp nhất toạ độ đã được thử và bỏ, vì một box lớn điểm thấp phủ cả đám đông kéo box của từng người thành box cả nhóm. So với SAHI bằng bootstrap cặp trên VisDrone val, bộ cắt ô riêng kém 0,006 AP50 (khoảng tin cậy −0,011 đến −0,003) nhưng nhỉnh hơn ở người dưới 8 px (`visdrone_tiled_vs_sahi.md`; chương 5, Bảng 5.6).

### 3.3.4. Ngưỡng tin cậy

Pipeline giữ box có conf ≥ 0,1, thấp hơn ngưỡng 0,25 dùng cho recall vận hành ở chương 5. Ngưỡng thấp để ít bỏ sót; báo nhầm do ngưỡng thấp sinh ra được lọc ở khâu xác nhận (mục 3.6), vì báo nhầm hiếm khi lặp lại ở cùng một chỗ trên mặt đất qua nhiều khung. Đặt ngưỡng riêng cho từng cỡ box đã được thử và không có lợi (`conf_by_size.md`).

## 3.4. Thu nhỏ khung theo độ cao bay

### 3.4.1. Động lực

Mô hình tinh chỉnh học chủ yếu người nhỏ: trên SeaDronesSee thu nhỏ nhiều mức, nó bắt tốt người khoảng 6–23 px nhưng tụt mạnh với người trên 45 px (`e6_sds_pilot.md`; chương 5, Bảng 5.2). Khi UAV bay thấp, người to ra đúng vào vùng mô hình yếu, và cắt ô ở độ phân giải gốc lại làm người to thêm. Trên SeaDronesSee 4K, cắt ô gốc cho AP50 thấp hơn hẳn chạy toàn ảnh (0,235 so với 0,468, `scale_by_altitude.md`).

### 3.4.2. Cách làm

Trước khi cắt ô, ước lượng người sẽ to bao nhiêu pixel từ độ cao trong telemetry (mục 3.2.1), rồi thu nhỏ khung để người về cỡ mục tiêu p* mà mô hình làm tốt:

```
px_dự_kiến = 0,5 · f / h
s = max(1, px_dự_kiến / p*)
thu khung đi s lần → cắt ô → phát hiện → nhân toạ độ box với s để về ảnh gốc
```

Box luôn được quy về toạ độ ảnh gốc, nên khâu định vị và xác nhận không cần biết khung đã bị thu nhỏ. Không bao giờ phóng to (s ≥ 1): phóng to khi người dự kiến dưới 8 px đã được thử như một phần mở rộng và không cải thiện có ý nghĩa (`upscale_small.md`). Mục tiêu p* = 10 px được chọn trên SeaDronesSee (đã thử 10 và 20 px), không trên tập ảnh lũ. Đây là số pixel **dự kiến** theo giả định người 0,5 m; box người bơi trong nhãn SeaDronesSee lớn hơn khoảng 1,8–2,6 lần ở khung nhìn thẳng, nên trên tập đó người sau khi thu nhỏ thực tế khoảng 18–26 px (`person_px_check.md`).

### 3.4.3. Hai tác dụng

Thu nhỏ theo độ cao có hai tác dụng, ứng với hai câu hỏi nghiên cứu:

- **Độ chính xác (câu hỏi 1):** đưa người về cỡ mô hình làm tốt nhất. Trên SeaDronesSee, AP50 của cắt ô từ 0,235 lên 0,531 với p* = 10 px (`scale_by_altitude.md`; chương 5, mục 5.1.4).
- **Khối lượng tính (câu hỏi 2):** khung nhỏ đi thì số ô giảm theo bình phương hệ số s. Ví dụ ở 30 m, người khoảng 42 px; với p* = 10 px thì s = 4,2, khung 3840 × 2160 còn khoảng 914 × 514 và chỉ cần 2 ô thay vì 32. Trên thiết bị yếu, đây là cách để theo kịp tần số cần thiết khi bay thấp (mục 3.8.3; chương 5, mục 5.2).

**Công trình liên quan.** Đổi cỡ ảnh theo độ cao chụp không phải ý tưởng mới: Messmer và cộng sự đổi cỡ ảnh UAV theo độ cao trước khi phát hiện (Adaptive Resizing, ICPR 2022), và Ahmed và Pizarro kết hợp thu nhỏ theo độ cao với số ô động, đánh giá trên chính SeaDronesSee (OCEANS 2025); ý "khớp thang kích thước" lúc huấn luyện có từ TinyPerson (WACV 2020). Phần của luận văn là **đưa bước này vào pipeline chạy trên thiết bị biên theo telemetry từng khung** và đo hai tác dụng cùng lúc trên một mô hình đã tinh chỉnh cho người nhỏ: độ chính xác theo nhóm cỡ người (bootstrap cặp theo video) và số ô phải tính, nối với giả lập thời gian thiết bị và với khâu xác nhận. So với [AltTiling], ý tưởng và cả cỡ đích gần như trùng (họ chọn khoảng 9 px, luận văn 10 px), nên đây **không phải phương pháp mới**. Khác biệt nằm ở cách dùng và cách đo: hệ số ở đây liên tục, tính lại mỗi khung từ telemetry, không làm tròn về vài mức; đánh giá trên tập val gốc của SeaDronesSee với độ cao thật từ metadata (Messmer và cộng sự phải suy độ cao từ nhãn cho VisDrone, UAVDT), theo nhóm cỡ người và bằng bootstrap cặp theo video, trong khi cả hai bài chạy một lần không có khoảng tin cậy; tốc độ đo bằng TensorRT kèm biên Pareto và tách riêng chặng đổi cỡ khung (chương 5, mục 5.2.1); và cùng độ cao đó còn quyết định tần số xử lý và bán kính xác nhận (mục 3.5, 3.6). Kiểm tra cỡ người trên nhãn SeaDronesSee cũng cho thấy giả định cỡ người ảnh hưởng mạnh: box thật lớn hơn giả định 0,5 m khoảng 1,8–2,6 lần (`person_px_check.md`). Giới hạn: tập ảnh lũ lấy từ video công khai không có độ cao bay, nên đóng góp này chỉ đánh giá được trên SeaDronesSee (có độ cao từ metadata) và trong mô phỏng (quyết định #13).

## 3.5. Tần số xử lý theo độ cao

Thiết bị biên không xử lý kịp 30 khung 4K mỗi giây, và cũng không cần. Một người nằm trong khung trong khoảng thời gian

```
T_dwell = L_v / v,     L_v = 2h · tan(VFOV / 2)
```

(L_v là chiều dọc vùng chụp, v là vận tốc bay), nên ở tần số xử lý F khung/giây, người đó được nhìn thấy tối đa `K_max = ⌊T_dwell · F⌋` lần. Ở 50 m, 10 m/s, 2 khung/giây, K_max = 8.

Nếu mỗi lần nhìn mô hình thấy người với xác suất r và các lần độc lập, xác suất thấy ít nhất N trong K lần là

```
P(xác nhận) = Σ_{k=N..K} C(K, k) · r^k · (1 − r)^(K − k)
```

Ví dụ K = 8, r = 0,5: N = 3 cho P ≈ 0,86; N = 5 cho P ≈ 0,36. Công thức này nối recall mỗi khung (câu hỏi 1) với khả năng xác nhận của cả hệ thống (câu hỏi 3).

Tần số cố định không hợp với mọi độ cao: bay cao thì người nằm trong khung lâu, xử lý 2 khung/giây đã thừa; bay thấp thì thời gian ngắn, 2 khung/giây có thể không đủ N lần nhìn. Phần mở rộng **tần số theo độ cao** đặt tần số sao cho mỗi người được nhìn khoảng n_views lần:

```
F = clamp(n_views · v / L_v, F_min, F_max)
```

tính lại sau mỗi khung từ độ cao và vận tốc trong telemetry; cửa sổ đếm của khâu xác nhận dãn theo T_dwell. Kết quả mô phỏng ở chương 5, mục 5.3.1.

## 3.6. Đóng góp: xác nhận theo toạ độ mặt đất

### 3.6.1. Vì sao cần xác nhận, và vì sao theo dõi thông dụng gãy

Ở một khung, mô hình có thể nhầm sóng, rác trôi, ánh phản chiếu là người. Nhầm kiểu đó thường không lặp lại ở đúng một chỗ nhiều lần; người thật thì có. Khâu xác nhận chỉ cảnh báo khi một người được thấy đủ N lần, và mỗi người chỉ một lần. Muốn vậy phải biết box ở khung này và box ở khung sau là **cùng một người** (bài toán ghép).

Cách ghép thông dụng là theo dõi đối tượng trên ảnh như ByteTrack: ghép box giữa hai khung theo độ chồng lấn (IoU), với bộ lọc Kalman dự đoán vị trí. Cách này giả định một người chỉ dịch vài pixel giữa hai khung. Ở đây giả định đó sai: giữa hai khung cách 0,5 s, UAV bay 10 m/s đi được 5 m, tức khoảng **254 px** ở 50 m, trong khi box người chỉ khoảng 25 px. Hai box của cùng một người không chồng nhau, IoU bằng 0, nên mỗi khung sinh một track mới và không người nào đủ N lần. Bộ lọc Kalman không cứu được: chuyển động là của camera chứ không của người, và ở khung đầu của một track nó chưa biết vận tốc.

Một cách sửa trong không gian ảnh là **bù chuyển động camera** (như BoT-SORT, nhưng tính từ telemetry thay vì từ ảnh): chiếu bốn góc ảnh xuống mặt đất bằng telemetry khung trước, chiếu ngược lên ảnh bằng telemetry khung này, khớp một phép biến đổi affine và dời mọi track trước khi ghép. Cách này kế thừa toàn bộ dao động của telemetry giữa hai khung: GPS dao động vài chục cm là đủ lệch vài chục pixel, xấp xỉ cỡ box người.

### 3.6.2. Thuật toán gom theo vị trí mặt đất

Ý tưởng: người đứng yên (hoặc trôi chậm) trên mặt nước nên **toạ độ mặt đất của họ gần như không đổi giữa các khung**, dù camera bay. Ghép trên mặt đất thay vì trên ảnh.

Hệ thống giữ một danh sách **cụm**; mỗi cụm là một người nghi vấn, gồm vị trí trên mặt đất, các lần thấy (thời điểm, conf) và cờ đã cảnh báo. Tham số: bán kính gom r = 3 m, số lần thấy N = 3, cửa sổ T_win = 5 s, thời gian xoá T_exp = 6 s.

```
Với các phát hiện D của khung tại thời điểm t (đã có toạ độ mặt đất):
1. Xoá cụm có lần thấy gần nhất cách t quá T_exp.
2. Ghép một-một: tính khoảng cách mặt đất mọi cặp (cụm, phát hiện), sắp tăng dần;
   duyệt lần lượt, ghép nếu khoảng cách ≤ r và cả hai chưa được ghép.
3. Cập nhật: phát hiện được ghép thêm vào cụm, vị trí cụm là trung bình có trọng số conf
   của mọi lần thấy; phát hiện không ghép được tạo cụm mới.
4. Xác nhận: cụm chưa cảnh báo có ≥ N lần thấy trong T_win giây gần nhất → cảnh báo,
   đánh dấu đã cảnh báo.
```

Ghép **một-một** để hai người đứng cạnh nhau trong cùng khung không bị nhập làm một. Luật "N lần trong T_win giây" không đòi N khung liên tiếp, nên chịu được bỏ sót ở vài khung. Bán kính r tính bằng mét, chịu được sai số GPS cỡ vài mét, vì GPS lệch **chậm**: giữa hai khung cách 0,5 s, sai số gần như giống nhau nên vị trí tương đối giữa các lần thấy của cùng một người vẫn gần nhau dù vị trí tuyệt đối lệch. Độ phức tạp mỗi khung là O(nm log nm) với n phát hiện và m cụm, không đáng kể so với chạy mô hình.

Để so sánh công bằng, cả ba chiến lược (gom theo mặt đất, ByteTrack, ByteTrack có bù chuyển động camera) dùng chung bước xoá, cập nhật và xác nhận; chúng **chỉ khác ở bước ghép**. Ví dụ tính tay trọn bốn khung cho cả ba chiến lược ở `docs/THUAT_TOAN.md` mục 4 [đưa vào phụ lục].

### 3.6.3. Giới hạn đã biết

- Hai người gần nhau hơn r có thể bị gộp thành một cảnh báo. Trong cứu hộ, lỗi này ít nguy hiểm hơn bỏ sót: đội cứu hộ tới nơi vẫn thấy cả nhóm. Mỗi cảnh báo mang thêm **ước tính số người** trong 5 m (số phát hiện của khung xác nhận quanh vị trí đó) để đội mang đủ phao, xuồng; hai cách đếm qua nhiều khung đã thử, tốt hơn trong mô phỏng nhưng kém hơn trên video thật, nên không dùng (`rq3_group.md`).
- Khi GPS trôi, một người có thể rơi ra khỏi cụm cũ và được cảnh báo lần nữa (tách nhầm). Phần này được xử lý ở trạm (mục 3.7.3) chứ không chặn ở UAV, vì chặn ở UAV cũng chặn luôn người thật thứ hai đứng gần (`alert_memory.md`).
- Người trôi nhanh hơn mức cụm theo kịp sẽ bị tách thành cụm mới; la bàn lệch cố định làm cùng một người bị chiếu tới các chỗ khác nhau khi UAV bay qua, rõ hơn khi bay cao (mục 3.2.3).

## 3.7. Gửi cảnh báo và trạm mặt đất

### 3.7.1. Hàng đợi gửi trên UAV

Mạng giữa UAV và trạm chập chờn, nên mọi cảnh báo được **ghi vào bảng SQLite trên UAV trước khi gửi** (mẫu transactional outbox); mất mạng hay mất điện giữa chừng không làm mất cảnh báo. Mỗi cảnh báo sinh hai thông điệp cùng mã:

- **toạ độ** (vài trăm byte, ưu tiên cao): vị trí, sai số vị trí, độ tin cậy, số lần thấy, ước tính số người;
- **ảnh cắt** 256 × 256 JPEG quanh người (vài chục KB): chỉ gửi **sau khi** trạm xác nhận đã nhận gói toạ độ.

Vòng gửi chạy sau mỗi khung và tiếp tục tối đa 60 s sau khung cuối:

```
lấy các thông điệp chưa được xác nhận, đã đến hạn, theo (ưu tiên, thời điểm tạo);
gửi; trạm xác nhận → xong;
lỗi → hẹn thử lại sau min(30, 2^(số lần thử − 1)) giây, nhân thêm 0–20% ngẫu nhiên;
       dừng lượt gửi này (đường truyền đang hỏng)
```

Thời gian chờ tăng dần để không gửi dồn dập khi mất sóng; phần ngẫu nhiên để nhiều UAV không cùng gửi lại một lúc khi sóng có lại.

**Thăm dò đường truyền** (đề xuất của luận văn, bật mặc định từ quyết định #17): với trần 30 s, một gói hỏng ngay trước khi sóng có lại có thể nằm chờ thêm gần 30 s. Khi mọi gói đang chờ tới lượt và đã 2 s không gửi gì, UAV thử gửi gói toạ độ cũ nhất; gửi được (sóng đã có lại) thì mọi gói đang chờ đến hạn ngay. Lần thăm dò hỏng không đẩy lùi thêm thời gian chờ. Kết quả ở chương 5, mục 5.3.4.

### 3.7.2. Bảo đảm giao nhận

Cơ chế trên bảo đảm mỗi thông điệp tới **ít nhất một lần**: nếu xác nhận của trạm bị mất trên đường về, UAV gửi lại và trạm nhận hai lần. Trạm bỏ qua mã thông điệp đã có, nên về mặt hiệu ứng mỗi cảnh báo được ghi **đúng một lần**.

### 3.7.3. Gộp cảnh báo thành sự cố

Trạm gắn mỗi cảnh báo mới vào **sự cố** còn mở gần nhất trong bán kính 5 m và 300 s (theo đồng hồ chuyến bay), không có thì mở sự cố mới; vị trí sự cố là trung bình các cảnh báo. Cảnh báo từ hai UAV khác nhau dùng bán kính rộng hơn, theo căn tổng bình phương sai số vị trí của hai cảnh báo, vì GPS của hai UAV độc lập. Bản đồ hiện sự cố thay cho từng cảnh báo; không cảnh báo nào bị bỏ, nên gộp nhầm chỉ làm bản đồ kém rõ chứ không làm mất người. Bán kính 5 m chọn trên ba đoạn SeaDronesSee (chương 5, Bảng 5.15). Luật gộp là một hàm thuần, chạy trong một giao dịch SQLite.

### 3.7.4. Xếp ưu tiên và công cụ cho đội cứu hộ

Điểm ưu tiên của sự cố là tổng có trọng số, mỗi phần kèm một dòng lý do hiện trên bản đồ: thẻ người vận hành gắn khi xem ảnh cắt (dưới nước 3, trên mái 0,5), độ tin cậy cao nhất, số UAV cùng thấy, số sự cố mở khác trong 30 m, và thời gian chờ chưa xử lý. Trọng số là lựa chọn thiết kế giải thích được, không học từ dữ liệu, vì không có dữ liệu cứu hộ thật để học.

Bản đồ vẽ vùng tìm 95% quanh mỗi sự cố (mục 3.2.3), vị trí UAV, vùng camera đang nhìn và vùng đã quét. Đội cứu hộ đặt vị trí thuyền và nhận khoảng cách, hướng tới từng sự cố, gợi ý thứ tự đi cứu (ưu tiên trước, gần trước), toạ độ để gửi tin nhắn, và tệp GPX cho máy định vị cầm tay. Bản đồ chạy được không cần internet.

## 3.8. Công cụ giả lập dùng để đánh giá

Luận văn không có chuyến bay thật trên vùng lũ, không có thiết bị Jetson và không có mạng thật để thử. Ba công cụ giả lập thay cho các phần đó; cả ba chạy **cùng mã** pipeline ở các mục trên, chỉ thay nguồn đầu vào. Số sinh ra từ đây được ghi nhãn **mô phỏng** hoặc **ước lượng** ở chương 5 và không đặt cạnh số đo.

### 3.8.1. Chuyến bay mô phỏng

Một chuyến bay giả (đường thẳng hoặc quét luống cày) sinh telemetry theo thời gian; người được đặt ở toạ độ biết trước trên mặt nước (rời từng người hoặc theo nhóm, đứng yên hoặc trôi). Hàm ngược của phép chiếu (mục 3.2.2) cho biết mỗi người hiện ở pixel nào trong mỗi khung. Một **detector giả** phát hiện mỗi người với xác suất recall và sinh thêm báo nhầm ngẫu nhiên; recall có thể lấy theo cỡ người trên ảnh từ đường recall đo được trên SeaDronesSee (chương 5, Bảng 5.2), nên quét được độ cao bay. Nhiễu telemetry được giả lập theo đặc tính thật: GPS lệch chậm theo quá trình Gauss–Markov bậc một (tương quan khoảng 30 s), có thể kém đi giữa chuyến; độ cao lệch; la bàn lệch cố định. Vì biết vị trí thật, mô phỏng đo được những chỉ số không đo được trên video: tỉ lệ bỏ sót, báo nhầm mỗi phút, thời gian tới cảnh báo, sai số vị trí, tỉ lệ người nằm trong vùng tìm 95% (định nghĩa ở chương 4, mục 4.3.3).

### 3.8.2. Mạng giả lập

Đường truyền được bọc bằng một lớp giả lập theo đồng hồ mô phỏng, với seed cố định: mất gói rải rác (mỗi lần gửi mất độc lập với xác suất p), **mất theo cụm** (đường truyền đổi qua lại giữa trạng thái tốt và xấu, thời gian ở mỗi trạng thái theo phân phối mũ, trạng thái xấu mất mọi gói; dạng Gilbert–Elliott), và các khoảng mất sóng hoàn toàn. Mất theo cụm cho phép so với mất rải rác ở **cùng tỉ lệ mất trung bình**, chỉ khác mất liền hay rời.

### 3.8.3. Giả lập thời gian thiết bị biên

Không có Jetson nên không đo được trực tiếp, và không có công cụ nào giả lập được GPU của Jetson. Cách làm: pipeline chạy thật trên máy này, nhưng đồng hồ mô phỏng coi mỗi khung tốn thời gian của thiết bị đích,

```
độ_trễ = overhead + số_ô × t_ô + số_lượt_toàn_ảnh × t_toàn_ảnh + megapixel_khung_gốc × t_thu_nhỏ
```

với số ô tính từ kích thước khung sau khi thu nhỏ theo độ cao (mục 3.4), và số hạng cuối chỉ có khi khung bị thu nhỏ. Thiết bị bận tới khi xử lý xong; khung tới trong lúc bận bị bỏ, như trên máy thật, và cảnh báo vào hàng đợi gửi lúc xử lý xong. Hồ sơ thời gian của từng thiết bị lấy từ số đo trên GPU T4 (chương 4, mục 4.4.2) nhân với tỉ lệ thời gian thiết bị/T4 theo bảng benchmark công bố của Ultralytics trên cùng họ mô hình (Bảng 3.x). Số hạng thu nhỏ khung được thêm sau khi đo trên T4 thấy đổi cỡ một khung 4K trên CPU tốn hơn cả suy luận (chương 5, mục 5.2.1).

**Bảng 3.x.** Hồ sơ thời gian thiết bị, TensorRT FP16 (`configs/devices/`, `rq2_t4.md`). Hàng T4 là số đo; các hàng Jetson là ước lượng.

| Thiết bị | overhead (ms) | t_ô, ô 640 (ms) | t_toàn_ảnh, 1280 (ms) | t_thu_nhỏ (ms mỗi megapixel) |
|---|---|---|---|---|
| Tesla T4 (đo) | 0,55 | 3,75 | 23,72 | 5,574 |
| Jetson AGX Orin 64GB | 0,85 | 5,78 | 36,56 | 8,59 |
| Jetson Orin NX 16GB | 1,34 | 9,12 | 57,63 | 13,539 |
| Jetson Orin Nano Super | 1,48 | 10,09 | 63,77 | 14,983 |

Tỉ lệ Jetson/T4 lấy từ thời gian suy luận YOLO26n công bố và được dùng chung cho phần chạy trên CPU (đọc khung, thu nhỏ, gộp box), một giả định chưa kiểm chứng. Không giả lập được: giảm xung khi nóng, chế độ công suất thấp, tranh chấp bộ nhớ dùng chung giữa CPU và GPU.

## Tóm tắt chương

Hệ thống phát hiện người ở độ phân giải gốc bằng cắt ô theo lô, đổi vị trí sang toạ độ mặt đất bằng telemetry, và chỉ cảnh báo khi một vị trí trên mặt đất được thấy lặp lại; cảnh báo được ghi trước khi gửi, gửi toạ độ trước, và gộp thành sự cố ở trạm. Hai thành phần phương pháp chính đều dùng dữ liệu bay sẵn có của UAV: **thu nhỏ khung theo độ cao bay** (đã có công trình trước; luận văn đưa vào pipeline thiết bị biên và đo cả độ chính xác lẫn khối lượng tính) và **xác nhận theo toạ độ mặt đất** (đóng góp chính) (ghép các lần thấy ở nơi người đứng yên, thay cho ghép trên ảnh vốn gãy khi UAV bay nhanh và xử lý ít khung). Chương 4 mô tả dữ liệu và cách đo; chương 5 trình bày kết quả.
