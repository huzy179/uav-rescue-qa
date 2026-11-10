#!/usr/bin/env bash
# Demo bảo vệ: trạm mặt đất + pipeline UAV phát lại theo thời gian thực, thời gian xử lý của một thiết bị biên giả lập.
# Không cần GPU khi trình bày: phát hiện đã tính trước (chuan-bi), lúc demo chỉ phát lại (--replay).
#
#   scripts/demo_bao_ve.sh chuan-bi sds_v21_goc            # một lần, có GPU: chạy E2c trên mọi khung, lưu phát hiện
#   scripts/demo_bao_ve.sh chay sds_v21_goc orin_nano_super # demo: mở màn hình điều phối (video, drone, bản đồ) trên trình duyệt
#   scripts/demo_bao_ve.sh chay sds_v21_goc orin_nano_super 20 30   # thêm mất sóng từ giây 20 tới 30
#   scripts/demo_bao_ve.sh so-sanh sds_v21_goc agx_orin_64gb orin_nano_super   # video hai thiết bị cạnh nhau
#   scripts/demo_bao_ve.sh chuan-bi hotay_quet && scripts/demo_bao_ve.sh chay hotay_quet orin_nano_super 60 80
#                                                           # chuyến bay mô phỏng quét vùng (ảnh tổng hợp), mất sóng giây 60–80
#   scripts/demo_bao_ve.sh kiem-tra                         # trước hôm bảo vệ: soát đủ dữ liệu, video, ô bản đồ, cổng
#
# Kịch bản: configs/demo/<tên>.yaml. Thiết bị: configs/devices/<tên>.yaml (ước lượng, không phải số đo; xem
# TECHNICAL mục 14.6). Ô bản đồ đã xem khi diễn tập được giữ ở runs/ground/tiles, nên vẫn hiện khi mất mạng.
set -euo pipefail
cd "$(dirname "$0")/.."

PY=.venv/bin/python
CMD="${1:?Cần lệnh: chuan-bi, chay, so-sanh hoặc kiem-tra}"

if [ "$CMD" = kiem-tra ]; then
  # Soát mọi thứ demo cần (DEMO_BAO_VE.md, mục Chuẩn bị); in OK hoặc THIẾU từng mục, thoát 1 nếu thiếu mục bắt buộc.
  fail=0
  check() {  # check <bắt buộc 1/0> <mô tả> <lệnh kiểm tra...>
    local must=$1 what=$2; shift 2
    if "$@" >/dev/null 2>&1; then echo "  OK     $what"
    elif [ "$must" = 1 ]; then echo "  THIẾU  $what"; fail=1
    else echo "  (chưa) $what"; fi
  }
  nonempty_dir() { [ -n "$(find "$1" -type f 2>/dev/null | head -n 1)" ]; }
  port_free() { $PY -c "import socket,sys; s=socket.socket(); s.bind((\"127.0.0.1\", int(sys.argv[1])))" "$1"; }
  echo "Dữ liệu phát lại (chuan-bi):"
  for n in sds_v21_goc sds_v21_px10 hotay_quet; do
    check 1 "$n: phát hiện" test -s "runs/edge/demo_cache/$n/detections.jsonl"
    check 1 "$n: lớp đáp án" test -s "runs/edge/demo_cache/$n/truth_layer.json"
  done
  echo "Hồ sơ thiết bị:"
  for d in agx_orin_64gb orin_nano_super; do check 1 "$d đã hiệu chỉnh" grep -q '^calibrated: *true' "configs/devices/$d.yaml"; done
  echo "Video cho slide và dự phòng:"
  check 1 "so sánh AGX Orin và Orin Nano Super" test -s runs/edge/demo_bao_ve/so_sanh_sds_v21_goc_agx_orin_64gb_orin_nano_super/so_sanh.mp4
  check 1 "so sánh Orin Nano Super, khung gốc và thu nhỏ" test -s runs/edge/demo_bao_ve/so_sanh_nano_goc_px10.mp4
  check 0 "quay màn hình toàn bộ demo (runs/edge/demo_bao_ve/du_phong.mp4)" test -s runs/edge/demo_bao_ve/du_phong.mp4
  echo "Ảnh tập lũ (sau khi khoá, tools/demo_panels.py):"
  check 0 "tập test lũ đã khoá" test -f data/processed/flood/MANIFEST.sha256
  check 0 "ảnh so sánh trên tập lũ" test -s runs/demo/flood_panels/picks.csv
  echo "Chạy không cần mạng:"
  check 1 "ô bản đồ đã lưu (diễn tập một lần có mạng)" nonempty_dir runs/ground/tiles
  check 1 "Leaflet đóng gói sẵn" test -s ground/static/leaflet/leaflet.js
  check 1 "thư viện trạm mặt đất" $PY -c "import uvicorn, fastapi"
  echo "Cổng trống:"
  check 1 "8000 (trạm mặt đất)" port_free 8000
  check 1 "8001 (video trực tiếp)" port_free 8001
  [ $fail = 0 ] && echo "Đủ để demo." || echo "Còn thiếu mục bắt buộc ở trên."
  exit $fail
fi
NAME="${2:?Cần tên kịch bản trong configs/demo/}"
CFG="configs/demo/$NAME.yaml"
CACHE="runs/edge/demo_cache/$NAME"
[ -f "$CFG" ] || { echo "Không có $CFG"; exit 1; }
profile() { local p="configs/devices/$1.yaml"; [ -f "$p" ] || { echo "Không có $p" >&2; exit 1; }; echo "$p"; }
need_cache() { [ -f "$CACHE/detections.jsonl" ] || { echo "Chưa có $CACHE/detections.jsonl: chạy 'chuan-bi $NAME' trước"; exit 1; }; }
title() { sed -n 's/^name: *//p' "$1"; }

case "$CMD" in
  chuan-bi)
    SCENARIO="configs/demo/${NAME}_scenario.yaml"
    if [ -f "$SCENARIO" ]; then
      # Chuyến bay mô phỏng: sinh ảnh tổng hợp, telemetry và phát hiện giả vào cache; không cần GPU.
      $PY -m sim.make_rq3 --config "$SCENARIO" --output "$CACHE"
      $PY tools/make_truth_layer.py --rq3 "$CACHE/ground_truth.json" --output "$CACHE/truth_layer.json"
      exit 0
    fi
    # Phát hiện cho mọi khung nguồn (--fps bằng fps nguồn, bỏ --min-views), để lúc phát lại thiết bị nào chọn khung
    # nào cũng có sẵn. Bước này cần mô hình và GPU.
    SRC_FPS=$(sed -n 's/^source_fps: *//p' "$CFG")
    $PY -m edge.main --config "$CFG" --fps "${SRC_FPS:-30}" --min-views 0 --output "$CACHE" --drain-s 0
    # Lớp đáp án từ nhãn SeaDronesSee của cùng đoạn (thư mục chứa telemetry trong cấu hình), cho nút "Đối chiếu đáp án".
    SEQ=$(dirname "$(sed -n 's/^telemetry: *//p' "$CFG")")
    [ -f "$SEQ/truth.json" ] && $PY tools/make_truth_layer.py --sds "$SEQ" --config "$CFG" --output "$CACHE/truth_layer.json"
    ;;
  chay)
    need_cache
    DEV=$(profile "${3:-orin_nano_super}")
    OUTAGE=()
    [ $# -ge 5 ] && OUTAGE=(--net-outage "$4" "$5")
    PORT=8000
    mkdir -p runs/ground
    rm -f runs/ground/demo.sqlite*   # mỗi lần demo bắt đầu với bản đồ trống
    FLOODEYE_GROUND_DB=runs/ground/demo.sqlite FLOODEYE_TILE_CACHE=runs/ground/tiles \
      $PY -m uvicorn --factory ground.app:default_app --port "$PORT" --log-level warning &
    GROUND_PID=$!
    trap 'kill $GROUND_PID 2>/dev/null' EXIT
    for _ in $(seq 1 40); do curl -s -o /dev/null "http://localhost:$PORT/" && break; sleep 0.25; done
    # Nạp lớp đáp án nếu có: nút "Đối chiếu đáp án" trên bản đồ (tắt sẵn, bấm để hiện người thật, bỏ sót, báo nhầm).
    if [ -f "$CACHE/truth_layer.json" ]; then
      curl -s -X POST -H "Content-Type: application/json" --data @"$CACHE/truth_layer.json" "http://localhost:$PORT/api/truth" > /dev/null
    fi
    LIVE=8001
    echo "Màn hình điều phối: http://localhost:$PORT/?video=http://localhost:$LIVE/"
    echo "(mở trên trình duyệt, rồi bấm Enter để bắt đầu chuyến bay)"
    read -r _
    # Drone gửi trạng thái mỗi giây (vị trí, vùng camera nhìn, cảnh báo đang chờ) qua cùng giả lập mất sóng; video đã vẽ
    # phát ở cổng $LIVE để trang điều phối nhúng (drone thật không gửi video).
    $PY -m edge.main --config "$CFG" --replay "$CACHE/detections.jsonl" --device-profile "$DEV" --realtime \
        --ground-url "http://localhost:$PORT" --state-every-s 1 --live-port "$LIVE" \
        --output "runs/edge/demo_bao_ve/$NAME" --save-video --drain-s 15 "${OUTAGE[@]}"
    echo "Xong chuyến bay. Trạm mặt đất vẫn chạy để xem bản đồ; Ctrl+C để tắt."
    wait $GROUND_PID
    ;;
  so-sanh)
    need_cache
    A=$(profile "${3:?Cần thiết bị bên trái}"); B=$(profile "${4:?Cần thiết bị bên phải}")
    OUT="runs/edge/demo_bao_ve/so_sanh_${NAME}_$3_$4"
    for side in "$3:$A" "$4:$B"; do
      $PY -m edge.main --config "$CFG" --replay "$CACHE/detections.jsonl" --device-profile "${side#*:}" \
          --output "$OUT/${side%%:*}" --save-video --drain-s 15
    done
    $PY scripts/ghep_video.py --left "$OUT/$3/annotated.mp4" --right "$OUT/$4/annotated.mp4" \
        --left-title "$(title "$A")" --right-title "$(title "$B")" --output "$OUT/so_sanh.mp4"
    ;;
  *)
    echo "Lệnh phải là chuan-bi, chay hoặc so-sanh, nhận được: $CMD"; exit 1 ;;
esac
