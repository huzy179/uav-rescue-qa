# Đầu ra một-một không NMS của YOLO26: kết quả âm về độ chính xác

Đề xuất ở `docs/CAI_TIEN.md` mục 2. YOLO26 có hai đầu dự đoán: đầu một-nhiều cần bước loại bỏ box trùng (NMS) và đầu một-một cho kết quả cuối không cần NMS. Ultralytics 8.4.174 mặc định dùng đầu một-nhiều kèm NMS, và mọi kết quả của luận văn trước 8/11 dùng mặc định đó (TECHNICAL mục 3.1). Câu hỏi: dùng đầu một-một (`nms=False`), vốn được giới thiệu là đơn giản và nhanh hơn cho thiết bị biên, có giữ được độ chính xác với người nhỏ không.

## Cách làm

- Cờ mới `--nms-free` ở `scripts/run_baseline.py`, `scripts/run_tiled.py` và `edge.detector.YoloDetector(nms_free=...)`: truyền `nms=False` cho ultralytics; mặc định tắt, nên mọi kết quả cũ không đổi.
- Cùng trọng số E2c (`runs/train/E2c_s0/weights/best.pt`), chỉ đổi đầu ra, trên ba tập:
  - VisDrone val và test-dev, toàn ảnh 1280 (`configs/experiments/E2cnf_visdrone.yaml`, `E2cnf_visdrone-testdev.yaml`), so với `runs/visdrone/E2c`, `runs/visdrone-testdev/E2c`;
  - SeaDronesSee val, cắt ô 640 thu nhỏ về 10 px theo độ cao, tức cấu hình cuối (`E2cnf_sds_tiled_px10.yaml`), so với `runs/sds_det/E2c_tiled_px10`.
- Bootstrap cặp 1.000 lần theo video (`eval/compare_runs.py`; VisDrone `'^(\d+)_'`, SeaDronesSee `'^(v\d+)_'`), IoU 0,5 và 0,3, conf 0,001 và `max_det` 1000 như mọi bảng. Chạy trên RTX 5060 (WSL) ngày 8/11 ở commit `b4e1380`, `dirty: true` vì cờ `--nms-free` lúc đó chưa commit (commit ngay sau, cùng nội dung).
- Kết quả: `runs/visdrone/compare_E2c_E2cnf_iou*`, `runs/visdrone-testdev/compare_E2c_E2cnf_iou*`, `runs/sds_det/compare_E2c_tiled_px10_E2cnf_iou*`.

## Kết quả, IoU 0,5 (B − A: đầu một-một trừ mặc định; in đậm là có ý nghĩa thống kê)

| Tập | Nhóm | Chỉ số | Mặc định (A) | Một-một (B) | Hiệu (KTC 95%) |
|---|---|---|---|---|---|
| VisDrone val | tất cả | AP50 | 0,747 | 0,740 | **−0,007 (−0,010 đến −0,004)** |
| | tất cả | recall | 0,665 | 0,632 | **−0,034 (−0,040 đến −0,028)** |
| | < 8 px | AP50 | 0,546 | 0,526 | **−0,019 (−0,026 đến −0,012)** |
| | < 8 px | recall | 0,456 | 0,401 | **−0,056 (−0,065 đến −0,044)** |
| | > 32 px | AP50 | 0,887 | 0,867 | **−0,020 (−0,033 đến −0,005)** |
| VisDrone test-dev | tất cả | AP50 | 0,507 | 0,506 | −0,001 (−0,009 đến +0,003) |
| | tất cả | recall | 0,459 | 0,429 | **−0,030 (−0,038 đến −0,025)** |
| | < 8 px | AP50 | 0,241 | 0,245 | +0,004 (−0,011 đến +0,006) |
| | < 8 px | recall | 0,218 | 0,189 | **−0,029 (−0,057 đến −0,023)** |
| | > 32 px | AP50 | 0,887 | 0,856 | **−0,031 (−0,045 đến −0,017)** |
| SeaDronesSee, cấu hình cuối | tất cả | AP50 | 0,531 | 0,517 | −0,014 (−0,022 đến +0,019) |
| | tất cả | recall | 0,579 | 0,563 | −0,016 (−0,027 đến +0,013) |

Recall là recall vận hành ở conf 0,25. Ở IoU 0,3, nhóm dưới 8 px: VisDrone val recall −0,067 (−0,079 đến −0,051), test-dev −0,050 (−0,073 đến −0,046), đều có ý nghĩa. SeaDronesSee không có người dưới 8 px, và nhóm 8–16 px có recall 0 ở cả hai cách (`compare.csv`).

**Thời gian** (RTX 5060, PyTorch, chỉ so tương đối): toàn ảnh 1280 trên VisDrone, trung vị 15,2 ms/ảnh ở cả hai cách (`per_image.csv`). Lần chạy cắt ô mặc định trên SeaDronesSee làm ngày 26/10 với mã khác, nên không so thời gian cắt ô được.

## Nhận xét

1. **Đầu một-một mất recall vận hành ở mọi tập VisDrone, nhiều nhất ở người nhỏ**: dưới 8 px, recall ở conf 0,25 giảm 0,056 (val) và 0,029 (test-dev); AP50 chung gần như không đổi trên test-dev. AP gần như giữ nhưng recall ở ngưỡng cố định giảm; giải thích hợp lý (chưa kiểm tra riêng) là đầu một-một xếp hạng box gần như cũ nhưng cho conf thấp hơn, nên ở ngưỡng 0,25 bỏ bớt người. Trên SeaDronesSee (người to, cấu hình cuối) chênh lệch không có ý nghĩa.
2. **Không thấy lợi về thời gian trên PyTorch**: NMS trên GPU cho vài trăm box đã rẻ so với suy luận ở 1280. Lợi ích được giới thiệu chủ yếu ở các định dạng triển khai (TensorRT, thiết bị không có NMS nhanh), nơi luận văn chưa đo.
3. **Quyết định:** giữ mặc định (đầu một-nhiều kèm NMS) cho mọi cấu hình. Đầu một-một chỉ đáng xét lại nếu đo trên TensorRT cho thấy nhanh hơn rõ, và khi đó phải hạ ngưỡng conf để lấy lại recall, tức là đổi điểm vận hành, cần chọn lại trên tập val.

## Giới hạn

- Một mô hình (E2c), không đo thời gian trên TensorRT hay Jetson.
- Ngưỡng conf 0,25 cố định cho cả hai cách; đầu một-một có thể cần ngưỡng khác để cùng recall, chưa chọn (chọn phải làm trên val, không trên tập lũ).

## Tái lập

```bash
.venv/bin/python scripts/run_baseline.py --config configs/experiments/E2cnf_visdrone.yaml --device 0
.venv/bin/python scripts/run_baseline.py --config configs/experiments/E2cnf_visdrone-testdev.yaml --device 0
.venv/bin/python scripts/run_tiled.py --config configs/experiments/E2cnf_sds_tiled_px10.yaml --device 0
V=data/processed/visdrone; S=data/processed/sds_det
for iou in 0.5 0.3; do
  .venv/bin/python eval/compare_runs.py --a runs/visdrone/E2c --b runs/visdrone/E2cnf --images $V/images/val --labels $V/labels/val \
      --ignore $V/ignore/val --iou $iou --cluster-pattern '^(\d+)_' --output runs/visdrone/compare_E2c_E2cnf_iou$iou
  .venv/bin/python eval/compare_runs.py --a runs/visdrone-testdev/E2c --b runs/visdrone-testdev/E2cnf --images $V/images/test-dev \
      --labels $V/labels/test-dev --ignore $V/ignore/test-dev --iou $iou --cluster-pattern '^(\d+)_' \
      --output runs/visdrone-testdev/compare_E2c_E2cnf_iou$iou
  .venv/bin/python eval/compare_runs.py --a runs/sds_det/E2c_tiled_px10 --b runs/sds_det/E2cnf_tiled_px10 --images $S/images/val \
      --labels $S/labels/val --iou $iou --cluster-pattern '^(v\d+)_' --output runs/sds_det/compare_E2c_tiled_px10_E2cnf_iou$iou
done
```
