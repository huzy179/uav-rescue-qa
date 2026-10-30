#!/usr/bin/env bash
# Đánh giá RQ1 trên tập test lũ, từ file XML xuất từ CVAT tới bảng kết quả, một lệnh.
#
#   scripts/eval_flood.sh exports/                   # thư mục chứa file xuất "CVAT for images 1.1" (.zip hoặc .xml), mỗi task một file
#   scripts/eval_flood.sh annotations.xml            # hoặc một file
#   scripts/eval_flood.sh exports/ E1 E2c            # chỉ những thí nghiệm này (mặc định: mọi configs/experiments/*_flood.yaml)
#
# Các bước: tools/convert_cvat.py -> dự đoán từng thí nghiệm (bỏ qua thí nghiệm chưa có trọng số hoặc đã có kết quả)
# -> eval_by_size.py ở IoU 0,5 và 0,3, có vùng bỏ qua, bootstrap theo video -> recall_by_tag.py.
# Không đọc nhãn để chọn gì cho mô hình; tập test đã khoá thì không sửa nhãn sau khi xem kết quả (CLAUDE.md).
set -euo pipefail
cd "$(dirname "$0")/.."

SRC="${1:?Cần thư mục hoặc file xuất từ CVAT}"
shift
if [ -d "$SRC" ]; then
  shopt -s nullglob; XMLS=("$SRC"/*.zip "$SRC"/*.xml); shopt -u nullglob
  [ ${#XMLS[@]} -gt 0 ] || { echo "Không có file .zip hay .xml trong $SRC"; exit 1; }
else
  XMLS=("$SRC")
fi
D=data/processed/flood
PY=.venv/bin/python
CLUSTER='^(.+)_\d+$'   # tên ảnh <video>_<khung>.jpg của tools/extract_frames.py

$PY tools/convert_cvat.py --xml "${XMLS[@]}" --images data/raw/flood/frames --dst "$D" --split test
cat "$D/stats_test.json"
# Tập đã khoá (LABELING mục 8): nhãn vừa chuyển phải trùng mã băm lúc khoá, kể cả không thêm bớt file.
if [ -f "$D/MANIFEST.sha256" ]; then
  (cd "$D" && sha256sum --check --quiet MANIFEST.sha256) || { echo "Tập test lũ khác lúc khoá (MANIFEST.sha256)"; exit 1; }
  (cd "$D" && diff <(find -L images/test labels/test ignore/test boxes_test.csv tags_test.csv -type f | sort) \
      <(awk '{print $2}' MANIFEST.sha256)) || { echo "Tập test lũ thêm hoặc bớt file so với lúc khoá"; exit 1; }
else
  echo "[cảnh báo] Chưa có $D/MANIFEST.sha256: tập test lũ chưa khoá (LABELING mục 8)"
fi

if [ $# -gt 0 ]; then names=("$@"); else names=(); for f in configs/experiments/*_flood.yaml; do b=$(basename "$f"); names+=("${b%_flood.yaml}"); done; fi
runs=()
for name in "${names[@]}"; do
  cfg="configs/experiments/${name}_flood.yaml"
  [ -f "$cfg" ] || { echo "Không có $cfg"; exit 1; }
  model=$(sed -n 's/^model: *//p' "$cfg"); out=$(sed -n 's/^output: *//p' "$cfg")
  if [[ "$model" == */* && ! -f "$model" ]]; then echo "[bỏ qua] $name: chưa có trọng số $model"; continue; fi
  if [ ! -f "$out/boxes.csv" ]; then
    if grep -q '^tile:' "$cfg"; then script=scripts/run_tiled.py; else script=scripts/run_baseline.py; fi
    echo "== $name ($script)"
    $PY "$script" --config "$cfg"
  fi
  runs+=("$out")
done
[ ${#runs[@]} -gt 0 ] || { echo "Không có thí nghiệm nào chạy được"; exit 1; }

# eval_by_size không gộp được hai lần chạy cùng phương pháp và imgsz, nên chấm từng lần chạy riêng.
for run in "${runs[@]}"; do
  for iou in 0.5 0.3; do
    $PY eval/eval_by_size.py --runs "$run" --images "$D/images/test" --labels "$D/labels/test" \
        --ignore "$D/ignore/test" --iou "$iou" --cluster-pattern "$CLUSTER" --output "runs/flood/eval_$(basename "$run")_iou$iou"
  done
done
$PY eval/recall_by_tag.py --runs "${runs[@]}" --annotations "$D" --split test --ignore "$D/ignore/test" \
    --cluster-pattern "$CLUSTER" --output runs/flood/eval_tags
echo "Xong. Bảng theo kích thước: runs/flood/eval_*_iou*/eval_by_size.csv; theo loại nhiễu: runs/flood/eval_tags/recall_by_tag.csv"
