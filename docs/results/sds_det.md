# SeaDronesSee: người bơi trên biển, E1 / E2 / E2c

Tập đánh giá người dưới nước **độc lập với dữ liệu huấn luyện** (khác AFO, vốn có phần train dùng cho E2c). Dùng để kiểm tra mức tăng của E2c trên AFO test có chuyển sang dữ liệu nước khác không.

## Dữ liệu

- SeaDronesSee-MOT, bản Kaggle `rameezakther/seadronessee-mot-sampled-dataset` (Apache-2.0), phần val: 11 video, ảnh 3840×2160.
- Lấy 1 khung mỗi 15 khung (0,5 s ở 30 FPS) để giảm ảnh gần trùng: **317 ảnh, 1.055 người** (lớp swimmer và swimmer with life jacket; thuyền bỏ, không làm vùng bỏ qua).
- Người phần lớn lớn: cạnh ngắn trung vị 65 px; 976 người trên 32 px, 76 người 16–32 px, 3 người 8–16 px.
- Dựng tại `data/processed/sds_det` (lệnh ở mục Tái lập).

## Kết quả, IoU 0,5

| Mô hình | AP50 | KTC 95% (bootstrap theo video) | Recall @0,25 | Precision @0,25 | Recall tối đa |
|---|---|---|---|---|---|
| E1 · gốc COCO | 0,535 | 0,362–0,616 | 0,481 | 0,660 | 0,804 |
| E2 · + VisDrone | 0,186 | 0,025–0,409 | 0,099 | 0,584 | 0,525 |
| E2c · + AFO | 0,468 | 0,151–0,554 | 0,465 | 0,640 | 0,757 |

| So cặp | Hiệu AP50 | KTC 95% | Có ý nghĩa |
|---|---|---|---|
| E2c − E1 | −0,067 | −0,426 đến +0,171 | không |
| E2c − E2 | +0,281 | +0,053 đến +0,506 | có |

Khoảng tin cậy lấy mẫu lại theo **video** (`--cluster-pattern '^(v\d+)_'`), vì các ảnh cùng video không độc lập; với 11 video nên khoảng rất rộng.

## Nhận xét

1. **E2 (chỉ VisDrone) mất khả năng nhận người bơi**, giống trên AFO: 0,535 → 0,186.
2. **E2c lấy lại phần lớn** (+0,281 so với E2, có ý nghĩa), **nhưng chưa hơn mô hình gốc** (−0,067 so với E1, không có ý nghĩa thống kê).
3. Vì vậy mức tăng lớn của E2c trên AFO test (0,103 → 0,568, `E2c.md`) **một phần là do test và train cùng nguồn AFO**. Kết luận đúng hiện tại: thêm dữ liệu nước giúp fine-tune **không đánh đổi** khả năng nhận người dưới nước; chưa chứng minh tốt hơn mô hình gốc với người dưới nước nói chung. Tập test lũ là nơi trả lời.
4. Người ở đây phần lớn trên 32 px, loại mà mô hình COCO vốn nhận tốt; lợi ích chính của fine-tune nằm ở người nhỏ (VisDrone, nhóm dưới 8 px).

## Giới hạn

- 11 video, khoảng tin cậy rộng; người lớn, ít người nhỏ.
- Cảnh biển, nước trong; không phải nước lũ.

## Tái lập

```bash
python tools/convert_seadronessee_mot.py --src data/raw/seadronessee_mot --dst data/processed/sds_mot   # tải dữ liệu: sds_mot_confirm.md
python tools/make_sds_det.py --src data/raw/seadronessee_mot --dst data/processed/sds_det --split val --every 15
for m in E1 E2 E2c; do
  python scripts/run_baseline.py --config configs/experiments/${m}_sds.yaml
  python eval/eval_by_size.py --runs runs/sds_det/$m --images data/processed/sds_det/images/val \
      --labels data/processed/sds_det/labels/val --iou 0.5 --cluster-pattern '^(v\d+)_' --output runs/sds_det/eval_${m}_iou0.5
done
```
