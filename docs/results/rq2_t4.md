# Câu hỏi 2 trên Kaggle T4: nén mô hình, cách chạy và tốc độ cả pipeline

Câu hỏi 2: chạy kịp trên thiết bị biên không, và cấu hình nào tốt nhất khi cân tốc độ với độ chính xác. Không có Jetson (ROADMAP quyết định #2), nên đo trên GPU Tesla T4 của Kaggle với TensorRT. **Số trên T4 chỉ dùng để so thứ hạng giữa các cấu hình trên cùng phần cứng**, không phải số của thiết bị biên (TECHNICAL 14.4).

## Môi trường và cấu hình

- Kaggle, Tesla T4, ngày 7–8/11/2026; `notebooks/kaggle_rq2.ipynb` clone kho ở commit `d675085` (`dirty: false`). Python 3.13.16, ultralytics 8.4.174, torch 2.11.0+cu130, TensorRT 10.16.1.11, onnx 1.23.2, opencv-python 5.0.0.93 (`runs/rq2/models/run_config.json`).
- Mô hình chính E2c (`runs/train/E2c_s0/weights/best.pt`, sha256 `e8b6439b…`), xuất TensorRT FP16 và INT8 cho cỡ vào 1280 (toàn ảnh) và 640 (ô). Cả bốn engine xuất được (`failed: {}`). INT8 hiệu chỉnh trên ô 640 cắt từ ảnh val của VisDrone và AFO, một ô mỗi ảnh (tập dùng để chọn `best.pt` của E2c, không phải tập test).
- Chín biến thể = {PyTorch, TensorRT FP16, TensorRT INT8} × {toàn ảnh 1280, cắt ô 640 ở độ phân giải gốc, cắt ô sau khi thu nhỏ về 10 px dự kiến theo độ cao}. Cấu hình `configs/experiments/rq2_t4.yaml` (bản đã chạy: `runs/rq2/rq2_config.yaml`).
- **Độ chính xác:** SeaDronesSee val (`sds_det`, ảnh 4K, có độ cao; 1.055 người) và VisDrone test-dev (1.610 ảnh, 27.382 người, có vùng bỏ qua). Dự đoán ở conf 0,001; recall vận hành ở conf 0,25; bootstrap cặp theo video. Thu nhỏ theo độ cao chỉ chạy trên SeaDronesSee (VisDrone không có độ cao).
- **Tốc độ:** cả pipeline `edge/main.py` (đọc khung, thu nhỏ, cắt ô, suy luận, gộp box, georef, xác nhận) trên 100 khung của đoạn SeaDronesSee-MOT val v21 (4K, Matrice 100, telemetry thật), 2 khung/giây. `runs/rq2/timing.csv`, từng khung ở `runs/rq2/speed/<biến thể>/timings.jsonl`. **Chỉ đo trên video 4K này**, nên thời gian không áp cho ảnh VisDrone (nhỏ hơn, ít ô hơn).
- Bảng tổng hợp `runs/rq2/rq2.csv`; so cặp, biên Pareto, phân bố độ tin cậy ở `runs/rq2/report/` (`scripts/after_rq2.py`, `eval/rq2_report.py`) trên RTX 5060 ngày 8/11 từ boxes.csv đã tải về.

## Kết quả 1: tốc độ cả pipeline (T4, chỉ so sánh tương đối)

`runs/rq2/report/speed.csv`, `runs/rq2/timing.csv`. Thu nhỏ là thời gian đổi cỡ khung trước khi cắt ô (cột `tile_ms`).

| Biến thể | Số ô | Thu nhỏ p50 (ms) | Suy luận p50 (ms) | Tổng p50 (ms) | Tổng p95 (ms) | FPS theo p95 | Nhanh hơn PyTorch cùng cách chạy (lần, p95) |
|---|---|---|---|---|---|---|---|
| PyTorch, toàn ảnh | 1 | 0,00 | 54,37 | 54,71 | 55,52 | 18,01 | 1,000 |
| FP16, toàn ảnh | 1 | 0,00 | 23,72 | 24,06 | 25,06 | 39,90 | 2,215 |
| INT8, toàn ảnh | 1 | 0,00 | 20,11 | 20,37 | 22,43 | 44,58 | 2,475 |
| PyTorch, cắt ô gốc | 32 | 0,05 | 385,50 | 386,06 | 403,75 | 2,48 | 1,000 |
| FP16, cắt ô gốc | 32 | 0,05 | 120,10 | 120,57 | 133,34 | 7,50 | 3,028 |
| INT8, cắt ô gốc | 32 | 0,05 | 105,98 | 106,58 | 110,65 | 9,04 | 3,649 |
| PyTorch, thu nhỏ 10 px | 6 | 46,35 | 90,97 | 138,49 | 158,32 | 6,32 | 1,000 |
| FP16, thu nhỏ 10 px | 6 | 46,28 | 30,56 | 77,34 | 86,38 | 11,58 | 1,833 |
| INT8, thu nhỏ 10 px | 6 | 45,74 | 25,84 | 72,10 | 83,45 | 11,98 | 1,897 |

## Kết quả 2: nén mô hình làm mất gì

Hiệu B − A, bootstrap cặp 95% (`runs/rq2/compare/<tập>/<B>__vs__<A>_iou<iou>/compare.csv`); * có ý nghĩa thống kê.

**VisDrone test-dev, IoU 0,5** (FP16 so với PyTorch gần như không đổi nên chỉ ghi một dòng):

| So sánh | Hiệu AP50, tất cả | Hiệu recall vận hành, tất cả | Hiệu AP50 < 8 px | Hiệu recall vận hành < 8 px |
|---|---|---|---|---|
| FP16 − PyTorch, toàn ảnh | −0,005 (−0,006 đến −0,001) * | −0,002 (−0,003 đến −0,000) * | −0,008 (−0,020 đến −0,006) * | −0,001 (−0,007 đến +0,000) |
| INT8 − PyTorch, toàn ảnh | −0,021 (−0,028 đến −0,018) * | −0,130 (−0,154 đến −0,117) * | −0,018 (−0,041 đến −0,015) * | −0,109 (−0,176 đến −0,096) * |
| INT8 − PyTorch, cắt ô | −0,015 (−0,023 đến −0,011) * | −0,109 (−0,131 đến −0,098) * | −0,009 (−0,025 đến −0,006) * | −0,098 (−0,159 đến −0,084) * |

Ở IoU 0,3, nhóm dưới 8 px: INT8 − PyTorch toàn ảnh AP50 −0,035 (−0,052 đến −0,029) *, recall vận hành −0,172 (−0,216 đến −0,160) *.

Theo nhóm cỡ (VisDrone test-dev, toàn ảnh, IoU 0,5; `eval_<biến thể>_iou0.5/eval_by_size.csv`):

| Nhóm cỡ | AP50 PyTorch → INT8 | Recall vận hành PyTorch → INT8 | Recall tối đa (mọi ngưỡng) PyTorch → INT8 |
|---|---|---|---|
| < 8 px | 0,241 → 0,223 | 0,217 → 0,108 | 0,477 → 0,461 |
| 8–16 px | 0,623 → 0,592 | 0,572 → 0,407 | 0,853 → 0,834 |
| 16–32 px | 0,823 → 0,808 | 0,783 → 0,664 | 0,951 → 0,945 |
| > 32 px | 0,888 → 0,879 | 0,853 → 0,768 | 0,969 → 0,970 |

Phân bố độ tin cậy của mọi box dự đoán (`runs/rq2/report/conf.csv`):

| Tập, biến thể | Số box conf ≥ 0,25 | Phân vị 99 của conf | Conf lớn nhất |
|---|---|---|---|
| VisDrone, FP16 toàn ảnh | 19.423 | 0,639 | 0,845 |
| VisDrone, INT8 toàn ảnh | 10.940 | 0,492 | 0,749 |
| SeaDronesSee, FP16 thu nhỏ 10 px | 928 | 0,749 | 0,820 |
| SeaDronesSee, INT8 thu nhỏ 10 px | 834 | 0,653 | 0,742 |

**SeaDronesSee val, IoU 0,5:**

| So sánh | Hiệu AP50, tất cả | Hiệu recall vận hành, tất cả |
|---|---|---|
| FP16 − PyTorch, thu nhỏ 10 px | +0,004 (−0,001 đến +0,005) | +0,001 (+0,000 đến +0,002) |
| INT8 − PyTorch, thu nhỏ 10 px | −0,007 (−0,073 đến +0,032) | −0,025 (−0,100 đến +0,010) |
| INT8 − PyTorch, toàn ảnh | +0,003 (−0,024 đến +0,062) | −0,024 (−0,036 đến +0,009) |
| INT8 − PyTorch, cắt ô gốc | −0,070 (−0,129 đến −0,018) * | −0,084 (−0,139 đến −0,012) * |
| Thu nhỏ 10 px − cắt ô gốc, FP16 | +0,301 (+0,060 đến +0,414) * | +0,208 (+0,117 đến +0,321) * |
| Thu nhỏ 10 px − cắt ô gốc, INT8 | +0,359 (+0,065 đến +0,476) * | +0,265 (+0,102 đến +0,384) * |

## Kết quả 3: biên Pareto recall theo tốc độ (SeaDronesSee)

`runs/rq2/report/pareto.csv`, hình `runs/rq2/rq2_sds_det.png`. Một cấu hình trên biên khi không cấu hình nào khác vừa có FPS theo p95 vừa có recall vận hành cao hơn hoặc bằng nó (và hơn hẳn ở ít nhất một).

| Biến thể | FPS theo p95 | Recall vận hành | AP50 | Trên biên |
|---|---|---|---|---|
| INT8, toàn ảnh | 44,58 | 0,443 | 0,470 | có |
| FP16, toàn ảnh | 39,90 | 0,468 | 0,457 | có |
| PyTorch, toàn ảnh | 18,01 | 0,466 | 0,468 | |
| INT8, thu nhỏ 10 px | 11,98 | 0,554 | 0,524 | có |
| FP16, thu nhỏ 10 px | 11,58 | 0,580 | 0,534 | có |
| INT8, cắt ô gốc | 9,04 | 0,290 | 0,164 | |
| FP16, cắt ô gốc | 7,50 | 0,372 | 0,234 | |
| PyTorch, thu nhỏ 10 px | 6,32 | 0,579 | 0,531 | |
| PyTorch, cắt ô gốc | 2,48 | 0,374 | 0,234 | |

## Kết quả 4: thiết bị yếu hơn (mô phỏng, hồ sơ ước lượng)

Hồ sơ thời gian `configs/devices/*.yaml` hiệu chỉnh từ số đo trên (`tools/fit_device_profile.py` qua `scripts/after_rq2.py`): mỗi khung tốn `overhead + số ô × tile_ms + megapixel khung gốc × resize_ms_per_mpx` (số hạng cuối chỉ khi thu nhỏ theo độ cao; thêm 8/11 sau khi thấy chặng thu nhỏ khung lớn). T4 là số đo; ba Jetson **nhân tỉ lệ thời gian suy luận công bố của Ultralytics** (Jetson / T4, YOLO26n FP16; giả định áp được cho bản s và cho cả phần chạy trên CPU), nên là ước lượng.

| Hồ sơ | overhead (ms) | Một ô 640 (ms) | Toàn ảnh 1280 (ms) | Thu nhỏ khung (ms mỗi megapixel) |
|---|---|---|---|---|
| Tesla T4 (đo) | 0,55 | 3,75 | 23,72 | 5,574 |
| Jetson AGX Orin 64GB (ước lượng) | 0,85 | 5,78 | 36,56 | 8,59 |
| Jetson Orin NX 16GB (ước lượng) | 1,34 | 9,12 | 57,63 | 13,539 |
| Jetson Orin Nano Super (ước lượng) | 1,48 | 10,09 | 63,77 | 14,983 |

Kiểm tra lại trên chính T4: hồ sơ cho khung 4K thu nhỏ về 6 ô thấp hơn số đo trung vị (77,34 ms), vì suy luận mỗi ô khi chạy 6 ô chậm hơn khi chạy 32 ô; hồ sơ vì vậy hơi lạc quan.

Mô phỏng `configs/experiments/rq3_device.yaml` (cùng chuyến bay như `rq3_adaptive.md`: 60 s, 10 người, kịch bản quay 8 khung/giây, recall theo cỡ người của E2c, thu nhỏ về 10 px, xác nhận geo N = 3, 3 seed): pipeline xin xử lý 2, 4 hoặc 8 khung/giây; thiết bị bận thì bỏ khung tới. Kết quả `runs/rq3/device/summary.csv`, chạy 8/11 trên RTX 5060 ở commit `e6d91b9` (`dirty: true`, số hạng thu nhỏ khung chưa commit). **Mô phỏng**, trung bình 3 seed.

| Độ cao | Thiết bị | Độ trễ giả lập mỗi khung, trung vị (ms) | Khung xử lý / 60 s khi xin 8 khung/giây | Bỏ sót khi xin 8 | Bỏ sót khi xin 4 | Bỏ sót khi xin 2 |
|---|---|---|---|---|---|---|
| 30 m | T4 | 54,283 | 480 | 0,000 | 0,067 | 0,500 |
| 30 m | AGX Orin | 83,659 | 480 | 0,000 | 0,067 | 0,500 |
| 30 m | Orin NX | 131,878 | 240 | 0,067 | 0,067 | 0,500 |
| 30 m | Orin Nano Super | 145,935 | 240 | 0,067 | 0,067 | 0,500 |
| 50 m | T4 | 69,283 | 480 | 0,000 | 0,033 | 0,100 |
| 50 m | AGX Orin | 106,779 | 480 | 0,000 | 0,033 | 0,100 |
| 50 m | Orin NX | 168,358 | 240 | 0,033 | 0,033 | 0,100 |
| 50 m | Orin Nano Super | 186,295 | 240 | 0,033 | 0,033 | 0,100 |
| 100 m | T4 | 136,783 | 240 | 0,000 | 0,000 | 0,000 |
| 100 m | AGX Orin | 210,819 | 240 | 0,000 | 0,000 | 0,000 |
| 100 m | Orin NX | 332,518 | 160 | 0,000 | 0,000 | 0,000 |
| 100 m | Orin Nano Super | 367,915 | 160 | 0,000 | 0,000 | 0,000 |

Số ô mỗi khung tăng theo độ cao (30 m: 2 ô, 50 m: 6, 100 m: 24) vì bay càng cao người càng nhỏ nên càng ít phải thu nhỏ. Kịch bản quay 8 khung/giây nên số khung xử lý được chỉ nhận các mức 480, 240, 160… (thiết bị bận qua 1, 2, 3 khung nguồn).

## Nhận xét

1. **FP16 là lựa chọn mặc định:** nhanh hơn PyTorch 1,833–3,028 lần (p95) mà độ chính xác gần như không đổi: trên SeaDronesSee không khác có ý nghĩa; trên VisDrone AP50 giảm 0,005 và recall vận hành dưới 8 px không khác có ý nghĩa.
2. **INT8 nhanh thêm ít mà mất nhiều recall vận hành.** So với FP16, INT8 chỉ nhanh thêm từ 39,90 lên 44,58 FPS (toàn ảnh) và 11,58 lên 11,98 (thu nhỏ 10 px). Trên VisDrone, AP50 mất ít (−0,021) nhưng recall ở conf 0,25 mất 0,130, ở người dưới 8 px mất một nửa (0,217 → 0,108). Recall tối đa gần như giữ (0,477 → 0,461), và số box có conf ≥ 0,25 giảm từ 19.423 xuống 10.940, phân vị 99 của conf từ 0,639 xuống 0,492: **INT8 nén độ tin cậy xuống**, thứ tự giữa các box gần như giữ nên AP ít đổi, nhưng ngưỡng 0,25 (chọn cho mô hình không nén) cắt mất nhiều người. Trên SeaDronesSee với thu nhỏ theo độ cao, hiệu không có ý nghĩa nhưng khoảng tin cậy rộng (−0,100 đến +0,010 recall).
3. **Cắt ô ở độ phân giải gốc là cấu hình tệ trên ảnh 4K**: chậm nhất (32 ô) và AP50 thấp nhất (0,234; INT8 0,164), vì người trên SeaDronesSee to so với cỡ mô hình học tốt (`scale_by_altitude.md`). Thu nhỏ theo độ cao giải quyết cả hai: AP50 lên 0,534 và số ô từ 32 xuống 6.
4. **Thu nhỏ theo độ cao giờ tốn thời gian ở chỗ khác: đổi cỡ khung 4K mất 46,28 ms (trung vị) trên CPU của Kaggle**, nhiều hơn cả suy luận FP16 của 6 ô (30,56 ms), trong tổng thời gian trung vị 77,34 ms. Đây là chặng cần tối ưu tiếp (`CAI_TIEN.md` mục 2), không phải mô hình.
5. **Biên Pareto trên SeaDronesSee** gồm hai nhóm: toàn ảnh (FP16, INT8; 39,90–44,58 FPS theo p95, recall vận hành 0,443–0,468) và thu nhỏ theo độ cao (FP16, INT8; 11,58–11,98 FPS, recall 0,554–0,580). PyTorch và cắt ô gốc bị vượt. Với tần số cần thiết của câu hỏi 3, trần 8 khung/giây (`rq3_adaptive.md`), mọi cấu hình trên biên đều đủ nhanh trên T4, nên **cấu hình đề xuất là FP16 với thu nhỏ theo độ cao**: recall cao nhất trên biên, nhanh hơn PyTorch 1,833 lần. INT8 chỉ đáng cân nhắc khi thiết bị không theo kịp và sau khi chọn lại ngưỡng conf cho riêng nó trên tập val.
6. **Thiết bị yếu (mô phỏng, hồ sơ ước lượng):** Orin NX và Orin Nano Super không chạy kịp 8 khung/giây ở 30–50 m, chỉ được 4, nên bỏ sót 0,067 ở 30 m thay vì 0,000 trên T4 và AGX Orin; ở 100 m mọi thiết bị đều không bỏ sót vì 2 khung/giây đã đủ. Chỗ thiếu rơi đúng vào lúc bay thấp, nơi tần số cần cao nhất. Ở 30 m mỗi khung chỉ có 2 ô, nên phần lớn độ trễ ước lượng là **thu nhỏ khung 4K** (14,983 ms mỗi megapixel trên Orin Nano Super, so với 10,09 ms mỗi ô): đổi cỡ khung trên GPU (`CAI_TIEN.md` mục 2) là cải tiến có khả năng giúp thiết bị yếu nhiều nhất, còn INT8 thì không (chỉ đổi phần suy luận).

## Giới hạn

- T4 không phải Jetson; thứ hạng giữa các cấu hình có thể đổi trên Jetson (CPU ARM yếu hơn nhiều so với GPU, nên chặng thu nhỏ khung có thể còn nặng hơn tương đối).
- Thời gian đo trên một đoạn video 4K, 100 khung, một lần chạy mỗi biến thể; INT8 hiệu chỉnh trên một tập nhỏ không gồm ảnh nước.
- Độ chính xác của SeaDronesSee val có 1.055 người và gần như không có người dưới 16 px, nên câu hỏi "INT8 mất gì ở người nhỏ" chỉ trả lời được trên VisDrone. Chưa chạy trên tập ảnh lũ (chờ khoá).
- Phần thiết bị yếu là mô phỏng: hồ sơ Jetson nhân một tỉ lệ công bố cho YOLO26n, dùng chung cho cả phần chạy trên CPU (thu nhỏ khung), điều chưa kiểm chứng; detector giả có recall độc lập giữa các khung.
- Recall vận hành của INT8 tính ở cùng ngưỡng 0,25 như các biến thể khác; chưa thử ngưỡng riêng cho INT8.

## Tái lập

```bash
# Kaggle: notebooks/kaggle_rq2.ipynb (COMMIT d6750853), Output tải về runs/rq2/ (bỏ ảnh hiệu chỉnh và engine)
kaggle kernels output <người dùng>/<notebook> -p <thư mục> --file-pattern 'runs/rq2/(?!calib_)(?!.*\.(engine|onnx|pt|cache)$)'
# máy cá nhân: so cặp, hiệu chỉnh hồ sơ thiết bị, bảng
.venv/bin/python scripts/after_rq2.py --rq2 runs/rq2
# thiết bị yếu, mô phỏng (sau khi hồ sơ đã hiệu chỉnh)
.venv/bin/python -m sim.sweep_rq3 --config configs/experiments/rq3_device.yaml --jobs 12
```
