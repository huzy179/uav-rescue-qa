# Khối xác nhận trên video thật: SeaDronesSee-MOT (sơ bộ)

**Sơ bộ:** ba đoạn video, drone gần như đứng yên; chưa phải kết quả chính thức của RQ3. Mục đích: kiểm chứng trên dữ liệu thật (GPS, độ cao, hướng thật từ metadata drone; người thật có track_id) điều mô phỏng dự đoán, rằng ghép theo IoU trên ảnh gãy ở 2 khung/giây.

## Dữ liệu

- SeaDronesSee-MOT, bản lấy mẫu trên Kaggle (`rameezakther/seadronessee-mot-sampled-dataset`, Apache-2.0): ảnh 3840×2160, mỗi ảnh có `video_id`, `frame_index` (liên tiếp), `track_id` của từng người, metadata GPS, độ cao, góc gimbal, hướng, vận tốc.
- `tools/convert_seadronessee_mot.py` chuyển thành chuỗi khung, `telemetry.csv`, `truth.json` theo video (lớp swimmer, swimmer with life jacket; thuyền bỏ). 23 đoạn; chỉ chọn đoạn camera gần nhìn thẳng xuống, vì `georef` giả định nadir:

- `val-m100-DJI_0001-v21`: m100, 40 m, gimbal 79–90°, gần đứng yên, 34 người
- `val-mavic-DJI_0065-v5`: Mavic, 122–140 m, gimbal 76–78°, đứng yên, 6 người
- `train-mavic-DJI_0064-v13`: Mavic, 91 m, gimbal 90°, đứng yên, 2 người

Hạn chế của dữ liệu cho đề tài: phần lớn đoạn có drone đứng yên và camera nhìn xiên (gimbal 29–45°); đoạn duy nhất bay nhanh (v13 phần val, 7,2 m/s) chỉ 58 khung (2 s).

## Cách chạy và chấm

Detector E2c (`runs/train/E2c_s0/weights/best.pt`, cắt ô, conf 0,1) chạy một lần mỗi video ở 2 khung/giây; ba chiến lược xác nhận đọc lại cùng phát hiện (`--replay`), N = 3, cửa sổ 5 s, r = 3 m. Chấm bằng `eval/track_confirm_eval.py` trong không gian ảnh: cảnh báo ghép với người thật cùng khung khi IoU ≥ 0,3 hoặc tâm nằm trong box; người "đủ điều kiện" là người thấy trong ít nhất 3 khung đã xử lý. Kết quả từng lần ở `runs/sds/<video>/<chiến lược>/track_eval.json`.

## Kết quả

| Video | Chiến lược | FPS | Người được cảnh báo / đủ điều kiện | Cảnh báo | Nhầm | Lặp | Thời gian tới cảnh báo (s, trung vị) |
|---|---|---|---|---|---|---|---|
| val-m100-DJI_0001-v21 | geo | 2 | 12 / 19 | 37 | 13 | 12 | 2,00 |
| val-m100-DJI_0001-v21 | bytetrack (ngưỡng 0,25) | 2 | 2 / 19 | 2 | 0 | 0 | 27,00 |
| val-m100-DJI_0001-v21 | bytetrack (ngưỡng 0,1) | 2 | 2 / 19 | 2 | 0 | 0 | 25,25 |
| val-m100-DJI_0001-v21 | bytetrack_cmc (ngưỡng 0,1) | 2 | 2 / 19 | 4 | 0 | 2 | 21,00 |
| val-m100-DJI_0001-v21 | geo | 10 | 13 / 26 | 78 | 44 | 21 | 1,60 |
| val-m100-DJI_0001-v21 | bytetrack (ngưỡng 0,1) | 10 | 12 / 26 | 39 | 2 | 25 | 3,55 |
| val-mavic-DJI_0065-v5 | geo | 2 | 6 / 6 | 9 | 3 | 0 | 1,00 |
| val-mavic-DJI_0065-v5 | bytetrack (ngưỡng 0,25) | 2 | 6 / 6 | 11 | 0 | 5 | 1,50 |
| val-mavic-DJI_0065-v5 | bytetrack (ngưỡng 0,1) | 2 | 6 / 6 | 11 | 0 | 5 | 1,50 |
| val-mavic-DJI_0065-v5 | bytetrack_cmc (ngưỡng 0,1) | 2 | 6 / 6 | 12 | 0 | 6 | 1,50 |
| train-mavic-DJI_0064-v13 | geo | 2 | 2 / 2 | 4 | 0 | 2 | 3,00 |
| train-mavic-DJI_0064-v13 | bytetrack (ngưỡng 0,25) | 2 | 1 / 2 | 2 | 0 | 1 | 1,00 |
| train-mavic-DJI_0064-v13 | bytetrack (ngưỡng 0,1) | 2 | 1 / 2 | 2 | 0 | 1 | 1,00 |
| train-mavic-DJI_0064-v13 | bytetrack_cmc (ngưỡng 0,1) | 2 | 1 / 2 | 2 | 0 | 1 | 1,00 |

## Vì sao ByteTrack gãy ngay cả khi drone đứng yên

IoU giữa box nhãn thật của cùng một người ở hai khung đã xử lý liên tiếp:

| Video | 2 khung/giây | 30 khung/giây |
|---|---|---|
| v21 | trung vị 0,46; 36% cặp dưới 0,3 | trung vị 0,93 |
| v5 | trung vị 0,53; 22% dưới 0,3 | trung vị 0,94 |
| v13 | trung vị 0,05; 53% dưới 0,3 | trung vị 0,84 |

Ở 2 khung/giây, drone trôi, xoay nhẹ, người bơi di chuyển, box nhỏ: độ chồng lấn giữa hai khung đã thấp ngay cả khi không bay. Thêm recall mỗi khung thấp (v21: 0,41 ở conf 0,1; 0,25 ở conf 0,25), ByteTrack gần như mỗi khung tạo track mới (v21, ngưỡng 0,1: 314 lần ghép, 299 ID khác nhau). Hạ ngưỡng tạo track từ 0,25 xuống 0,1 không đổi kết quả. Ở 10 khung/giây ByteTrack hoạt động lại (v21: 12/26), xác nhận nguyên nhân là tần số khung, không phải cách dùng tracker.

## Nhận xét

1. Trên dữ liệu thật, gom theo vị trí mặt đất (`geo`) xác nhận được nhiều người hơn hẳn ByteTrack ở 2 khung/giây (v21: 12/19 so với 2/19), khớp với mô phỏng (`TONG_QUAN` mục 3.11).
2. Cái giá của `geo`: nhiều cảnh báo lặp (một người tách thành nhiều cụm khi GPS thật trôi qua 52 s) và cảnh báo nhầm (vật cố định được phát hiện lặp lại). Ở 10 khung/giây, cảnh báo nhầm tăng mạnh (44) vì đủ 3 lần thấy chỉ trong 0,3 s: N và cửa sổ phải chọn theo FPS.
3. Recall mỗi khung của detector trên đoạn v21 thấp (0,41) dù người khá to (cạnh ngắn trung vị 80 px): giới hạn chung cho mọi chiến lược ở video này.

## Giới hạn

- Ba đoạn, drone gần như đứng yên; chưa có đoạn bay nhanh đủ dài, nên trường hợp chính của đề tài vẫn dựa vào mô phỏng.
- Camera của m100 và Mavic khác Matrice 4T; FOV dùng mặc định 82° chéo cho `georef`, ảnh hưởng tới bán kính tính bằng mét.
- Metadata `altitude` coi là độ cao so với mặt nước (drone cất cánh từ thuyền hoặc bờ ngang mặt nước); chưa kiểm chứng.

## Tái lập

```bash
kaggle datasets download rameezakther/seadronessee-mot-sampled-dataset -p data/raw/seadronessee_mot --unzip
python tools/convert_seadronessee_mot.py --src data/raw/seadronessee_mot --dst data/processed/sds_mot
V=val-m100-DJI_0001-v21; D=data/processed/sds_mot/$V
python -m edge.main --config configs/edge.yaml --source $D/frames --source-fps 30 --fps 2 \
    --model runs/train/E2c_s0/weights/best.pt --telemetry $D/telemetry.csv --confirm geo --output runs/sds/$V/geo --drain-s 0
python -m edge.main --config configs/edge.yaml --source $D/frames --source-fps 30 --fps 2 --replay runs/sds/$V/geo/detections.jsonl \
    --telemetry $D/telemetry.csv --confirm bytetrack --track-thresh 0.1 --output runs/sds/$V/bytetrack_t01 --drain-s 0
python eval/track_confirm_eval.py --run runs/sds/$V/geo --truth $D/truth.json
```
