#!/usr/bin/env bash
# Demo trọn hệ thống: trạm mặt đất (bản đồ) + pipeline UAV chạy trên một video, telemetry giả lập.
#
#   scripts/demo.sh                                  # video mặc định, mô hình gốc yolo26s.pt
#   scripts/demo.sh video.mp4                        # video khác
#   scripts/demo.sh video.mp4 runs/train/E2_s0/weights/best.pt   # mô hình đã fine-tune
#
# Mở http://localhost:8000 để xem cảnh báo hiện lên bản đồ. Video có vẽ khung: <thư mục kết quả>/annotated.mp4.
# Ctrl+C để tắt trạm mặt đất sau khi xem xong.
set -euo pipefail
cd "$(dirname "$0")/.."

VIDEO="${1:-data/raw/demo/afo_demo.mp4}"
MODEL="${2:-yolo26s.pt}"
OUT="runs/edge/demo_$(basename "${VIDEO%.*}")_$(basename "${MODEL%.*}")"   # tên video + tên trọng số: các lần demo không ghi đè nhau
PORT=8000

[ -f "$VIDEO" ] || { echo "Không thấy video: $VIDEO"; exit 1; }
mkdir -p runs/ground
rm -f runs/ground/demo.sqlite*   # mỗi lần demo bắt đầu với bản đồ trống

FLOODEYE_GROUND_DB=runs/ground/demo.sqlite .venv/bin/python -m uvicorn --factory ground.app:default_app \
    --port "$PORT" --log-level warning &
GROUND_PID=$!
trap 'kill $GROUND_PID 2>/dev/null' EXIT
for _ in $(seq 1 40); do curl -s -o /dev/null "http://localhost:$PORT/" && break; sleep 0.25; done
echo "Trạm mặt đất: http://localhost:$PORT  (mở trên trình duyệt ngay bây giờ)"

.venv/bin/python -m edge.main --config configs/edge.yaml --source "$VIDEO" --model "$MODEL" \
    --output "$OUT" --ground-url "http://localhost:$PORT" --save-video --drain-s 5

echo "Video có vẽ khung: $OUT/annotated.mp4"
echo "Trạm mặt đất vẫn chạy để xem bản đồ; Ctrl+C để tắt."
wait $GROUND_PID
