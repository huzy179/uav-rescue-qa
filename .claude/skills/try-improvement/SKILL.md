---
name: try-improvement
description: Thử một cải tiến trong docs/CAI_TIEN.md của FloodEye từ đầu tới cuối - cài thành tuỳ chọn mặc định tắt, viết test, đo (mô phỏng và/hoặc dữ liệu có nhãn, không dùng tập lũ), ghi docs/results, cập nhật CAI_TIEN, TECHNICAL, TONG_QUAN, ROADMAP, chương 5, và đề xuất bật hay bỏ. Dùng khi người dùng nói "làm mục 3.4 của CAI_TIEN", "thử ngưỡng theo cỡ", "code tính năng tiếp theo", "cải thiện điểm yếu X".
argument-hint: <mục hoặc tên cải tiến trong CAI_TIEN.md>
---

# Thử một cải tiến

Tham số: `$ARGUMENTS`. Không có thì đọc `docs/CAI_TIEN.md`, đề xuất một mục còn "Đề xuất" (ưu tiên không cần GPU, liên quan câu hỏi hội đồng dễ hỏi) và chờ người dùng đồng ý.

Quy ước đo ở `.claude/rules/experiments.md`, ràng buộc kiến trúc ở `.claude/rules/pipeline.md`. Không bao giờ dùng tập test lũ để thử hay chọn tham số.

## 1. Đặt câu hỏi và cách đo trước khi viết mã

- Ghi ra: điểm yếu đo được ở file nào trong `docs/results/`, giả thuyết, chỉ số quyết định, mốc so sánh, tham số nào cố định trước (ngưỡng, bán kính, lưới). Tham số chọn trên tập nào (val), kiểm chứng trên tập nào.
- Có cả mô phỏng và dữ liệu thật (SeaDronesSee v21, v5, v13; VisDrone val/test-dev) thì đo cả hai. Mô phỏng hay bỏ qua đúng hiện tượng quyết định kết quả (ví dụ một người tách thành nhiều cụm khi GPS trôi, `rq3_group.md`); kết quả mô phỏng một mình chưa đủ để bật mặc định.

## 2. Cài đặt

- Thêm thành **tuỳ chọn, mặc định tắt** (cờ dòng lệnh trong `edge/main.py` hoặc script tương ứng, khoá cấu hình Pydantic nếu cần). Không bật thì kết quả cũ phải giống hệt: bộ sinh số ngẫu nhiên mới tách riêng, không chen vào chuỗi cũ.
- Đúng ràng buộc của `.claude/rules/pipeline.md`; chỉ số tính sau từ log bằng script trong `eval/`, không tính trong pipeline.
- Test trong `tests/` không cần mô hình, GPU, `data/` hay `runs/`: một test cho hành vi mới, một test "tắt thì như cũ". Chạy `.venv/bin/pytest`.
- Cần quét mô phỏng: tạo `configs/experiments/rq3_<tên>.yaml` (dòng chú thích đầu file mô tả câu hỏi), thêm chỉ số mới vào `METRICS` của `sim/sweep_rq3.py` nếu có.

## 3. Đo

- Mô phỏng: `.venv/bin/python -m sim.sweep_rq3 --config configs/experiments/rq3_<tên>.yaml --jobs 12` (chạy nền nếu lâu). Ít nhất 3 seed; hiện tượng dao động mạnh (mất theo cụm) thì 5.
- Dữ liệu có nhãn: dùng lại `boxes.csv` hoặc `detections.jsonl` đã có khi được (phát lại bằng `--replay`), so cặp bằng `eval/compare_runs.py` hoặc bootstrap cặp trong script `eval/` mới.
- Đọc `run_config.json`: nếu `dirty: true` (mã chưa commit lúc chạy) thì ghi rõ trong file kết quả và commit ngay sau.

## 4. Ghi kết quả

- `docs/results/<tên>.md` theo bố cục `visdrone_baseline.md`: câu hỏi, cách làm, bảng, nhận xét, giới hạn, tái lập. Nhãn **Mô phỏng** hoặc **Sơ bộ** ngay đầu file nếu đúng. Số chép từ CSV, không tự trừ hay chia; tỉ lệ cần thì để script tính.
- Kết quả âm ghi như kết quả dương, tiêu đề nói rõ "kết quả âm".
- Cập nhật cùng lúc:
  - `docs/CAI_TIEN.md`: mục đó thành "Đã làm, tuỳ chọn", "Đã làm" hoặc "Đã thử, bỏ", kèm số chính và file; thêm dòng "Đề xuất" tiếp theo nếu có.
  - `docs/TECHNICAL.md`: đoạn **[Đã có]** hoặc **[Đã có, tuỳ chọn]** ở mục liên quan, bảng file nếu có script mới.
  - `docs/TONG_QUAN.md` mục 8, `docs/ROADMAP.md` (khối "Cập nhật <ngày>"), `docs/DAN_Y_LUAN_VAN.md` (cột kết quả), `docs/luan_van/chuong5.md` (một đoạn ở câu hỏi con tương ứng, giữ nhãn mô phỏng).
  - Thuật ngữ mới thì thêm vào `docs/THUAT_NGU.md`.
  - File kết quả cũ mà kết luận đổi thì thêm một dòng trỏ sang file mới, không sửa số cũ.
- Tính năng nhìn thấy được trong demo thì thêm vào sân thử (`console/sandbox.py`, `sandbox.js`, câu hỏi dựng sẵn) và sửa số câu hỏi dựng sẵn ở README, TECHNICAL 11.4.

## 5. Đề xuất bật hay bỏ

- Đổi mặc định của cấu hình cuối (`configs/edge.yaml`, `configs/demo/`) là một quyết định: thêm một dòng vào mục 6 của ROADMAP với số liệu và đề xuất, hỏi người dùng trước khi đổi.
- Commit theo từng bước (mã + test, rồi kết quả + tài liệu), message tiếng Việt; push khi người dùng đã cho phép trong phiên.
- Báo lại người dùng: một bảng số chính, kết luận, quyết định cần họ chốt.
