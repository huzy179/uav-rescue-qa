# Ước tính số người quanh mỗi cảnh báo khi người đứng theo nhóm: tốt trong mô phỏng, kém trên video thật

**Mô phỏng.** **Mô phỏng và ba đoạn video thật SeaDronesSee.** Đề xuất ở `docs/CAI_TIEN.md` mục 3.5. Mỗi cảnh báo mang `group_size`: ở đây có khoảng mấy người, để đội cứu hộ mang đủ phao, xuồng. Cách hiện có đếm số phát hiện **của khung xác nhận** trong 5 m quanh người được báo. Detector bỏ sót vài người của nhóm ở đúng khung đó thì con số hụt. Câu hỏi: đếm thêm các cụm đã thấy vài lần gần đây (mỗi người của nhóm là một cụm riêng trên UAV) có cho số đúng hơn không, và có đếm thừa không.

## Cách làm

- **Đếm theo cụm** (`--group-count clusters`, `edge.confirm.with_cluster_group_sizes`): số cụm còn sống trong 5 m quanh người được báo có ít nhất 2 lần thấy trong cửa sổ xác nhận (5 s), lấy số lớn hơn giữa cách này và đếm theo khung. Điều kiện "ít nhất 2 lần" đặt trước khi chạy, để loại báo nhầm một khung; không thử giá trị khác. Mặc định vẫn là đếm theo khung (`frame`).
- **Kịch bản có nhóm** (`sim/make_rq3.py --group-size K --group-spread-m 2`): tâm nhóm rải như người lẻ, mỗi nhóm K người nằm đều trong hình tròn bán kính 2 m quanh tâm. K = 1 giữ đúng kịch bản cũ.
- **Chỉ số** (`eval/rq3_metrics.py`): với mỗi cảnh báo đúng, số người thật trong 5 m quanh người được báo (lúc cảnh báo) so với `group_size`: tỉ lệ cảnh báo đúng số người, sai số trung bình (âm là đếm thiếu), sai số tuyệt đối trung bình.
- 12 người, 60 s, GPS σ 0,5 m, 0,5 báo nhầm mỗi khung, xác nhận geo N = 3; nhóm {1, 2, 4} × recall detector {0,7; 0,9} × cách đếm {theo khung, theo cụm}; 5 seed. Cấu hình `configs/experiments/rq3_group.yaml`, kết quả `runs/rq3/group/summary.csv` (trung bình 5 seed, "±" là độ lệch chuẩn qua seed). Chạy ở commit `7e04d86`, `dirty: true` vì mã đếm theo cụm và kịch bản có nhóm lúc đó chưa commit (commit ngay sau, cùng nội dung).

## Kết quả

| Người mỗi nhóm | Recall detector | Cách đếm | Cảnh báo đúng số người | Sai số trung bình | Sai số tuyệt đối | Người không có cảnh báo riêng |
|---|---|---|---|---|---|---|
| 1 | 0,700 | theo khung | 1,000 ± 0,000 | 0,000 | 0,000 | 0,000 |
| 1 | 0,700 | theo cụm | 1,000 ± 0,000 | 0,000 | 0,000 | 0,000 |
| 1 | 0,900 | theo khung | 0,983 ± 0,037 | 0,017 | 0,017 | 0,000 |
| 1 | 0,900 | theo cụm | 0,983 ± 0,037 | 0,017 | 0,017 | 0,000 |
| 2 | 0,700 | theo khung | 0,700 ± 0,126 | −0,300 | 0,300 | 0,133 |
| 2 | 0,700 | theo cụm | 0,883 ± 0,074 | −0,117 | 0,117 | 0,133 |
| 2 | 0,900 | theo khung | 0,833 ± 0,059 | −0,133 | 0,167 | 0,100 |
| 2 | 0,900 | theo cụm | 0,900 ± 0,037 | −0,067 | 0,100 | 0,100 |
| 4 | 0,700 | theo khung | 0,303 ± 0,154 | −1,040 | 1,040 | 0,250 |
| 4 | 0,700 | theo cụm | 0,524 ± 0,132 | −0,494 | 0,494 | 0,250 |
| 4 | 0,900 | theo khung | 0,533 ± 0,321 | −0,500 | 0,500 | 0,200 |
| 4 | 0,900 | theo cụm | 0,900 ± 0,070 | −0,100 | 0,100 | 0,200 |

Cột cuối là `missed_rate`: người không có cảnh báo của riêng mình (cảnh báo gần nhất thuộc về người khác trong nhóm). Với người theo nhóm, con số này không có nghĩa là bỏ sót, vì người đó nằm trong số `group_size` của cảnh báo bên cạnh; nó như nhau giữa hai cách đếm.

## Nhận xét

1. **Đếm theo khung hụt rõ khi nhóm đông và detector bỏ sót**: nhóm 4 người, recall 0,7, chỉ 0,303 số cảnh báo đúng số người, trung bình thiếu 1,040 người.
2. **Đếm theo cụm sửa được phần lớn**: cùng ô đó 0,524, thiếu 0,494; recall 0,9 thì 0,533 → 0,900. Nhóm 2 người: 0,700 → 0,883 (recall 0,7).
3. **Không thấy đếm thừa tăng thêm**: với người lẻ hai cách cho cùng kết quả (sai số dương 0,017 ở recall 0,9 có ở cả hai, từ người khác tình cờ trong 5 m hoặc báo nhầm cùng khung); ở mọi ô có nhóm, sai số trung bình của cả hai cách đều âm, tức đếm thiếu nhiều hơn đếm thừa.
4. Kết luận mô phỏng chưa đủ để bật: xem kiểm chứng trên video thật dưới đây.

## Kiểm chứng trên video thật (SeaDronesSee)

- Phát lại phát hiện đã lưu của lần chạy geo (`runs/sds/<đoạn>/geo/detections.jsonl`, 2 khung/giây, cấu hình `configs/edge.yaml`) trên ba đoạn của `alert_memory.md`, với hai cách đếm (`runs/sds/<đoạn>/group_frame`, `group_clusters`; commit `5a2eff1`).
- Chấm bằng `eval/group_count_eval.py`: với mỗi cảnh báo, khung nhãn ở thời điểm cảnh báo, nhãn khớp box của cảnh báo (IoU ≥ 0,3; không khớp thì bỏ qua), chiếu mọi nhãn của khung xuống mặt đất bằng telemetry, đếm người trong 5 m quanh người được báo. Kết quả `runs/sds/<đoạn>/group_count.csv`.

| Đoạn | Cách đếm | Cảnh báo khớp nhãn | Đúng số người | Sai số trung bình | Đếm thừa | Đếm thiếu |
|---|---|---|---|---|---|---|
| v21 (người thật mỗi cảnh báo: 1 người ×15, 2 ×8, 3 ×1) | theo khung | 24/37 | 0,792 | −0,250 | 0 | 5 |
| | theo cụm | 24/37 | 0,583 | +0,292 | 8 | 2 |
| v5 (1 người ×6) | theo khung | 6/9 | 0,667 | +0,333 | 2 | 0 |
| | theo cụm | 6/9 | 0,667 | +0,333 | 2 | 0 |
| v13 (2 người ×2) | theo khung | 2/4 | 0,000 | −1,000 | 0 | 2 |
| | theo cụm | 2/4 | 0,500 | −0,500 | 0 | 1 |

5. **Trên v21, đoạn đông người nhất, đếm theo cụm kém hơn**: đúng số người 0,792 → 0,583, đếm thừa ở 8/24 cảnh báo thay vì 0. Nguyên nhân hợp lý nhất là điều mô phỏng không có: trên v21 vị trí một người trôi theo GPS nên **một người bị tách thành nhiều cụm** (37 cảnh báo cho 12 người, `alert_memory.md`); các cụm thừa đó đã thấy vài lần nên bị đếm như người khác. Mô phỏng dùng GPS σ 0,5 m nên gần như không tách cụm.
6. Hai đoạn thưa người quá ít cảnh báo (6 và 2) để kết luận; v13 đi theo chiều mô phỏng (2 cảnh báo, đếm thiếu 2 → 1).
7. **Quyết định #18 (chốt 7/11): không bật**, giữ `--group-count clusters` làm tuỳ chọn, mặc định đếm theo khung. Muốn đếm theo cụm dùng được thì phải phân biệt cụm tách nhầm của cùng một người với người khác trong nhóm; một hướng chưa thử: chỉ đếm các cụm từng được thấy **cùng một khung** với người được báo (một người không xuất hiện hai lần trong cùng khung).

## Giới hạn

- Mô phỏng: người trong nhóm đứng yên tương đối với nhau, detector giả bỏ sót độc lập từng người; ngoài thực tế người sát nhau có thể bị gộp thành một box (detector), điều cách đếm nào ở đây cũng không sửa được.
- Một bán kính nhóm (2 m), một bán kính đếm (5 m, `GROUP_RADIUS_M`), 5 seed.
- Kiểm chứng thật chỉ ba đoạn SeaDronesSee (32 cảnh báo khớp nhãn), người thật chỉ đếm trong khung; nhãn chiếu xuống mặt đất bằng cùng telemetry nên số người thật trong 5 m cũng có sai số định vị.

## Tái lập

```bash
.venv/bin/python -m sim.sweep_rq3 --config configs/experiments/rq3_group.yaml --jobs 12
for V in val-m100-DJI_0001-v21 val-mavic-DJI_0065-v5 train-mavic-DJI_0064-v13; do
  for M in frame clusters; do
    .venv/bin/python edge/main.py --config configs/edge.yaml --source data/processed/sds_mot/$V/frames --source-fps 30 --fps 2 \
      --replay runs/sds/$V/geo/detections.jsonl --telemetry data/processed/sds_mot/$V/telemetry.csv \
      --confirm geo --group-count $M --output runs/sds/$V/group_$M --drain-s 0
  done
  .venv/bin/python eval/group_count_eval.py --sds data/processed/sds_mot/$V \
      --runs runs/sds/$V/group_frame runs/sds/$V/group_clusters --output runs/sds/$V/group_count.csv
done
```
