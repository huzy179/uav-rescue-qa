# Cắt ô kèm một lượt toàn ảnh cho người to: không đáng khi đã thu nhỏ theo độ cao

**Sơ bộ, trên SeaDronesSee 4K (nước biển, không phải lũ).** Đề xuất ở `docs/CAI_TIEN.md` mục 1.1: người to có thể bị cắt đôi giữa các ô 640; một lượt suy luận toàn ảnh (như `perform_standard_pred` của SAHI) có thể bắt lại họ. Kiểm tra lượt này có thêm gì so với thu nhỏ theo độ cao (`scale_by_altitude.md`) hay không.

## Cách làm

- 317 ảnh SDS 3840×2160, 1.055 người, 11 video (`sds_det.md`); E2c (`runs/train/E2c_s0/weights/best.pt`), cắt ô 640, chồng 0,2, conf 0,001, max_det 1000.
- Lượt toàn ảnh: `--full-pass --imgsz 1280` (E2c huấn luyện ở 1280), chạy trên khung **sau** khi thu nhỏ; box gộp với box của các ô bằng NMS theo IOS như giữa các ô (`edge/detector.py`).
- Lần chạy mới ở commit `aaab032` (`dirty: true`, thay đổi chưa commit lúc đó không nằm trên đường chạy của `run_tiled.py`). `E2c_tiled_px10_r` chạy lại `E2c_tiled_px10` của `scale_by_altitude.md` trên cùng commit để so cặp và có cột số ô: cho lại đúng AP50 0,531 và recall 0,579.
- IoU 0,5, bootstrap theo video (`'^(v\d+)_'`); số đọc từ `runs/sds_det/eval_<lần chạy>_iou0.5/eval_by_size.csv` và `runs/sds_det/compare_<A>_<B>/compare.csv`. Số lần suy luận đọc từ cột `n_tiles` của `per_image.csv` (lượt toàn ảnh tính là một).

## Kết quả

| Lần chạy | Cách chạy | AP50 | KTC 95% | Recall @0,25 | Precision @0,25 | Số lần suy luận (317 ảnh) |
|---|---|---|---|---|---|---|
| `E2c_tiled` | cắt ô ở độ phân giải gốc | 0,235 | 0,083–0,551 | 0,374 | 0,065 | |
| `E2c_tiled_full` | cắt ô gốc + lượt toàn ảnh | 0,354 | 0,135–0,588 | 0,526 | 0,088 | 10.461 |
| `E2c_tiled_px10_r` | thu nhỏ về 10 px dự kiến, cắt ô | 0,531 | 0,451–0,684 | 0,579 | 0,656 | 1.513 |
| `E2c_tiled_px10_full` | thu nhỏ về 10 px + lượt toàn ảnh | 0,518 | 0,412–0,635 | 0,600 | 0,628 | 1.830 |

Dòng `E2c_tiled` lấy từ `scale_by_altitude.md` (lần chạy cũ, chưa ghi số ô).

### So cặp

| B − A | Nhóm | Hiệu AP50 (KTC 95%) | Hiệu recall (KTC 95%) |
|---|---|---|---|
| px10 + toàn ảnh − px10 | tất cả | −0,013 (−0,071 đến +0,001) | +0,021 (−0,010 đến +0,040) |
| | > 32 px | −0,012 (−0,066 đến +0,004) | +0,028 (+0,005 đến +0,042), có ý nghĩa |
| cắt ô gốc + toàn ảnh − cắt ô gốc | tất cả | +0,119 (−0,020 đến +0,149) | +0,152 (−0,023 đến +0,198) |
| | > 32 px | +0,054 (−0,022 đến +0,076) | +0,166 (−0,003 đến +0,206) |

## Nhận xét

1. **Khi đã thu nhỏ theo độ cao, lượt toàn ảnh không cải thiện AP50** (−0,013, không có ý nghĩa); recall người trên 32 px tăng nhẹ có ý nghĩa (+0,028) nhưng precision giảm và số lần suy luận tăng từ 1.513 lên 1.830 (mỗi ảnh thêm một lượt ở 1280, nặng hơn một ô 640).
2. **Không thu nhỏ thì lượt toàn ảnh có giúp** (điểm ước lượng +0,119 AP50, +0,152 recall, chưa có ý nghĩa với 11 video), nhưng vẫn kém xa thu nhỏ theo độ cao (0,354 so với 0,531) mà tốn gấp nhiều lần số lần suy luận (10.461 so với 1.513). Precision vẫn rất thấp (0,088): báo nhầm của các ô ở độ phân giải gốc vẫn còn đó.
3. **Quyết định:** cấu hình cuối giữ thu nhỏ theo độ cao, không bật lượt toàn ảnh. `--full-pass` vẫn là tuỳ chọn (dùng cho so sánh với SAHI).

## Giới hạn

- Một tập, 11 video, người phần lớn trên 32 px (976/1.055); một mô hình, một mục tiêu thu nhỏ (10 px), lượt toàn ảnh một cỡ (1280).
- Thời gian không báo (máy cá nhân); số lần suy luận chỉ là đại diện thô cho chi phí vì lượt toàn ảnh 1280 nặng hơn một ô 640.

## Tái lập

```bash
C="--source data/processed/sds_det/images/val --model runs/train/E2c_s0/weights/best.pt --tile 640 --overlap 0.2 --conf 0.001 \
   --max-det 1000 --device 0 --no-images --altitude-csv data/processed/sds_det/meta_val.csv"
.venv/bin/python scripts/run_tiled.py $C --imgsz 640 --target-person-px 10 --output runs/sds_det/E2c_tiled_px10_r
.venv/bin/python scripts/run_tiled.py $C --imgsz 1280 --full-pass --target-person-px 10 --output runs/sds_det/E2c_tiled_px10_full
.venv/bin/python scripts/run_tiled.py $C --imgsz 1280 --full-pass --output runs/sds_det/E2c_tiled_full
D=data/processed/sds_det
for r in E2c_tiled_px10_r E2c_tiled_px10_full E2c_tiled_full; do
  .venv/bin/python eval/eval_by_size.py --runs runs/sds_det/$r --images $D/images/val --labels $D/labels/val --iou 0.5 \
      --cluster-pattern '^(v\d+)_' --output runs/sds_det/eval_${r}_iou0.5
done
.venv/bin/python eval/compare_runs.py --a runs/sds_det/E2c_tiled_px10_r --b runs/sds_det/E2c_tiled_px10_full --images $D/images/val \
    --labels $D/labels/val --iou 0.5 --cluster-pattern '^(v\d+)_' --output runs/sds_det/compare_E2c_tiled_px10_r_E2c_tiled_px10_full
.venv/bin/python eval/compare_runs.py --a runs/sds_det/E2c_tiled --b runs/sds_det/E2c_tiled_full --images $D/images/val \
    --labels $D/labels/val --iou 0.5 --cluster-pattern '^(v\d+)_' --output runs/sds_det/compare_E2c_tiled_E2c_tiled_full
```
