# Thuật toán của FloodEye

Tài liệu này mô tả **thuật toán xử lý trên UAV**: dữ liệu đi qua những bước nào, mỗi bước làm gì và vì sao, kèm một ví dụ tính tay từ đầu đến cuối và nguồn tham khảo cho từng phần. Viết cho người mới tiếp cận thị giác máy tính; thuật ngữ được giải thích khi xuất hiện lần đầu.

Đọc kèm: [TONG_QUAN.md](TONG_QUAN.md) (các bước của cả đồ án), [TECHNICAL.md](TECHNICAL.md) (công thức và chi tiết cài đặt; "T 9.4" là mục 9.4 của TECHNICAL).

Tham số ghi trong tài liệu là giá trị mặc định đang dùng trong mã (`configs/edge.yaml`, `edge/`). Số trong ví dụ ở mục 4 là số tự đặt cho dễ tính, không phải số đo; số đo thật ghi rõ nguồn trong `runs/`.

---

## 1. Ý tưởng cốt lõi

> Tìm người ở từng khung hình với **độ phân giải gốc** (cắt ô), đổi vị trí người sang **toạ độ trên mặt đất**, rồi chỉ cảnh báo khi thấy người ở **cùng một chỗ trên mặt đất qua nhiều khung**.

Ba ý tưởng này giải quyết ba khó khăn của bài toán:

| Khó khăn | Ý tưởng giải quyết | Bước |
|---|---|---|
| Người rất nhỏ trong ảnh (khoảng 25 pixel trong khung 3840 pixel ở 50 m) | Cắt ảnh thành ô nhỏ, giữ nguyên độ phân giải; khi bay thấp người to ra thì thu nhỏ khung theo độ cao trước khi cắt (tuỳ chọn) | Bước 2 |
| Camera bay nên người "trôi" trên ảnh, tracking thông dụng không ghép được | Đổi sang toạ độ mặt đất, nơi người đứng yên | Bước 3, 4 |
| Mô hình đôi khi nhận nhầm sóng, rác là người | Chỉ tin khi thấy lặp lại ở cùng chỗ nhiều lần | Bước 4 |

---

## 2. Đầu vào, đầu ra

**Đầu vào:**
- Video từ camera UAV, nhìn thẳng xuống, 4K (3840 × 2160 pixel), 30 khung mỗi giây.
- **Telemetry**, tức dữ liệu bay của UAV theo thời gian: vĩ độ, kinh độ (GPS), độ cao so với mặt nước, hướng bay (góc so với hướng Bắc).
- Thông số camera: góc nhìn (82° theo đường chéo với camera của DJI Matrice 4T).

**Đầu ra:**
- Các **cảnh báo**, mỗi cảnh báo gồm: mã cảnh báo, toạ độ GPS của người, sai số vị trí ước lượng, độ tin cậy, số khung đã thấy, và một ảnh cắt 256 × 256 pixel quanh người.
- Cảnh báo được gửi về trạm mặt đất và hiện trên bản đồ.

---

## 3. Thuật toán, từng bước

Toàn bộ thuật toán lặp lại cho mỗi khung được lấy:

```
Lặp mỗi 0,5 giây (2 khung mỗi giây):
  Bước 1  LẤY MẪU     lấy một khung ảnh và telemetry tại đúng thời điểm đó
  Bước 2  PHÁT HIỆN   cắt khung thành 32 ô → YOLO tìm người trên cả 32 ô một lượt → ghép, gộp box trùng
  Bước 3  ĐỊNH VỊ     mỗi box người → toạ độ GPS trên mặt đất
  Bước 4  XÁC NHẬN    gom phát hiện theo vị trí mặt đất qua nhiều khung;
                      cụm nào thấy đủ N lần trong T_win giây → tạo cảnh báo (mỗi người một lần)
  Bước 5  GỬI         ghi cảnh báo vào hàng đợi; gửi toạ độ trước, ảnh sau; lỗi thì gửi lại
```

Mã nguồn: mỗi bước là một file trong `edge/`; `edge/main.py` nối chúng lại.

### Bước 1: Lấy mẫu khung hình (`edge/sampler.py`, `edge/telemetry.py`)

**Làm gì.** Video có 30 khung mỗi giây; chỉ lấy một khung sau mỗi `round(30 / 2) = 15` khung, tức 2 khung mỗi giây. Thời điểm của khung tính từ **chỉ số khung**: `t = chỉ số khung / 30`. Telemetry thường ghi ở tần số khác video, nên giá trị tại thời điểm `t` được **nội suy** từ hai mẫu gần nhất. Riêng góc hướng nội suy theo đường ngắn nhất trên vòng tròn (từ 359° sang 1° là tăng 2°, không phải giảm 358°).

**Vì sao chỉ 2 khung mỗi giây.** Máy tính trên UAV không xử lý kịp 30 khung 4K mỗi giây, và cũng không cần. Ở 50 m, vùng chụp dài khoảng 43 m theo chiều bay; bay 10 m/s thì một người nằm trong khung khoảng 4,3 giây. Lấy 2 khung mỗi giây, mỗi người vẫn được nhìn thấy tối đa 8 lần (T 2.4).

Có thể tính trước xác suất bắt được người. Nếu mỗi lần nhìn mô hình thấy người với xác suất `r`, các lần nhìn độc lập, thì xác suất thấy ít nhất `N` trong `K` lần là:

```
P = Σ (k từ N tới K) C(K, k) · r^k · (1 − r)^(K − k)
```

Ví dụ `K = 8`, `r = 0,5`: `N = 3` cho `P ≈ 0,86`; `N = 5` cho `P ≈ 0,36`. Công thức này nối độ chính xác mỗi khung (RQ1) với khả năng của cả hệ thống (RQ3).

**Vì sao thời gian lấy từ chỉ số khung, không lấy từ đồng hồ máy.** Chạy lại cùng một video thì ra đúng cùng kết quả, và mô phỏng chạy nhanh hơn thời gian thực được.

### Bước 2: Phát hiện người (`edge/detector.py`)

**2a. Cắt ô.** Chia khung 3840 × 2160 thành các ô 640 × 640, hai ô cạnh nhau chồng lên nhau 20% (128 pixel). Bước nhảy giữa hai ô là `640 × 0,8 = 512` pixel. Số ô theo một chiều dài `L`:

```
n = ⌈(L − 640) / 512⌉ + 1
```

Chiều ngang 3840: `n = ⌈3200/512⌉ + 1 = 8`. Chiều dọc 2160: `n = ⌈1520/512⌉ + 1 = 4`. Tổng **32 ô**. Ô cuối mỗi hàng, mỗi cột được kéo sát mép ảnh để không thừa ra ngoài.

*Vì sao.* Mô hình YOLO thường thu ảnh về 640 pixel trước khi xử lý. Ảnh 3840 thu về 640 là chia 6: người 25 pixel còn khoảng 4 pixel, gần như biến mất. Cắt ô thì mỗi ô đã là 640 nên không phải thu nhỏ; người vẫn giữ 25 pixel. Các ô chồng nhau để người nằm ở mép ô vẫn trọn vẹn trong ít nhất một ô.

**2b. Chạy mô hình theo lô.** Đưa **cả 32 ô vào YOLO trong một lần gọi**. Mô hình là YOLO26s đã **fine-tune** (học tiếp) trên ảnh UAV: E2c, học trên VisDrone và AFO (`docs/results/E2c.md`). YOLO trả về các **box** (hình chữ nhật bao quanh người, cho bằng toạ độ góc trên trái và góc dưới phải), mỗi box kèm **điểm tin cậy** (`conf`, từ 0 tới 1). Chỉ giữ box có `conf ≥ 0,1`.

*Vì sao theo lô.* GPU xử lý song song nhiều ảnh cùng lúc. Thư viện cắt ô có sẵn (SAHI) gọi mô hình từng ô một, chậm hơn trên GPU và khó dùng với mô hình đã tối ưu cho thiết bị biên (TensorRT).

*Vì sao ngưỡng thấp (0,1).* Để ít bỏ sót người. Các báo nhầm do ngưỡng thấp sinh ra được lọc ở bước 4.

**2c. Đổi toạ độ và gộp box trùng.** Cộng toạ độ góc trên trái của ô vào box để ra toạ độ trên ảnh gốc. Một người nằm ở vùng hai ô chồng nhau sẽ cho hai box gần trùng nhau; phải gộp lại:

```
Sắp các box theo conf giảm dần.
Lặp: lấy box điểm cao nhất còn lại, giữ nó;
     bỏ mọi box còn lại có IOS với nó > 0,5.
IOS (Intersection over Smaller) = diện tích phần giao / diện tích box nhỏ hơn.
```

*Vì sao dùng IOS chứ không dùng IoU.* Người ở mép ô có thể cho một box đầy đủ (từ ô này) và một box nửa người (từ ô bên cạnh). IoU của hai box này chỉ khoảng 0,5 nên dễ bị giữ cả hai. Box nửa người nằm gọn trong box đầy đủ nên IOS gần bằng 1, bị gộp đúng.

*Cách khác đã thử và bỏ:* hợp nhất toạ độ các box trùng (lấy hình chữ nhật bao cả nhóm, như SAHI làm) thay vì giữ box điểm cao nhất. Trên VisDrone, AP50 tụt dưới 0,05, vì box lớn điểm thấp phủ cả đám đông kéo box của từng người thành box cả nhóm (`docs/results/visdrone_tiled_vs_sahi.md`).

**Kết quả đã đo** trên VisDrone val (mô hình chưa fine-tune; `docs/results/visdrone_baseline.md`, `docs/results/visdrone_tiled_vs_sahi.md`):

| Cách | AP50 mọi người | AP50 người dưới 8 px |
|---|---|---|
| Thu ảnh về 640 | 0,276 | 0,050 |
| Thu ảnh về 1280 | 0,497 | 0,167 |
| Cắt ô bằng SAHI | 0,460 | 0,149 |
| Cắt ô theo lô của dự án | 0,452 | 0,153 |

Cắt ô không hơn 1280 trên VisDrone vì ảnh VisDrone chỉ rộng khoảng 1360 pixel. So với SAHI bằng bootstrap cặp, cắt ô của dự án kém hơn 0,008 AP50 (khoảng tin cậy −0,011 đến −0,003) nhưng tốt hơn ở người dưới 8 px.

Trên ảnh 4K thật (SeaDronesSee, người bơi, phần lớn to), cắt ô ở độ phân giải gốc với mô hình fine-tune lại **kém** chạy toàn ảnh: AP50 0,235 so với 0,468. Lý do ở bước 2d.

**2d. Thu nhỏ khung theo độ cao (tuỳ chọn, `--target-person-px`).** Mô hình fine-tune học chủ yếu người nhỏ, nên bắt tốt người khoảng 6–23 pixel mà tụt mạnh với người trên 45 pixel (`docs/results/e6_sds_pilot.md`). Bay thấp thì người to, đúng chỗ mô hình yếu. Trước khi cắt ô, ước lượng người sẽ to bao nhiêu pixel từ độ cao trong telemetry, rồi thu nhỏ khung để người về cỡ mục tiêu:

```
px_dự_kiến = 0,5 m · f / h          (f: tiêu cự tính bằng pixel, h: độ cao)
s = max(1, px_dự_kiến / mục_tiêu)   (không bao giờ phóng to)
thu khung đi s lần → cắt ô → YOLO → nhân toạ độ box với s để về ảnh gốc
```

Ví dụ: ở 30 m người khoảng 42 pixel (T 2.3); mục tiêu 10 pixel thì `s = 4,2`, khung 3840 × 2160 còn khoảng 914 × 514, chỉ cần 2 ô thay vì 32. Box đã quy về ảnh gốc nên bước 3 và 4 không đổi. Trên SeaDronesSee 4K: AP50 từ 0,235 (cắt ô gốc) lên 0,531 với mục tiêu 10 pixel (`docs/results/scale_by_altitude.md`). Mới thử trên một tập biển; còn chờ kiểm chứng trên tập lũ. Mặc định tắt.

### Bước 3: Đổi vị trí trên ảnh sang toạ độ GPS (`edge/georef.py`)

**Giả định:** camera nhìn thẳng xuống. Khi đó **tâm ảnh là điểm ngay dưới UAV**.

**Công thức.** Ký hiệu: ảnh rộng `W`, cao `H`, tâm `(c_x, c_y) = (W/2, H/2)`; độ cao `h`; hướng bay `ψ` (góc của đỉnh ảnh so với hướng Bắc, theo chiều kim đồng hồ); tiêu cự tính bằng pixel `f = (W/2) / tan(góc nhìn ngang / 2)`. Với một điểm ảnh `(u, v)` (u sang phải, v xuống dưới):

```
Bước a: mét theo hướng UAV
  phía trước = −(v − c_y) · h / f          (phía trên ảnh là phía trước)
  bên phải   =  (u − c_x) · h / f

Bước b: xoay sang hướng Bắc, Đông
  Bắc  = phía trước · cos ψ − bên phải · sin ψ
  Đông = phía trước · sin ψ + bên phải · cos ψ

Bước c: cộng vào GPS của UAV (xấp xỉ mặt phẳng, đủ chính xác trong vài km; R = 6.378.137 m)
  vĩ độ  = vĩ độ UAV  + Bắc / R · (180/π)
  kinh độ = kinh độ UAV + Đông / (R · cos(vĩ độ UAV)) · (180/π)
```

`h / f` chính là **GSD**, kích thước một pixel trên mặt đất: ở 50 m khoảng 1,97 cm (`runs/gsd/m4t_diag82/gsd_table.csv`).

Điểm lấy trên box là **tâm cạnh dưới** (chân người khi đứng); nhìn từ trên xuống thì gần trùng tâm box.

**Hàm ngược** (GPS → pixel) làm ngược ba bước trên. Dùng để kiểm thử (đổi đi rồi đổi về phải ra đúng điểm cũ, sai dưới 0,01 pixel) và để mô phỏng.

**Sai số.** Lớn nhất thường là GPS của UAV (vài mét với GPS thường). Các nguồn khác: độ cao sai, hướng bay sai, camera nghiêng (1° ở 50 m làm lệch khoảng 0,9 m ở tâm ảnh), méo ống kính ở mép ảnh (chưa hiệu chỉnh) (T 8.4).

### Bước 4: Xác nhận qua nhiều khung (`edge/confirm.py`)

**Mục tiêu:** chỉ cảnh báo khi một người được thấy ở ít nhất `N` khung, và mỗi người chỉ một cảnh báo.

**Vì sao cần.** Ở một khung, mô hình có thể nhầm sóng, rác, bóng phản chiếu là người. Nhầm kiểu đó thường ngẫu nhiên, không lặp lại ở đúng một chỗ nhiều lần; người thật thì có.

**Vấn đề cần giải quyết:** biết box ở khung này và box ở khung sau là **cùng một người**. Gọi là bước **ghép** (association).

**Thuật toán gom theo vị trí mặt đất (chiến lược `geo`).**

Hệ thống giữ một danh sách **cụm**. Mỗi cụm là một người nghi vấn, gồm: vị trí trên mặt đất, danh sách các lần thấy `(thời điểm, conf)`, lần thấy gần nhất, và cờ "đã cảnh báo".

Tham số mặc định: bán kính gom `r = 3 m`, số lần thấy `N = 3`, cửa sổ đếm `T_win = 5 s`, thời gian xoá cụm `T_exp = 6 s`.

```
Với các phát hiện D của khung tại thời điểm t (đã có toạ độ mặt đất từ bước 3):

  1. XOÁ cụm cũ: bỏ mọi cụm có lần thấy gần nhất cách t quá T_exp giây.

  2. GHÉP:
     tính khoảng cách mặt đất giữa mọi cặp (cụm c, phát hiện d);
     sắp các cặp theo khoảng cách tăng dần;
     duyệt lần lượt: nếu khoảng cách ≤ r và cả c lẫn d chưa được ghép
                     → ghép d vào c, đánh dấu cả hai đã ghép.
     (Ghép một-một: mỗi cụm nhận nhiều nhất một phát hiện mỗi khung,
      để hai người đứng cạnh nhau trong cùng khung không bị nhập làm một.)

  3. CẬP NHẬT:
     phát hiện được ghép → thêm (t, conf) vào cụm; dời vị trí cụm thành
       trung bình có trọng số theo conf của mọi lần thấy;
     phát hiện không ghép được → tạo cụm mới tại vị trí đó.

  4. XÁC NHẬN:
     với mỗi cụm chưa cảnh báo: đếm số lần thấy trong T_win giây gần nhất;
     nếu ≥ N → tạo cảnh báo (vị trí cụm, conf trung bình, số lần thấy),
               đánh dấu cụm "đã cảnh báo".
```

Khoảng cách mặt đất tính bằng xấp xỉ mặt phẳng: đổi chênh lệch vĩ độ, kinh độ sang mét Bắc, Đông rồi lấy căn bậc hai tổng bình phương.

**Độ phức tạp.** Với `n` phát hiện và `m` cụm mỗi khung, bước ghép tính `n × m` khoảng cách và sắp xếp chúng: `O(nm log(nm))`. Mỗi khung chỉ vài chục phát hiện và cụm, nên không đáng kể so với chạy YOLO trên 32 ô.

**Hai chiến lược khác để so sánh trong RQ3.** Cả ba dùng chung bước 1, 3, 4 ở trên (xoá, cập nhật, xác nhận); chỉ khác **cách ghép** ở bước 2, để so sánh công bằng:

| Chiến lược | Ghép bằng | Ý tưởng |
|---|---|---|
| `geo` | Khoảng cách mặt đất ≤ r | Như trên |
| `bytetrack` | Độ chồng nhau của box trên ảnh (IoU), bộ lọc Kalman dự đoán vị trí box ở khung sau, hai vòng ghép (box điểm cao trước, box điểm thấp sau) | Cách tracking thông dụng nhất hiện nay |
| `bytetrack_cmc` | Như `bytetrack`, nhưng trước khi ghép, dời mọi track của khung trước theo **chuyển động camera** tính từ telemetry | Bù chuyển động camera |

**Vì sao `bytetrack` gãy ở đây.** ByteTrack được thiết kế cho camera gần như đứng yên, khi một người giữa hai khung chỉ dịch vài pixel. Ở đây UAV bay 5 m giữa hai khung (10 m/s, 2 khung mỗi giây). Ở 50 m, 5 m tương đương khoảng **254 pixel**, trong khi box người chỉ khoảng 25 pixel. Hai box của cùng một người không chồng nhau, IoU bằng 0, nên ByteTrack coi đó là người mới ở mỗi khung. Bộ lọc Kalman không cứu được vì chuyển động là của camera chứ không phải của người, và ở khung đầu của một track, Kalman chưa biết vận tốc (T 9.2).

**Cách `bytetrack_cmc` bù chuyển động.** Lấy 4 góc ảnh, đổi sang GPS bằng telemetry khung trước, rồi đổi ngược về pixel bằng telemetry khung này; khớp một phép biến đổi affine (dịch, xoay, co giãn) từ 4 cặp điểm đó; áp lên vị trí và vận tốc của mọi track trước khi ghép (`georef.frame_motion`, T 9.3). Cách này kế thừa mọi sai số của telemetry: GPS dao động vài chục cm giữa hai khung là đủ lệch vài chục pixel, xấp xỉ cỡ box người.

**Vì sao `geo` không gặp vấn đề đó.** Người đứng yên (hoặc trôi chậm) trên mặt nước, nên **toạ độ mặt đất của họ gần như không đổi giữa các khung**, dù camera bay. Bán kính `r` tính bằng mét, chịu được sai số GPS cỡ vài mét, vì GPS lệch chậm: giữa hai khung cách 0,5 giây, sai số gần như giống nhau.

**Kết quả mô phỏng chạy thử** (10 người, mô hình giả bắt được 70% mỗi khung, 0,5 báo nhầm mỗi khung, 3 lần lặp; chưa phải kết quả chính thức; `runs/rq3/gps/summary.csv`). Tỉ lệ bỏ sót:

| Sai số GPS | `geo` | `bytetrack` | `bytetrack_cmc` |
|---|---|---|---|
| 0 m | 0,000 | 1,000 | 0,000 |
| 0,5 m | 0,000 | 1,000 | 0,200 |
| 1 m | 0,000 | 1,000 | 0,767 |
| 3 m | 0,033 | 1,000 | 1,000 |

Không có báo động giả nào ở cả ba cách: báo nhầm ngẫu nhiên không lặp lại ở cùng chỗ 3 lần. `bytetrack_cmc` bỏ sót chủ yếu do **độ chênh GPS giữa hai khung liên tiếp**, không phải sai số tuyệt đối: cùng sai số 0,5 m ở 50 m, GPS nhảy nhanh bỏ sót 0,900, trôi chậm chỉ 0,033 (`docs/results/rq3_cmc_cause.md`).

**Kiểm chứng trên video thật** (SeaDronesSee, 2 khung mỗi giây, sơ bộ): `geo` xác nhận 12/19 người ở đoạn đông nhất, `bytetrack` 2/19 (`docs/results/sds_mot_confirm.md`).

**Điểm yếu của `geo`:**
- Hai người đứng gần nhau hơn `r` có thể bị gộp thành một cảnh báo. Trong cứu hộ, lỗi này ít nguy hiểm hơn bỏ sót: đội cứu hộ tới nơi vẫn thấy cả nhóm.
- Người trôi theo dòng nước: tâm cụm là trung bình các lần thấy nên đi chậm hơn vị trí thật. Người trôi đủ nhanh để cách tâm cụm hơn `r` sẽ bị tách thành cụm mới (tách nhầm). Ngưỡng tốc độ cụ thể chưa đo; mô phỏng có kịch bản người trôi (`--drift-mps`).
- Dựa vào định vị: telemetry sai lớn (hướng bay sai nhiều độ) thì vị trí các lần thấy tản ra.

### Bước 5: Gửi cảnh báo (`edge/alerts.py`, `ground/`)

**Hàng đợi lưu trên UAV** (bảng SQLite). Mỗi cảnh báo sinh hai thông điệp cùng mã cảnh báo:
- `coords`: toạ độ và thông tin, vài trăm byte, **ưu tiên cao**;
- `crop`: ảnh cắt JPEG 256 × 256 quanh người, khoảng vài chục KB, chỉ gửi **sau khi** trạm đã xác nhận nhận được `coords`.

**Vòng gửi**, chạy mỗi khung (và tiếp tục sau khi video kết thúc):

```
Lặp: lấy thông điệp chưa gửi được, đến hạn thử, ưu tiên cao nhất, cũ nhất;
     gửi;
     trạm xác nhận đã nhận → đánh dấu xong;
     lỗi → hẹn thử lại sau min(30, 1 · 2^(số lần đã thử − 1)) giây, nhân thêm 0–20% ngẫu nhiên;
           dừng lượt gửi này (đường truyền đang hỏng, gửi tiếp chỉ tốn băng thông).
```

**Trạm mặt đất** bỏ qua thông điệp có mã đã nhận. Gửi lại bao nhiêu lần cũng không sinh cảnh báo trùng.

**Gộp thành sự cố ở trạm** (`ground/incidents.py`). Trên video thật, `geo` đôi khi cảnh báo một người hai lần khi GPS trôi làm người đó rơi ra khỏi cụm cũ. Trạm gắn mỗi cảnh báo mới vào **sự cố** còn mở gần nhất trong 5 m và 300 giây (theo đồng hồ chuyến bay); không có thì mở sự cố mới. Vị trí sự cố là trung bình các cảnh báo; bản đồ hiện sự cố thay cho từng cảnh báo. Không cảnh báo nào bị bỏ, nên gộp nhầm chỉ làm bản đồ kém rõ chứ không làm mất người. Cách chặn ngay trên UAV (không cảnh báo lại trong bán kính quanh chỗ đã cảnh báo, `--suppress-s`) đã thử và tắt, vì nó chặn luôn người thật thứ hai đứng gần (`docs/results/alert_memory.md`).

*Vì sao.* Ghi trước khi gửi để mất điện, mất mạng không làm mất cảnh báo. Toạ độ gửi trước vì quan trọng nhất và nhỏ nhất. Thời gian chờ tăng dần để không dội liên tục khi mất sóng; phần ngẫu nhiên để nhiều UAV không cùng gửi lại một lúc khi sóng có lại.

---

## 4. Ví dụ tính tay từ đầu đến cuối

Số tự đặt cho dễ tính, không phải số đo.

### Bối cảnh

- UAV bay ở **50 m**, hướng **Bắc**, **10 m/s**, lấy **2 khung mỗi giây**; giữa hai khung UAV bay **5 m**.
- Để dễ tính, coi **1 pixel = 2 cm**. Tâm ảnh là pixel (1920, 1080), ngay dưới UAV.
- Toạ độ mặt đất đơn giản: **x** = mét về phía Đông, **y** = mét về phía Bắc, tính từ điểm UAV xuất phát.
- **An** đứng yên trên mái nhà tại **(3, 20)**.
- Sóng nước đôi khi bị nhận nhầm là người.
- Tham số xác nhận: `r = 3 m`, `N = 3`, `T_win = 5 s`, `T_exp = 6 s`.
- Để đơn giản, lấy tâm box làm vị trí (mã thật lấy tâm cạnh dưới).

### Bước 1: bốn khung

| Khung | Thời điểm | UAV ở y = | An cách UAV về phía trước | An ở hàng pixel |
|---|---|---|---|---|
| K1 | 0,0 s | 0 m | 20 m | 1080 − 20/0,02 = **80** |
| K2 | 0,5 s | 5 m | 15 m | 1080 − 750 = **330** |
| K3 | 1,0 s | 10 m | 10 m | 1080 − 500 = **580** |
| K4 | 1,5 s | 15 m | 5 m | 1080 − 250 = **830** |

Cột pixel của An luôn là 1920 + 3/0,02 = **2070**.

**An đứng yên nhưng trên ảnh trôi xuống 250 pixel mỗi khung**, trong khi An chỉ rộng khoảng 25 pixel (0,5 m ÷ 2 cm).

### Bước 2: phát hiện

An ở cột 2070, nằm trong vùng chồng nhau của ô bắt đầu từ cột 1536 (phủ 1536–2176) và ô bắt đầu từ cột 2048 (phủ 2048–2688). Hai ô cùng cho box của An; bước gộp giữ lại một box.

Giả sử mô hình cho ra (cố ý cho bỏ sót An ở K2 và nhận nhầm sóng):

| Khung | Box (tâm, pixel) | conf | Thật ra là |
|---|---|---|---|
| K1 | (2070, 80) | 0,6 | An |
| K1 | (900, 1500) | 0,3 | sóng |
| K2 | (3100, 400) | 0,3 | sóng (An bị bỏ sót) |
| K3 | (2072, 581) | 0,7 | An |
| K4 | (2069, 829) | 0,8 | An |

### Bước 3: định vị

```
x = (cột − 1920) × 0,02
y = y_UAV + (1080 − hàng) × 0,02
```

| Khung | Box | Toạ độ mặt đất |
|---|---|---|
| K1 | An (2070, 80) | x = 150 × 0,02 = 3; y = 0 + 1000 × 0,02 = 20 → **(3; 20)** |
| K1 | sóng (900, 1500) | **(−20,4; −8,4)** |
| K2 | sóng (3100, 400) | x = 1180 × 0,02; y = 5 + 680 × 0,02 → **(23,6; 18,6)** |
| K3 | An (2072, 581) | **(3,04; 19,98)** |
| K4 | An (2069, 829) | **(2,98; 20,02)** |

Trên ảnh, An nhảy từ hàng 80 tới 581 rồi 829. **Trên mặt đất, An luôn ở khoảng (3; 20).**

### Bước 4: xác nhận bằng `geo`

| Khung | Phát hiện | Khoảng cách tới các cụm | Hành động | Trạng thái sau khung |
|---|---|---|---|---|
| K1 | An (3; 20) | chưa có cụm | tạo **cụm A** | A: 1 lần |
| K1 | sóng (−20,4; −8,4) | A: √(23,4² + 28,4²) ≈ 37 m | tạo **cụm B** | B: 1 lần |
| K2 | sóng (23,6; 18,6) | A: √(20,6² + 1,4²) ≈ 20,6 m; B: xa | tạo **cụm C** | C: 1 lần |
| K3 | An (3,04; 19,98) | A: khoảng 0,04 m ≤ 3 | ghép vào **A**; tâm A dời thành trung bình có trọng số conf: ((3 · 0,6 + 3,04 · 0,7) / 1,3; …) ≈ (3,02; 19,99) | A: 2 lần |
| K4 | An (2,98; 20,02) | tâm A (3,02; 19,99): khoảng 0,05 m ≤ 3 | ghép vào **A** | A: **3 lần trong 1,5 s** → **CẢNH BÁO** |

Sau đó, B và C không được thấy lại; sau 6 giây bị xoá, không bao giờ thành cảnh báo. An ở các khung tiếp theo vẫn ghép vào A nhưng không sinh cảnh báo mới (A đã cảnh báo).

Ví dụ cho thấy ba tính chất:
1. **Lọc báo nhầm:** sóng không lặp lại ở cùng chỗ.
2. **Chịu được bỏ sót:** An bị bỏ sót ở K2 vẫn được xác nhận, vì luật là "N lần trong T_win giây", không đòi N khung liên tiếp.
3. **Mỗi người một cảnh báo.**

### So sánh: `bytetrack` trên cùng ví dụ

Giả sử box của An cao 50 pixel:

| Khung | Box của An trên ảnh (hàng) |
|---|---|
| K1 | 55 tới 105 |
| K3 | 556 tới 606 |
| K4 | 804 tới 854 |

Box K1 và K3 cách nhau hơn 450 pixel, không chồng nhau; K3 và K4 cũng vậy. IoU bằng 0, nên ByteTrack tạo một track mới ở mỗi khung. An bị coi là ba người khác nhau, mỗi người thấy một lần: **không bao giờ đủ 3 lần, không cảnh báo**.

`bytetrack_cmc` dời box K3 xuống 250 pixel trước khi so với K4, nên khớp. Nhưng nếu GPS dao động 0,5 m giữa hai khung, phép dời lệch 25 pixel, đúng bằng cỡ người, và việc ghép bắt đầu thất bại.

### Bước 5: gửi

Cảnh báo "người tại (3; 20)" được ghi vào hàng đợi, gửi `coords` trước. Nếu mất sóng: thử lại sau khoảng 1, 2, 4… giây. Trạm nhận được thì hiện một chấm trên bản đồ; sau đó nhận `crop` và hiện ảnh cắt khi bấm vào chấm.

---

## 5. Tham số và cách chọn

| Tham số | Mặc định | Ý nghĩa | Cách chọn |
|---|---|---|---|
| Số khung mỗi giây `F` | 2 | Tần số xử lý | Đủ để mỗi người được thấy nhiều lần (bước 1); giới hạn bởi tốc độ thiết bị (RQ2) |
| Cạnh ô, độ chồng | 640, 0,2 | Cắt ô | Ô 640 chạy ở imgsz 640 nên 1 pixel ảnh là 1 pixel vào mạng; chồng 20% như SAHI |
| Cỡ người mục tiêu `--target-person-px` | tắt | Thu nhỏ khung theo độ cao (bước 2d) | Đã thử 10 và 20 pixel trên SeaDronesSee; chọn trên dữ liệu ngoài tập test lũ |
| Ngưỡng `conf` | 0,1 | Giữ box nào | Thấp để ít bỏ sót; bước 4 lọc báo nhầm |
| Ngưỡng gộp IOS | 0,5 | Gộp box trùng giữa các ô | Như SAHI |
| Bán kính gom `r` | 3 m | Cùng một người nếu gần hơn | Vài lần sai số định vị tương đối giữa hai khung; quét 1, 2, 3, 5, 8 m trong RQ3 |
| Số lần thấy `N` | 3 | Xác nhận | Nhỏ hơn số lần tối đa nhìn thấy được (8 ở 50 m, 10 m/s); quét 1, 3, 5, 10 trong RQ3 |
| Cửa sổ `T_win` | 5 s | Đếm lần thấy trong khoảng này | Cỡ thời gian người nằm trong khung |
| Thời gian xoá `T_exp` | 6 s | Bỏ cụm không thấy lại | Lớn hơn `T_win` một chút |
| Bán kính, cửa sổ gộp sự cố (trạm) | 5 m, 300 s | Gắn cảnh báo vào sự cố cũ | Trên ba đoạn SeaDronesSee, 10 m làm mọi người đều nằm trong sự cố lẫn người khác; 5 m không gộp nhầm ở hai đoạn thưa, còn đoạn đông nhất vẫn có (`alert_memory.md`, `runs/sds/incident_merge.csv`) |

Đánh đổi chính của RQ3: **ngưỡng conf thấp với N lớn** hay **ngưỡng cao với N nhỏ**. Công thức nhị thức ở bước 1 giúp dự đoán trước.

---

## 6. Giả định và giới hạn

| Giả định | Khi sai thì sao | Xử lý trong đồ án |
|---|---|---|
| Camera nhìn thẳng xuống | Vị trí lệch khoảng `h · tan(góc nghiêng)` | Mô phỏng nghiêng 1–3°; nêu trong giới hạn |
| Mặt nước phẳng, độ cao lấy so với mặt nước | Độ cao sai làm vị trí lệch theo tỉ lệ | Hiệu chỉnh độ cao theo mặt nước khi đọc telemetry |
| Ống kính không méo | Mép ảnh lệch thêm | Chưa hiệu chỉnh; nêu trong giới hạn |
| Người đứng yên hoặc trôi chậm | Người di chuyển nhanh có thể bị tách thành nhiều cụm | Mô phỏng có kịch bản người trôi |
| Telemetry đồng bộ với video | Lệch thời gian làm lệch vị trí | Cần kiểm tra với file SRT thật của DJI |

---

## 7. Nguồn tham khảo cho từng phần

Cột "Trạng thái" cho biết nguồn đã được tra trên mạng trong quá trình làm dự án hay mới là trích dẫn từ trí nhớ. **Trước khi đưa vào luận văn, mở từng bài kiểm tra lại tên, tác giả, năm, nơi công bố và nội dung.**

| Phần | Nguồn | Quan hệ với dự án | Trạng thái |
|---|---|---|---|
| Mô hình phát hiện | Redmon và cộng sự, "You Only Look Once", CVPR 2016 (bài gốc của họ YOLO); tài liệu YOLO26 của Ultralytics | Dùng lại | Từ trí nhớ |
| Cắt ô, gộp bằng IOS | Akyon và cộng sự, "Slicing Aided Hyper Inference and Fine-tuning for Small Object Detection" (SAHI), ICIP 2022 | Dựa trực tiếp; chạy theo lô là cải tiến kỹ thuật | Từ trí nhớ; mã SAHI 0.12.8 đã dùng trong dự án |
| Người rất nhỏ, khớp thang kích thước khi huấn luyện | Yu và cộng sự, "Scale Match for Tiny Person Detection" (TinyPerson), WACV 2020 | Dựa trên ý tưởng | Từ trí nhớ |
| Phát hiện nhiều tầng, đầu P2 | Lin và cộng sự, "Feature Pyramid Networks for Object Detection", CVPR 2017 | Kiến thức nền | Từ trí nhớ |
| Dữ liệu UAV | Zhu và cộng sự, VisDrone; Nihal và cộng sự, C2A (arXiv 2408.04922) | Dùng lại | C2A đã tra |
| Chiếu pixel sang mặt đất | Hartley và Zisserman, *Multiple View Geometry in Computer Vision* (mô hình camera lỗ kim) | Kiến thức nền | Từ trí nhớ |
| Tracking mốc so sánh | Zhang và cộng sự, "ByteTrack: Multi-Object Tracking by Associating Every Detection Box", ECCV 2022 | Mốc so sánh; dùng mã của Ultralytics | Từ trí nhớ |
| Bù chuyển động camera | Aharon, Orfaig, Bobrovsky, "BoT-SORT: Robust Associations Multi-Pedestrian Tracking", arXiv 2206.14651, 2022 | BoT-SORT ước lượng chuyển động camera từ ảnh; dự án tính từ telemetry | Đã tra |
| Gộp phát hiện thành bản đồ vị trí | "Human Body Detection and Geolocalization for UAV Search and Rescue Missions Using Color and Thermal Imagery" (Rudol và Doherty, khoảng 2008) | Công trình gần nhất với ý tưởng `geo` tìm được tới nay | Đã tra tiêu đề; cần kiểm tra tác giả, năm, nội dung |
| Xác nhận "thấy M lần trong N lần quét" | Luật xác nhận track kinh điển trong theo dõi mục tiêu bằng radar (sách của Blackman; của Bar-Shalom) | Cùng nguyên lý với bước xác nhận N lần | Từ trí nhớ |
| Nhiễu GPS Gauss–Markov | Brown và Hwang, *Introduction to Random Signals and Applied Kalman Filtering* | Mô hình nhiễu trong mô phỏng | Từ trí nhớ |
| Tổng quan phát hiện người cho tìm kiếm cứu nạn | "Aerial Person Detection for Search and Rescue: Survey and Benchmarks"; "Maritime Search and Rescue Missions with Aerial Images: A Survey" (arXiv 2411.07649) | Bối cảnh, chương 2 | Đã tra |

**Phần nào là của dự án:**
- **Kế thừa có cải tiến:** cắt ô theo lô; fine-tune và đánh giá theo nhóm kích thước người.
- **Phân tích có cơ sở:** vì sao tracking trên ảnh gãy khi UAV bay nhanh và xử lý ít khung, có chứng minh bằng kiểm thử và mô phỏng.
- **Đề xuất của dự án:** xác nhận bằng gom theo toạ độ mặt đất, ghép từ phép chiếu ảnh lên mặt đất và luật xác nhận M trên N. **Chưa khảo sát tài liệu một cách có hệ thống**, nên chưa khẳng định được đây là cách mới; cần tìm công trình gần nhất để trích dẫn và so sánh.
- **Đề xuất đang cân nhắc** (quyết định #13 của ROADMAP): chọn thang ảnh theo độ cao bay (bước 2d), tức nối khối phát hiện với telemetry. Ý tưởng gần với "khớp thang kích thước" của TinyPerson (bảng trên), nhưng làm lúc chạy thay vì lúc huấn luyện; cũng cần tìm công trình gần nhất.

---

## 8. Mã nguồn tương ứng

| Bước | File | Hàm, lớp chính |
|---|---|---|
| 1 | `edge/sampler.py`, `edge/telemetry.py` | `iter_timed_frames`, `SampledTelemetry.at` |
| 2 | `edge/detector.py`, `edge/georef.py` | `tile_origins`, `merge_boxes`, `YoloDetector.detect`, `person_scale`, `expected_person_px` |
| 3 | `edge/georef.py` | `pixel_to_gps`, `gps_to_pixel`, `locate`, `frame_motion` |
| 4 | `edge/confirm.py`, `edge/detector.py` | `GeoConfirmer`, `TrackConfirmer`, `ByteTracker` |
| 5 | `edge/alerts.py`, `ground/app.py`, `ground/incidents.py` | `Outbox.enqueue`, `Outbox.pump`, `create_app`, `choose_incident` |
| Nối các bước | `edge/main.py` | `main`, `build_confirmer` |
| Kiểm thử | `tests/test_georef.py`, `tests/test_confirm.py`, `tests/test_detector.py`, `tests/test_alerts.py` | Kiểm thử ByteTrack gãy và `geo` xác nhận ở khung thứ 3: `test_bytetrack_breaks_at_2fps_and_camera_motion_compensation_fixes_it` |
