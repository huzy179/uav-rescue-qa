# Định vị khi camera nghiêng: kiểm chứng bằng track SeaDronesSee

**Sơ bộ, kết quả lẫn lộn.** Phép chiếu cũ giả định camera nhìn thẳng xuống. Mọi đoạn SeaDronesSee có drone di chuyển đều quay với gimbal nghiêng 20–78°, nên không dùng được cho định vị và demo phải chuyển sang chuyến bay mô phỏng. Ngày 7/11 phép chiếu được mở rộng để tính góc nghiêng (`edge/georef.py`, TECHNICAL 8.3; cờ `--use-pitch`, mặc định tắt). File này kiểm tra xem bật góc nghiêng có làm định vị nhất quán hơn không.

## Cách làm

- `tools/eval_georef_pitch.py` trên 20 đoạn `data/processed/sds_mot` có nhãn (`truth.json`: box và `track_id` mỗi khung, `telemetry.csv` có `pitch_deg` từ metadata gimbal).
- Người là người bơi, gần như đứng yên trong vài giây. Mỗi track: các khung trong 10 s đầu, mỗi 5 khung một lần, chiếu tâm đáy box xuống mặt nước bằng telemetry của khung. **Độ tản** = trung vị khoảng cách tới vị trí trung vị (mét). Phép chiếu đúng thì độ tản nhỏ.
- Hai cách chiếu trên cùng điểm: nhìn thẳng xuống (pitch ép −90°, như mọi kết quả trước 7/11) và theo góc gimbal.
- Góc nhìn 82° chéo cho mọi drone (như `configs/demo`); bỏ track dưới 5 điểm chiếu được.
- Kết quả: `runs/georef_pitch/summary.csv`, `per_track.csv`.

## Kết quả (trung vị qua các track)

| Đoạn | Số track | Pitch trung vị | Độ tản nhìn thẳng (m) | Độ tản theo gimbal (m) | Tỉ lệ track tốt hơn |
|---|---|---|---|---|---|
| train-mavic-DJI_0062-v8 | 5 | −48,0° | 4,982 | 1,301 | 1,000 |
| train-m210-DJI_0010_d3-v14 | 3 | −21,4° | 8,945 | 3,954 | 1,000 |
| train-m210-DJI_0001-v15 | 1 | −31,1° | 10,264 | 4,536 | 1,000 |
| val-mavic-DJI_0069-v9 | 7 | −38,5° | 6,409 | 2,596 | 0,857 |
| val-mavic-DJI_0065-v5 | 6 | −76,8° | 0,651 | 0,324 | 1,000 |
| train-mavic-DJI_0065-v5 | 7 | −69,8° | 0,932 | 0,530 | 0,857 |
| train-mavic-DJI_0059-v12 | 4 | −33,3° | 4,106 | 2,371 | 1,000 |
| train-mavic-DJI_0057-v0 | 15 | −45,4° | 0,422 | 1,643 | 0,000 |
| train-m100-DJI_0001-v21 | 21 | −58,1° | 0,927 | 1,733 | 0,333 |
| train-mavic-DJI_0050-v7 | 9 | −8,4° | 6,010 | 8,856 | 0,000 |
| train-m210-DJI_0011_d3-v18 | 3 | −13,3° | 9,727 | 20,064 | 0,333 |
| val-m100-DJI_0001-v21 | 21 | −86,8° | 1,402 | 1,437 | 0,667 |
| **tất cả** | **132** | **−58,0°** | **1,336** | **1,603** | **0,515** |

Các đoạn còn lại (1–6 track mỗi đoạn) ở `summary.csv`.

## Nhận xét

1. **Tốt hơn rõ khi drone di chuyển hoặc xoay với camera nghiêng vừa phải**: v8, v14, v15, v9 (val) giảm độ tản từ 4,982–10,264 m xuống 1,301–4,536 m. Đây là trường hợp giả định nhìn thẳng xuống sai nặng nhất: vị trí một người đứng yên trôi theo chuyển động của drone.
2. **Kém hơn ở hai nhóm.** (a) Camera gần chân trời (v7 −8,4°, v18 −13,3°): mỗi độ sai của góc gimbal làm điểm chiếu lệch rất xa, nên nhiễu metadata bị phóng đại. (b) Một số đoạn drone gần như đứng yên (v0, v21 train): khi drone đứng yên, giả định nhìn thẳng xuống chỉ làm lệch **đều** (sai chỗ nhưng ổn định), độ tản vẫn nhỏ; tính theo gimbal lại đưa dao động của góc gimbal vào vị trí. Thước đo độ tản không thấy được lệch đều, nên ở nhóm này nó không nói cách nào đúng hơn.
3. Tính chung, trung vị độ tản tăng (1,336 → 1,603 m) và chỉ 0,515 số track tốt hơn: **chưa bật mặc định**. Giữ `--use-pitch` cho đoạn drone di chuyển với camera nghiêng vừa phải.
4. Hướng kiểm tra tiếp (`docs/CAI_TIEN.md` mục 3.6): độ trễ giữa metadata gimbal và khung ảnh (`tools/shift_telemetry.py`), quy ước góc của từng loại drone, góc nhìn thật của từng camera (Mavic, M210, M100 khác nhau), làm mượt góc gimbal theo thời gian; và một thước đo thấy được lệch đều (vị trí người đứng yên nhìn từ hai hướng bay khác nhau).

## Giới hạn

- Người bơi có di chuyển thật; độ tản gồm cả chuyển động đó và sai số GPS, như nhau ở hai cách.
- Góc nhìn 82° chung cho mọi drone; mặt nước phẳng; bỏ qua roll.
- Nhiều đoạn chỉ 1–5 track.

## Tái lập

```bash
.venv/bin/python tools/eval_georef_pitch.py --root data/processed/sds_mot --output runs/georef_pitch
```
