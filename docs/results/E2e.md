# E2e: E2c thêm C2A (thêm người cỡ to), đủ 55 epoch

**Kết quả âm với mục tiêu chính.** E2e = dữ liệu của E2c (VisDrone + AFO) thêm C2A (ảnh thảm hoạ có người cỡ to), để chữa điểm yếu của E2c với người trên 32 px (`e6_sds_pilot.md`, quyết định #14 của ROADMAP). Trên SeaDronesSee, nơi người phần lớn trên 32 px, E2e không hơn E2c có ý nghĩa thống kê; trên VisDrone, E2e kém E2c rõ ở người nhỏ. **Giữ E2c làm mô hình chính**; với người to, thu nhỏ theo độ cao (`scale_by_altitude.md`) là cách chữa đã đo được.

## Môi trường và cấu hình

- Huấn luyện: Kaggle, Tesla T4, notebook `floodeye-train-e2e`; mã ở commit `7ca5240` (ghim trong `notebooks/kaggle_train.ipynb`; `run_config.json` không ghi được commit). Phiên 1: phiên bản 2, epoch 1–33 (`--stop-after-epochs 33`); phiên 2: chạy tiếp từ `last_resume.pt` (dataset `floodeye-e2e-resume`), epoch 34–55. `results.csv` đủ 55 dòng liên tục, 33 dòng đầu trùng bản phiên 1 (`runs/train/E2e_s0_phien1/`); log phiên 2 ở `runs/train/E2e_s0_phien2/kaggle_log.ipynb` (dòng "Resuming training ... from epoch 34 to 55 total epochs").
- `configs/experiments/E2e_s0.yaml`: VisDrone train + AFO train + C2A train (15.387 ảnh), val VisDrone + AFO (887 ảnh) như E2c; YOLO26s, imgsz 1280, batch 8, seed 0, 55 epoch.
- Thời gian: phiên 1 trung vị 19,1 phút mỗi epoch, phiên 2 trung vị 18,7 phút (cột `time` của `results.csv`), phiên 2 tổng 6,77 giờ; E2c trung vị 10,0 phút mỗi epoch.
- Đánh giá: máy cá nhân, RTX 5060 (WSL), ultralytics 8.4.174, torch 2.14.1; `best.pt` sha256 `788b6001…6927` (`runs/visdrone/E2e/run_config.json`). Toàn ảnh 1280, conf 0,001, max_det 1000, như E2c. Suy luận trung vị 17,49–18,82 ms/ảnh (`per_image.csv`; máy cá nhân, chỉ để so tương đối).
- Cấu hình: `E2e_visdrone.yaml`, `E2e_visdrone-testdev.yaml`, `E2e_afo.yaml`, `E2e_sds.yaml`. Cách chấm giống hệt E2c trên từng tập: VisDrone có vùng bỏ qua; AFO không dùng vùng bỏ qua (như `E2c.md`); SeaDronesSee bootstrap theo video (`'^(v\d+)_'`, 11 video).

## mAP50 trên val của ultralytics (trong lúc huấn luyện)

| Epoch | E2e | E2c |
|---|---|---|
| 1 | 0,589 | 0,515 |
| 10 | 0,674 | 0,650 |
| 20 | 0,727 | 0,723 |
| 33 | 0,759 | 0,760 |
| 34 | 0,766 | 0,763 |
| 40 | 0,771 | 0,775 |
| 50 | 0,770 | 0,779 |
| 55 | 0,771 | 0,782 |

Cột `metrics/mAP50(B)` của hai `results.csv`; không vùng bỏ qua, không theo nhóm cỡ. E2e học nhanh hơn ở đầu nhưng dừng tăng từ khoảng epoch 40, E2c tiếp tục tăng.

## AP50 theo nhóm cỡ, IoU 0,5 (so cặp bằng bootstrap, `compare.csv`)

| Tập | Nhóm | E2c | E2e | Hiệu | KTC 95% | Có ý nghĩa |
|---|---|---|---|---|---|---|
| VisDrone val | tất cả | 0,747 | 0,718 | −0,029 | −0,035 đến −0,023 | có |
| | < 8 px | 0,546 | 0,492 | −0,053 | −0,067 đến −0,040 | có |
| | 8–16 px | 0,777 | 0,751 | −0,026 | −0,035 đến −0,018 | có |
| | 16–32 px | 0,849 | 0,833 | −0,015 | −0,023 đến −0,007 | có |
| | > 32 px | 0,888 | 0,871 | −0,017 | −0,034 đến +0,002 | không |
| VisDrone test-dev | tất cả | 0,507 | 0,466 | −0,041 | −0,047 đến −0,035 | có |
| | < 8 px | 0,241 | 0,202 | −0,040 | −0,048 đến −0,030 | có |
| | > 32 px | 0,887 | 0,879 | −0,008 | −0,023 đến +0,004 | không |
| AFO test | tất cả | 0,568 | 0,624 | +0,057 | +0,037 đến +0,078 | có |
| | > 32 px | 0,591 | 0,637 | +0,046 | +0,026 đến +0,068 | có |
| SeaDronesSee val | tất cả | 0,468 | 0,509 | +0,041 | −0,167 đến +0,167 | không |
| | > 32 px | 0,470 | 0,525 | +0,055 | −0,161 đến +0,173 | không |

Recall ở conf 0,25 trên SeaDronesSee: E2c 0,465, E2e 0,575, hiệu +0,110 (−0,112 đến +0,264), không có ý nghĩa. E2e so với mô hình gốc E1 trên SeaDronesSee: 0,535 → 0,509, hiệu −0,027 (−0,406 đến +0,176), không có ý nghĩa (`runs/sds_det/compare_E1_E2e_iou0.5`).

Ở IoU 0,3 kết luận giữ nguyên: VisDrone val tất cả −0,025 (có ý nghĩa), < 8 px −0,041 (có); VisDrone test-dev tất cả −0,048 (có); AFO +0,029 (có); SeaDronesSee +0,063 (−0,047 đến +0,144, không). Bảng đầy đủ: `runs/<tập>/compare_E2c_E2e_iou{0.5,0.3}/compare.csv`, `runs/<tập>/eval_E2e*_iou{0.5,0.3}/eval_by_size.csv`.

## Nhận xét

1. **Trái với dự đoán của ROADMAP** (thêm người to giúp người to mà không mất người nhỏ). Người nhỏ mất rõ trên cả VisDrone val và test-dev, ở mọi nhóm dưới 32 px; người trên 32 px trên VisDrone không đổi có ý nghĩa.
2. **Trên AFO E2e tốt hơn** có ý nghĩa (+0,057). AFO là người dưới nước, phần lớn trên 32 px, và train, test cùng nguồn (`sds_det.md` mục nhận xét 3), nên mức tăng này không chắc chuyển sang tập khác.
3. **Trên SeaDronesSee mức tăng không có ý nghĩa**: điểm ước lượng +0,041 AP50 và +0,110 recall, nhưng 11 video cho khoảng tin cậy rộng từ −0,167 tới +0,167. Chưa đủ bằng chứng để nói C2A chữa được điểm yếu người to; cũng chưa vượt mô hình gốc E1.
4. Một giải thích hợp lý (chưa kiểm chứng): C2A chiếm 6.129 trên 15.387 ảnh train, toàn người cỡ to trên nền thảm hoạ; tỉ lệ người nhỏ trong dữ liệu giảm nên mô hình dồn sức vào người to. Đúng điều đề tài cần tránh, vì người trong ảnh lũ từ UAV phần lớn nhỏ.
5. Hệ quả: E2c vẫn là mô hình chính cho tập lũ và pipeline. Người to xử lý bằng thu nhỏ theo độ cao (AP50 0,531 trên SeaDronesSee 4K khi cắt ô, `scale_by_altitude.md`; khác cách chạy nên không so trực tiếp với bảng trên). Cách thêm dữ liệu người to mà không mất người nhỏ: `docs/CAI_TIEN.md` mục 1.1.

## Giới hạn

- Một seed. Hiệu trên VisDrone nhỏ nhưng ổn định ở hai tập và hai ngưỡng IoU.
- SeaDronesSee chỉ 11 video, khoảng tin cậy rất rộng; chưa chấm trên tập test lũ (chưa khoá). Cấu hình `E2e_flood.yaml` có sẵn; quyết định có chạy trên tập lũ hay không nằm ở ROADMAP.
- `best.pt` chọn theo val VisDrone + AFO, như E2c.

## Tái lập

```bash
# Huấn luyện: notebooks/kaggle_train.ipynb, COMMIT 7ca5240, CONFIG configs/experiments/E2e_s0.yaml, EPOCHS 55;
#   phiên 1 MODE "train", STOP_AFTER 33, Add Input AFO, C2A; phiên 2 MODE "resume", STOP_AFTER None, thêm Input floodeye-e2e-resume
V=data/processed/visdrone; A=data/processed/afo; S=data/processed/sds_det
for t in visdrone visdrone-testdev afo sds; do python scripts/run_baseline.py --config configs/experiments/E2e_$t.yaml; done
for iou in 0.5 0.3; do
  python eval/eval_by_size.py --runs runs/visdrone/E2e --images $V/images/val --labels $V/labels/val --ignore $V/ignore/val --iou $iou --output runs/visdrone/eval_E2e_iou$iou
  python eval/compare_runs.py --a runs/visdrone/E2c --b runs/visdrone/E2e --images $V/images/val --labels $V/labels/val --ignore $V/ignore/val --iou $iou --output runs/visdrone/compare_E2c_E2e_iou$iou
  python eval/eval_by_size.py --runs runs/visdrone-testdev/E2e --images $V/images/test-dev --labels $V/labels/test-dev --ignore $V/ignore/test-dev --iou $iou --output runs/visdrone-testdev/eval_E2e_iou$iou
  python eval/compare_runs.py --a runs/visdrone-testdev/E2c --b runs/visdrone-testdev/E2e --images $V/images/test-dev --labels $V/labels/test-dev --ignore $V/ignore/test-dev --iou $iou --output runs/visdrone-testdev/compare_E2c_E2e_iou$iou
  python eval/eval_by_size.py --runs runs/afo/E2e --images $A/images/test --labels $A/labels/test --iou $iou --output runs/afo/eval_E2e_test_iou$iou
  python eval/compare_runs.py --a runs/afo/E2c --b runs/afo/E2e --images $A/images/test --labels $A/labels/test --iou $iou --output runs/afo/compare_E2c_E2e_iou$iou
  python eval/eval_by_size.py --runs runs/sds_det/E2e --images $S/images/val --labels $S/labels/val --iou $iou --cluster-pattern '^(v\d+)_' --output runs/sds_det/eval_E2e_iou$iou
  python eval/compare_runs.py --a runs/sds_det/E2c --b runs/sds_det/E2e --images $S/images/val --labels $S/labels/val --iou $iou --cluster-pattern '^(v\d+)_' --output runs/sds_det/compare_E2c_E2e_iou$iou
done
python eval/compare_runs.py --a runs/sds_det/E1 --b runs/sds_det/E2e --images $S/images/val --labels $S/labels/val --iou 0.5 --cluster-pattern '^(v\d+)_' --output runs/sds_det/compare_E1_E2e_iou0.5
```
