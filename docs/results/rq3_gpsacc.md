# RQ3c mô phỏng: bán kính sai số theo độ chính xác GPS do bộ thu báo (`--gps-sigma-from-telemetry`)

**Mô phỏng.** Nối tiếp `rq3_geoerr.md`: bán kính sai số mỗi cảnh báo tính với σ GPS cố định (`--gps-sigma-m`, mặc định 3 m). GPS thật kém hơn giả định (σ 5 m) thì vùng tìm 95% chỉ chứa 0,763–0,833 số người; GPS thật tốt hơn thì vùng tìm rộng thừa. Đề xuất ở `docs/CAI_TIEN.md` mục 3.2: lấy độ chính xác mà bộ thu GPS tự báo theo thời gian.

## Cách làm

- `shared.schema.Telemetry.gps_acc_m`: độ chính xác ngang bộ thu tự báo, quy về σ mỗi trục (m); đọc từ cột `gps_acc_m` của telemetry CSV khi có. `edge/main.py --gps-sigma-from-telemetry`: khi khung có `gps_acc_m` thì mô hình sai số dùng giá trị này thay `--gps-sigma-m` (các nguồn sai số khác giữ mặc định: độ cao 2 m, hướng 2°, nghiêng 1°).
- Mô phỏng: `sim/make_rq3.py --gps-sigma-profile 't:σ,...'` (σ GPS đổi theo thời gian, sai số = σ(t) × quá trình Gauss–Markov đơn vị, τ 30 s) và `--gps-acc-report` (ghi cột `gps_acc_m` = σ(t) × `--gps-acc-scale`). Hệ số 1 là bộ thu báo đúng; 0,5 là bộ thu báo lạc quan, chỉ bằng nửa σ thật.
- Kịch bản như `rq3_geoerr.md`: 60 s, 10 người, 10 m/s, 2 khung/giây, detector giả recall 0,7, 0,5 báo nhầm mỗi khung; geo, N = 3; 3 seed.
- Lưới: độ cao {50, 100} m × GPS {1 m; 3 m; 5 m; 1 m rồi tăng lên 5 m từ giây 25 tới 30} × hệ số báo {1; 0,5} × bán kính theo {σ cố định 3 m, σ bộ thu báo}. Cấu hình `configs/experiments/rq3_gpsacc.yaml`; số đọc từ `runs/rq3/gpsacc/summary.csv` (trung bình 3 seed).
- Chỉ số mới `search_radius_95_m_median` (`eval/rq3_metrics.py`): trung vị bán kính vùng tìm 95% (2,448 × bán kính 1σ của cảnh báo đầu tiên) qua những người đã được cảnh báo, tức cái giá về diện tích phải tìm.

## Kết quả (σ cố định 3 m → σ bộ thu báo)

| Độ cao | GPS thật σ | Bộ thu báo | Trong vùng 95% | Bán kính vùng 95% trung vị (m) | Sai số vị trí trung vị (m) |
|---|---|---|---|---|---|
| 50 m | 1 m | đúng | 1,000 → 1,000 | 8,069 → 4,141 | 1,282 |
| 50 m | 3 m | đúng | 1,000 → 1,000 | 8,082 → 8,082 | 3,956 |
| 50 m | 5 m | đúng | 0,833 → 1,000 | 8,147 → 12,732 | 6,591 |
| 50 m | 1 m rồi 5 m | đúng | 0,933 → 1,000 | 8,069 → 10,219 | 3,083 |
| 100 m | 1 m | đúng | 1,000 → 1,000 | 9,126 → 5,948 | 1,387 |
| 100 m | 3 m | đúng | 1,000 → 1,000 | 9,126 → 9,126 | 4,275 |
| 100 m | 5 m | đúng | 0,763 → 1,000 | 9,118 → 13,381 | 7,362 |
| 100 m | 1 m rồi 5 m | đúng | 0,833 → 1,000 | 9,118 → 10,921 | 3,425 |
| 50 m | 3 m | lạc quan (×0,5) | 1,000 → 0,759 | 8,082 → 4,985 | 3,956 |
| 50 m | 5 m | lạc quan (×0,5) | 0,833 → 0,652 | 8,147 → 7,058 | 6,591 |
| 100 m | 3 m | lạc quan (×0,5) | 1,000 → 0,963 | 9,126 → 6,548 | 4,275 |
| 100 m | 5 m | lạc quan (×0,5) | 0,763 → 0,656 | 9,118 → 8,163 | 7,362 |

Sai số vị trí, bỏ sót và báo giả không đổi giữa hai cách (cùng kịch bản, cùng cảnh báo; chỉ bán kính khác). Với σ cố định, hai cột "trong vùng 95%" ở dòng GPS 5 m khớp `rq3_geoerr.md` (0,833 và 0,763). Đủ 32 ô ở `summary.csv`.

## Nhận xét

1. **Bộ thu báo đúng thì vùng tìm 95% chứa đủ người ở mọi ô**, kể cả khi GPS kém đi giữa chuyến (1,000, so với 0,833–0,933 khi dùng σ cố định). Vùng tìm tự rộng ra khi GPS kém (100 m, σ 5 m: bán kính 9,118 → 13,381 m).
2. **GPS tốt thì vùng tìm hẹp lại**: σ 1 m, bán kính từ 8,069 xuống 4,141 m ở 50 m, từ 9,126 xuống 5,948 m ở 100 m, vẫn chứa đủ người. Đội cứu hộ tìm trong vùng nhỏ hơn.
3. **Rủi ro: bộ thu báo lạc quan.** Nếu độ chính xác bộ thu báo chỉ bằng nửa sai số thật, vùng tìm hẹp lại quá mức: ở các ô GPS σ 3 và 5 m chỉ còn chứa 0,652–0,963 số người, kém hơn cả dùng σ cố định 3 m. Độ chính xác bộ thu tự báo trên drone thật phải được kiểm tra trước (so với RTK hoặc điểm mốc đã biết) và nhân hệ số an toàn nếu nó lạc quan.
4. **Đề xuất:** bật `--gps-sigma-from-telemetry` khi telemetry có độ chính xác GPS đã được kiểm tra; không thì giữ σ cố định đặt theo GPS thật của drone. Thẻ drone ở trạm hiện độ chính xác GPS đang báo.

## Giới hạn

- Mô phỏng: sai số GPS Gauss–Markov thuần, bộ thu báo đúng tỉ lệ với σ thật (thực tế độ chính xác tự báo có nhiễu và trễ riêng); người đứng yên, camera nhìn thẳng xuống, 3 seed.
- Định dạng log DJI SRT phổ biến không ghi độ chính xác GPS; cần nguồn telemetry khác (log bay, MAVLink `GPS_RAW_INT.h_acc`) hoặc quy đổi từ HDOP. `SampledTelemetry` hiện đọc cột này từ CSV.
- Người có cảnh báo lệch quá 10 m bị tính là bỏ sót và loại khỏi tỉ lệ "trong vùng", nên ở σ 5 m các tỉ lệ đó lạc quan (như `rq3_geoerr.md`).

## Tái lập

```bash
.venv/bin/python -m sim.sweep_rq3 --config configs/experiments/rq3_gpsacc.yaml --jobs 6
```
