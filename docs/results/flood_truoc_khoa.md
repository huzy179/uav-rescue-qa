# Tập test lũ trước khi khoá: rò rỉ và nguồn trùng (4/11/2026)

Kiểm tra trên ảnh, chưa cần nhãn: tập test lũ có trùng ảnh hay trùng video với dữ liệu huấn luyện không, và các video trong tập có độc lập với nhau không. Chạy trước khi gán để sửa thành phần tập khi còn được phép sửa (LABELING mục 8).

## Môi trường và dữ liệu

- Máy cá nhân (WSL), `tools/check_leakage.py` ở commit `97f8c63` (khoá mã băm gồm tên bộ dữ liệu, để ảnh trùng tên ở hai bộ không ghi đè nhau).
- Tập đánh giá: `data/raw/flood/frames`, ban đầu 212 khung từ 10 video, sau khi gộp San Angelo còn 188.
- Tập huấn luyện, 16.193 ảnh: VisDrone train (6.471), AFO train (2.787), HydroVigilance train (627) và val (179), C2A train (6.129).
- C2A tải lại ngày 4/11 từ Kaggle `rgbnihal/c2a-dataset` phiên bản 2, cũng là bản notebook huấn luyện dùng. Ghi giấy phép **MIT** trên Kaggle (liên quan quyết định #12). Chuyển bằng `tools/convert_yolo_subset.py --class-names human --keep human`: train 6.129 ảnh, 215.821 người; val 2.043 ảnh, 72.123 người; test 2.043 ảnh, 72.523 người; không ảnh hỏng, không ảnh thiếu nhãn (`data/processed/c2a/stats.json`).

## Kết quả

| Lần chạy | Ảnh đánh giá | Video chung | Cặp gần trùng | Thư mục |
|---|---|---|---|---|
| Với tập huấn luyện, ≤ 5 bit (mặc định) | 212 | 0 | 0 | `runs/leakage/flood_frames_truockhoa` |
| Với tập huấn luyện, ≤ 10 bit | 212 | 0 | 37 cặp, 9 khung | `runs/leakage/flood_frames_truockhoa_10bit` |
| Với tập huấn luyện, ≤ 5 bit, sau khi gộp | 188 | 0 | 0 | `runs/leakage/flood_frames_188` |
| Bên trong tập lũ, ≤ 5 bit, sau khi gộp | 188 | | 0 | `runs/leakage/flood_frames_188_noibo` |

37 cặp ở ngưỡng 10 bit đều đã xem bằng mắt (ghép từng khung lũ với tối đa 4 ảnh train gần nhất): không cặp nào cùng cảnh. Chúng chỉ giống nhau về bố cục sáng tối, ví dụ nước phía trên và bờ phía dưới, hoặc cảnh đêm.

## Nguồn trùng bên trong tập (xem bằng mắt, mã băm không bắt được)

- **texas-xBvDRr6vy-k và sanangelo-police:** cùng là cảnh quay của cảnh sát San Angelo, cùng trận lũ 4/7/2025 (cùng logo trên mọi khung, cùng chú thích "Ft Worth FD"). Đã gộp thành một nguồn: giữ 15 khung mỗi video, rải đều theo thời gian, bỏ 24 khung; khi bootstrap theo video thì hai video là một cụm. Chi tiết ở LABELING mục 6.
- **washington-D4xd0xNP9Gg và duvall-2HE-TIf4Lk0:** cùng trận lũ Duvall 11/12/2025, nhưng khác máy quay. Washington có giao diện camera "KING COUNTY SHERIFF", 40 hải lý/giờ, 632 ft, nhiều khả năng quay từ trực thăng. Giữ hai cụm riêng, ghi vào phần giới hạn.
- Hai video Huế (Tuổi Trẻ, Thanh Niên) và vn-tuoitre-1: cảnh khác nhau, không thấy trùng.

Sau khi gộp: 188 khung, 9 cụm khi bootstrap (30, 30, 29, 23, 23, 22, 15, 8, 8 khung).

## Giới hạn

- dHash so cả ảnh, nên không bắt được hai khung khác thời điểm của cùng một cảnh quay, hay một đoạn đã cắt hoặc chèn chữ. Nguồn trùng San Angelo chỉ thấy nhờ xem bằng mắt.
- 9 cụm là ít cho bootstrap theo cụm: khoảng tin cậy rộng và có thể vẫn hẹp hơn thực tế. Ghi vào phần giới hạn.

## Lệnh tái lập

```bash
.venv/bin/python tools/convert_yolo_subset.py --src data/raw/c2a/C2A_Dataset/new_dataset3 --dst data/processed/c2a \
    --class-names human --keep human --splits train val test
TRAIN="data/processed/visdrone/images/train data/processed/afo/images/train data/processed/hydrovigilance/images/train \
    data/processed/hydrovigilance/images/val data/processed/c2a/images/train"
.venv/bin/python tools/check_leakage.py --train $TRAIN --eval data/raw/flood/frames --output runs/leakage/flood_frames_188
.venv/bin/python tools/check_leakage.py --train $TRAIN --eval data/raw/flood/frames --max-distance 10 --output runs/leakage/flood_frames_truockhoa_10bit
.venv/bin/python tools/check_leakage.py --eval data/raw/flood/frames --output runs/leakage/flood_frames_188_noibo
```
