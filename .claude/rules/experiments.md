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

Đổi bất kỳ quy ước nào ở trên thì mọi bảng cũ không còn so sánh được: hỏi trước, và nếu đổi thì chạy lại các thí nghiệm đã có.

## Cấu hình

- Mỗi thí nghiệm một file `configs/experiments/<Mã>_<tập>.yaml`, dòng đầu là chú thích mô tả cấu hình. Không sửa file của thí nghiệm đã có kết quả; cần biến thể thì tạo file mới.
- Kết quả ghi vào `runs/<tập>/<Mã>/`. `run_config.json` trong đó là bằng chứng tái lập; không xoá, không sửa tay.

## Mã đánh giá

- Sửa `eval/metrics.py` thì phải giữ hoặc thêm ví dụ tính tay trong `tests/test_metrics.py`.
- Sau khi sửa cách tính, đối chiếu lại với `yolo val` trên E1 của VisDrone (mốc: mAP50 0,496; script cho 0,490 khi không dùng vùng bỏ qua).

## Tài liệu kết quả

- File trong `docs/results/` theo bố cục của `visdrone_baseline.md`: môi trường chạy, dữ liệu, cấu hình, bảng số, nhận xét, giới hạn, lệnh tái lập.
- Số trong bảng chép từ `eval_by_size.csv`, ba chữ số thập phân, dấu phẩy.
- Ghi rõ file cấu hình nào sinh ra bảng nào.

## Huấn luyện

- Huấn luyện thật chạy trên Kaggle; trên Mac chỉ chạy thử vài epoch để kiểm tra mã.
- Notebook chỉ clone kho ở một commit cố định, cài gói và gọi `training/train.py`. Logic không nằm trong notebook.
