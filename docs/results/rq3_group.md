# Ước tính số người quanh mỗi cảnh báo khi người đứng theo nhóm (mô phỏng)

**Mô phỏng.** Đề xuất ở `docs/CAI_TIEN.md` mục 3.5. Mỗi cảnh báo mang `group_size`: ở đây có khoảng mấy người, để đội cứu hộ mang đủ phao, xuồng. Cách hiện có đếm số phát hiện **của khung xác nhận** trong 5 m quanh người được báo. Detector bỏ sót vài người của nhóm ở đúng khung đó thì con số hụt. Câu hỏi: đếm thêm các cụm đã thấy vài lần gần đây (mỗi người của nhóm là một cụm riêng trên UAV) có cho số đúng hơn không, và có đếm thừa không.

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
4. **Đề xuất:** bật đếm theo cụm trong cấu hình cuối và demo (`group_count: clusters` trong `configs/edge.yaml`). Nó chỉ đổi con số "nhóm khoảng N người" trên bản đồ; không đổi cảnh báo nào được gửi, nên mọi chỉ số khác (bỏ sót, báo nhầm, độ trễ) giữ nguyên. Chờ quyết định.

## Giới hạn

- Mô phỏng: người trong nhóm đứng yên tương đối với nhau, detector giả bỏ sót độc lập từng người; ngoài thực tế người sát nhau có thể bị gộp thành một box (detector), điều cách đếm nào ở đây cũng không sửa được.
- Một bán kính nhóm (2 m), một bán kính đếm (5 m, `GROUP_RADIUS_M`), 5 seed.
- Chưa kiểm chứng trên video thật (SeaDronesSee v21 có nhóm người bơi; cần lớp đáp án theo nhóm, `tools/make_truth_layer.py`).

## Tái lập

```bash
.venv/bin/python -m sim.sweep_rq3 --config configs/experiments/rq3_group.yaml --jobs 12
```
