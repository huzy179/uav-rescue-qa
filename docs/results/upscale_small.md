# Phóng to khung khi người dự kiến dưới 8 px (`--min-person-px`): kết quả âm

**Sơ bộ, trên SeaDronesSee thu nhỏ (nước biển, không phải lũ).** Đề xuất ở `docs/CAI_TIEN.md` mục 1.2: dưới khoảng 6 px recall của E2c gần bằng 0 (`e6_sds_pilot.md`), nên khi độ cao bay cho thấy người sẽ rất nhỏ thì phóng to khung trước khi cắt ô, để người chiếm nhiều ô lưới của mạng hơn. Đổi lại số ô tăng theo bình phương hệ số phóng to.

## Cách làm

- `edge.detector.person_scale(expected_px, target_px, min_px, max_upscale)`: người dự kiến nhỏ hơn `min_px` thì hệ số < 1 (phóng to về khoảng `min_px`), tối đa `max_upscale` lần; nội suy tuyến tính. Box quy về toạ độ ảnh gốc như khi thu nhỏ. Bật bằng `--min-person-px` trong `scripts/run_tiled.py` và `edge/main.py`; không đặt thì giữ hành vi cũ.
- Dữ liệu: 317 ảnh SDS, 1.055 người, 11 video, thu nhỏ 1, 2, 3, 4, 6 lần (`data/processed/sds_rescale`, như `e6_sds_pilot.md`). Số px dự kiến tính từ độ cao trong `meta_val.csv` và góc nhìn 82° chéo trên **ảnh đã thu nhỏ**.
- Hai lần chạy trên cùng ảnh, cùng commit `aaab032` (`dirty: true` vì lúc chạy có thay đổi chưa commit ở `edge/main.py` và `edge/device_sim.py`, không nằm trên đường chạy của `run_tiled.py`):
  - `E2c_goc`: cắt ô 640, chồng 0,2, không lượt toàn ảnh, conf 0,001 (`--max-upscale 1`, tức không đổi cỡ; trùng kết quả `E2c` của `e6_sds_pilot.md`: recall nhóm 4–6 px 0,256 ở cả hai);
  - `E2c_up8`: như trên, `--min-person-px 8 --max-upscale 2`.
- Chấm: `eval/recall_by_pixels.py` (recall ở conf 0,25 theo cạnh ngắn của người trong ảnh đã thu nhỏ, trước khi phóng to) và `eval/compare_runs.py` từng mức, bootstrap cặp theo video. Máy RTX 5060 (WSL); thời gian không báo.
- `min_px = 8` chọn trước khi chạy, theo ngưỡng "khoảng 6–8 px" của `e6_sds_pilot.md`; không thử giá trị khác.

## Kết quả

### Recall theo cạnh ngắn người (`runs/e6_sds/eval_upscale/recall_by_pixels.csv`)

| Cạnh ngắn (px) | Số người | Không phóng to | Phóng to về 8 px |
|---|---|---|---|
| 0–4 | 24 | 0,000 (0,000–0,000) | 0,042 (0,000–0,158) |
| 4–6 | 160 | 0,256 (0,000–0,320) | 0,281 (0,000–0,489) |
| 6–8 | 257 | 0,494 (0,186–0,613) | 0,525 (0,267–0,834) |
| 8–11 | 500 | 0,532 (0,220–0,781) | 0,562 (0,250–0,823) |
| 11–16 | 758 | 0,588 (0,440–0,795) | 0,591 (0,455–0,796) |
| 16–23 | 868 | 0,624 (0,437–0,728) | 0,608 (0,437–0,727) |
| 23–32 | 655 | 0,537 (0,270–0,670) | 0,537 (0,270–0,670) |
| 32–45 | 706 | 0,516 (0,219–0,625) | 0,518 (0,219–0,625) |
| 45–64, 64–91, ≥ 91 | 492, 357, 498 | 0,390; 0,261; 0,133 | 0,390; 0,261; 0,133 |

### So cặp theo mức thu nhỏ (`runs/e6_sds/compare_goc_up8_x<f>/compare.csv`), IoU 0,5

| Thu nhỏ | Ảnh được phóng to | Số ô (không → có) | Hiệu AP50, tất cả (KTC 95%) | Hiệu recall, tất cả (KTC 95%) | Hiệu recall < 8 px (KTC 95%) |
|---|---|---|---|---|---|
| 2 | 0,041 | 2.536 → 2.724 | +0,009 (−0,000 đến +0,036) | +0,002 (0,000 đến +0,012) | 0,000 (0,000 đến 0,000) |
| 3 | 0,041 | 1.902 → 2.019 | +0,013 (0,000 đến +0,084) | +0,008 (0,000 đến +0,046) | +0,100 (0,000 đến +0,316) |
| 4 | 0,457 | 634 → 788 | +0,020 (−0,002 đến +0,060) | +0,007 (−0,007 đến +0,070) | +0,089 (0,000 đến +0,256) |
| 6 | 0,719 | 317 → 673 | +0,017 (−0,043 đến +0,064) | +0,001 (−0,030 đến +0,073) | +0,012 (−0,053 đến +0,244) |

Ở mức 1 không ảnh nào được phóng to (hai lần chạy giống hệt). Tỉ lệ ảnh được phóng to và số ô đọc từ cột `scale`, `n_tiles` của `per_image.csv`. Không ô nào trong bảng có ý nghĩa thống kê.

## Nhận xét

1. **Không có cải thiện có ý nghĩa ở mức nào.** Điểm ước lượng của recall ở người dưới 11 px tăng nhẹ (4–6 px: 0,256 → 0,281; 6–8 px: 0,494 → 0,525), nhưng khoảng tin cậy theo video rộng và mọi hiệu số cặp đều chứa 0.
2. **Chi phí thì chắc chắn:** ở mức 6, số ô tăng từ 317 lên 673. Trên thiết bị biên, chi phí này đi thẳng vào thời gian mỗi khung (câu hỏi 2).
3. Phóng to không thêm chi tiết của cảm biến; điều nó làm được chỉ là người chiếm nhiều ô lưới hơn. Với E2c, vốn đã học người rất nhỏ từ VisDrone ở đầu vào 1280, chừng đó không đủ.
4. Ước lượng số px dự kiến thấp hơn cỡ người trong nhãn (như `scale_by_altitude.md`; ví dụ ở mức 6, video v17 dự kiến 4,2 px trong khi trung vị nhãn 10,0 px), nên một phần ảnh bị phóng to dù người không thật sự dưới 8 px. Đây là một lý do khiến mức tăng bị loãng, nhưng cũng là điều kiện thật của hệ thống khi góc nhìn camera chỉ biết gần đúng.
5. **Quyết định:** giữ `--min-person-px` là tuỳ chọn, mặc định tắt; không đưa vào cấu hình cuối, RQ2 hay mô phỏng RQ3. Người dưới 8 px vẫn là giới hạn dưới của hệ thống; cách chữa còn lại là bay thấp hơn (`rq3_altitude.md`).

## Giới hạn

- Một tập (11 video), thu nhỏ ảnh không tái tạo nhiễu và nhoè của camera thật; người dưới 8 px (ba nhóm đầu của bảng recall) dồn trong vài video bay cao.
- Một giá trị `min_px`, một giá trị `max_upscale`, một mô hình (E2c), không có lượt toàn ảnh.

## Tái lập

```bash
for f in 1 2 3 4 6; do
  C="--source data/processed/sds_rescale/x$f/images/val --model runs/train/E2c_s0/weights/best.pt --tile 640 --overlap 0.2 \
     --imgsz 640 --conf 0.001 --max-det 1000 --device 0 --no-images --altitude-csv data/processed/sds_det/meta_val.csv"
  .venv/bin/python scripts/run_tiled.py $C --min-person-px 8 --max-upscale 1 --output runs/e6_sds/x$f/E2c_goc
  .venv/bin/python scripts/run_tiled.py $C --min-person-px 8 --max-upscale 2 --output runs/e6_sds/x$f/E2c_up8
done
.venv/bin/python eval/recall_by_pixels.py --data data/processed/sds_rescale --runs runs/e6_sds --models E2c_goc E2c_up8 \
    --factors 1 2 3 4 6 --cluster-pattern '^(v\d+)_' --output runs/e6_sds/eval_upscale
for f in 2 3 4 6; do D=data/processed/sds_rescale/x$f
  .venv/bin/python eval/compare_runs.py --a runs/e6_sds/x$f/E2c_goc --b runs/e6_sds/x$f/E2c_up8 --images $D/images/val \
      --labels $D/labels/val --iou 0.5 --cluster-pattern '^(v\d+)_' --output runs/e6_sds/compare_goc_up8_x$f
done
```
