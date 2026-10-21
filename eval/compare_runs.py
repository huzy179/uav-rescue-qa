"""So sánh hai lần chạy trên cùng tập ảnh bằng bootstrap cặp: hiệu số B − A của AP và recall theo nhóm kích thước.

Dùng khi cần nói "B tốt hơn A" có ý nghĩa thống kê, thay cho việc nhìn hai khoảng tin cậy riêng có chồng nhau không.

Ví dụ:
    .venv/bin/python eval/compare_runs.py --a runs/visdrone/E4 --b runs/visdrone/E4tiled \\
        --images data/processed/visdrone/images/val --labels data/processed/visdrone/labels/val \\
        --ignore data/processed/visdrone/ignore/val --output runs/visdrone/compare_E4_E4tiled
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from eval.eval_by_size import evaluate_config, image_clusters, load_ground_truth
from eval.metrics import average_precision, operating_point, paired_bootstrap
from shared.provenance import write_run_config


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--a", type=Path, required=True, help="Thư mục kết quả mốc (có boxes.csv, per_image.csv)")
    parser.add_argument("--b", type=Path, required=True, help="Thư mục kết quả cần so với mốc")
    parser.add_argument("--images", type=Path, required=True, help="Thư mục ảnh gốc")
    parser.add_argument("--labels", type=Path, required=True, help="Thư mục nhãn YOLO")
    parser.add_argument("--ignore", type=Path, default=None, help="Thư mục vùng bỏ qua dạng YOLO")
    parser.add_argument("--gt-classes", type=int, nargs="+", default=[0], help="Các mã lớp trong nhãn được coi là người")
    parser.add_argument("--iou", type=float, default=0.5, help="Ngưỡng IoU")
    parser.add_argument("--conf", type=float, default=0.25, help="Ngưỡng conf của recall vận hành")
    parser.add_argument("--bootstrap", type=int, default=1000, help="Số lần bootstrap")
    parser.add_argument("--cluster-pattern", default=None, help="Regex lấy mã video từ tên ảnh để bootstrap theo video, ví dụ '^(\\d+)_' cho VisDrone")
    parser.add_argument("--output", type=Path, required=True, help="Thư mục kết quả")
    return parser.parse_args()


def load_run(run: Path) -> tuple[pd.DataFrame, list[str]]:
    """Đọc box và danh sách ảnh của một lần chạy; mỗi thư mục phải chỉ có một cấu hình (method, imgsz)."""
    boxes, images = pd.read_csv(run / "boxes.csv"), pd.read_csv(run / "per_image.csv")
    configs = images[["method", "imgsz"]].drop_duplicates()
    if len(configs) != 1:
        raise SystemExit(f"{run} có {len(configs)} cấu hình; compare_runs cần đúng một (chạy lại với một imgsz).")
    return boxes, sorted(images["image"])


def main() -> None:
    """Đánh giá hai lần chạy trên cùng nhãn, rồi tính hiệu số từng chỉ số bằng bootstrap cặp."""
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    boxes_a, images_a = load_run(args.a)
    boxes_b, images_b = load_run(args.b)
    if images_a != images_b:
        raise SystemExit(f"Hai lần chạy không trên cùng tập ảnh ({len(images_a)} và {len(images_b)} ảnh).")
    ground_truth = load_ground_truth(images_a, args.images, args.labels, args.gt_classes, args.ignore)
    results_a = evaluate_config(boxes_a, ground_truth, args.iou)
    results_b = evaluate_config(boxes_b, ground_truth, args.iou)
    clusters = image_clusters(list(ground_truth), args.cluster_pattern)
    metrics = {"AP": average_precision, "recall": lambda m: operating_point(m, args.conf)[0]}

    rows = []
    for size_label in results_a:
        for name, metric in metrics.items():
            d = paired_bootstrap(results_a[size_label], results_b[size_label], metric, args.bootstrap, clusters=clusters)
            rows.append(
                {
                    "size_bin": size_label, "metric": name, "A": round(d.a, 4), "B": round(d.b, 4),
                    "diff": round(d.diff, 4), "diff_lo": round(d.lo, 4), "diff_hi": round(d.hi, 4),
                    "p_value": round(d.p_value, 4), "significant": bool(d.lo > 0 or d.hi < 0),
                }
            )
    table = pd.DataFrame(rows)
    table.to_csv(args.output / "compare.csv", index=False)
    write_run_config(args.output, Path(__file__).name, None, None, vars(args))
    print(f"A = {args.a}\nB = {args.b}\nIoU ≥ {args.iou:g}; recall tại conf ≥ {args.conf:g}; diff = B − A, khoảng tin cậy 95% bootstrap cặp theo {'video' if args.cluster_pattern else 'ảnh'}.")
    print(table.to_string(index=False))
    print(f"\nKết quả lưu tại: {args.output}")


if __name__ == "__main__":
    main()
