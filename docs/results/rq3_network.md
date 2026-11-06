# RQ3d mô phỏng: mất gói, mất sóng và độ trễ cảnh báo

**Mô phỏng.** Câu hỏi: mất gói ngẫu nhiên và mất sóng hẳn một khoảng làm cảnh báo tới trạm mặt đất trễ bao lâu, có mất cảnh báo nào không, và thăm dò đường truyền (mới thêm) rút ngắn độ trễ tới đâu.

## Cách làm

- Kịch bản `sim/make_rq3.py`: 60 s, 10 người, 2 khung/giây, GPS σ 0,5 m; detector giả recall 0,7, 0,5 báo nhầm mỗi khung; xác nhận geo, N = 3; 3 seed. Mọi ô có cùng 10 cảnh báo mỗi kịch bản và không bỏ sót ai, nên chỉ phần gửi khác nhau.
- Mạng giả lập `sim/netem.py` bọc ngoài đường gửi: `--net-loss` là xác suất mất mỗi lần gửi; `--net-outage` là khoảng mất sóng hoàn toàn.
- Gửi cảnh báo (`edge/alerts.py`, TECHNICAL mục 10.2): gửi lại với thời gian chờ tăng gấp đôi sau mỗi lần hỏng (1, 2, 4… s), trần 30 s, nhiễu tới 20%. Sau khung cuối tiếp tục gửi bù tối đa 60 s.
- **Thăm dò đường truyền** (`--link-probe-s 2`, mới): khi mọi gói đang chờ tới lượt và đã 2 s không gửi gì, thử gửi gói toạ độ cũ nhất; gửi được (sóng đã có lại) thì gửi ngay mọi gói đang chờ. Lần thăm dò hỏng không đẩy lùi thêm thời gian chờ. Mặc định tắt, nên các kết quả cũ không đổi.
- Độ trễ gửi: từ lúc cảnh báo được tạo tới lúc trạm xác nhận đã nhận gói toạ độ. Mất cảnh báo: tỉ lệ cảnh báo không được xác nhận cả sau 60 s gửi bù.
- Lưới: mất gói {0; 0,2; 0,5} × mất sóng {không, 20–35 s, 15–45 s} × thăm dò {không, mỗi 2 s}. Cấu hình `configs/experiments/rq3_network.yaml`, kết quả `runs/rq3/network/summary.csv` (trung bình 3 seed; "±" là độ lệch chuẩn qua seed).

## Kết quả

| Mất gói | Mất sóng | Thăm dò | Độ trễ trung vị (s) | Độ trễ lớn nhất (s) | Mất cảnh báo | KB mỗi cảnh báo |
|---|---|---|---|---|---|---|
| 0,000 | không | không | 0,000 | 0,000 ± 0,000 | 0,000 | 2,465 |
| 0,000 | không | có | 0,000 | 0,000 ± 0,000 | 0,000 | 2,465 |
| 0,000 | 20–35 s | không | 0,000 | 10,000 ± 6,874 | 0,000 | 2,629 |
| 0,000 | 20–35 s | có | 0,000 | 7,667 ± 4,253 | 0,000 | 2,647 |
| 0,000 | 15–45 s | không | 8,667 | 36,500 ± 1,323 | 0,000 | 3,079 |
| 0,000 | 15–45 s | có | 5,917 | 27,500 ± 4,770 | 0,000 | 3,189 |
| 0,200 | không | không | 0,000 | 1,833 ± 2,021 | 0,000 | 2,948 |
| 0,200 | không | có | 0,000 | 1,667 ± 1,756 | 0,000 | 2,948 |
| 0,200 | 20–35 s | không | 0,417 | 16,000 ± 17,037 | 0,000 | 3,186 |
| 0,200 | 20–35 s | có | 0,667 | 7,667 ± 4,253 | 0,000 | 3,076 |
| 0,200 | 15–45 s | không | 9,083 | 37,000 ± 1,000 | 0,000 | 4,000 |
| 0,200 | 15–45 s | có | 6,583 | 27,833 ± 4,619 | 0,000 | 3,919 |
| 0,500 | không | không | 0,250 | 41,167 ± 26,629 | 0,000 | 4,346 |
| 0,500 | không | có | 1,167 | 8,333 ± 1,607 | 0,000 | 4,218 |
| 0,500 | 20–35 s | không | 3,000 | 48,000 ± 17,769 | 0,033 | 4,381 |
| 0,500 | 20–35 s | có | 3,417 | 17,333 ± 2,566 | 0,000 | 4,401 |
| 0,500 | 15–45 s | không | 10,583 | 60,500 ± 20,785 | 0,000 | 5,423 |
| 0,500 | 15–45 s | có | 9,000 | 29,167 ± 4,481 | 0,000 | 4,404 |

## Nhận xét

1. **Không mất cảnh báo nào khi có thăm dò**, kể cả mất một nửa số gói cộng 30 s mất sóng. Không thăm dò thì có một ô mất 0,033 (một cảnh báo trong 3 kịch bản không tới trạm sau 60 s gửi bù, mất gói 0,5 và mất sóng 20–35 s). Cảnh báo được ghi xuống đĩa trước khi gửi (`edge/alerts.py`), nên chỉ mất khi drone hết thời gian gửi bù.
2. **Độ trễ trung vị nhỏ, độ trễ lớn nhất mới là vấn đề.** Phần lớn cảnh báo tới ngay; cảnh báo sinh ra trong lúc mất sóng phải chờ. Với thời gian chờ tăng gấp đôi, trần 30 s, một gói hỏng ngay trước khi sóng có lại có thể đợi thêm gần 30 s: không thăm dò, mất sóng 15–45 s cho độ trễ lớn nhất 36,500 s; mất gói 0,5 không có mất sóng vẫn tới 41,167 s.
3. **Thăm dò cắt phần chờ thừa đó**: độ trễ lớn nhất còn 27,500 s (mất sóng 15–45 s), 8,333 s (mất gói 0,5) và 17,333 s (mất gói 0,5 với mất sóng 20–35 s), và độ lệch giữa các seed nhỏ hơn hẳn. Chi phí không đáng kể: số KB mỗi cảnh báo gần như không đổi (2,647 so với 2,629 khi mất sóng 20–35 s), vì mỗi lần thăm dò chỉ là một gói toạ độ vài trăm byte. Đề xuất bật mặc định cho demo và cấu hình cuối (cần chốt, ROADMAP quyết định #17).
4. Với mất sóng 15–45 s, phần trễ còn lại khi đã thăm dò chủ yếu là chính khoảng mất sóng: cảnh báo tạo trong lúc mất sóng không thể tới trạm trước giây 45, dù gửi lại thế nào.
5. Mất gói làm tăng dữ liệu gửi mỗi cảnh báo (2,465 KB khi mạng tốt lên 4,346–5,423 KB khi mất một nửa gói không thăm dò) vì gói và ảnh cắt phải gửi lại; vẫn rất nhỏ so với truyền video.

## Giới hạn

- Mất gói độc lập giữa các lần gửi; mạng thật mất theo cụm. Mất sóng là khoảng cố định, trạm luôn sẵn sàng.
- Mô phỏng đồng hồ: lượt gửi chạy theo khung đã xử lý (2 lần mỗi giây) và mỗi giây trong lúc gửi bù; không đo thời gian truyền thật hay băng thông.
- 3 seed, một chuyến 60 s với 10 cảnh báo mỗi kịch bản: độ trễ lớn nhất dao động mạnh giữa các seed (xem cột ±).

## Tái lập

```bash
.venv/bin/python -m sim.sweep_rq3 --config configs/experiments/rq3_network.yaml --jobs 8
```
