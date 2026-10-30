---
name: run-experiment
description: Chạy trọn một thí nghiệm của FloodEye (E0–E6) trên một tập dữ liệu - tạo file cấu hình nếu chưa có, chạy dự đoán, đánh giá theo nhóm kích thước ở IoU 0,5 và 0,3, rồi cập nhật bảng trong docs/results. Dùng khi người dùng nói "chạy E1 trên sds", "chạy lại E4", "đánh giá E2c".
argument-hint: <mã thí nghiệm> <tập dữ liệu>, ví dụ "E1 visdrone"
---

# Chạy một thí nghiệm

Tham số: `$ARGUMENTS` (mã thí nghiệm và tên tập dữ liệu). Thiếu một trong hai thì hỏi lại.

Mọi lệnh chạy từ thư mục gốc dự án bằng `.venv/bin/python`. Quy ước đo nằm trong `.claude/rules/experiments.md`; không đổi chúng ở đây.

## 1. Cấu hình

Tìm `configs/experiments/<Mã>_<tập>.yaml`.

- Có rồi và `runs/<tập>/<Mã>/` đã có kết quả: hỏi người dùng muốn chạy lại hay chỉ đánh giá lại.
- Chưa có: tạo từ file gần nhất của cùng mã hoặc cùng tập, đổi `source` và `output`, viết dòng chú thích đầu file mô tả cấu hình. Định nghĩa từng mã ở mục 4 của `docs/ROADMAP.md`.

## 2. Kiểm tra đầu vào

- `data/processed/<tập>/images/<split>` và `labels/<split>` phải tồn tại. Thiếu thì dừng và đưa lệnh chuẩn bị dữ liệu trong `README.md`; không tự tải dữ liệu.
- File trọng số trong cấu hình phải tồn tại. Thí nghiệm cần fine-tune (E2 trở đi) dùng trọng số tải về từ Kaggle; thiếu thì dừng và nói rõ, không huấn luyện trên máy cá nhân.
- Tập `flood`: không làm theo skill này. Tập chưa khoá (`data/processed/flood/MANIFEST.sha256` chưa có) thì dừng; đã khoá thì dùng `scripts/eval_flood.sh <thư mục file xuất CVAT> <Mã>`, rồi làm tiếp từ bước 5.

## 3. Dự đoán

- Cấu hình có `slice_size`: `scripts/run_sahi.py --config <file>`.
- Cấu hình có `tile`: `scripts/run_tiled.py --config <file>` (thu nhỏ theo độ cao cần thêm `--altitude-csv` và `--target-person-px`).
- Còn lại: `scripts/run_baseline.py --config <file>`.

Lần chạy trên cả tập mất vài phút tới vài chục phút: chạy nền và báo khi xong.

## 4. Đánh giá

Chạy ở cả hai ngưỡng, kèm mọi thí nghiệm đã có của cùng tập để ra một bảng so sánh:

```bash
D=data/processed/<tập>
for iou in 0.5 0.3; do
  .venv/bin/python eval/eval_by_size.py --runs runs/<tập>/E* \
      --images $D/images/<split> --labels $D/labels/<split> --iou $iou \
      --output runs/<tập>/eval_iou$iou
done
```

Thêm `--ignore $D/ignore/<split>` nếu thư mục đó tồn tại, và `--cluster-pattern` nếu nhiều ảnh cùng một video (`sds_det`: `'^(v\d+)_'`). Hai lần chạy cùng `method` và `imgsz` (ví dụ hai mô hình cùng chạy toàn ảnh 1280) không gộp được vào một lệnh: chấm từng lần chạy riêng, `--output runs/<tập>/eval_<Mã>_iou$iou`.

So với mốc gần nhất (thường là thí nghiệm trước của cùng tập) bằng bootstrap cặp, cũng ở cả hai ngưỡng:

```bash
.venv/bin/python eval/compare_runs.py --a runs/<tập>/<Mốc> --b runs/<tập>/<Mã> --images $D/images/<split> \
    --labels $D/labels/<split> --iou $iou --output runs/<tập>/compare_<Mốc>_<Mã>_iou$iou
```

## 5. Ghi kết quả

Cập nhật file của tập trong `docs/results/` (tạo mới theo bố cục `visdrone_baseline.md` nếu chưa có):

- chép số từ `eval_by_size.csv` và `compare.csv`, ba chữ số thập phân, dấu phẩy; hiệu số lấy từ `compare.csv`, không tự trừ;
- lấy phiên bản thư viện, mã băm trọng số, thiết bị từ `run_config.json`;
- lấy ms/ảnh từ `per_image.csv`, ghi rõ đo trên máy nào;
- thêm lệnh vừa chạy vào mục "Tái lập";
- chép `eval_by_size.png` sang `docs/results/` nếu bảng có thay đổi.

Không sửa số của thí nghiệm không được chạy lại. Thí nghiệm đổi trạng thái thì cập nhật cùng lúc bảng trạng thái ở TONG_QUAN mục 8 và ROADMAP mục 4.

## 6. Báo lại

Đưa bảng của thí nghiệm vừa chạy cạnh mốc so sánh gần nhất, và một hai nhận xét. Nêu rõ nếu kết quả trái với dự đoán trong ROADMAP hoặc với thí nghiệm trước, vì đó thường là dấu hiệu lỗi cấu hình hoặc lỗi nhãn chứ chưa chắc là phát hiện mới.
