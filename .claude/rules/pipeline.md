---
paths:
  - "edge/**"
  - "ground/**"
  - "sim/**"
  - "shared/**"
---

# Pipeline UAV và trạm mặt đất

Thiết kế chi tiết ở mục 3 của `docs/ROADMAP.md` và mục 7 trở đi của `docs/TECHNICAL.md`. Các ràng buộc dưới đây không được phá:

- **Ultralytics chỉ được import trong `edge/detector.py`.** Mọi khối khác nhận `Detection` từ `shared/schema.py`, nhờ đó test chạy bằng `FakeDetector` mà không cần mô hình.
- **Không gọi `time.time()` hay `datetime.now()` trong pipeline.** Thời gian lấy từ dấu thời gian của khung hình (`frame_time`); bộ giả lập mạng cũng chạy theo đồng hồ này với seed cố định, để một lần chạy RQ3 cho cùng kết quả khi chạy lại. Thời gian xử lý thật đo riêng bằng `perf_counter` và chỉ ghi vào log.
- **Mỗi khối là một `Protocol` có bản giả** (`Detector`, `TelemetrySource`, `Transport`). `edge/main.py` chỉ nối các khối, không chứa logic.
- **Mỗi chặng ghi log JSONL; chỉ số tính sau từ log** bằng script trong `eval/`. Không tính chỉ số ngay trong pipeline.
- **`georef` là hàm thuần và có hàm ngược.** Thêm hay sửa phép chiếu thì phải có test đi một vòng pixel → GPS → pixel.
- **Cảnh báo gửi qua outbox SQLite**: `coords` trước, `crop` sau, cùng `alert_id`. Trạm mặt đất bỏ qua `alert_id` đã có, nên gửi lại không sinh cảnh báo trùng.
- **`ground/` không được import torch, ultralytics hay opencv.** `shared/` chỉ dùng pydantic và PyYAML, vì cả hai phía đều cài nó.
- **Cấu hình mới đọc bằng Pydantic**, để sai tên khoá hay sai kiểu bị báo ngay lúc khởi động.
