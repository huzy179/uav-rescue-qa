# Thu nhỏ khung trên GPU (`--gpu-resize`)

**Sơ bộ: thời gian đo trên máy cá nhân (RTX 5060, WSL), chỉ để so sánh tương đối; chưa đo trên T4 hay Jetson.**

## Câu hỏi

Ở câu hỏi 2 (`rq2_t4.md`, kết quả 1), cấu hình được chọn (FP16, cắt ô 640, thu nhỏ theo độ cao về 10 px) tốn 46,28 ms (trung vị) cho chặng chuẩn bị khung trên Kaggle T4, nhiều hơn suy luận 6 ô (30,56 ms). Chặng này gần như toàn bộ là `cv2.resize` với `INTER_AREA` trên khung 4K (CAI_TIEN mục 2).

Giả thuyết: đổi cỡ bằng torch trên GPU (`F.interpolate` song tuyến có khử răng cưa) nhanh hơn rõ mà độ chính xác không đổi.

- **Chỉ số quyết định:** thời gian chặng chuẩn bị khung (`tile_ms`) và AP50, recall ở conf 0,25 so cặp.
- **Mốc:** cùng cấu hình, `cv2.resize` trên CPU, chạy lại cùng phiên.
- **Tham số cố định trước:** cấu hình cuối E2c cắt ô 640, chồng 0,2, `--target-person-px 10`; không chọn tham số nào mới.
- **Kiểm chứng:** SeaDronesSee val (317 ảnh 4K, có độ cao bay). Không dùng tập lũ.

## Cách làm

- `edge/detector.py`, hàm `resize_torch`: khung uint8 được chép lên GPU ở dạng uint8, đổi sang số thực trên GPU, rồi nội suy song tuyến (`antialias=True` khi thu nhỏ). Kết quả là uint8 được chép về CPU, nên phần cắt ô và suy luận phía sau không đổi.
- Bật bằng `YoloDetector(gpu_resize=True)`, hoặc cờ `--gpu-resize` của `edge/main.py` và `scripts/run_tiled.py`. Mặc định tắt: tắt thì vẫn dùng `cv2.resize` như mọi kết quả trước (`tests/test_gpu_resize.py`).
- `scripts/run_tiled.py` ghi thêm cột `tile_ms` vào `per_image.csv`. `eval/per_image_timing.py` tóm tắt thời gian của nhiều lần chạy.
- `tools/bench_resize.py` đo riêng thời gian đổi cỡ một khung 4K, với cv2 ở 1, 2, 4 luồng và mặc định, và với torch trên GPU.
- **Môi trường:**
  - RTX 5060 trên WSL;
  - ultralytics 8.4.174, torch 2.14.1, opencv-python 5.0.0.93;
  - trọng số `runs/train/E2c_s0/weights/best.pt`;
  - commit `a2632b9`, `dirty: false` (`run_config.json`).
- **Chấm:** bootstrap cặp 1.000 lần theo video (`--cluster-pattern '^(v\d+)_'`), IoU 0,5 và 0,3, conf 0,001, `max_det` 1000.

## Kết quả 1: thời gian trên cả SeaDronesSee val

Nguồn: `runs/gpu_resize/timing_summary.csv`. `tile_ms` là chặng chuẩn bị khung (đổi cỡ và cắt ô). `infer_ms` là tổng mỗi ảnh (chuẩn bị, suy luận, gộp). PyTorch, chưa TensorRT.

| Cấu hình | `tile_ms` trung vị | `tile_ms` p95 | Tổng trung vị | Tổng trung bình | Tổng p95 |
|---|---|---|---|---|---|
| `cv2.resize` trên CPU (`E2c_sds_tiled_px10_cpu.yaml`) | 21,34 | 27,09 | 50,60 | 53,72 | 71,97 |
| torch trên GPU (`E2c_sds_tiled_px10_gpuresize.yaml`) | 5,39 | 6,69 | 43,55 | 44,10 | 65,30 |

## Kết quả 2: vì sao `cv2.resize` chậm trong pipeline

Nguồn: `runs/gpu_resize/bench.csv`, ảnh `v00_000585.jpg` (3840×2160), trung vị 20 lần. Hệ số 3,35 gần trung vị hệ số thu nhỏ trên tập val.

| Hệ số thu nhỏ | cv2, 1 luồng | cv2, 2 luồng | cv2, 4 luồng | cv2, mặc định (16 luồng) | torch trên GPU |
|---|---|---|---|---|---|
| 1,5 | 25,95 | 13,158 | 7,082 | 3,734 | 6,659 |
| 3,0 | 9,284 | 4,633 | 2,665 | 1,518 | 4,736 |
| 3,35 | 23,078 | 12,073 | 6,515 | 4,167 | 5,446 |
| 6,0 | 6,157 | 2,872 | 1,930 | 1,558 | 4,407 |
| 14,4 | 13,984 | 13,639 | 13,582 | 13,613 | 5,301 |

**Ultralytics gọi `cv2.setNumThreads(0)` khi được import** (`ultralytics/utils/__init__.py`, để tránh xung đột với DataLoader của PyTorch). Vì vậy, trong pipeline `cv2.resize` luôn chạy **một luồng**: chặng chuẩn bị khung khi chạy thật (21,34 ms trung vị) khớp với cột 1 luồng, không khớp với cột mặc định. Điều này giải thích phần lớn con số 46,28 ms trên T4.

Torch trên GPU tốn 4,407–6,659 ms, ít đổi theo hệ số; cv2 nhanh hơn GPU khi được nhiều luồng hoặc khi hệ số là số nguyên (3,0), chậm hơn rõ khi một luồng với hệ số lẻ, là trường hợp của pipeline.

## Kết quả 3: độ chính xác không đổi có ý nghĩa

Nguồn: `runs/sds_det/compare_E2c_tiled_px10_cpu_gpuresize_iou{0.5,0.3}/compare.csv`. A là CPU, B là GPU. Nhóm < 8 px không có nhãn; nhóm 8–16 px có AP 0 ở cả hai.

| IoU | Nhóm | Chỉ số | CPU | GPU | Hiệu (KTC 95%) | p | Có ý nghĩa |
|---|---|---|---|---|---|---|---|
| 0,5 | tất cả | AP50 | 0,531 | 0,510 | −0,021 (−0,038 đến +0,017) | 0,206 | không |
| 0,5 | tất cả | recall (conf 0,25) | 0,579 | 0,567 | −0,012 (−0,027 đến +0,029) | 0,338 | không |
| 0,5 | 16–32 px | AP50 | 0,559 | 0,517 | −0,042 (−0,072 đến 0,000) | 0,739 | không |
| 0,5 | > 32 px | AP50 | 0,533 | 0,514 | −0,019 (−0,035 đến +0,020) | 0,198 | không |
| 0,3 | tất cả | AP | 0,815 | 0,816 | +0,001 (−0,005 đến +0,021) | 0,506 | không |
| 0,3 | tất cả | recall (conf 0,25) | 0,740 | 0,737 | −0,003 (−0,012 đến +0,015) | 0,732 | không |

Mức sai khác điểm ảnh so với `cv2.INTER_AREA` (`mean_abs_diff` trong `bench.csv`) là 0,109–1,339 mức xám trên thang 0–255.

## Nhận xét

1. **Đổi cỡ trên GPU giảm chặng chuẩn bị khung từ 21,34 ms xuống 5,39 ms (trung vị)**, và tổng mỗi ảnh từ 50,60 ms xuống 43,55 ms trên máy này. Tổng giảm ít hơn chặng chuẩn bị (suy luận trung bình chậm hơn một chút ở bản GPU); chưa tách được lý do.
2. **Độ chính xác không khác có ý nghĩa** ở cả hai ngưỡng IoU. Ở IoU 0,5, ước lượng điểm của AP50 thấp hơn 0,021, nhưng khoảng tin cậy chứa 0. Ở IoU 0,3 hai bản gần như trùng, nên khác biệt chủ yếu nằm ở độ khít của box, không phải bắt hay bỏ người.
3. **Nguyên nhân gốc là OpenCV bị ép chạy một luồng**, không phải CPU yếu. Có hai cách sửa:
   - đổi cỡ trên GPU (đã làm);
   - trả lại số luồng cho OpenCV sau khi nạp mô hình (`cv2.setNumThreads`; theo `bench.csv`, 4 luồng còn 6,515 ms ở hệ số 3,35).

   Cách thứ hai chưa cài và chưa kiểm chứng trong pipeline (DataLoader không dùng khi suy luận nên có thể an toàn, nhưng chưa thử).
4. Ở hệ số lớn (14,4, bay rất thấp so với người 10 px), cv2 chậm bất kể số luồng (13,582–13,984 ms); GPU 5,301 ms.

## Giới hạn

- Thời gian đo trên RTX 5060 với CPU máy bàn, không phải T4 hay Jetson. Trên Jetson, CPU và GPU dùng chung bộ nhớ nên phép chép có thể rẻ hơn, nhưng chưa đo.
- Hồ sơ thiết bị (`configs/devices/*.yaml`, `resize_ms_per_mpx`) vẫn theo số đo T4 với `cv2.resize`. Chưa hiệu chỉnh lại cho `--gpu-resize` vì chưa có số đo T4.
- Chạy PyTorch, không phải TensorRT. Với TensorRT, phần suy luận ngắn hơn nên tỉ trọng của chặng chuẩn bị còn lớn hơn.
- Một tập (SeaDronesSee val, 317 ảnh); tập lũ không có độ cao bay nên không dùng thu nhỏ theo độ cao (quyết định #13).

## Đề xuất

- **Đã bật 10/11** trong `configs/edge.yaml` và `configs/demo/sds_v21_px10.yaml` (ROADMAP mục 6, #20). Giả lập thời gian thiết bị vẫn dùng `resize_ms_per_mpx` đo với cv2 trên T4, tức ước lượng thận trọng. Nên đo lại một lần trên T4 nếu còn giờ Kaggle, để hiệu chỉnh `resize_ms_per_mpx` cho hồ sơ thiết bị.
- **Trả lại số luồng cho OpenCV:** là tuỳ chọn tiếp theo, rẻ, không cần GPU (CAI_TIEN mục 2).

## Tái lập

```bash
.venv/bin/python scripts/run_tiled.py --config configs/experiments/E2c_sds_tiled_px10_cpu.yaml
.venv/bin/python scripts/run_tiled.py --config configs/experiments/E2c_sds_tiled_px10_gpuresize.yaml
S=data/processed/sds_det
for iou in 0.5 0.3; do
  .venv/bin/python eval/compare_runs.py --a runs/sds_det/E2c_tiled_px10_cpu --b runs/sds_det/E2c_tiled_px10_gpuresize \
      --images $S/images/val --labels $S/labels/val --iou $iou --cluster-pattern '^(v\d+)_' \
      --output runs/sds_det/compare_E2c_tiled_px10_cpu_gpuresize_iou$iou
done
.venv/bin/python eval/per_image_timing.py --runs runs/sds_det/E2c_tiled_px10_cpu runs/sds_det/E2c_tiled_px10_gpuresize \
    --output runs/gpu_resize/timing_summary.csv
.venv/bin/python tools/bench_resize.py --images $S/images/val/v00_000585.jpg $S/images/val/v21_007725.jpg \
    --scales 1.5 3.0 3.35 6.0 14.4 --output runs/gpu_resize/bench.csv
```
