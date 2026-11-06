# RQ3c mô phỏng: sai số vị trí cảnh báo theo GPS, hướng bay và độ cao

**Mô phỏng.** Câu hỏi: sai số GPS, sai số hướng bay và sai số độ cao trong telemetry làm vị trí cảnh báo lệch bao nhiêu, và bán kính sai số mà hệ thống tự ghi kèm mỗi cảnh báo có chứa người thật không khi điều kiện thật khác giả định.

## Cách làm

- Kịch bản `sim/make_rq3.py`: 60 s, 10 người đứng yên, cách đường bay tối đa 25 m, 10 m/s, 2 khung/giây, ảnh 4K, góc nhìn 82° chéo; detector giả recall 0,7, 0,5 báo nhầm mỗi khung; 3 seed.
- Nhiễu thật trong telemetry: GPS Gauss–Markov σ mỗi trục, τ 30 s (TECHNICAL mục 11); hướng bay lệch cố định `--yaw-bias-deg`; độ cao lệch cố định `--alt-bias-m`.
- Pipeline: xác nhận geo, N = 3, mô hình sai số **giữ mặc định** (GPS 3 m, độ cao 2 m, hướng 2°, nghiêng 1°; TECHNICAL mục 8.4), như khi chưa biết GPS thật tốt hay kém.
- Chỉ số (`eval/rq3_metrics.py`, TECHNICAL mục 15.4): sai số vị trí lấy ở **cảnh báo đầu tiên** của mỗi người; "trong bán kính 1σ" là tỉ lệ người có sai số ≤ `position_error_m` của cảnh báo đó; "trong vùng 95%" là ≤ 2,448 × `position_error_m` (`shared/schema.py`, `R95_FACTOR`). Chỉ tính người đã được cảnh báo; cảnh báo lệch quá 10 m (`r_eval`) bị tính là báo động giả và người đó là bỏ sót.
- Lưới: độ cao {50, 100} m × GPS σ {0, 1, 3, 5} m × lệch hướng {0, 5}° × lệch độ cao {0, 5} m. Cấu hình `configs/experiments/rq3_geoerr.yaml`, kết quả `runs/rq3/geoerr/summary.csv` (cột `*_mean`, trung bình 3 seed).

## Chỉ có nhiễu GPS (hướng và độ cao đúng)

| Độ cao | GPS σ | Sai số trung vị (m) | Sai số lớn nhất (m) | Trong bán kính 1σ | Trong vùng 95% | Bỏ sót | Tách nhầm |
|---|---|---|---|---|---|---|---|
| 50 m | 0 m | 0,250 | 0,290 | 1,000 | 1,000 | 0,000 | 0,000 |
| 50 m | 1 m | 1,282 | 1,908 | 1,000 | 1,000 | 0,000 | 0,000 |
| 50 m | 3 m | 3,956 | 5,680 | 0,278 | 1,000 | 0,033 | 0,333 |
| 50 m | 5 m | 6,591 | 8,356 | 0,181 | 0,833 | 0,100 | 1,333 |
| 100 m | 0 m | 0,250 | 0,250 | 1,000 | 1,000 | 0,000 | 0,000 |
| 100 m | 1 m | 1,387 | 1,919 | 1,000 | 1,000 | 0,000 | 0,000 |
| 100 m | 3 m | 4,275 | 5,986 | 0,274 | 1,000 | 0,033 | 2,000 |
| 100 m | 5 m | 7,362 | 9,125 | 0,241 | 0,763 | 0,033 | 5,000 |

## Thêm lệch hướng và lệch độ cao (GPS σ 1 m)

| Độ cao | Lệch hướng | Lệch độ cao | Sai số trung vị (m) | Trong bán kính 1σ | Trong vùng 95% | Tách nhầm |
|---|---|---|---|---|---|---|
| 50 m | 0° | 0 m | 1,282 | 1,000 | 1,000 | 0,000 |
| 50 m | 0° | 5 m | 2,156 | 0,900 | 1,000 | 0,000 |
| 50 m | 5° | 0 m | 1,692 | 1,000 | 1,000 | 0,333 |
| 50 m | 5° | 5 m | 2,285 | 0,756 | 1,000 | 0,333 |
| 100 m | 0° | 0 m | 1,387 | 1,000 | 1,000 | 0,000 |
| 100 m | 0° | 5 m | 2,174 | 1,000 | 1,000 | 0,333 |
| 100 m | 5° | 0 m | 2,572 | 0,833 | 1,000 | 5,333 |
| 100 m | 5° | 5 m | 3,202 | 0,567 | 1,000 | 7,667 |

Ở GPS σ 5 m, tỉ lệ trong vùng 95% từ 0,752 đến 0,967 tuỳ ô, báo động giả 0,667–2,667 mỗi phút (`summary.csv`).

## Nhận xét

1. **GPS là nguồn sai số chính**, đúng như bảng lan truyền ở TECHNICAL 8.4: sai số trung vị đi theo σ của GPS (0,250 m khi GPS không nhiễu; 3,956 m và 4,275 m khi σ 3 m), gần như không đổi theo độ cao.
2. **Vòng 1σ quá hẹp để đi tìm người.** Khi GPS thật đúng bằng giả định (σ 3 m), chỉ 0,278 (50 m) và 0,274 (100 m) số người nằm trong bán kính 1σ. Điều này khớp lý thuyết: sai số hai chiều có phân bố Rayleigh, bán kính 1σ chỉ chứa 1 − e^(−1/2), khoảng 39%. Vùng 95% (2,448σ) chứa 1,000 ở mọi ô có GPS σ ≤ 3 m. Vì vậy bản đồ trạm mặt đất **vẽ vùng tìm 95%** chứ không phải 1σ (`ground/map.html`); trường `position_error_m` trong cảnh báo vẫn là 1σ.
3. **Khi GPS tệ hơn giả định (σ 5 m), vùng 95% không còn đủ** (0,763–0,833 khi không có lệch khác), và một số cảnh báo lệch quá 10 m thành báo động giả. Bán kính chỉ đúng khi mô hình sai số (`--gps-sigma-m`) đặt theo GPS thật của drone; với drone thật cần đo σ GPS trước khi bay, hoặc lấy từ chỉ số độ chính xác mà bộ thu GPS báo.
4. **Lệch hướng bay cố định gây tách nhầm ở độ cao lớn.** Ở 100 m với lệch hướng 5°, tách nhầm 5,333 (GPS σ 1 m) và 7,667 (thêm lệch độ cao 5 m) mỗi kịch bản, trong khi ở 50 m là 0,333. Lệch hướng xoay toạ độ quanh điểm ngay dưới drone; khi drone bay qua, cùng một người bị đặt ở các vị trí khác nhau theo thời gian, xa hơn bán kính gom 3 m, nên bị tách thành nhiều cảnh báo. Trạm mặt đất gộp được phần này thành một sự cố (`alert_memory.md`), nhưng la bàn của drone cần hiệu chỉnh khi bay cao.

## Giới hạn

- Người đứng yên, camera nhìn thẳng xuống; một chuyến 60 s, 3 seed. Lệch hướng và lệch độ cao là hằng số trong cả chuyến.
- Sai số lấy ở cảnh báo đầu tiên; người có cảnh báo lệch quá 10 m bị loại khỏi tỉ lệ "trong vùng", nên với GPS σ 5 m các tỉ lệ đó **lạc quan**.
- Detector giả (recall cố định, box đúng tâm người), không có lỗi định vị do box lệch.

## Tái lập

```bash
.venv/bin/python -m sim.sweep_rq3 --config configs/experiments/rq3_geoerr.yaml --jobs 8
```
