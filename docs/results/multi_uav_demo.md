# Demo hai drone: gộp cảnh báo khác drone và xếp ưu tiên ở trạm mặt đất

**Minh hoạ, không phải thí nghiệm.** Hai "drone" phát lại cùng một đoạn video thật, nên chúng thấy đúng cùng những người ở đúng cùng chỗ trên ảnh; chỉ GPS khác nhau. Hai drone thật nhìn một người từ hai góc và hai thời điểm khác nhau. Mục đích là kiểm tra luồng nhiều drone của trạm mặt đất (`ground/incidents.py` khi cảnh báo đến từ drone khác, `ground/priority.py`), không phải đo độ chính xác gộp.

## Cách làm

- Đoạn SeaDronesSee-MOT `val-m100-DJI_0001-v21` (4K, telemetry thật, đoạn đông người nhất trong `sds_mot_confirm.md`: 19 người xuất hiện ở các khung được xử lý), E2c cắt ô, geo, N = 3, 2 khung/giây.
- `uav1`: telemetry gốc. `uav2`: cùng phát hiện của `uav1` (`--replay`), telemetry dời 3 m về phía Đông (`tools/shift_telemetry.py`), giả lập GPS của drone thứ hai lệch độc lập.
- Sai số vị trí trong cảnh báo tính bằng `edge.georef.position_error_m` với giá trị mặc định (GPS σ 3 m); trạm gộp cảnh báo cùng drone trong 5 m, khác drone trong `max(5, căn(e1² + e2²))` m.
- Lệnh: `scripts/demo_multi.sh` (mặc định đúng cấu hình trên). Số đọc từ `runs/ground/demo_multi.sqlite` và `runs/edge/demo_multi/uav*/alerts.jsonl`.

## Kết quả

| | Số |
|---|---|
| Cảnh báo `uav1` / `uav2` | 37 / 37 |
| Sai số vị trí trong cảnh báo | 3,09–3,68 m |
| Sự cố | 20 |
| Sự cố có cả hai drone | 18 (72 cảnh báo) |
| Sự cố chỉ một drone | 1 của `uav1`, 1 của `uav2` |

Một drone đơn lẻ trên đoạn này cho 19 sự cố ở bán kính 5 m (`runs/sds/incident_merge.csv`). Thêm drone thứ hai lệch GPS 3 m chỉ thêm 1 sự cố: hầu hết cảnh báo của drone thứ hai được gắn vào sự cố của drone thứ nhất (không có nhãn để kiểm từng cặp, xem Giới hạn). Hai sự cố còn tách là hai cảnh báo mà bán kính khác drone (căn tổng bình phương hai sai số) không phủ được khi cộng thêm phần lệch giữa hai lần cảnh báo của cùng người.

Bản đồ tô màu theo điểm ưu tiên; ở đoạn này các sự cố đứng đầu đều được cộng điểm "nhóm người" tối đa vì nhiều người bơi trong vài chục mét, và điểm "hai drone cùng thấy".

## Giới hạn

- Cùng khung hình cho cả hai drone: không có khác biệt góc nhìn, thời điểm, mô hình; lệch GPS cố định chứ không trôi.
- Không có nhãn người thật cho từng sự cố trong lần chạy này, nên không đếm gộp nhầm; chấm gộp nhầm theo nhãn ở `eval/incident_merge_eval.py` (một drone).
- Trọng số ưu tiên là lựa chọn thiết kế (TECHNICAL 12.4), chưa được kiểm chứng với người vận hành.
