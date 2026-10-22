# AFO: người dưới nước, E1 so với E2 lượt 1

AFO (Aerial dataset of Floating Objects; Gąsienica-Józkowy và cộng sự, 2021) là ảnh drone chụp người bơi, ván, thuyền trên hồ và biển. Dùng ở đây làm **thước đo người dưới nước** cho mô hình, trước khi có tập test lũ. Kết quả này là lý do E2 lượt 2 thêm AFO vào dữ liệu huấn luyện (`configs/experiments/E2c_s0.yaml`).

## Dữ liệu

- Nguồn: Kaggle `jangsienicajzkowy/afo-aerial-dataset-of-floating-objects`, giấy phép CC BY-NC-SA 3.0 (phi thương mại, trích dẫn tác giả; không phân phối lại ảnh).
- Chuẩn bị: `tools/prepare_afo.py` (gom ảnh từ ba phần, chia tập theo `train.txt`, `validation.txt`, `test.txt` của tác giả), rồi `tools/convert_yolo_subset.py --keep human` (bỏ ván, thuyền, phao, thuyền buồm, kayak).
- Sau chuyển (`data/processed/afo/stats.json`): train 2.787 ảnh, 22.272 người; val 339 ảnh, 4.391 người; **test 514 ảnh, 6.511 người**. Ảnh từ 1280×720 tới 3840×2160; người phần lớn lớn hơn 32 px (khác hẳn VisDrone).

### Độ độc lập của tập test

Tác giả lấy test từ 9 video không dùng cho train. Kiểm tra lại (`runs/leakage/afo_test/`):
- **Theo tên:** 2 nhóm tên (`a`, `z3`) có ở cả test và train. Xem tận mắt: ảnh test và train cùng nhóm `a` là **cùng một bãi tắm, khác thời điểm**. Test không hoàn toàn độc lập về địa điểm.
- **Theo dHash:** 287 cặp gần trùng (≤ 5 bit) liên quan 29 ảnh test. Xem tận mắt cặp đầu: hai cảnh khác hẳn nhau. Mặt nước ít chi tiết làm dHash báo nhầm; với ảnh mặt nước, kết quả dHash phải xem lại bằng mắt (TECHNICAL mục 15.6).

Vì vậy báo hai mức: **cả tập test** (514 ảnh) và **test bỏ nhóm `a`, `z3`** (363 ảnh, `data/processed/afo/images/test-noshared`).

## Cấu hình và môi trường

| Mã | Trọng số | Suy luận |
|---|---|---|
| E1 | `yolo26s.pt` (COCO, chưa huấn luyện) | Toàn ảnh, imgsz 1280 |
| E2 | `best.pt` của E2_s0 (fine-tune chỉ trên VisDrone, `docs/results/visdrone_E2.md`) | Toàn ảnh, imgsz 1280 |

Cấu hình `configs/experiments/E1_afo.yaml`, `E2_afo.yaml`. Chung: conf 0,001, `max_det` 1000, IoU 0,5, recall và precision ở conf 0,25, AP nội suy 101 điểm, khoảng tin cậy bootstrap 1.000 lần theo ảnh; AFO không có vùng bỏ qua. Chạy ngày 22/10/2026 trên WSL2, RTX 5060, Python 3.12.3, torch 2.14.1, ultralytics 8.4.174.

## Kết quả: cả tập test (514 ảnh)

| Cấu hình | Nhóm | Số người | AP | KTC 95% của AP | Recall @0,25 | Precision @0,25 | Recall tối đa |
|---|---|---|---|---|---|---|---|
| E1 | tất cả | 6.511 | 0,147 | 0,133–0,163 | 0,201 | 0,300 | 0,649 |
|  | 16–32 px | 125 | 0,005 | 0,002–0,013 | 0,056 | 0,014 | 0,304 |
|  | >32 px | 6.386 | 0,181 | 0,167–0,202 | 0,203 | 0,369 | 0,656 |
| E2 | tất cả | 6.511 | 0,103 | 0,092–0,116 | 0,125 | 0,218 | 0,617 |
|  | 16–32 px | 125 | 0,016 | 0,009–0,034 | 0,184 | 0,030 | 0,560 |
|  | >32 px | 6.386 | 0,133 | 0,121–0,150 | 0,123 | 0,286 | 0,618 |

So cặp (`runs/afo/compare_E1_E2_test_iou0.5/compare.csv`):

| Chỉ số | E1 | E2 | Hiệu E2 − E1 | KTC 95% của hiệu |
|---|---|---|---|---|
| AP | 0,147 | 0,103 | −0,044 | −0,065 đến −0,025 |
| Recall @0,25 | 0,201 | 0,125 | −0,076 | −0,101 đến −0,052 |

## Kết quả: test bỏ nhóm `a`, `z3` (363 ảnh)

| Cấu hình | Nhóm | Số người | AP | KTC 95% của AP | Recall @0,25 | Precision @0,25 | Recall tối đa |
|---|---|---|---|---|---|---|---|
| E1 | tất cả | 2.734 | 0,188 | 0,155–0,219 | 0,259 | 0,368 | 0,661 |
|  | 16–32 px | 124 | 0,006 | 0,002–0,016 | 0,057 | 0,016 | 0,306 |
|  | >32 px | 2.610 | 0,325 | 0,290–0,361 | 0,269 | 0,596 | 0,678 |
| E2 | tất cả | 2.734 | 0,105 | 0,084–0,131 | 0,146 | 0,246 | 0,629 |
|  | 16–32 px | 124 | 0,016 | 0,010–0,032 | 0,185 | 0,031 | 0,565 |
|  | >32 px | 2.610 | 0,212 | 0,179–0,251 | 0,144 | 0,555 | 0,633 |

| Chỉ số | E1 | E2 | Hiệu E2 − E1 | KTC 95% của hiệu |
|---|---|---|---|---|
| AP | 0,188 | 0,105 | −0,083 | −0,121 đến −0,038 |
| Recall @0,25 | 0,259 | 0,146 | −0,113 | −0,163 đến −0,055 |

## Nhận xét

1. **Fine-tune chỉ trên VisDrone làm mô hình kém đi với người dưới nước**, có ý nghĩa thống kê ở cả hai mức của tập test. Ngược hẳn với VisDrone, nơi E2 tăng mạnh. Người trong AFO phần lớn lớn hơn 32 px, nên đây không phải chuyện kích thước mà là hình dạng: VisDrone chỉ có người đi bộ trên phố nhìn xiên; người bơi nằm ngang, chìm một phần, trên nền nước. Fine-tune một lớp làm mô hình chuyên vào kiểu người của VisDrone và mất phần tổng quát của mô hình COCO.
2. **Cả hai mô hình đều yếu trên AFO** (AP dưới 0,2), dù người lớn. Precision ở conf 0,25 thấp (khoảng 0,2–0,4): nhiều box trên mặt nước, ván, thuyền bị gọi là người. Đây là loại báo nhầm mà cảnh lũ cũng sẽ có (rác trôi, vật nổi).
3. **Hệ quả cho kế hoạch:** E2 lượt 2 thêm AFO train (`E2c_s0.yaml`); mọi mô hình fine-tune phải được đo cả trên dữ liệu có nước, không chỉ VisDrone. Tập test lũ vẫn là thước đo chính; AFO chỉ là cảnh hồ và biển.

## Giới hạn

- AFO là hồ và biển, nước trong, người bơi tự nguyện; không phải nước lũ đục với rác và mái nhà.
- Nhãn `human` của AFO theo quy ước của tác giả (người trên ván cũng có thể được gán `human`); khác quy ước của tập test lũ.
- Test chung địa điểm một phần với train (đã báo bản bỏ nhóm chung).
- Một seed cho E2.

## Tái lập

```bash
# Tải từ Kaggle (cần token): kaggle datasets download jangsienicajzkowy/afo-aerial-dataset-of-floating-objects -p data/raw/afo --unzip
python tools/prepare_afo.py --src data/raw/afo --out data/raw/afo_yolo
python tools/convert_yolo_subset.py --src data/raw/afo_yolo --dst data/processed/afo \
    --names-file data/raw/afo_yolo/classes.txt --keep human --splits train val test
python tools/check_leakage.py --train data/processed/afo/images/train --eval data/processed/afo/images/test \
    --group-pattern '^(.+)_\d+$' --output runs/leakage/afo_test
D=data/processed/afo
for r in E1 E2; do
  python scripts/run_baseline.py --config configs/experiments/${r}_afo.yaml
  python eval/eval_by_size.py --runs runs/afo/$r --images $D/images/test --labels $D/labels/test --iou 0.5 \
      --output runs/afo/eval_${r}_test_iou0.5
  # test bỏ nhóm a, z3: liên kết các ảnh còn lại vào $D/images/test-noshared (và labels), rồi
  python scripts/run_baseline.py --config configs/experiments/${r}_afo.yaml --source $D/images/test-noshared \
      --output runs/afo-noshared/$r
  python eval/eval_by_size.py --runs runs/afo-noshared/$r --images $D/images/test-noshared \
      --labels $D/labels/test-noshared --iou 0.5 --output runs/afo-noshared/eval_${r}_iou0.5
done
python eval/compare_runs.py --a runs/afo/E1 --b runs/afo/E2 --images $D/images/test --labels $D/labels/test \
    --iou 0.5 --output runs/afo/compare_E1_E2_test_iou0.5
python eval/compare_runs.py --a runs/afo-noshared/E1 --b runs/afo-noshared/E2 --images $D/images/test-noshared \
    --labels $D/labels/test-noshared --iou 0.5 --output runs/afo-noshared/compare_E1_E2_iou0.5
```
