# RQ3 mô phỏng: độ cao đổi giữa chuyến

**Mô phỏng, sơ bộ.** Nối tiếp `rq3_adaptive.md` (độ cao cố định trong mỗi kịch bản). Ở đây UAV bay dò ở 120 m trong 25 s, hạ xuống 40 m trong 10 s, giữ 40 m tới hết 60 s: tình huống mà tần số xử lý và thu nhỏ khung theo độ cao phải tự đổi theo telemetry giữa chuyến.

## Cách làm

- Kịch bản như `rq3_adaptive.md` (60 s, 10 người, 10 m/s, GPS σ 0,5 m, recall theo cỡ người của E2c từ E6 thử, geo, N = 3, 3 seed, kịch bản quay 8 khung/giây); độ cao theo `sim/flight.AltitudeProfile` (`--alt-profile`); với thu nhỏ, recall của từng khung lấy ở cỡ người sau thu nhỏ theo độ cao đo của chính khung đó.
- So với giữ nguyên 120 m và giữ nguyên 40 m. Cấu hình `configs/experiments/rq3_altprofile.yaml`; số đọc từ `runs/rq3/altprofile/summary.csv`.

## Tỉ lệ bỏ sót / số khung chạy detector (trung bình 3 seed)

| Độ cao | Cố định 2 | Cố định 8 | 12 lần nhìn, trần 8 | 12 lần nhìn, trần 8, thu nhỏ 10 px |
|---|---|---|---|---|
| 120 m cả chuyến | 0,000 / 120 | 0,000 / 480 | 0,000 / 71,7 | 0,000 / 71,7 |
| 40 m cả chuyến | 0,200 / 120 | 0,000 / 480 | 0,067 / 211,7 | 0,033 / 211,7 |
| 120 m rồi hạ 40 m | 0,067 / 120 | 0,000 / 480 | 0,033 / 137 | 0,000 / 137 |

Báo giả mỗi phút: 0,333 với cố định 8 ở 40 m và ở hồ sơ đổi độ cao; 0 ở mọi ô còn lại.

## Nhận xét

1. Khi độ cao đổi giữa chuyến, **12 lần nhìn, trần 8 khung/giây** gần bằng xử lý cố định 8 khung/giây về bỏ sót (0,033 so với 0) với 137 khung thay vì 480; thêm thu nhỏ 10 px thì 0 bỏ sót. Cố định 2 khung/giây bỏ sót 0,067 vì phần bay thấp có quá ít lần nhìn.
2. Ở 120 m cả chuyến, tần số theo độ cao chạy 71,7 khung thay vì 120 mà không bỏ sót ai: tiết kiệm tính toán khi bay cao.
3. Thu nhỏ theo độ cao chỉ cải thiện nhỏ trong mô phỏng (như `rq3_adaptive.md`: đường recall của E2c gần phẳng ở 8–45 px; mô phỏng không có báo nhầm tăng khi cắt ô người to).

## Giới hạn

- Hồ sơ độ cao viết trước, không phải UAV tự hạ khi nghi có người; các khung độc lập (lợi ích của tần số cao bị phóng đại); 3 seed, độ lệch chuẩn tới 0,115.

## Tái lập

```bash
.venv/bin/python -m sim.sweep_rq3 --config configs/experiments/rq3_altprofile.yaml --jobs 8
```
