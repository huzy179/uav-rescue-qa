# RQ3 mô phỏng: độ cao bay khi recall phụ thuộc cỡ người

**Mô phỏng, sơ bộ.** Trước đây mô phỏng RQ3 dùng recall cố định 0,7 cho mọi người. Ở đây recall của detector giả lấy từ đường recall theo cỡ người đo ở E6 thử (`e6_sds_pilot.md`, `runs/e6_sds/eval/recall_by_pixels.csv`), cho E1 (gốc COCO) và E2c (fine-tune). Cỡ người trong mô phỏng là 0,5 m trên ảnh 4K, góc nhìn 82° chéo, nên đổi theo độ cao (TECHNICAL mục 2.3).

## Cách làm

- `sim/scenario.py`, `RecallCurve`: mỗi người ở mỗi khung được thấy với xác suất bằng recall của nhóm cỡ chứa cạnh ngắn box của họ; `sim/make_rq3.py --recall-curve --recall-model`.
- Kịch bản: 60 s, 10 người, cách đường bay tối đa 15 m (luôn lọt khung từ 30 m), 10 m/s, 2 khung/giây, GPS σ 0,5 m τ 30 s, 0,5 báo nhầm mỗi khung; xác nhận geo, N = 3; 3 seed.
- Lưới: độ cao ∈ {30, 50, 80, 120, 160, 200} m × mô hình ∈ {E1, E2c}. Cấu hình `configs/experiments/rq3_altitude.yaml`, kết quả `runs/rq3/altitude/summary.csv`.

## Tỉ lệ bỏ sót (trung bình 3 seed)

| Độ cao | E1 | E2c |
|---|---|---|
| 30 m | 0,767 | 0,567 |
| 50 m | 0,567 | 0,033 |
| 80 m | 0,533 | 0,000 |
| 120 m | 0,600 | 0,000 |
| 160 m | 0,967 | 0,000 |
| 200 m | 0,900 | 0,000 |

Gộp nhầm trung bình: E1 0,000–0,333, E2c 0,667–1,333 mỗi kịch bản. Tách nhầm 0 ở mọi ô. Báo giả mỗi phút 0,333 ở 30 m, 0 ở các độ cao khác.

## Nhận xét

1. **Hai lực kéo ngược nhau khi đổi độ cao:** bay cao thì người nhỏ đi (recall mỗi khung giảm) nhưng ở lâu hơn trong khung (nhiều lần thấy hơn, TECHNICAL mục 2.4). Với E2c, recall ở người nhỏ vẫn cao nên lực thứ hai thắng: từ 80 m tới 200 m không bỏ sót ai trong mô phỏng.
2. **Bay thấp lại tệ** với cả hai mô hình: ở 30 m người chỉ nằm trong ít khung mà vẫn cần thấy 3 lần; với E2c người lại "to" (42 px ở 30 m theo bảng TECHNICAL mục 2.3), đúng chỗ E2c yếu. Thu nhỏ theo độ cao (`scale_by_altitude.md`) và tăng FPS khi bay thấp là hai cách chữa; mô phỏng này chưa tính đến cả hai.
3. **E1 không dùng được cho bay cao:** từ 160 m bỏ sót 0,900 trở lên.
4. Hệ quả cho khuyến nghị độ cao (E6): với mô hình fine-tune, giới hạn bay cao không nằm ở khối xác nhận mà ở chỗ người còn đủ px để detector thấy (dưới 4 px recall bằng 0, `e6_sds_pilot.md`); trong mô phỏng tới 200 m E2c chưa bỏ sót. Giới hạn thật còn phụ thuộc đường recall đo trên tập lũ thật.

## Giới hạn

- Các khung độc lập: người khó thấy ở khung này không khó hơn ở khung sau. Thực tế lỗi tương quan theo thời gian (sóng, lóa kéo dài), nên mô phỏng **lạc quan** với độ cao lớn.
- Đường recall đo trên SDS (biển, người bơi), ở conf 0,25 và cắt ô ở độ phân giải gốc; pipeline dùng conf 0,1.
- Báo nhầm cố định 0,5 mỗi khung cho cả hai mô hình và mọi độ cao; thực tế khác theo mô hình và cách chạy (E2c cắt ô gốc có precision rất thấp, `scale_by_altitude.md`).
- Người đứng yên, 10 người, 3 seed.

## Tái lập

```bash
.venv/bin/python eval/recall_by_pixels.py ...   # e6_sds_pilot.md, ra runs/e6_sds/eval/recall_by_pixels.csv
.venv/bin/python -m sim.sweep_rq3 --config configs/experiments/rq3_altitude.yaml --jobs 8
```
