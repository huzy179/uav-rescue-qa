# Thu nhỏ khung theo độ cao bay (`--target-person-px`): sửa điểm yếu người to của E2c

**Sơ bộ, trên SeaDronesSee (nước biển, không phải lũ).** Xuất phát từ E6 thử (`e6_sds_pilot.md`): E2c bắt tốt nhất người khoảng 10–30 px và tụt mạnh với người trên 45 px. Ảnh 4K bay thấp thì người to, nên cắt ô ở độ phân giải gốc đưa vào E2c đúng loại người nó yếu.

## Cách làm

Trước khi cắt ô, khung được thu nhỏ theo hệ số `s = max(1, px_dự_kiến / mục_tiêu)`, với `px_dự_kiến = 0,5 m × f_px / độ_cao` (`edge.georef.expected_person_px`, camera coi như nhìn thẳng xuống; `edge.detector.person_scale`). Không bao giờ phóng to. Box trả về quy lại toạ độ ảnh gốc, nên georef và xác nhận không đổi. Bật bằng `--target-person-px` trong `edge/main.py` và `scripts/run_tiled.py` (đọc độ cao từ `--altitude-csv`).

Thử trên 317 ảnh SDS 3840×2160 (1.055 người, 11 video; `sds_det.md`), độ cao từng ảnh lấy từ metadata (`tools/make_sds_det.py` ghi `meta_val.csv`). Cắt ô 640, chồng 0,2, không lượt toàn ảnh, E2c, conf 0,001; góc nhìn coi là 82° chéo cho mọi drone. IoU 0,5; khoảng tin cậy bootstrap theo video.

Kiểm tra ước lượng cỡ người: theo từng video, số px dự kiến thường **thấp hơn** cạnh ngắn trung vị của nhãn, ở vài video thấp hơn nhiều lần (người bơi nằm ngang, máy quay có thể hẹp hơn 82°, nhiều đoạn gimbal nghiêng), nên hệ số thu nhỏ thực tế nghiêng về an toàn (thu nhỏ ít hơn cần).

## Kết quả

Số đọc từ `runs/sds_det/eval_<lần chạy>_iou0.5/eval_by_size.csv`.

| Lần chạy | Cách chạy | AP50 | KTC 95% | Recall @0,25 | Precision @0,25 |
|---|---|---|---|---|---|
| `E1` | toàn ảnh 1280, mô hình gốc | 0,535 | 0,362–0,616 | 0,481 | 0,660 |
| `E2c` | toàn ảnh 1280 | 0,468 | 0,151–0,554 | 0,465 | 0,640 |
| `E2c_tiled` | cắt ô ở độ phân giải gốc | 0,235 | 0,083–0,551 | 0,374 | 0,065 |
| `E2c_tiled_px20` | cắt ô, thu nhỏ về 20 px dự kiến | 0,523 | 0,337–0,660 | 0,510 | 0,690 |
| `E2c_tiled_px10` | cắt ô, thu nhỏ về 10 px dự kiến | 0,531 | 0,451–0,684 | 0,579 | 0,656 |

Hệ số thu nhỏ (`runs/sds_det/E2c_tiled_px*/per_image.csv`, cột `scale`): mục tiêu 20 px trung vị 1,676 (1,0–12,671), 0,959 số ảnh bị thu nhỏ; mục tiêu 10 px trung vị 3,352 (1,0–25,343), 0,978 số ảnh.

### So cặp (bootstrap theo video)

Số đọc từ `runs/sds_det/compare_<A>_<B>/compare.csv`.

| B − A | Hiệu AP50 | KTC 95% | Hiệu recall | KTC 95% |
|---|---|---|---|---|
| px20 − cắt ô gốc | +0,288 | +0,054 đến +0,396 | +0,136 | +0,063 đến +0,196 |
| px10 − cắt ô gốc | +0,296 | +0,061 đến +0,412 | +0,205 | +0,118 đến +0,318 |
| px10 − E2c toàn ảnh | +0,063 | −0,016 đến +0,377 | +0,114 | +0,053 đến +0,392 |
| px10 − px20 | +0,008 | −0,030 đến +0,122 | +0,069 | +0,030 đến +0,152 |
| px10 − E1 | −0,005 | −0,115 đến +0,273 | +0,099 | −0,109 đến +0,451 |

## Nhận xét

1. **Cắt ô ở độ phân giải gốc là cách tệ nhất cho E2c trên ảnh bay thấp** (AP50 0,235, precision 0,065): người to bị nhận thành nhiều mảnh hoặc không nhận, nền bị báo nhầm nhiều.
2. **Thu nhỏ theo độ cao sửa được gần hết**: +0,288 (mục tiêu 20 px) và +0,296 (10 px) AP50 so với cắt ô gốc, có ý nghĩa. So với E2c toàn ảnh, recall cao hơn có ý nghĩa (+0,114), AP50 cao hơn nhưng chưa có ý nghĩa.
3. **E2c có thu nhỏ ngang mô hình gốc trên nước biển** (AP50 0,531 so với 0,535), trong khi vẫn giữ lợi thế lớn ở người nhỏ (`visdrone_E2.md`, `e6_sds_pilot.md`). Đây là câu trả lời tốt hơn cho lưu ý ở `sds_det.md` ("E2c chưa hơn mô hình gốc với người dưới nước"): một phần khoảng cách là do đưa người sai cỡ vào mô hình, không phải do mô hình.
4. Mục tiêu 10 px cho recall cao hơn 20 px có ý nghĩa; vì ước lượng px đang thấp hơn thực tế, "10 px dự kiến" thực ra đưa người về cỡ lớn hơn 10 px, gần vùng E2c mạnh nhất. Khi có camera và góc nhìn thật của drone dùng cho lũ, nên hiệu chỉnh lại ước lượng này.
5. Thu nhỏ còn giảm số ô phải chạy, nên nhanh hơn; chưa đo kỹ thời gian (máy RTX 5060, không phải Jetson).

## Đề xuất

- Bật `--target-person-px` cho pipeline khi dùng mô hình fine-tune; giá trị chọn trên tập lũ khi có nhãn (thử 10 và 20), **không chọn trên tập test lũ đã khoá** mà trên phần val hoặc dữ liệu khác.
- Nếu tập lũ cũng cho kết quả như vậy, đây là một đóng góp thuật toán rõ ràng cho khối phát hiện: chọn thang xử lý theo GSD thay vì cố định, kết nối khối phát hiện với telemetry.

## Giới hạn

- Một tập (SDS, 11 video), người phần lớn to; góc nhìn camera giả định chung 82°, gimbal nhiều đoạn không nhìn thẳng xuống.
- Chọn mục tiêu 10/20 px sau khi xem kết quả trên cùng tập: đây là khảo sát, không phải đánh giá độc lập.

## Tái lập

```bash
.venv/bin/python tools/make_sds_det.py --src data/raw/seadronessee_mot --dst data/processed/sds_det --split val --every 15
C="--source data/processed/sds_det/images/val --model runs/train/E2c_s0/weights/best.pt --tile 640 --overlap 0.2 --imgsz 640 --conf 0.001 --max-det 1000 --no-images"
.venv/bin/python scripts/run_tiled.py $C --output runs/sds_det/E2c_tiled
for p in 20 10; do
  .venv/bin/python scripts/run_tiled.py $C --altitude-csv data/processed/sds_det/meta_val.csv --target-person-px $p \
      --output runs/sds_det/E2c_tiled_px$p
done
for r in E2c_tiled E2c_tiled_px20 E2c_tiled_px10; do
  .venv/bin/python eval/eval_by_size.py --runs runs/sds_det/$r --images data/processed/sds_det/images/val \
      --labels data/processed/sds_det/labels/val --iou 0.5 --cluster-pattern '^(v\d+)_' --output runs/sds_det/eval_${r}_iou0.5
done
.venv/bin/python eval/compare_runs.py --a runs/sds_det/E2c_tiled --b runs/sds_det/E2c_tiled_px20 \
    --images data/processed/sds_det/images/val --labels data/processed/sds_det/labels/val \
    --cluster-pattern '^(v\d+)_' --output runs/sds_det/compare_E2c_tiled_E2c_tiled_px20   # tương tự cho các cặp khác
```
