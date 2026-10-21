# VisDrone val: bộ cắt ô riêng so với SAHI (E4, chưa huấn luyện)

Mục đích: kiểm tra `edge/detector.py` (cắt ô theo lô, gộp bằng NMS theo IOS) cho độ chính xác tương đương SAHI trước khi dùng nó cho E4 trên dữ liệu khác và cho RQ2.

Chạy ngày 21/10/2026 trên Mac M4 (MPS). Mô hình `yolo26s.pt` (COCO, SHA-256 bắt đầu bằng `646f8bc3fe0a`), ultralytics 8.4.174, torch 2.14.1. Lần chạy SAHI là E4 ngày 10/10/2026 (xem [visdrone_baseline.md](visdrone_baseline.md)).

## Dữ liệu

VisDrone2019-DET val: 548 ảnh, 13.969 người, 1.410 vùng bỏ qua (như [visdrone_baseline.md](visdrone_baseline.md)).

## Cấu hình

| Mã | File cấu hình | Cắt ô | Lượt toàn ảnh | Gộp box giữa các ô |
|---|---|---|---|---|
| E4 | `configs/experiments/E4_visdrone.yaml` | SAHI, lát 640, chồng 0,2 | Có, 640 | GREEDYNMM theo IOS 0,5 (hợp nhất toạ độ) |
| E4tiled | `configs/experiments/E4tiled_visdrone.yaml` | `edge/detector.py`, ô 640, chồng 0,2, cả lô trong một lần `predict` | Có, 640 | NMS theo IOS 0,5 (giữ box điểm cao nhất) |

Chung: conf 0,001, `max_det` 1000; recall và precision vận hành ở conf 0,25; dự đoán trong vùng bỏ qua không bị tính là sai; khoảng tin cậy 95% bằng bootstrap 1000 lần theo ảnh.

## Kết quả

### IoU 0,5

| Cấu hình | Nhóm | AP | Khoảng tin cậy 95% của AP | Recall @0,25 | Precision @0,25 | Recall tối đa |
|---|---|---|---|---|---|---|
| SAHI (E4) | tất cả | 0,460 | 0,443–0,477 | 0,321 | 0,777 | 0,686 |
|  | <8 px | 0,149 | 0,133–0,169 | 0,054 | 0,638 | 0,383 |
|  | 8–16 px | 0,469 | 0,448–0,491 | 0,300 | 0,791 | 0,716 |
|  | 16–32 px | 0,673 | 0,645–0,699 | 0,543 | 0,787 | 0,876 |
|  | >32 px | 0,749 | 0,700–0,798 | 0,708 | 0,743 | 0,927 |
| Cắt ô riêng | tất cả | 0,452 | 0,437–0,469 | 0,313 | 0,810 | 0,610 |
|  | <8 px | 0,153 | 0,137–0,173 | 0,054 | 0,669 | 0,349 |
|  | 8–16 px | 0,462 | 0,441–0,481 | 0,295 | 0,816 | 0,636 |
|  | 16–32 px | 0,657 | 0,628–0,681 | 0,530 | 0,826 | 0,783 |
|  | >32 px | 0,706 | 0,653–0,759 | 0,654 | 0,786 | 0,808 |

### IoU 0,3

| Cấu hình | Nhóm | AP | Khoảng tin cậy 95% của AP | Recall @0,25 | Precision @0,25 | Recall tối đa |
|---|---|---|---|---|---|---|
| SAHI (E4) | tất cả | 0,569 | 0,553–0,584 | 0,347 | 0,840 | 0,824 |
|  | <8 px | 0,299 | 0,273–0,328 | 0,076 | 0,797 | 0,613 |
|  | 8–16 px | 0,592 | 0,570–0,613 | 0,332 | 0,857 | 0,859 |
|  | 16–32 px | 0,757 | 0,732–0,782 | 0,577 | 0,841 | 0,946 |
|  | >32 px | 0,825 | 0,788–0,866 | 0,755 | 0,802 | 0,978 |
| Cắt ô riêng | tất cả | 0,585 | 0,569–0,600 | 0,339 | 0,878 | 0,775 |
|  | <8 px | 0,324 | 0,297–0,350 | 0,075 | 0,836 | 0,591 |
|  | 8–16 px | 0,606 | 0,584–0,625 | 0,327 | 0,885 | 0,811 |
|  | 16–32 px | 0,774 | 0,749–0,797 | 0,568 | 0,883 | 0,905 |
|  | >32 px | 0,856 | 0,818–0,886 | 0,723 | 0,869 | 0,931 |

### So sánh cặp (bootstrap cặp, 1000 lần, theo ảnh)

Hai khoảng tin cậy riêng ở trên chồng nhau, nhưng điều đó **không** có nghĩa là hai cách cho kết quả như nhau. Bootstrap cặp rút cùng một bộ ảnh cho cả hai cấu hình rồi tính hiệu số (TECHNICAL mục 15), nên phát hiện được chênh lệch nhỏ mà ổn định.

### IoU 0,5

| Nhóm | Chỉ số | SAHI (A) | Cắt ô riêng (B) | B − A | Khoảng tin cậy 95% của B − A | p | Khác có ý nghĩa |
|---|---|---|---|---|---|---|---|
| tất cả | AP | 0,460 | 0,452 | -0,008 | -0,011 đến -0,003 | 0,000 | có |
| tất cả | Recall @0,25 | 0,321 | 0,313 | -0,008 | -0,010 đến -0,006 | 0,000 | có |
| <8 px | AP | 0,149 | 0,153 | +0,004 | +0,001 đến +0,009 | 0,020 | có |
| <8 px | Recall @0,25 | 0,054 | 0,054 | -0,001 | -0,002 đến +0,000 | 0,260 | không |
| 8–16 px | AP | 0,469 | 0,462 | -0,008 | -0,014 đến -0,002 | 0,006 | có |
| 8–16 px | Recall @0,25 | 0,300 | 0,295 | -0,005 | -0,007 đến -0,003 | 0,000 | có |
| 16–32 px | AP | 0,673 | 0,657 | -0,016 | -0,025 đến -0,009 | 0,000 | có |
| 16–32 px | Recall @0,25 | 0,543 | 0,530 | -0,012 | -0,016 đến -0,009 | 0,000 | có |
| >32 px | AP | 0,749 | 0,706 | -0,043 | -0,071 đến -0,016 | 0,004 | có |
| >32 px | Recall @0,25 | 0,708 | 0,654 | -0,053 | -0,080 đến -0,029 | 0,000 | có |

### IoU 0,3

| Nhóm | Chỉ số | SAHI (A) | Cắt ô riêng (B) | B − A | Khoảng tin cậy 95% của B − A | p | Khác có ý nghĩa |
|---|---|---|---|---|---|---|---|
| tất cả | AP | 0,569 | 0,585 | +0,016 | +0,012 đến +0,021 | 0,000 | có |
| tất cả | Recall @0,25 | 0,347 | 0,339 | -0,007 | -0,009 đến -0,006 | 0,000 | có |
| <8 px | AP | 0,299 | 0,324 | +0,024 | +0,017 đến +0,031 | 0,000 | có |
| <8 px | Recall @0,25 | 0,076 | 0,075 | -0,001 | -0,002 đến +0,000 | 0,256 | không |
| 8–16 px | AP | 0,592 | 0,606 | +0,014 | +0,006 đến +0,019 | 0,000 | có |
| 8–16 px | Recall @0,25 | 0,332 | 0,327 | -0,006 | -0,008 đến -0,004 | 0,000 | có |
| 16–32 px | AP | 0,757 | 0,774 | +0,017 | +0,009 đến +0,024 | 0,000 | có |
| 16–32 px | Recall @0,25 | 0,577 | 0,568 | -0,009 | -0,013 đến -0,007 | 0,000 | có |
| >32 px | AP | 0,825 | 0,856 | +0,030 | -0,003 đến +0,053 | 0,084 | không |
| >32 px | Recall @0,25 | 0,755 | 0,723 | -0,032 | -0,048 đến -0,018 | 0,000 | có |

Số box sau gộp: SAHI 94.895, cắt ô riêng 61.981. Thời gian trung bình mỗi ảnh trên Mac (chỉ để so sánh tương đối): SAHI 160,4 ms, cắt ô riêng 115,3 ms.

Lấy mẫu theo video (cluster bootstrap, 76 video; `runs/visdrone/compare_E4_E4tiled_iou0.5_cluster`) cho hiệu AP50 nhóm tất cả −0,011 đến −0,003, gần như trùng với lấy mẫu theo ảnh: kết luận không đổi.

## Nhận xét

1. **Bộ cắt ô riêng kém SAHI một chút nhưng có ý nghĩa thống kê ở IoU 0,5**: AP50 thấp hơn 0,008 (khoảng tin cậy −0,011 đến −0,003), recall vận hành thấp hơn 0,008. Nếu chỉ nhìn hai khoảng tin cậy riêng (0,437–0,469 và 0,443–0,477) sẽ kết luận sai là "như nhau". Chênh lệch tập trung ở người lớn (>32 px: AP −0,043); ở người dưới 8 px, bộ cắt ô riêng **cao hơn** (+0,004 ở IoU 0,5, +0,024 ở IoU 0,3). Với đề tài người nhỏ, mức đánh đổi này chấp nhận được: dùng bộ cắt ô riêng cho RQ2 vì chạy theo lô và xuất được TensorRT, và ghi rõ chênh lệch này.
2. **Precision vận hành của bộ cắt ô riêng cao hơn ở mọi nhóm** (0,810 so với 0,777 ở nhóm tất cả), nhưng **recall tối đa thấp hơn** (0,610 so với 0,686), và giữ ít box hơn khoảng một phần ba. Giả thuyết, chưa kiểm chứng: ở conf 0,001, NMS theo IOS xoá box của người đứng sát nhau trong đám đông (box nhỏ nằm gọn trong box bên cạnh có IOS gần 1). Chênh lệch chủ yếu ở vùng conf thấp, nên ảnh hưởng tới điểm vận hành nhỏ.
3. **Ở IoU 0,3, bộ cắt ô riêng cao hơn SAHI có ý nghĩa** (AP +0,016, khoảng tin cậy +0,012 đến +0,021), kể cả ở nhóm dưới 8 px. Box của bộ cắt ô riêng tìm đúng chỗ nhưng kém khít hơn, khớp với việc NMS giữ box điểm cao nhất chứ không hợp nhất toạ độ.
4. **Đã thử và bỏ:** hợp nhất toạ độ kiểu NMM (như GREEDYNMM) trên bộ cắt ô riêng làm AP50 tụt xuống dưới 0,05, vì box lớn điểm thấp phủ cả nhóm người kéo box của từng người thành box cả nhóm. Lần chạy đó không giữ lại; lý do được ghi trong docstring của `merge_boxes`.

## Giới hạn

- Như [visdrone_baseline.md](visdrone_baseline.md): VisDrone không có cảnh lũ, mô hình chưa huấn luyện, ảnh chỉ rộng 1360 px nên cắt ô không có lợi thế độ phân giải như trên video 4K.
- Thời gian đo trên Mac, không đại diện cho Jetson; lô ô trên MPS khác với trên TensorRT.

## Tái lập

```bash
.venv/bin/python scripts/run_tiled.py --config configs/experiments/E4tiled_visdrone.yaml
D=data/processed/visdrone
for run in E4 E4tiled; do for iou in 0.5 0.3; do
  .venv/bin/python eval/eval_by_size.py --runs runs/visdrone/$run --images $D/images/val --labels $D/labels/val \
      --ignore $D/ignore/val --iou $iou --output runs/visdrone/$run/eval_iou$iou
done; done
for iou in 0.5 0.3; do
  .venv/bin/python eval/compare_runs.py --a runs/visdrone/E4 --b runs/visdrone/E4tiled --images $D/images/val \
      --labels $D/labels/val --ignore $D/ignore/val --iou $iou --output runs/visdrone/compare_E4_E4tiled_iou$iou
done
```

Phải đánh giá từng lần chạy riêng: `eval_by_size.py` nhận diện cấu hình theo `method` và `imgsz`, nên hai lần chạy cùng `method` đưa vào chung một lệnh sẽ bị gộp thành một cấu hình.
