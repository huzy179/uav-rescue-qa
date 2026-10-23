# E2 lượt 2 (E2c): VisDrone + AFO

Fine-tune YOLO26s một lớp `person` trên VisDrone train cộng AFO train (người bơi trên hồ, biển). Mục đích: E2 lượt 1 (chỉ VisDrone) kém cả mô hình gốc với người dưới nước (`afo_E1_E2.md`).

## Huấn luyện

- Cấu hình `configs/experiments/E2c_s0.yaml`, seed 0, imgsz 1280, batch 8, **55 epoch** (truyền từ notebook; file cấu hình ghi 100), `scale` 0,5.
- Dữ liệu: VisDrone train (6.471 ảnh) + AFO train (2.787 ảnh, thu về cạnh dài 1920 px bằng `prepare_afo.py --max-side 1920`); best.pt chọn theo val gộp VisDrone val + AFO val.
- Kaggle, Tesla T4; mã ở commit `5c8a860` (`dirty: false`); 55 epoch trong 9,116 giờ; batch giữ 8 (`runs/kaggle_E2c/floodeye-train.log`).
- best.pt: epoch 54; mAP50 ultralytics trên val gộp 0,782, epoch cuối 0,782 (`runs/train/E2c_s0/results.csv`).

## Đánh giá

Ngày 23/10/2026, WSL2, RTX 5060; cùng quy ước như `visdrone_E2.md` (conf 0,001, `max_det` 1000, IoU 0,5, vùng bỏ qua với VisDrone, bootstrap 1.000 lần theo ảnh). E1, E2 lấy từ các lần chạy đã có trên cùng máy. Cấu hình: `E2c_visdrone.yaml`, `E2c_visdrone-testdev.yaml`, `E2c_afo.yaml`.

### AP50

| Tập | Nhóm | E1 | E2 | E2c | KTC 95% của E2c | Recall @0,25 E2c | Precision @0,25 E2c |
|---|---|---|---|---|---|---|---|
| VisDrone val | tất cả | 0,497 | 0,758 | 0,747 | 0,734–0,760 | 0,665 | 0,796 |
| VisDrone val | dưới 8 px | 0,167 | 0,554 | 0,546 | 0,521–0,570 | 0,456 | 0,718 |
| VisDrone test-dev | tất cả | 0,269 | 0,513 | 0,507 | 0,475–0,540 | 0,459 | 0,698 |
| VisDrone test-dev | dưới 8 px | 0,086 | 0,247 | 0,241 | 0,221–0,266 | 0,218 | 0,577 |
| AFO test | tất cả | 0,147 | 0,103 | 0,568 | 0,537–0,601 | 0,668 | 0,582 |
| AFO test bỏ nhóm a, z3 | tất cả | 0,188 | 0,105 | 0,734 | 0,702–0,765 | 0,789 | 0,624 |

### Hiệu số AP50 (bootstrap cặp)

| Tập | E2c − E1 | KTC 95% | E2c − E2 | KTC 95% |
|---|---|---|---|---|
| VisDrone val | +0,250 | +0,236 đến +0,263 | −0,011 | −0,015 đến −0,008 |
| VisDrone test-dev | +0,239 | +0,226 đến +0,255 | −0,006 | −0,010 đến −0,002 |
| AFO test | +0,421 | +0,391 đến +0,454 | +0,465 | +0,439 đến +0,493 |
| AFO test bỏ nhóm a, z3 | +0,547 | +0,501 đến +0,591 | +0,629 | +0,604 đến +0,654 |

## Nhận xét

1. **Thêm AFO lấy lại người dưới nước**: AFO test tăng từ 0,103 (E2) lên 0,568, vượt cả mô hình gốc (0,147); bỏ nhóm ảnh chung địa điểm với train thì 0,734. Hiệu số có ý nghĩa thống kê.
2. **Cái giá trên ảnh phố rất nhỏ**: VisDrone val giảm 0,011, test-dev giảm 0,006 so với E2, có ý nghĩa thống kê nhưng nhỏ hơn nhiều so với mức tăng trên AFO. E2c thay E2 làm mô hình chính.
3. AFO test vẫn có phần chung địa điểm với AFO train (nhóm `a`); bản bỏ nhóm chung cho số cao hơn, nên không phải do rò rỉ mà có lẽ do các nhóm còn lại dễ hơn. Kết luận về cảnh lũ vẫn phải chờ tập test lũ.

## Giới hạn

- Một seed; E2 60 epoch, E2c 55 epoch (khác nhau do giới hạn 12 giờ của Kaggle).
- AFO là hồ và biển, không phải nước lũ.

## Tái lập

```bash
# Huấn luyện: notebooks/kaggle_train.ipynb, COMMIT 5c8a860, CONFIG configs/experiments/E2c_s0.yaml, MODE "train", EPOCHS 55, Add Input AFO
python scripts/run_baseline.py --config configs/experiments/E2c_visdrone.yaml
python scripts/run_baseline.py --config configs/experiments/E2c_visdrone-testdev.yaml
python scripts/run_baseline.py --config configs/experiments/E2c_afo.yaml
python scripts/run_baseline.py --config configs/experiments/E2c_afo.yaml --source data/processed/afo/images/test-noshared --output runs/afo-noshared/E2c
# đánh giá và so cặp: như visdrone_E2.md và afo_E1_E2.md, thay E2 bằng E2c
```
