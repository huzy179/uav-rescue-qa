# E2e: E2c thêm C2A (thêm người cỡ to), phiên 1/2 (33/55 epoch)

**Giữa chừng, chưa phải kết quả.** Phiên 1 chạy 33 trong 55 epoch theo lịch tốc độ học của 55 epoch (`--stop-after-epochs 33`); phiên 2 chạy tiếp 22 epoch. Bảng dưới chỉ để xem mô hình có học đúng hướng không; so sánh chính thức làm sau phiên 2, trên SeaDronesSee và tập test lũ (quyết định #14 của ROADMAP).

## Môi trường và cấu hình

- Kaggle, Tesla T4, notebook `floodeye-train-e2e` phiên bản 2; mã ở commit `7ca5240` (ghim trong `notebooks/kaggle_train.ipynb`; `run_config.json` lần này không ghi được mã commit, trường `git_commit` rỗng).
- `configs/experiments/E2e_s0.yaml`: VisDrone train + AFO train + C2A train (15.387 ảnh), val VisDrone + AFO (887 ảnh) như E2c; YOLO26s, imgsz 1280, batch 8, seed 0, `--epochs 55 --stop-after-epochs 33`.
- Dữ liệu chuẩn bị trên Kaggle: C2A `rgbnihal/c2a-dataset` (train 6.129 ảnh), AFO như E2c.
- Kết quả: `runs/train/E2e_s0/` (`results.csv`, `weights/last_resume.pt` để chạy tiếp).

## Thời gian

33 epoch trong 10,53 giờ (cột `time` của `results.csv`), mỗi epoch trung vị 19,1 phút; E2c trung vị 10,0 phút mỗi epoch (`runs/train/E2c_s0/results.csv`). Cả phiên, kể cả chuẩn bị dữ liệu: 11 giờ 31 phút theo Kaggle, sát giới hạn 12 giờ. Phiên 2 (22 epoch) dự kiến khoảng 7 giờ.

## mAP50 trên val của ultralytics (VisDrone + AFO val), cùng epoch với E2c

| Epoch | E2e | E2c |
|---|---|---|
| 1 | 0,589 | 0,515 |
| 5 | 0,615 | 0,595 |
| 10 | 0,674 | 0,650 |
| 20 | 0,727 | 0,723 |
| 30 | 0,756 | 0,748 |
| 33 | 0,759 | 0,760 |

E2c sau 55 epoch: 0,782. Số đọc từ cột `metrics/mAP50(B)` của hai file `results.csv`; đây là chỉ số ultralytics trên val (không vùng bỏ qua, không theo nhóm kích thước), không phải `eval_by_size.py`.

## Nhận xét sơ bộ

- Thêm C2A không làm kém trên val VisDrone + AFO tới epoch 33 (ngang E2c ở cùng epoch). Val này chủ yếu người nhỏ, nên không đo được điều E2e nhắm tới (người to).
- Câu hỏi chính cần chờ phiên 2: E2e có tốt hơn E2c với người trên 32 px (SeaDronesSee, `e6_sds_pilot.md`) và trên tập test lũ không.

## Chạy tiếp (phiên 2)

Lần thử đầu (phiên bản 3 của notebook, 6/11) dừng ở ô huấn luyện vì Input chưa có `last_resume.pt`; phiên bản 3 không có file này, nên gắn "output mới nhất" của notebook sẽ lỗi lại. Cách chạy: tải `runs/train/E2e_s0/weights/last_resume.pt` và `results.csv` lên thành một dataset riêng (`floodeye-e2e-resume`, hai file cùng thư mục để `results.csv` nối tiếp), Add Input dataset đó cùng AFO, C2A; `MODE = "resume"`, `STOP_AFTER = None`, giữ `COMMIT`, `CONFIG`, `EPOCHS = 55`; Save & Run All (Commit).
