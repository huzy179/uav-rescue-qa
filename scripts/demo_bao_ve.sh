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
#
# Kịch bản: configs/demo/<tên>.yaml. Thiết bị: configs/devices/<tên>.yaml (ước lượng, không phải số đo; xem
# TECHNICAL mục 14.6). Ô bản đồ đã xem khi diễn tập được giữ ở runs/ground/tiles, nên vẫn hiện khi mất mạng.
set -euo pipefail
cd "$(dirname "$0")/.."

PY=.venv/bin/python
CMD="${1:?Cần lệnh: chuan-bi, chay hoặc so-sanh}"
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
      exit 0
    fi
    # Phát hiện cho mọi khung nguồn (--fps bằng fps nguồn, bỏ --min-views), để lúc phát lại thiết bị nào chọn khung
    # nào cũng có sẵn. Bước này cần mô hình và GPU.
    SRC_FPS=$(sed -n 's/^source_fps: *//p' "$CFG")
    $PY -m edge.main --config "$CFG" --fps "${SRC_FPS:-30}" --min-views 0 --output "$CACHE" --drain-s 0
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
