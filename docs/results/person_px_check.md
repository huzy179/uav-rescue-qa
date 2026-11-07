# Cỡ người dự kiến so với nhãn SeaDronesSee, và độ nhạy của mô phỏng theo cỡ người

Đề xuất ở `docs/CAI_TIEN.md` mục 3.6 ("góc nhìn thật của từng camera"). Thu nhỏ theo độ cao (`--target-person-px`) và mô phỏng câu hỏi 3 đều ước lượng cỡ người trên ảnh bằng `0,5 m × f / h`, với góc nhìn 82° chéo cho mọi drone. `scale_by_altitude.md` và `upscale_small.md` đã thấy số px dự kiến thấp hơn cỡ người trong nhãn; ở đây đo chênh lệch đó và xem nó làm lệch kết quả mô phỏng tới đâu.

## Phần 1: chênh lệch đo được

- `tools/person_px_check.py`: với mỗi đoạn SeaDronesSee-MOT, tích "cạnh ngắn box nhãn × độ cao" của từng người (hằng số nếu mô hình đúng), chia cho `0,5 × f` (góc 82° chéo, ảnh 3840 px). Lấy riêng các khung camera gần nhìn thẳng xuống (góc gimbal ≤ −80°), vì camera nghiêng làm người nhỏ hơn trên ảnh. Kết quả `runs/stats/person_px_check.csv`.
- Chỉ bốn đoạn có khung gần nhìn thẳng xuống:

| Đoạn | Drone | Box | Độ cao trung vị | Tỉ số nhãn / dự kiến |
|---|---|---|---|---|
| train v13 | Mavic 2 Pro | 466 | 91,2 m | 1,973 |
| val v13 | Mavic 2 Pro | 116 | 90,8 m | 1,756 |
| val v21 | Matrice 100 | 7.601 | 40,9 m | 2,582 |
| val v18 | Matrice 210 | 227 | 23,7 m | 4,040 |

- Ở các khung camera nghiêng, tỉ số thấp hơn (ví dụ val v9, góc trung vị −38,5°: 1,134), như dự kiến.

**Nhận xét.**

1. Box người trong nhãn lớn hơn dự kiến **khoảng 1,8–2,6 lần** ở khung nhìn thẳng, ở cả Mavic (camera góc rộng gắn liền) lẫn Matrice 100. Phần lớn chênh lệch vì vậy đến từ **cỡ người**: box người bơi gồm cả thân, tay và bọt nước, lớn hơn bề rộng vai 0,5 m nhìn từ trên xuống. Bài SeaDronesSee [SeaDronesSee] liệt kê các camera (Hasselblad L1D-20c, Zenmuse X5, Zenmuse XT2…) nhưng không ghi drone nào mang camera nào và ống kính nào, nên góc nhìn riêng của từng camera **không tách được** khỏi cỡ người bằng dữ liệu này. Phần train hầu như không có khung nhìn thẳng của Matrice 100, 210 (góc trung vị −58°, −24°), nên cũng không ước lượng riêng trên train được.
2. Hệ quả cho thu nhỏ theo độ cao trên SeaDronesSee: "thu nhỏ về 10 px dự kiến" thực tế đưa người trong nhãn về khoảng 18–26 px, đúng vùng mô hình chính mạnh nhất (`e6_sds_pilot.md`); kết quả đo của `scale_by_altitude.md` vẫn đúng, nhưng tên "10 px" là theo giả định 0,5 m.
3. **Quyết định:** giữ 82° và 0,5 m làm giả định của pipeline (không có cơ sở chọn khác cho camera của drone cứu hộ); ghi rõ mục tiêu thu nhỏ là "px dự kiến theo người 0,5 m". Khi có drone và camera thật, đo lại tỉ số này trên một chuyến bay có người đứng yên ở độ cao biết trước.

## Phần 2: độ nhạy của mô phỏng theo cỡ người

Mô phỏng câu hỏi 3 tra recall theo **cạnh ngắn của box nhãn** (đường recall đo trên SeaDronesSee, `e6_sds_pilot.md`), nhưng tính cạnh đó từ người 0,5 m. Nếu người thật to như box nhãn, mô phỏng đặt người vào sai chỗ trên đường recall.

- `sim/make_rq3.py --person-m`: cỡ box người thật trong cảnh; pipeline vẫn giả định 0,5 m khi thu nhỏ. Mặc định 0,5 m, kết quả cũ không đổi.
- Lặp lại quét độ cao của `rq3_altitude.md` (E2c, xác nhận geo, N = 3, GPS σ 0,5 m, 3 seed) với người 0,5 m và 1,0 m (1,0 m chọn trước, gần mức "gấp khoảng 2" đo ở phần 1), có và không thu nhỏ về 10 px dự kiến. Cấu hình `configs/experiments/rq3_altitude_person1m.yaml`, kết quả `runs/rq3/altitude_person1m/summary.csv`, chạy ở commit `5726c25` (`dirty: true`, tham số `--person-m` chưa commit). Ô người 0,5 m không thu nhỏ trùng bảng của `rq3_altitude.md`.

**Mô phỏng.** Tỉ lệ bỏ sót (trung bình ± độ lệch chuẩn qua 3 seed):

| Độ cao | Người 0,5 m | Người 0,5 m, thu nhỏ 10 px | Người 1,0 m | Người 1,0 m, thu nhỏ 10 px |
|---|---|---|---|---|
| 30 m | 0,567 ± 0,116 | 0,533 ± 0,153 | 0,867 ± 0,116 | 0,400 ± 0,200 |
| 50 m | 0,033 ± 0,058 | 0,067 ± 0,058 | 0,133 ± 0,116 | 0,033 ± 0,058 |
| 80 m | 0,000 ± 0,000 | 0,000 ± 0,000 | 0,033 ± 0,058 | 0,033 ± 0,058 |
| 120–200 m | 0,000 | 0,000 | 0,000 | 0,000 |

**Nhận xét.**

4. Với người cỡ như box nhãn (1,0 m), bay thấp bỏ sót **nhiều hơn** (30 m: 0,867 so với 0,567), vì người to hơn rơi sâu hơn vào vùng mô hình chính yếu.
5. **Thu nhỏ theo độ cao giúp rõ hơn khi người to cỡ đó**: 30 m từ 0,867 xuống 0,400, 50 m từ 0,133 xuống 0,033; với người 0,5 m mức giúp nhỏ (30 m: 0,567 → 0,533). Điều này giải thích vì sao các mô phỏng trước (`rq3_altitude.md`, `rq3_altprofile.md`, `rq3_adaptive.md`) thấy thu nhỏ theo độ cao giúp ít trong khi trên SeaDronesSee thật nó tăng AP50 mạnh: mô phỏng dùng người nhỏ hơn box nhãn.
6. Kết luận định tính của `rq3_altitude.md` (bay quá thấp thì bỏ sót nhiều với mô hình chính, từ khoảng 80 m trở lên không bỏ sót) giữ nguyên ở cả hai cỡ người; con số bỏ sót khi bay thấp phụ thuộc mạnh vào cỡ người giả định, nên báo cả hai.

## Giới hạn

- Bốn đoạn có khung nhìn thẳng; người trong SeaDronesSee là người bơi, cỡ box của người trên mái nhà hay người ngập tới ngực trong lũ có thể khác. Tập ảnh lũ không có độ cao bay nên không đo được tỉ số này trên cảnh lũ.
- Mô phỏng: 3 seed, một đường recall (E2c, SeaDronesSee), hai cỡ người.

## Tái lập

```bash
.venv/bin/python tools/person_px_check.py --mot data/processed/sds_mot --output runs/stats/person_px_check.csv
.venv/bin/python -m sim.sweep_rq3 --config configs/experiments/rq3_altitude_person1m.yaml --jobs 12
```
