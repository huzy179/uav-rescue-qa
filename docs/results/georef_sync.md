# Đồng bộ thời gian metadata gimbal và làm mượt góc: không sửa được định vị theo góc nghiêng

**Sơ bộ, kết quả âm.** Nối tiếp `georef_pitch.md`: chiếu theo góc gimbal kém hơn giả định nhìn thẳng xuống ở một số đoạn (trung vị độ tản 1,603 so với 1,336 m). Hai nguyên nhân có thể sửa không cần GPU (`docs/CAI_TIEN.md` mục 3.6): metadata ghi lệch thời gian so với khung ảnh, và góc gimbal dao động giữa các mẫu.

## Cách làm

- `edge/telemetry.py`: `ShiftedTelemetry` đọc telemetry ở t + độ trễ; `SmoothedAngles` lấy trung bình pitch và yaw (yaw theo vectơ đơn vị) trong cửa sổ quanh t, 9 điểm đều nhau.
- `tools/eval_georef_pitch.py` với lưới độ trễ {−1; −0,5; −0,3; −0,2; −0,1; 0; 0,1; 0,2; 0,3; 0,5; 1} s × cửa sổ làm mượt {0; 0,5; 1; 2} s; cùng thước đo độ tản, cùng 132 track như `georef_pitch.md` (tổng khớp: 1,336 và 1,603 m).
- **Chọn trên phần train, đọc trên phần val** của SeaDronesSee-MOT (82 và 50 track). Hai phần cắt từ cùng các video gốc của SeaDronesSee (ví dụ `train-m100-DJI_0001-v21` và `val-m100-DJI_0001-v21`), nên không độc lập hẳn.
- Số đọc từ `runs/georef_sync/grid.csv` (trung vị độ tản qua các track, m; tỉ lệ track có độ tản nhỏ hơn cách nhìn thẳng).

## Kết quả

| Phần | Cách chiếu | Trung vị độ tản (m) | Tỉ lệ track tốt hơn nhìn thẳng |
|---|---|---|---|
| train (82 track) | nhìn thẳng xuống | 1,146 | |
| | theo gimbal, không đồng bộ | 1,631 | 0,427 |
| | theo gimbal, ô tốt nhất trên train: trễ +0,3 s, làm mượt 2 s | 1,512 | 0,366 |
| val (50 track) | nhìn thẳng xuống | 1,441 | |
| | theo gimbal, không đồng bộ | 1,481 | 0,660 |
| | theo gimbal, trễ +0,3 s, làm mượt 2 s | 1,397 | 0,700 |

Trên phần train, độ tản theo gimbal nằm trong khoảng 1,512–1,984 m ở mọi ô của lưới, đều lớn hơn cách nhìn thẳng (1,146 m); không có độ trễ nào nổi lên rõ (các ô kề nhau chênh nhau ngang chênh lệch giữa độ trễ âm và dương).

## Nhận xét

1. **Không có độ trễ chung nào sửa được phép chiếu theo gimbal.** Ô tốt nhất trên train vẫn kém nhìn thẳng trên chính phần train; trên val nó nhỉnh hơn nhìn thẳng (1,397 so với 1,441 m) nhưng chênh lệch nhỏ hơn dao động giữa các ô kề nhau, không đủ để coi là cải thiện.
2. Bề mặt kết quả lởm chởm theo độ trễ cho thấy độ tản ở đây bị chi phối bởi vài đoạn và vài track, không bởi một độ lệch thời gian có hệ thống. Nguyên nhân kém hơn nhiều khả năng nằm ở chỗ khác: góc nhìn chung 82° cho ba loại camera khác nhau, quy ước góc gimbal của từng drone, và thước đo độ tản không thấy được lệch đều khi drone đứng yên (`georef_pitch.md`, nhận xét 2).
3. **Quyết định:** không thêm tham số đồng bộ hay làm mượt vào `edge/main.py`; phép chiếu theo góc nghiêng vẫn là tuỳ chọn (`--use-pitch`), demo quét vùng vẫn dùng chuyến bay mô phỏng. Hai lớp bọc giữ lại trong `edge/telemetry.py` cho lần thử với log bay thật.

## Giới hạn

- Thước đo gián tiếp (độ tản của người gần như đứng yên), không có vị trí thật của người.
- Một độ trễ chung cho mọi đoạn và mọi drone; chưa thử độ trễ riêng từng loại drone (ít track mỗi loại).
- Train và val cắt từ cùng các video gốc.

## Tái lập

```bash
.venv/bin/python tools/eval_georef_pitch.py --root data/processed/sds_mot --output runs/georef_sync \
    --lags-s -1 -0.5 -0.3 -0.2 -0.1 0 0.1 0.2 0.3 0.5 1 --smooth-s 0 0.5 1 2
```
