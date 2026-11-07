# Dùng lại kết quả ô không đổi khi drone đứng yên: kết quả âm

Đề xuất ở `docs/CAI_TIEN.md` mục 2 (giảm khối lượng tính, câu hỏi 2). Khi drone treo tại chỗ, phần lớn ô của khung sau gần như giống khung trước; chạy lại mô hình trên các ô đó có vẻ thừa. Câu hỏi: dùng lại kết quả cũ của ô gần như không đổi bớt được bao nhiêu ô, và mất bao nhiêu recall.

## Cách làm

- `edge/tile_cache.py` (`TileCache`, `is_hovering`), bật bằng `edge/main.py --skip-static-tiles`; mặc định tắt. Tham số đặt **trước khi chạy**, không thử giá trị khác:
  - chỉ dùng lại khi drone gần như đứng yên theo telemetry: vận tốc mặt đất trong 1 s qua dưới 0,5 m/s và hướng đổi dưới 2°;
  - so mỗi ô với chính ô đó ở **lần chạy mô hình gần nhất** bằng ảnh xám thu về 32 × 32; chênh trung bình dưới 4 mức xám thì dùng lại box cũ của ô;
  - mỗi ô dùng lại tối đa 4 lần liên tiếp (khoảng 2 s ở 2 khung/giây) rồi bắt buộc chạy lại.
- Cấu hình cuối: E2c, cắt ô 640, thu nhỏ về 10 px theo độ cao (`--target-person-px 10`), `configs/edge.yaml`, 2 khung/giây, telemetry thật của SeaDronesSee-MOT. Mỗi đoạn chạy hai lần, tắt và bật, trên RTX 5060 ngày 8/11 ở commit `179d88f`, `dirty: true` vì mã lúc đó chưa commit (commit ngay sau, cùng nội dung).
- Bốn đoạn drone gần như đứng yên có người (vận tốc trung vị 0–0,3 m/s, `info.json`) và một đoạn drone bay (v13, 7,2 m/s) để kiểm tra không dùng lại khi bay. Mô hình chưa học trên SeaDronesSee nên dùng cả đoạn thuộc phần train.
- Chấm `eval/frame_recall_mot.py`: mỗi khung đã xử lý, phát hiện ở conf 0,25 so với nhãn của đúng khung đó, IoU 0,5; hiệu số bootstrap cặp theo khối 10 s. Kết quả `runs/sds/tile_skip/<đoạn>/frame_recall.csv`.

## Kết quả

| Đoạn | Khung | Ô chạy / tổng ô (tỉ lệ) khi bật | Recall (tắt → bật) | Hiệu recall (KTC 95%) | Precision (tắt → bật) | Hiệu precision (KTC 95%) |
|---|---|---|---|---|---|---|
| val v21 (m100, 40 m) | 105 | 411 / 630 (0,652) | 0,456 → 0,363 | −0,093 (−0,149 đến −0,012) | 0,750 → 0,597 | −0,153 (−0,257 đến +0,007) |
| val v9 (mavic, 38 m) | 50 | 104 / 200 (0,520) | 0,690 → 0,596 | −0,094 (−0,200 đến +0,000) | 0,659 → 0,551 | −0,108 (−0,204 đến −0,034) |
| val v18 (m210, 5–24 m) | 81 | 75 / 88 (0,852) | 0,306 → 0,271 | −0,035 (−0,110 đến +0,000) | 0,382 → 0,348 | −0,034 (−0,064 đến +0,000) |
| train v9 (mavic, 37–38 m) | 198 | 392 / 756 (0,518) | 0,809 → 0,571 | −0,238 (−0,335 đến −0,145) | 0,773 → 0,549 | −0,224 (−0,314 đến −0,137) |
| val v13 (mavic, bay 7,2 m/s) | 4 | 72 / 72 (1,000) | 0,500 → 0,500 | +0,000 | 0,286 → 0,286 | +0,000 |

## Nhận xét

1. **Chỉ còn chạy 0,518–0,852 số ô nhưng mất nhiều recall và precision**: ở cả bốn đoạn đứng yên, recall giảm 0,035–0,238; ở val v21 và train v9 có ý nghĩa thống kê.
2. **Vì sao:** drone đứng yên nhưng **người bơi vẫn cử động**. Một người khoảng 10 px trong ô 640 chỉ còn khoảng nửa pixel ở ảnh xám 32 × 32, nên người dịch chỗ gần như không làm ảnh thu nhỏ đổi; ô bị coi là "không đổi" và box cũ bị dùng lại ở vị trí cũ. Box lệch chỗ vừa thành bỏ sót (người thật không còn box khớp) vừa thành báo nhầm (box cũ không khớp ai), đúng như cả recall lẫn precision cùng giảm.
3. Khi drone bay (v13), điều kiện đứng yên không thoả nên không ô nào bị dùng lại, kết quả giống hệt: cơ chế không ảnh hưởng chuyến quét bình thường.
4. **Quyết định:** không dùng; giữ `--skip-static-tiles` làm tuỳ chọn để tái lập. Muốn dùng được phải phát hiện thay đổi ở cỡ người (so ảnh ở độ phân giải gốc, hoặc chỉ dùng lại ô **không có** box nào), và với cứu nạn, nơi người cử động là chuyện bình thường, lợi ích còn lại nhỏ. Ở chuyến quét, drone ít khi đứng yên, nên khối lượng tính nên giảm bằng thu nhỏ theo độ cao và tần số theo độ cao (đã có).

## Giới hạn

- Năm đoạn SeaDronesSee, một bộ tham số đặt trước, một mô hình; không chạy trên tập ảnh lũ.
- Chấm ở mức khung (box khớp nhãn), chưa đo ảnh hưởng tới khâu xác nhận và cảnh báo.

## Tái lập

```bash
for V in val-m100-DJI_0001-v21 val-mavic-DJI_0069-v9 val-m210-DJI_0011_d3-v18 train-mavic-DJI_0069-v9 val-mavic-DJI_0064-v13; do
  for M in off on; do
    X=""; [ $M = on ] && X="--skip-static-tiles"
    .venv/bin/python -m edge.main --config configs/edge.yaml --model runs/train/E2c_s0/weights/best.pt --target-person-px 10 \
        --device 0 --source data/processed/sds_mot/$V/frames --source-fps 30 --telemetry data/processed/sds_mot/$V/telemetry.csv \
        --drain-s 0 --output runs/sds/tile_skip/$V/$M $X
  done
  .venv/bin/python eval/frame_recall_mot.py --sds data/processed/sds_mot/$V --runs runs/sds/tile_skip/$V/off runs/sds/tile_skip/$V/on \
      --output runs/sds/tile_skip/$V/frame_recall.csv
done
```
