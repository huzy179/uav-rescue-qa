---
paths:
  - "configs/**"
  - "scripts/**"
  - "eval/**"
  - "training/**"
  - "docs/results/**"
---

# Thí nghiệm và đánh giá

Kế hoạch thí nghiệm ở mục 4 của `docs/ROADMAP.md`; cách đo ở mục 5 của `docs/TECHNICAL.md`.

## Quy ước đo (mục 8.5 của đề cương)

- Dự đoán để tính AP chạy ở `conf: 0.001`, `max_det: 1000`.
- Recall và precision vận hành tính ở conf 0,25.
- IoU 0,5 cho mọi nhóm; báo thêm IoU 0,3 cho nhóm dưới 8 px.
- Nhóm kích thước theo cạnh ngắn của nhãn: `<8`, `8-16`, `16-32`, `>32` px.
- Dự đoán rơi vào vùng bỏ qua không bị tính là sai (`--ignore`).
- Thí nghiệm có huấn luyện chạy 3 seed cho cấu hình cuối.
- Khoảng tin cậy bootstrap 1.000 lần; tập có nhiều khung cùng video thì lấy mẫu theo video (`--cluster-pattern`: SeaDronesSee `'^(v\d+)_'`, tập lũ `'^(.+)_\d+$'`).
- So hai mô hình bằng bootstrap cặp (`eval/compare_runs.py`) ở cả IoU 0,5 và 0,3; hai khoảng tin cậy riêng chồng nhau không có nghĩa là như nhau.

Đổi bất kỳ quy ước nào ở trên thì mọi bảng cũ không còn so sánh được: hỏi trước, và nếu đổi thì chạy lại các thí nghiệm đã có.

## Cấu hình

- Mỗi thí nghiệm một file `configs/experiments/<Mã>_<tập>.yaml`, dòng đầu là chú thích mô tả cấu hình. Không sửa file của thí nghiệm đã có kết quả; cần biến thể thì tạo file mới.
- Kết quả ghi vào `runs/<tập>/<Mã>/`. `run_config.json` trong đó là bằng chứng tái lập; không xoá, không sửa tay.
- Cấu hình có `slice_size` chạy bằng `scripts/run_sahi.py`, có `tile` bằng `scripts/run_tiled.py`, còn lại `scripts/run_baseline.py`.

## Tập test lũ

- Chỉ chạy mô hình sau khi khoá (`docs/LABELING.md` mục 8), qua `scripts/eval_flood.sh`; script dừng nếu nhãn khác `MANIFEST.sha256`.
- Mỗi cấu hình cuối chạy một lần. Mọi tham số (conf, `--target-person-px`, N, bán kính) chọn trên tập khác rồi mới đưa vào cấu hình `*_flood.yaml`.

## Mã đánh giá

- Sửa `eval/metrics.py` thì phải giữ hoặc thêm ví dụ tính tay trong `tests/test_metrics.py`.
- Sau khi sửa cách tính, đối chiếu lại với `yolo val` trên E1 của VisDrone (mốc: mAP50 0,496; script cho 0,490 khi không dùng vùng bỏ qua).

## Tài liệu kết quả

- File trong `docs/results/` theo bố cục của `visdrone_baseline.md`: môi trường chạy, dữ liệu, cấu hình, bảng số, nhận xét, giới hạn, lệnh tái lập.
- Số trong bảng chép từ CSV trong `runs/` (`eval_by_size.csv`, `compare.csv`, `recall_by_pixels.csv`…), ba chữ số thập phân, dấu phẩy. Hiệu số và tỉ lệ cũng đọc từ CSV, không tự tính rồi làm tròn.
- Khi một kết quả mới làm đổi kết luận của file cũ, thêm một dòng trỏ sang file mới trong file cũ thay vì sửa số cũ.
- Ghi rõ file cấu hình nào sinh ra bảng nào.

## Huấn luyện

- Huấn luyện thật chạy trên Kaggle; trên máy cá nhân chỉ chạy thử vài epoch để kiểm tra mã.
- Lần chạy dài hơn một phiên 12 giờ thì chia phiên bằng `--stop-after-epochs` rồi `MODE = "resume"` (README, TECHNICAL 13.5); giữ `--epochs` là tổng để lịch tốc độ học không đổi.
- Notebook chỉ clone kho ở một commit cố định, cài gói và gọi `training/train.py`. Logic không nằm trong notebook.
