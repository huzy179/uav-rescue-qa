# FloodEye

Đồ án: phát hiện người kích thước nhỏ từ ảnh UAV trong vùng ngập lụt, chạy trên thiết bị biên (Jetson). Mô hình nền YOLO26 (`ultralytics`). Một người làm, bảo vệ 15/12/2026.

Đọc trước khi làm việc lớn:

- [docs/ROADMAP.md](docs/ROADMAP.md): lịch theo tuần, cấu trúc mã đích, kế hoạch thí nghiệm E0–E6 và RQ1–RQ3, thứ tự cắt việc khi trễ.
- [docs/TECHNICAL.md](docs/TECHNICAL.md): giải thích kỹ thuật. Mỗi mục gắn nhãn `[Đã có]` hoặc `[Thiết kế]`; khi cài xong một phần thì đổi nhãn của mục đó.
- [README.md](README.md): cài đặt, dữ liệu, lệnh chạy, định dạng file kết quả.

## Lệnh

```bash
.venv/bin/pytest                      # nhanh, không cần mô hình hay dữ liệu
.venv/bin/python scripts/run_baseline.py --config configs/experiments/E0_visdrone.yaml
.venv/bin/python eval/eval_by_size.py --help
```

Luôn dùng `.venv/bin/python`, chạy từ thư mục gốc của dự án. Chạy cả một thí nghiệm thì dùng skill `/run-experiment`.

## Quy ước

- Docstring, chú thích, thông báo lỗi và tài liệu viết bằng tiếng Việt. Số thập phân trong tài liệu dùng dấu phẩy (0,497).
- Module có mã (không tính `__init__.py` rỗng) mở đầu bằng `from __future__ import annotations` và có type hint.
- Script dòng lệnh dùng `argparse` cùng `shared.config.parse_args_with_config`: khoá YAML trùng tên tham số, tham số gõ tay được ưu tiên.
- Phụ thuộc ghim đúng phiên bản trong `pyproject.toml`, chia theo nhóm `edge`, `ground`, `dev`. Nhóm `edge` phải cài được trên Jetson; nhóm `ground` không có torch. Hỏi trước khi thêm thư viện mới.
- `tests/` không được cần mô hình, GPU hay thư mục `data/`.

## Không được làm

- Không đưa `data/`, `runs/`, trọng số (`*.pt`, `*.onnx`, `*.engine`) lên git.
- Không ghi số liệu vào tài liệu nếu số đó không đọc được từ một file trong `runs/`. Không làm tròn hay ước lượng thay cho số đo.
- Không sửa nhãn hay thành phần tập test lũ sau khi đã khoá (dự kiến 4/11/2026).
- Không coi thời gian đo trên Mac (MPS) là số liệu cho Jetson; chỉ dùng để so sánh tương đối.
