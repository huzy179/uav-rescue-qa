# Ngưỡng tin cậy theo cỡ box: kết quả âm

Đề xuất ở `docs/CAI_TIEN.md` mục 1.4. Recall và precision vận hành dùng một ngưỡng conf 0,25 cho mọi box. Giả thuyết: người nhỏ có conf thấp hơn người to, nên hạ ngưỡng cho box nhỏ và nâng ngưỡng cho box to sẽ bắt thêm người mà không thêm tỉ lệ báo nhầm.

## Cách làm

- Ngưỡng riêng cho bốn nhóm cỡ của **box dự đoán** (cạnh ngắn < 8, 8–16, 16–32, > 32 px). Lúc chạy chỉ biết cỡ box, không biết cỡ nhãn.
- **Chọn trên VisDrone val** (E2c toàn ảnh 1280, `runs/visdrone/E2c`): tối đa recall với điều kiện precision chung không thấp hơn precision của ngưỡng chung 0,25 trên chính tập đó. Vét cạn mọi tổ hợp trên lưới 0,05–0,60 bước 0,05 cho bốn nhóm, rồi so khớp lại chính xác. Mục tiêu và lưới đặt trước khi chạy.
- **Kiểm chứng** trên VisDrone test-dev (E2c toàn ảnh 1280) và SeaDronesSee (E2c cắt ô thu nhỏ về 10 px, cấu hình cuối; khác tập và khác cách chạy so với lúc chọn). Bootstrap cặp 1.000 lần theo video (`'^(\d+)_'`, `'^(v\d+)_'`). IoU 0,5; vùng bỏ qua của VisDrone như mọi bảng khác.
- Ngưỡng chung 0,25 tái lập đúng số cũ: VisDrone val recall 0,6655, precision 0,7963 (`eval_E2c_iou0.5/eval_by_size.csv`).
- Script `eval/conf_by_size.py`, kết quả `runs/conf_by_size/` (`thresholds.json`, `results.csv`). Chạy ở commit `3837954`; script lúc đó chưa commit (commit ngay sau, cùng nội dung), nên `run_config.json` ghi `dirty: false` dù script chưa có trong commit đó.

## Kết quả

Số chép nguyên từ `results.csv` (bốn chữ số thập phân, không làm tròn lại); in đậm là có ý nghĩa thống kê.

Ngưỡng chọn trên VisDrone val: **< 8 px: 0,20; 8–16 px: 0,30; 16–32 px: 0,25; > 32 px: 0,20**.

| Tập | Recall (chung → theo cỡ) | Hiệu recall (KTC 95%) | Precision (chung → theo cỡ) | Hiệu precision (KTC 95%) |
|---|---|---|---|---|
| VisDrone val (tập chọn) | 0,6655 → 0,6657 | +0,0001 (−0,0058 đến +0,0063) | 0,7963 → 0,7967 | +0,0004 (−0,0069 đến +0,0073) |
| VisDrone test-dev | 0,4588 → 0,457 | −0,0019 (−0,0099 đến +0,0028) | 0,6978 → 0,6838 | −0,0141 (−0,0239 đến +0,0046) |
| SeaDronesSee | 0,5791 → 0,5991 | **+0,0199 (+0,0045 đến +0,0524)** | 0,6563 → 0,6208 | **−0,0355 (−0,0457 đến −0,0228)** |

Recall theo cỡ nhãn, VisDrone test-dev (hiệu, KTC 95%): < 8 px +0,0160 (+0,0132 đến +0,0289); 8–16 px −0,0220 (−0,0290 đến −0,0153); 16–32 px −0,0078 (−0,0148 đến −0,0026); > 32 px +0,0064 (+0,0020 đến +0,0090). Trên VisDrone val cùng chiều: < 8 px 0,4531 → 0,4943, 8–16 px 0,703 → 0,6829.

## Nhận xét

1. **Không có lợi trên chính tập chọn.** Tổ hợp tốt nhất thoả điều kiện precision chỉ tăng recall chung từ 0,6655 lên 0,6657. Conf của E2c đã gần như "cùng thang" giữa các cỡ: hạ ngưỡng cho box nhỏ thêm bao nhiêu người đúng thì cũng thêm bấy nhiêu box sai.
2. **Ngưỡng theo cỡ chỉ chuyển recall giữa các nhóm**: người dưới 8 px được thêm (test-dev +0,0160), người 8–16 px bị bớt (−0,0220), vì ngưỡng 8–16 px phải nâng để bù precision. Nhóm 8–16 px đông hơn, nên recall chung không đổi hoặc giảm.
3. **Không chuyển được sang tập khác**: trên test-dev precision giảm (không có ý nghĩa); trên SeaDronesSee recall tăng 0,0199 nhưng precision giảm 0,0355, cả hai có ý nghĩa: ngưỡng 0,20 cho box > 32 px giữ thêm box sai trên mặt nước.
4. **Quyết định:** giữ ngưỡng chung (0,25 cho recall vận hành; pipeline dùng 0,1 rồi để khối xác nhận lọc). `eval/conf_by_size.py` giữ lại để chạy lại nếu đổi mô hình.

## Giới hạn

- Một mô hình (E2c), một mục tiêu chọn (recall tối đa giữ precision); mục tiêu khác (ví dụ F1) chưa thử và không thử thêm để tránh chọn theo kết quả.
- Chọn trên kết quả toàn ảnh 1280; cấu hình cuối cắt ô thu nhỏ có phân bố conf có thể khác (SeaDronesSee là kiểm chứng duy nhất cho cách chạy đó, 11 video).
- Không kiểm chứng trong mô phỏng RQ3 (báo nhầm mỗi phút, bỏ sót): không cần vì đã âm ở mức khung.

## Tái lập

```bash
.venv/bin/python eval/conf_by_size.py \
  --fit runs/visdrone/E2c data/processed/visdrone/images/val data/processed/visdrone/labels/val \
  --fit-ignore data/processed/visdrone/ignore/val \
  --test visdrone-val runs/visdrone/E2c data/processed/visdrone/images/val data/processed/visdrone/labels/val '^(\d+)_' data/processed/visdrone/ignore/val \
  --test visdrone-testdev runs/visdrone-testdev/E2c data/processed/visdrone/images/test-dev data/processed/visdrone/labels/test-dev '^(\d+)_' data/processed/visdrone/ignore/test-dev \
  --test sds_det runs/sds_det/E2c_tiled_px10 data/processed/sds_det/images/val data/processed/sds_det/labels/val '^(v\d+)_' - \
  --bootstrap 1000 --output runs/conf_by_size
```
