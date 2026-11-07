# RQ3c mô phỏng: tự hiệu chỉnh lệch la bàn trên UAV (`--yaw-calib`)

**Mô phỏng.** Nối tiếp `rq3_geoerr.md`: la bàn lệch cố định làm cùng một người bị chiếu về các vị trí khác nhau khi drone bay qua, nên bị tách thành nhiều cảnh báo (ở 100 m, lệch 5°: tách nhầm 5,333 mỗi kịch bản). Đề xuất ở `docs/CAI_TIEN.md` mục 3.3: UAV tự ước lượng lệch bằng cách so hướng di chuyển tính từ GPS với hướng la bàn khi bay thẳng, rồi trừ đi.

## Cách làm

- `edge/telemetry.YawCalibrated` (TECHNICAL 8.4): trên lưới thời gian mỗi 0,5 s, hướng di chuyển tính từ hai điểm GPS cách nhau 2 s; lấy mẫu lệch = yaw − hướng di chuyển khi vận tốc ≥ 3 m/s và cả hướng di chuyển lẫn yaw đổi không quá 5° giữa hai đoạn 2 s liên tiếp (bỏ đoạn rẽ, đứng yên). Lệch ước lượng là trung vị 120 mẫu gần nhất, chỉ dùng khi đủ 10 mẫu, độ tản (trung vị độ lệch tuyệt đối) ≤ 10° và lệch ≤ 30°. Chỉ dùng telemetry đến thời điểm hiện tại. Giả định: mũi máy (và camera) nhìn theo hướng bay khi quét.
- Kịch bản như `rq3_geoerr.md`: 60 s, 10 người, 10 m/s, 2 khung/giây, detector giả recall 0,7, 0,5 báo nhầm mỗi khung, GPS Gauss–Markov τ 30 s; xác nhận geo, N = 3; mô hình sai số mặc định; 3 seed. Thêm đường bay quét luống (`--pattern zigzag`, mỗi luống 200 m, có rẽ).
- Lưới: độ cao {50, 100} m × GPS σ {1, 3} m × lệch la bàn {0, 5, 10}° × đường bay {thẳng, luống} × hiệu chỉnh {tắt, bật}. Cấu hình `configs/experiments/rq3_yawcalib.yaml`; chỉ số từ `runs/rq3/yawcalib/summary.csv` (trung bình 3 seed, `eval/rq3_metrics.py`); lệch ước lượng từ `runs/rq3/yawcalib/yaw_calib/summary.csv` (`eval/yaw_calib_summary.py`).

## Lệch ước lượng được

| GPS σ | Đường bay | Sai số tuyệt đối lớn nhất của lệch ước lượng (cuối chuyến) | Số mẫu bay thẳng trung bình | Bắt đầu hiệu chỉnh muộn nhất |
|---|---|---|---|---|
| 1 m | thẳng | 0,228° | 112,000 | giây 9 |
| 1 m | luống | 0,507° | 86,333 | giây 9 |
| 3 m | thẳng | 0,481° | 81,667 | giây 13 |
| 3 m | luống | 1,442° | 63,167 | giây 13 |

Giống nhau ở cả ba mức lệch thật (0, 5, 10°), vì cùng kịch bản chỉ khác hằng số cộng vào yaw. Đường quét luống cho lệch ước lượng trung bình cao hơn lệch thật (GPS 1 m: 5,306 khi lệch thật 5; GPS 3 m: 5,837): một phần đoạn rẽ vẫn lọt qua bộ lọc 5°.

## Ảnh hưởng tới cảnh báo (tắt → bật, trung bình 3 seed)

| Độ cao | GPS σ | Đường bay | Lệch la bàn | Tách nhầm | Sai số vị trí trung vị (m) | Báo giả mỗi phút | Bỏ sót | Trong vùng 95% |
|---|---|---|---|---|---|---|---|---|
| 50 m | 1 m | thẳng | 0° | 0,000 → 0,000 | 1,282 → 1,324 | 0,000 → 0,000 | 0,000 → 0,000 | 1,000 → 1,000 |
| 50 m | 1 m | thẳng | 5° | 0,333 → 0,000 | 1,692 → 1,280 | 0,000 → 0,000 | 0,000 → 0,000 | 1,000 → 1,000 |
| 50 m | 1 m | thẳng | 10° | 2,333 → 0,000 | 3,198 → 1,383 | 0,000 → 0,000 | 0,067 → 0,000 | 1,000 → 1,000 |
| 50 m | 1 m | luống | 10° | 4,667 → 1,667 | 4,107 → 1,160 | 0,000 → 0,333 | 0,067 → 0,000 | 1,000 → 1,000 |
| 50 m | 3 m | thẳng | 10° | 2,000 → 0,667 | 4,729 → 4,104 | 0,000 → 0,000 | 0,167 → 0,067 | 1,000 → 1,000 |
| 50 m | 3 m | luống | 10° | 4,667 → 2,000 | 5,806 → 3,535 | 0,333 → 0,333 | 0,167 → 0,000 | 0,884 → 1,000 |
| 100 m | 1 m | thẳng | 0° | 0,000 → 0,000 | 1,387 → 1,538 | 0,000 → 0,000 | 0,000 → 0,000 | 1,000 → 1,000 |
| 100 m | 1 m | thẳng | 5° | 5,333 → 0,333 | 2,572 → 1,652 | 0,000 → 0,000 | 0,000 → 0,000 | 1,000 → 1,000 |
| 100 m | 1 m | thẳng | 10° | 9,000 → 1,000 | 5,315 → 1,652 | 0,000 → 0,000 | 0,000 → 0,000 | 1,000 → 1,000 |
| 100 m | 1 m | luống | 5° | 8,333 → 3,000 | 4,288 → 1,348 | 0,000 → 0,000 | 0,000 → 0,000 | 1,000 → 1,000 |
| 100 m | 1 m | luống | 10° | 7,667 → 3,000 | 7,187 → 1,366 | 13,667 → 1,333 | 0,033 → 0,000 | 1,000 → 1,000 |
| 100 m | 3 m | thẳng | 0° | 2,000 → 1,667 | 4,275 → 4,711 | 0,000 → 0,000 | 0,033 → 0,033 | 1,000 → 1,000 |
| 100 m | 3 m | thẳng | 5° | 5,000 → 2,000 | 4,206 → 4,770 | 0,000 → 0,000 | 0,033 → 0,033 | 1,000 → 1,000 |
| 100 m | 3 m | thẳng | 10° | 8,000 → 2,000 | 5,621 → 4,779 | 1,333 → 0,000 | 0,033 → 0,033 | 0,933 → 1,000 |
| 100 m | 3 m | luống | 10° | 6,667 → 6,000 | 6,970 → 3,803 | 17,667 → 3,333 | 0,133 → 0,033 | 0,919 → 1,000 |

Đủ 48 ô ở `summary.csv`; các ô không chép ở đây cùng xu hướng.

## Nhận xét

1. **Hiệu chỉnh khử gần hết tách nhầm do la bàn lệch khi GPS tốt.** Ở 100 m, GPS σ 1 m, bay thẳng: lệch 5° từ 5,333 xuống 0,333 tách nhầm mỗi kịch bản, lệch 10° từ 9,000 xuống 1,000; sai số vị trí trung vị về gần mức không lệch (1,652 m so với 1,387 m khi la bàn đúng).
2. **Lệch lớn làm cảnh báo chệch quá 10 m thành báo giả**: quét luống ở 100 m, lệch 10°, báo giả mỗi phút 13,667 (GPS 1 m) và 17,667 (GPS 3 m); bật hiệu chỉnh còn 1,333 và 3,333. Vùng tìm 95% lại chứa mọi người (0,919 → 1,000).
3. **Khi la bàn không lệch, hiệu chỉnh có giá nhỏ**: lệch ước lượng sai vài phần mười độ nên sai số vị trí tăng nhẹ (100 m, GPS 1 m, bay thẳng: 1,387 → 1,538 m; GPS 3 m: 4,275 → 4,711 m). Với GPS σ 3 m, sai số vị trí bị nhiễu GPS chi phối và ở một số ô bật hiệu chỉnh cho sai số trung vị cao hơn tắt (100 m, lệch 5°: 4,206 → 4,770 m) dù tách nhầm vẫn giảm (5,000 → 2,000); 3 seed chưa đủ để tách hai hiệu ứng này.
4. **Quét luống còn tách nhầm cả khi la bàn đúng** (100 m, GPS 3 m: 5,667) vì rẽ đổi hướng nhìn; hiệu chỉnh không chữa phần này. Phần còn lại trạm mặt đất gộp thành sự cố (`alert_memory.md`).
5. **Đề xuất:** bật `--yaw-calib` khi drone bay quét theo đường thẳng hoặc luống, mũi máy theo hướng bay. Không bật khi drone bay ngang hoặc xoay tại chỗ (bộ lọc độ tản sẽ không áp dụng hiệu chỉnh, nhưng chưa kiểm chứng trên log thật). Màn hình điều phối hiện lệch đang trừ ở thẻ drone.

## Giới hạn

- Mô phỏng: yaw thật luôn trùng hướng bay (không có gió đẩy ngang); lệch la bàn là hằng số trong cả chuyến; 3 seed mỗi ô.
- Chưa thử trên log bay thật: SeaDronesSee có drone gần như đứng yên hoặc xoay gimbal độc lập với thân máy (`georef_pitch.md`).

## Tái lập

```bash
.venv/bin/python -m sim.sweep_rq3 --config configs/experiments/rq3_yawcalib.yaml --jobs 6
.venv/bin/python eval/yaw_calib_summary.py --runs runs/rq3/yawcalib --output runs/rq3/yawcalib/yaw_calib
```
