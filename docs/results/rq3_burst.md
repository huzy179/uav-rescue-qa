# RQ3d mô phỏng: mất gói theo cụm so với mất rải rác

**Mô phỏng.** `rq3_network.md` giả định mỗi lần gửi mất độc lập với nhau. Mạng thật thường mất theo cụm: sóng yếu kéo dài vài giây tới vài chục giây (drone bay sau vật cản, xa trạm). Câu hỏi: **cùng tỉ lệ mất trung bình**, mất theo cụm làm cảnh báo tới trạm trễ hơn bao nhiêu, có làm mất cảnh báo không, và thăm dò đường truyền (quyết định #17, bật mặc định) còn đủ không.

## Cách làm

- Mất theo cụm (`sim/netem.py`, `GilbertElliott`; `edge/main.py --net-burst BAD_S GOOD_S`): đường truyền đổi qua lại giữa trạng thái tốt và xấu; thời gian ở mỗi trạng thái theo phân phối mũ với trung bình BAD_S, GOOD_S; bắt đầu ở trạng thái tốt. Trạng thái xấu mất mọi gói (`--net-burst-loss 1`). Tỉ lệ thời gian xấu trung bình BAD/(BAD + GOOD). Các mốc đổi trạng thái chỉ phụ thuộc seed; không bật thì chuỗi sự kiện mạng giống hệt trước (test `tests/test_alerts.py`), nên kết quả của `rq3_network.md` không đổi.
- So cặp **cùng tỉ lệ mất trung bình**: mất rải rác 0,2 với cụm xấu 5 s / tốt 20 s và cụm dài 15 s / 60 s; mất rải rác 0,5 với 10 s / 10 s và 30 s / 30 s. Thêm các ô có cả hai loại mất.
- Kịch bản như `rq3_network.md` nhưng chuyến **120 s** (thay 60 s) và **5 seed** (thay 3), vì cụm dài 30–60 s mà chuyến ngắn thì mỗi seed chỉ gặp một hai cụm. Vì vậy số ở đây không so thẳng với bảng của `rq3_network.md`.
- 10 người, 2 khung/giây, detector giả recall 0,7, xác nhận geo N = 3; gửi bù tối đa 60 s sau khung cuối. Thăm dò mỗi 2 s hoặc tắt (`--link-probe-s 0`).
- Lưới: mất rải rác {0; 0,2; 0,5} × cụm {không, 5/20, 15/60, 10/10, 30/30} × thăm dò {tắt, 2 s}. Cấu hình `configs/experiments/rq3_burst.yaml`, kết quả `runs/rq3/burst/summary.csv` (trung bình 5 seed; "±" là độ lệch chuẩn qua seed). Chạy ở commit `024869e`, `dirty: true` vì `sim/netem.py` và `edge/main.py` lúc đó chưa commit (commit ngay sau, cùng nội dung).

## Kết quả

| Mất rải rác | Cụm xấu / tốt (s) | Thăm dò | Độ trễ trung vị (s) | Độ trễ lớn nhất (s) | Mất cảnh báo | KB mỗi cảnh báo |
|---|---|---|---|---|---|---|
| **Tỉ lệ mất trung bình 0,2** | | | | | | |
| 0,2 | không | không | 0,000 | 2,200 ± 1,754 | 0,000 | 3,126 |
| 0,2 | không | có | 0,000 | 2,000 ± 1,500 | 0,000 | 3,126 |
| 0 | 5 / 20 | không | 0,600 | 6,800 ± 6,695 | 0,000 | 2,669 |
| 0 | 5 / 20 | có | 0,500 | 4,500 ± 3,518 | 0,000 | 2,692 |
| 0 | 15 / 60 | không | 7,250 | 21,800 ± 29,096 | 0,000 | 2,796 |
| 0 | 15 / 60 | có | 4,500 | 16,200 ± 20,017 | 0,000 | 2,893 |
| **Tỉ lệ mất trung bình 0,5** | | | | | | |
| 0,5 | không | không | 0,600 | 13,300 ± 6,458 | 0,000 | 4,500 |
| 0,5 | không | có | 0,850 | 8,400 ± 3,525 | 0,000 | 4,119 |
| 0 | 10 / 10 | không | 6,050 | 33,900 ± 25,713 | 0,000 | 3,027 |
| 0 | 10 / 10 | có | 4,350 | 15,800 ± 8,379 | 0,000 | 3,200 |
| 0 | 30 / 30 | không | 21,100 | 63,500 ± 74,636 | 0,080 | 3,026 |
| 0 | 30 / 30 | có | 19,900 | 44,400 ± 34,028 | 0,000 | 3,590 |
| **Cả hai loại mất** | | | | | | |
| 0,2 | 30 / 30 | không | 14,800 | 57,200 ± 50,438 | 0,140 | 3,341 |
| 0,2 | 30 / 30 | có | 20,600 | 44,300 ± 34,219 | 0,000 | 3,950 |
| 0,5 | 10 / 10 | không | 9,150 | 83,300 ± 51,183 | 0,060 | 5,171 |
| 0,5 | 10 / 10 | có | 6,550 | 24,900 ± 6,199 | 0,000 | 5,548 |
| 0,5 | 30 / 30 | không | 25,750 | 62,600 ± 43,462 | 0,180 | 4,504 |
| 0,5 | 30 / 30 | có | 22,200 | 45,000 ± 33,296 | 0,000 | 5,769 |

Các ô còn lại của lưới (ví dụ mất rải rác 0,2 với cụm 5/20) ở `summary.csv`; không ô nào có thăm dò mà mất cảnh báo.

## Nhận xét

1. **Cùng tỉ lệ mất trung bình, mất theo cụm làm cảnh báo trễ hơn hẳn mất rải rác**, và cụm càng dài càng trễ. Có thăm dò, tỉ lệ 0,5: độ trễ trung vị 0,850 s khi mất rải rác, 4,350 s với cụm 10 s, 19,900 s với cụm 30 s; độ trễ lớn nhất 8,400 s, 15,800 s, 44,400 s. Mất rải rác thì lần gửi lại kế tiếp thường thành công; mất theo cụm thì mọi lần gửi trong cụm đều hỏng, cảnh báo phải chờ hết cụm. Vì vậy kết luận của `rq3_network.md` (độ trễ lớn nhất 8,333 s khi mất một nửa gói) là lạc quan so với sóng yếu kéo dài.
2. **Thăm dò vẫn giữ được không mất cảnh báo nào ở mọi ô**, kể cả cụm 30 s cộng mất rải rác 0,5. Không thăm dò thì các ô cụm 30 s mất 0,080–0,180 số cảnh báo (các ô khác có cụm: tới 0,060): thời gian chờ tăng gấp đôi, trần 30 s, cộng với cụm dài, đẩy lần gửi kế tiếp quá hạn gửi bù 60 s sau khung cuối.
3. **Thăm dò giúp nhiều hơn khi mất theo cụm**: cụm 10/10 không mất rải rác, độ trễ lớn nhất 33,900 → 15,800 s; thêm mất rải rác 0,5 thì 83,300 → 24,900 s. Lý do: sau một cụm dài, thời gian chờ đã lên tới trần; thăm dò phát hiện sóng có lại sau tối đa 2 s thay vì chờ hết lượt.
4. **Phần trễ còn lại khi đã thăm dò là chính độ dài cụm**: cảnh báo tạo trong cụm xấu không thể tới trạm trước khi cụm hết. Không có cách gửi lại nào rút ngắn được phần này; chỉ có đổi đường truyền (bay về gần trạm, trạm chuyển tiếp, liên lạc vệ tinh) mới giảm được. Đây là giới hạn cần nói khi trả lời "mạng yếu thì sao".
5. Dữ liệu gửi thêm vẫn nhỏ: cao nhất 5,769 KB mỗi cảnh báo (mất rải rác 0,5 với cụm 30 s, có thăm dò).

## Giới hạn

- Cụm xấu mất mọi gói, thời gian mỗi trạng thái theo phân phối mũ; không có số đo mạng thật (4G, Wi-Fi tầm xa, radio của drone) để chọn tham số. Hai cặp độ dài cụm (ngắn, dài) chỉ để thấy xu hướng.
- 5 seed, chuyến 120 s, khoảng 10 cảnh báo mỗi kịch bản: với cụm 30 s, số cụm thực tế mỗi seed khác nhau nhiều, nên độ lệch chuẩn của độ trễ lớn nhất lớn (tới 74,636 s). Tỉ lệ thời gian xấu thực tế của từng seed chưa được ghi vào log.
- Như `rq3_network.md`: không mô phỏng độ trễ truyền, băng thông; trạm luôn sẵn sàng.

## Tái lập

```bash
.venv/bin/python -m sim.sweep_rq3 --config configs/experiments/rq3_burst.yaml --jobs 12
```
