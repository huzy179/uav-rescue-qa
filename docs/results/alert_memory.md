# Bộ nhớ vị trí đã cảnh báo (`--suppress-s`): bớt cảnh báo lặp, đổi lại có thể bỏ sót người đứng gần

**Sơ bộ, chưa phải kết quả chính thức của RQ3.** Vấn đề: khi một người bị tách thành hai cụm (geo) hoặc track bị đứt rồi mở lại (ByteTrack), khối xác nhận gửi hai cảnh báo cho cùng một người. Trên video thật SeaDronesSee (`sds_mot_confirm.md`) geo gửi 12 cảnh báo lặp trên v21.

## Cách làm

`edge/confirm.py`, lớp `AlertMemory`: nhớ vị trí GPS các cảnh báo trong `suppress_s` giây gần nhất. Một cụm/track mới đủ N lần thấy mà nằm trong bán kính `radius_m` (3 m, như geo) quanh một cảnh báo đã gửi thì được đánh dấu đã cảnh báo nhưng không gửi thêm. `suppress_s = 0` (mặc định) giữ hành vi cũ. Dùng chung cho `geo`, `bytetrack`, `bytetrack_cmc`.

Cái giá có thể có: hai người thật đứng cách nhau dưới 3 m thì người thứ hai không được báo.

## Video thật SeaDronesSee-MOT, 2 khung/giây

Phát lại đúng detections đã lưu của lần chạy gốc (`--replay`), chỉ đổi khối xác nhận; chấm bằng `eval/track_confirm_eval.py` (IoU 0,3 hoặc tâm nằm trong box, người đủ điều kiện khi thấy ≥ 3 khung). ByteTrack dùng `--track-thresh 0.1`. Số đọc từ `runs/sds/<video>/<cách>/track_eval.json`.

| Video | Cách | Người được báo | Tổng cảnh báo | Nhầm | Lặp |
|---|---|---|---|---|---|
| val-m100-DJI_0001-v21 | geo | 12/19 | 37 | 13 | 12 |
| | geo, nhớ 60 s | 10/19 | 27 | 10 | 7 |
| | bytetrack | 2/19 | 2 | 0 | 0 |
| | bytetrack, nhớ 60 s | 2/19 | 2 | 0 | 0 |
| val-mavic-DJI_0065-v5 | geo | 6/6 | 9 | 3 | 0 |
| | geo, nhớ 60 s | 6/6 | 9 | 3 | 0 |
| | bytetrack | 6/6 | 11 | 0 | 5 |
| | bytetrack, nhớ 60 s | 6/6 | 6 | 0 | 0 |
| train-mavic-DJI_0064-v13 | geo | 2/2 | 4 | 0 | 2 |
| | geo, nhớ 60 s | 2/2 | 3 | 0 | 1 |
| | bytetrack | 1/2 | 2 | 0 | 1 |
| | bytetrack, nhớ 60 s | 1/2 | 1 | 0 | 0 |

Thời gian tới cảnh báo (trung vị) không đổi ở mọi dòng.

## Mô phỏng

Kịch bản như `rq3_gps.yaml` (60 s, recall 0,7, 0,5 báo nhầm mỗi khung, N = 3), τ GPS 30 s; lưới số người ∈ {10, 30} × σ_GPS ∈ {0,5; 3} m × nhớ ∈ {0, 60} s × {geo, bytetrack_cmc}, 3 seed. Cấu hình `configs/experiments/rq3_suppress.yaml`, kết quả `runs/rq3/suppress/summary.csv`. Trung bình 3 seed.

| Cách | Số người | σ GPS | Bỏ sót (0 → 60 s) | Tách nhầm (0 → 60 s) | Gộp nhầm (0 → 60 s) |
|---|---|---|---|---|---|
| geo | 10 | 0,5 m | 0,000 → 0,033 | 0,000 → 0,000 | 0,667 → 0,333 |
| geo | 10 | 3 m | 0,033 → 0,033 | 0,333 → 0,000 | 1,000 → 0,667 |
| geo | 30 | 0,5 m | 0,000 → 0,033 | 0,000 → 0,000 | 11,333 → 10,333 |
| geo | 30 | 3 m | 0,100 → 0,100 | 2,667 → 2,000 | 10,000 → 9,333 |
| bytetrack_cmc | 10 | 0,5 m | 0,200 → 0,200 | 0,333 → 0,000 | 0,667 → 0,667 |
| bytetrack_cmc | 10 | 3 m | 1,000 → 1,000 | 0,000 → 0,000 | 0,000 → 0,000 |
| bytetrack_cmc | 30 | 0,5 m | 0,244 → 0,256 | 0,333 → 0,000 | 8,667 → 8,333 |
| bytetrack_cmc | 30 | 3 m | 1,000 → 1,000 | 0,000 → 0,000 | 0,000 → 0,000 |

Báo giả mỗi phút bằng 0 ở mọi ô, cả hai mức.

## Nhận xét

1. **Bộ nhớ làm đúng việc của nó:** cảnh báo lặp giảm ở mọi nơi có lặp (SDS v5 bytetrack 5 → 0; v21 geo 12 → 7; mô phỏng tách nhầm về 0 trừ geo 30 người σ 3 m).
2. **Cái giá thấy rõ ở cảnh đông người.** v21 (19 người bơi gần nhau) geo mất 2 người được báo (12 → 10). Mô phỏng: geo bỏ sót tăng 0,000 → 0,033 ở σ 0,5 m; bytetrack_cmc 30 người 0,244 → 0,256.
3. Cảnh báo nhầm cũng giảm nhẹ trên v21 (13 → 10), có lẽ vì báo nhầm lặp lại quanh cùng một vật (sóng, phao) bị chặn; chưa kiểm tra từng cảnh báo.
4. Với cứu hộ, bỏ sót một người đắt hơn nhiều so với một cảnh báo thừa. Vì vậy **mặc định giữ `suppress_s = 0`** và gộp ở trạm mặt đất (mục dưới).

## Thay thế: gộp thành sự cố ở trạm mặt đất

Thay vì bỏ cảnh báo ở biên, trạm mặt đất gắn mỗi cảnh báo vào sự cố gần nhất còn mở (`ground/incidents.py`, TECHNICAL mục 12.3): không cảnh báo nào bị bỏ, người vận hành mở sự cố vẫn thấy từng cảnh báo và ảnh cắt. Phát lại cảnh báo geo của ba video SDS qua đúng hàm gộp (`eval/incident_merge_eval.py`, số đọc từ `runs/sds/incident_merge.csv`):

| Video | Luật gộp | Cảnh báo | Sự cố | Sự cố lẫn > 1 người | Người bị tách | Người bị gộp chung |
|---|---|---|---|---|---|---|
| v21 (12 người được báo) | cố định 3 m | 37 | 27 | 6 | 6 | 8 |
| | cố định 5 m | 37 | 19 | 5 | 6 | 9 |
| | cố định 10 m | 37 | 10 | 3 | 3 | 12 |
| | tổng sai số (10 m) | 37 | 10 | 3 | 3 | 12 |
| v5 (6 người) | cố định 3 m | 9 | 9 | 0 | 0 | 0 |
| | cố định 5 m | 9 | 8 | 0 | 0 | 0 |
| | cố định 10 m | 9 | 4 | 2 | 0 | 6 |
| v13 (2 người) | cố định 3 m | 4 | 3 | 0 | 1 | 0 |
| | cố định 5 m | 4 | 2 | 0 | 0 | 0 |
| | cố định 10 m | 4 | 1 | 1 | 0 | 2 |

Luật "tổng sai số" dùng `position_error_m` gửi kèm cảnh báo; `edge/main.py` hiện gửi hằng số 5 m chưa hiệu chỉnh, nên luật này trùng với bán kính cố định 10 m (v5, v13 cũng trùng). Nhận xét:

1. Bán kính 10 m gộp nhầm mọi người ở v21 và v5. **Mặc định chọn 5 m cố định**: hai video thưa người gộp đúng hoàn toàn (v13 hết lặp, v5 không lẫn người), v21 giảm 37 cảnh báo xuống 19 sự cố.
2. v21 thì không bán kính nào vừa hết tách vừa hết lẫn: người bơi sát nhau hơn độ trôi vị trí geo. Đó là giới hạn của định vị, không chữa được bằng luật gộp; vì gộp ở trạm không bỏ cảnh báo, cái giá là hiển thị gộp nhóm, không phải mất người.
3. Khi `position_error_m` được ước lượng thật (TECHNICAL mục 8.4) thì đáng thử lại luật theo sai số (`error_weight`).

## Giới hạn

- Ba video SDS, chỉ đối chiếu với nhãn trong không gian ảnh; mô phỏng 3 seed mỗi ô, người đứng yên, đặt ngẫu nhiên đều (chưa mô phỏng người tụ thành cụm như trên mái nhà).
- Chưa quét `suppress_s` và bán kính nhớ khác 60 s, 3 m.

## Tái lập

```bash
# SDS: phát lại detections của lần chạy geo, đổi khối xác nhận
V=val-m100-DJI_0001-v21
.venv/bin/python edge/main.py --config configs/edge.yaml --source data/processed/sds_mot/$V/frames --source-fps 30 --fps 2 \
    --replay runs/sds/$V/geo/detections.jsonl --telemetry data/processed/sds_mot/$V/telemetry.csv \
    --confirm geo --suppress-s 60 --output runs/sds/$V/geo_sup60 --drain-s 0
.venv/bin/python eval/track_confirm_eval.py --run runs/sds/$V/geo_sup60 --truth data/processed/sds_mot/$V/truth.json
# Trạm mặt đất: gộp sự cố
.venv/bin/python eval/incident_merge_eval.py --videos val-m100-DJI_0001-v21 val-mavic-DJI_0065-v5 train-mavic-DJI_0064-v13 \
    --mot data/processed/sds_mot --runs runs/sds --confirm geo --output runs/sds/incident_merge.csv
# Mô phỏng
.venv/bin/python -m sim.sweep_rq3 --config configs/experiments/rq3_suppress.yaml --jobs 8
```
