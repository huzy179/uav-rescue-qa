"""Bảng kết quả RQ2 để chép vào luận văn: tốc độ từng biến thể, số lần nhanh hơn PyTorch, hiệu độ chính xác theo cặp.

Đọc thư mục kết quả của scripts/run_rq2.py sau khi đã chạy scripts/after_rq2.py (bước so cặp):
- <rq2>/rq2_config.yaml: danh sách biến thể (run_rq2.py chép vào lúc chạy);
- <rq2>/timing.csv: thời gian từng chặng (eval/timing_summary.py);
- <rq2>/compare/<tập>/<B>__vs__<A>_iou<iou>/compare.csv: bootstrap cặp B − A (eval/compare_runs.py).

Ghi <rq2>/report/speed.csv (mỗi biến thể một dòng: số ô, thời gian suy luận và tổng theo p50, p95, FPS theo p95,
số lần nhanh hơn biến thể PyTorch cùng cách chạy) và <rq2>/report/accuracy_diff.csv (mỗi cặp × tập × IoU × nhóm cỡ:
hiệu AP và recall, khoảng tin cậy, có ý nghĩa hay không). In hai bảng Markdown, số thập phân dấu phẩy, để chép vào
docs/results/rq2_t4.md. Tỉ lệ tính ở đây để không phải tự chia tay rồi làm tròn (.claude/rules/experiments.md).

Các cặp so (comparison_pairs):
- nén: biến thể TensorRT so với PyTorch cùng cách chạy (toàn ảnh/cắt ô, cùng kích thước, cùng thu nhỏ theo độ cao);
- thu nhỏ theo độ cao: cắt ô có target_person_px so với cắt ô không thu nhỏ, cùng độ chính xác số;
- cắt ô: cắt ô không thu nhỏ so với toàn ảnh, cùng độ chính xác số.

Ví dụ:
    .venv/bin/python eval/rq2_report.py --rq2 runs/rq2
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import yaml

from shared.config import parse_args_with_config

KIND_QUANT = "nén"
KIND_ALT = "thu nhỏ theo độ cao"
KIND_TILE = "cắt ô so với toàn ảnh"
SIZE_BINS = ("all", "<8")


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rq2", type=Path, required=True, help="Thư mục kết quả của scripts/run_rq2.py")
    return parse_args_with_config(parser)


def _norm(v: dict[str, Any]) -> dict[str, Any]:
    """Biến thể với giá trị mặc định như Variant trong scripts/run_rq2.py."""
    return {"mode": "tiled", "imgsz": 1280, "tile": 640, "target_person_px": None, **v}


def _shape(v: dict[str, Any]) -> tuple[Any, ...]:
    """Cách chạy của một biến thể, không kể độ chính xác số."""
    return (v["mode"], v["imgsz"] if v["mode"] == "full" else v["tile"], v["target_person_px"])


def comparison_pairs(variants: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    """Các cặp (A mốc, B, loại so sánh) có đủ hai biến thể trong cấu hình."""
    vs = [_norm(v) for v in variants]
    pairs: list[tuple[str, str, str]] = []
    for b in vs:
        for a in vs:
            if a is b:
                continue
            same_precision = a["precision"] == b["precision"]
            if a["precision"] == "pt" and b["precision"] != "pt" and _shape(a) == _shape(b):
                pairs.append((a["name"], b["name"], KIND_QUANT))
            elif (same_precision and b["mode"] == a["mode"] == "tiled" and b["tile"] == a["tile"]
                  and b["target_person_px"] is not None and a["target_person_px"] is None):
                pairs.append((a["name"], b["name"], KIND_ALT))
            elif (same_precision and b["mode"] == "tiled" and b["target_person_px"] is None and a["mode"] == "full"):
                pairs.append((a["name"], b["name"], KIND_TILE))
    return pairs


def compare_dir(rq2: Path, dataset: str, a: str, b: str, iou: str) -> Path:
    """Thư mục kết quả bootstrap cặp B − A của một tập ở một ngưỡng IoU."""
    return rq2 / "compare" / dataset / f"{b}__vs__{a}_iou{iou}"


def read_csv(path: Path) -> list[dict[str, str]]:
    """Đọc CSV thành list dict; file không có thì list rỗng."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _num(value: str | None) -> float | None:
    return float(value) if value not in (None, "") else None


def speed_rows(variants: list[dict[str, Any]], timing: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Mỗi biến thể có thời gian một dòng; speedup_p95 = tổng p95 của PyTorch cùng cách chạy / tổng p95 của biến thể."""
    by_name = {Path(r["run"]).name: r for r in timing}
    vs = [_norm(v) for v in variants]
    pt_total = {_shape(v): _num(by_name.get(v["name"], {}).get("total_ms_p95")) for v in vs if v["precision"] == "pt"}
    rows = []
    for v in vs:
        t = by_name.get(v["name"])
        if t is None:
            continue
        total = _num(t.get("total_ms_p95"))
        base = pt_total.get(_shape(v))
        rows.append({
            "variant": v["name"], "precision": v["precision"], "mode": v["mode"],
            "target_person_px": v["target_person_px"], "n_tiles": _num(t.get("n_tiles")),
            "infer_ms_p50": _num(t.get("infer_ms_p50")), "infer_ms_p95": _num(t.get("infer_ms_p95")),
            "total_ms_p50": _num(t.get("total_ms_p50")), "total_ms_p95": total, "fps_at_p95": _num(t.get("fps_at_p95")),
            "speedup_p95_vs_pt": round(base / total, 3) if base and total else None, "gpu": t.get("gpu"),
        })
    return rows


def accuracy_rows(rq2: Path, datasets: list[str], pairs: list[tuple[str, str, str]]) -> list[dict[str, Any]]:
    """Hiệu AP, recall của mọi cặp đã so, nhóm cỡ 'all' và '<8', ở IoU 0,5 và 0,3."""
    rows = []
    for data in datasets:
        for a, b, kind in pairs:
            for iou in ("0.5", "0.3"):
                for r in read_csv(compare_dir(rq2, data, a, b, iou) / "compare.csv"):
                    if r["size_bin"] not in SIZE_BINS:
                        continue
                    rows.append({"dataset": data, "kind": kind, "a": a, "b": b, "iou": iou, "size_bin": r["size_bin"],
                                 "metric": r["metric"], "A": _num(r["A"]), "B": _num(r["B"]), "diff": _num(r["diff"]),
                                 "diff_lo": _num(r["diff_lo"]), "diff_hi": _num(r["diff_hi"]),
                                 "significant": r["significant"] == "True"})
    return rows


def vn(x: float | None, digits: int = 3) -> str:
    """Số theo quy ước tài liệu: cố định chữ số thập phân, dấu phẩy; thiếu thì gạch."""
    if x is None:
        return "–"
    return f"{x:.{digits}f}".replace(".", ",")


def signed(x: float | None) -> str:
    """Hiệu số có dấu, ba chữ số thập phân, dấu phẩy."""
    return "–" if x is None else f"{x:+.3f}".replace(".", ",").replace("-", "−")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Ghi list dict ra CSV (không ghi nếu rỗng)."""
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def markdown_speed(rows: list[dict[str, Any]]) -> str:
    """Bảng tốc độ dạng Markdown."""
    lines = ["| Biến thể | Số ô | Suy luận p50 (ms) | Tổng p50 (ms) | Tổng p95 (ms) | FPS theo p95 | Nhanh hơn PyTorch (lần, p95) |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['variant']} | {vn(r['n_tiles'], 1)} | {vn(r['infer_ms_p50'], 2)} | {vn(r['total_ms_p50'], 2)} | "
                     f"{vn(r['total_ms_p95'], 2)} | {vn(r['fps_at_p95'], 2)} | {vn(r['speedup_p95_vs_pt'])} |")
    return "\n".join(lines)


def markdown_accuracy(rows: list[dict[str, Any]], iou: str) -> str:
    """Bảng hiệu AP50 và recall (mọi người, dưới 8 px) theo cặp ở một ngưỡng IoU."""
    cell: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for r in rows:
        if r["iou"] == iou:
            cell[(r["dataset"], r["b"], r["size_bin"], r["metric"])] = r
    keys = sorted({(r["dataset"], r["kind"], r["a"], r["b"]) for r in rows if r["iou"] == iou})

    def fmt(r: dict[str, Any] | None) -> str:
        if r is None or r["diff"] is None:
            return "–"
        star = " *" if r["significant"] else ""
        return f"{signed(r['diff'])} ({signed(r['diff_lo'])} đến {signed(r['diff_hi'])}){star}"

    lines = [f"IoU {iou.replace('.', ',')}; * là có ý nghĩa thống kê (bootstrap cặp 95%).", "",
             "| Tập | So sánh | B − A | Hiệu AP, tất cả | Hiệu recall, tất cả | Hiệu recall < 8 px |", "|---|---|---|---|---|---|"]
    for data, kind, a, b in keys:
        lines.append(f"| {data} | {kind} | {b} − {a} | {fmt(cell.get((data, b, 'all', 'AP')))} | "
                     f"{fmt(cell.get((data, b, 'all', 'recall')))} | {fmt(cell.get((data, b, '<8', 'recall')))} |")
    return "\n".join(lines)


def main() -> None:
    """Đọc cấu hình đã chạy, ghi hai CSV, in bảng Markdown."""
    args = parse_args()
    config = yaml.safe_load((args.rq2 / "rq2_config.yaml").read_text(encoding="utf-8"))
    variants = config["variants"]
    datasets = [d["name"] for d in config["accuracy"]]
    speed = speed_rows(variants, read_csv(args.rq2 / "timing.csv"))
    accuracy = accuracy_rows(args.rq2, datasets, comparison_pairs(variants))
    write_csv(args.rq2 / "report" / "speed.csv", speed)
    write_csv(args.rq2 / "report" / "accuracy_diff.csv", accuracy)
    gpu = next((r["gpu"] for r in speed if r["gpu"]), "?")
    print(f"## Tốc độ cả pipeline ({gpu}; chỉ so sánh tương đối)\n\n{markdown_speed(speed)}\n")
    for iou in ("0.5", "0.3"):
        print(f"## Hiệu độ chính xác theo cặp\n\n{markdown_accuracy(accuracy, iou)}\n")
    if not accuracy:
        print("[lưu ý] Chưa có kết quả so cặp: chạy scripts/after_rq2.py trước.")
    print(f"Lưu tại: {args.rq2 / 'report'}")


if __name__ == "__main__":
    main()
