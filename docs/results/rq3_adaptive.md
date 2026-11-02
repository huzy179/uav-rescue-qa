# RQ3 mô phỏng: tần số xử lý theo độ cao (`--min-views`)

**Mô phỏng, sơ bộ.** Câu hỏi: thay vì cố định 2 khung/giây, đổi tần số xử lý theo độ cao và vận tốc để mỗi người được nhìn một số lần nhất định (`edge/sampler.views_fps`, TECHNICAL mục 7.5) có giảm bỏ sót ở bay thấp và giảm số khung phải chạy detector ở bay cao không. Phụ: thu nhỏ khung theo độ cao (`--target-person-px 10`) có đổi gì trong mô phỏng không.

## Cách làm

- Kịch bản như `rq3_altitude.md`: 60 s, 10 người cách đường bay tối đa 15 m, 10 m/s, GPS σ 0,5 m, 0,5 báo nhầm mỗi khung; recall theo cỡ người của E2c từ E6 thử (`runs/e6_sds/eval/recall_by_pixels.csv`); geo, N = 3; 3 seed. Kịch bản quay 8 khung/giây để pipeline chọn được khung.
- Lưới: độ cao {30, 50, 80, 120} m × thu nhỏ {không, 10 px} × trần tần số {2, 8} khung/giây × `min_views` {cố định, 6, 12, 20}. "Cố định" là xử lý đúng ở trần.
- Với `min_views`, tần số = min_views × vận tốc / chiều dài vùng chụp, kẹp trong [0,5; trần], và cửa sổ đếm của khối xác nhận dãn bằng thời gian một người nằm trong khung. Lần quét đầu chưa dãn cửa sổ (5 s cố định): bay cao lại bỏ sót nhiều hơn vì 3 lần thấy trải dài hơn 5 s; đã sửa trước lần quét dưới đây.
- Cấu hình `configs/experiments/rq3_adaptive.yaml`; số đọc từ `runs/rq3/adaptive/summary.csv`. "Khung" là số khung đã chạy detector trong 60 s (`frames_processed`), đại diện cho chi phí tính toán.

## Kết quả, không thu nhỏ (tỉ lệ bỏ sót / số khung, trung bình 3 seed)

| Độ cao | Cố định 2 | Cố định 8 | min_views 6, trần 8 | min_views 12, trần 8 | min_views 20, trần 8 |
|---|---|---|---|---|---|
| 30 m | 0,567 / 120 | 0,000 / 480 | 0,333 / 141,3 | 0,033 / 279,7 | 0,000 / 459 |
| 50 m | 0,067 / 120 | 0,000 / 480 | 0,233 / 85,7 | 0,000 / 169,3 | 0,000 / 279,7 |
| 80 m | 0,000 / 120 | 0,000 / 480 | 0,100 / 54 | 0,000 / 106,7 | 0,000 / 176,7 |
| 120 m | 0,000 / 120 | 0,000 / 480 | 0,300 / 36,3 | 0,000 / 71,7 | 0,000 / 118 |

Báo giả mỗi phút: 0 ở mọi ô trừ cố định 8 (1,667 ở 30 m; 0,333 ở 50 và 80 m) và min_views 12, 20 ở 30 m (0,667; 1,667).

## Nhận xét

1. **min_views 12, trần 8 không kém cố định 2 khung/giây ở độ cao nào, và tốt hơn hẳn khi bay thấp**: 30 m bỏ sót 0,033 so với 0,567 (chạy 279,7 khung thay vì 120); từ 80 m trở lên không bỏ sót mà chạy ít khung hơn (106,7 ở 80 m, 71,7 ở 120 m). Tức là đổi khung từ chỗ thừa (bay cao) sang chỗ thiếu (bay thấp), thay vì một tần số chung.
2. **6 lần nhìn là quá ít** với recall mỗi khung khoảng 0,5 của E2c: bỏ sót 0,1–0,33 ở mọi độ cao. Số lần nhìn cần thiết phụ thuộc recall và N (công thức nhị thức, TECHNICAL 2.4), nên `min_views` phải chọn theo recall đo được trên tập lũ, không chọn cố định.
3. Trần 2 khung/giây chặn mất lợi ích ở bay thấp: ở 30 m mọi mức min_views đều cần hơn 2 khung/giây, trần 2 cắt về 2 (120 khung, bỏ sót 0,567 như cố định). Đây là chỗ RQ2 nối vào: tần số trần là tốc độ thiết bị theo p95.
4. **Thu nhỏ theo độ cao không đổi kết quả trong mô phỏng** (bảng dưới): đường recall của E2c gần phẳng từ 8 tới 45 px (0,516–0,624, `e6_sds_pilot.md`), mà người trong mô phỏng ở 30–120 m nằm trong khoảng đó (42 px ở 30 m, bảng TECHNICAL 2.3). Lợi ích đo được trên SDS (`scale_by_altitude.md`) đến từ người trên 45 px và từ việc cắt ô ở độ phân giải gốc sinh nhiều báo nhầm; mô phỏng không có cả hai (báo nhầm cố định mỗi khung).

| Độ cao | Thu nhỏ 10 px: cố định 2 | Thu nhỏ 10 px: min_views 12, trần 8 |
|---|---|---|
| 30 m | 0,500 / 120 | 0,000 / 279,7 |
| 50 m | 0,100 / 120 | 0,033 / 169,3 |
| 80 m | 0,033 / 120 | 0,033 / 106,7 |
| 120 m | 0,000 / 120 | 0,000 / 71,7 |

## Giới hạn

- Các khung độc lập (như `rq3_altitude.md`): xử lý dày không gặp lỗi tương quan theo thời gian, nên lợi ích của tần số cao bị **phóng đại**.
- Báo nhầm cố định 0,5 mỗi khung bất kể độ cao và cách chạy; bay thẳng, độ cao không đổi trong một kịch bản (chưa thử đổi độ cao giữa chuyến, trường hợp mà tần số theo độ cao có ý nghĩa nhất).
- 3 seed; độ lệch chuẩn tới 0,2 ở vài ô.
- Vận tốc lấy từ telemetry một giây trước; khung đầu dùng tần số trần.

## Tái lập

```bash
.venv/bin/python -m sim.sweep_rq3 --config configs/experiments/rq3_adaptive.yaml --jobs 8
```
