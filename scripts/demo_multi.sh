#!/usr/bin/env bash
# Demo nhiều drone: trạm mặt đất + hai UAV phát lại cùng một đoạn video thật có telemetry (SeaDronesSee-MOT), UAV thứ
# hai có GPS lệch thêm vài mét (tools/shift_telemetry.py). Trạm gộp cảnh báo của hai drone cho cùng một người thành một
# sự cố (bán kính theo sai số của cả hai, ground/incidents.py) và xếp ưu tiên (ground/priority.py).
#
#   scripts/demo_multi.sh                                        # đoạn v21, trọng số E2c, lệch 3 m Đông
#   scripts/demo_multi.sh data/processed/sds_mot/<đoạn> <trọng số> <lệch Đông (m)>
#
# Mở http://localhost:8000: chấm màu theo ưu tiên; bấm chấm để gắn thẻ "dưới nước", đóng sự cố. Ctrl+C để tắt.
# Chỉ để minh hoạ: hai drone thật nhìn cùng người từ hai góc khác nhau, không phải cùng một khung hình.
set -euo pipefail
cd "$(dirname "$0")/.."

SEQ="${1:-data/processed/sds_mot/val-m100-DJI_0001-v21}"
MODEL="${2:-runs/train/E2c_s0/weights/best.pt}"
EAST="${3:-3}"
PORT=8000
OUT=runs/edge/demo_multi
[ -d "$SEQ/frames" ] || { echo "Không thấy $SEQ/frames (tools/convert_seadronessee_mot.py)"; exit 1; }

mkdir -p runs/ground "$OUT"
rm -f runs/ground/demo_multi.sqlite*
FLOODEYE_GROUND_DB=runs/ground/demo_multi.sqlite .venv/bin/python -m uvicorn --factory ground.app:default_app \
    --port "$PORT" --log-level warning &
GROUND_PID=$!
trap 'kill $GROUND_PID 2>/dev/null' EXIT
for _ in $(seq 1 40); do curl -s -o /dev/null "http://localhost:$PORT/" && break; sleep 0.25; done
echo "Trạm mặt đất: http://localhost:$PORT  (mở trên trình duyệt ngay bây giờ)"

.venv/bin/python tools/shift_telemetry.py --src "$SEQ/telemetry.csv" --dst "$OUT/telemetry_uav2.csv" --east-m "$EAST"
COMMON=(--config configs/edge.yaml --source "$SEQ/frames" --source-fps 30 --drain-s 5 --ground-url "http://localhost:$PORT")
# UAV 1 chạy mô hình; UAV 2 dùng lại phát hiện của UAV 1 với telemetry lệch, nên không tốn GPU lần hai.
.venv/bin/python -m edge.main "${COMMON[@]}" --model "$MODEL" --telemetry "$SEQ/telemetry.csv" --uav-id uav1 \
    --output "$OUT/uav1"
.venv/bin/python -m edge.main "${COMMON[@]}" --replay "$OUT/uav1/detections.jsonl" --telemetry "$OUT/telemetry_uav2.csv" \
    --uav-id uav2 --output "$OUT/uav2"

curl -s "http://localhost:$PORT/api/incidents" | .venv/bin/python -c "
import json, sys
incs = json.load(sys.stdin)
both = sum(len(i['uav_ids']) > 1 for i in incs)
print(f'{len(incs)} sự cố, {sum(i[\"n_alerts\"] for i in incs)} cảnh báo; {both} sự cố có cả hai drone')"
echo "Trạm mặt đất vẫn chạy để xem bản đồ; Ctrl+C để tắt."
wait $GROUND_PID
