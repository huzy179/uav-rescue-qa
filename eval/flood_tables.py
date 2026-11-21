"""Ghép kết quả tập test lũ thành các bảng Markdown cho luận văn (chương 4 Bảng 4.4, chương 5 câu hỏi 1).

Chỉ đọc file đã có, không tính lại chỉ số: thống kê nhãn từ data/processed/flood (boxes_test.csv, tags_test.csv,
ảnh), chỉ số từ runs/flood (eval_<mã>_iou<iou>/eval_by_size.csv, compare_<A>_<B>_iou<iou>/compare.csv,
eval_tags/recall_by_tag.csv). Số in ba chữ số thập phân, dấu phẩy; khoảng tin cậy và hiệu số chép nguyên từ CSV.
Lần chạy hay cặp so sánh nào chưa có thì bỏ qua và ghi chú ở cuối.

Ví dụ (scripts/eval_flood.sh tự gọi):
    .venv/bin/python eval/flood_tables.py --names E1 E2 E2c E3 E4tiled --output runs/flood/bang.md
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from eval.splits import image_paths
from shared.config import parse_args_with_config

# Tên mô tả theo docs/THUAT_NGU.md (mã nội bộ đi kèm trong ngoặc).
MODEL_NAMES = {
    "E0": "Mô hình nền, ảnh 640 px",
    "E1": "Mô hình nền, ảnh 1280 px",
    "E2": "Tinh chỉnh trên VisDrone",
    "E2c": "Tinh chỉnh trên VisDrone + AFO (mô hình chính)",
    "E2e": "Như mô hình chính, thêm C2A",
    "E3": "Như mô hình chính, thêm nhánh P2",
    "E4tiled": "Mô hình chính + cắt ô",
}
BINS = ["all", "<8", "8-16", "16-32", ">32"]
BIN_EDGES = [0, 8, 16, 32, math.inf]
BIN_LABELS = ["< 8 px", "8–16 px", "16–32 px", "> 32 px"]
SUBSET_NAMES = {
    "all": "Toàn tập", "glare": "Loá nước", "weather": "Mưa, sương, tối", "blur": "Nhoè",
    "floating_debris": "Vật trôi", "no_tag": "Không thẻ nào", "partly_submerged": "Người ngập một phần",
    "occluded": "Người bị che", "no_attribute": "Không thuộc tính nào",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--flood", type=Path, default=Path("data/processed/flood"), help="Thư mục tập lũ đã chuyển nhãn")
    parser.add_argument("--split", default="test", help="Phần dữ liệu")
    parser.add_argument("--runs-dir", type=Path, default=Path("runs/flood"), help="Thư mục kết quả trên tập lũ")
    parser.add_argument("--names", nargs="+", required=True, help="Mã thí nghiệm theo thứ tự hiện trong bảng")
    parser.add_argument("--main", default="E2c", help="Mô hình chính (bảng theo loại nhiễu)")
    parser.add_argument("--cluster-pattern", default=None,
                        help="Regex gom video thành nguồn cho Bảng 4.4 (mặc định: CLUSTER của scripts/eval_flood.sh)")
    parser.add_argument("--output", type=Path, required=True, help="File Markdown ra")
    return parser


def num(x: float, digits: int = 3) -> str:
    """Số kiểu tài liệu: ba chữ số thập phân, dấu phẩy, dấu trừ thật; NaN thành gạch."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    text = f"{x:.{digits}f}".replace(".", ",")
    return text.replace("-", "−")


def signed(x: float) -> str:
    return ("+" if x > 0 else "") + num(x)


def label(name: str) -> str:
    return f"{MODEL_NAMES.get(name, name)} ({name})"


def eval_flood_cluster() -> str:
    text = Path("scripts/eval_flood.sh").read_text(encoding="utf-8")
    return re.search(r"^CLUSTER='(.+)'", text, re.M).group(1)


def dataset_table(flood: Path, split: str, cluster: str) -> list[str]:
    """Bảng 4.4: mỗi video một dòng (khung, độ phân giải, số người theo nhóm cỡ, khung không có người), thêm dòng tổng."""
    from eval.splits import group_of

    boxes = pd.read_csv(flood / f"boxes_{split}.csv")
    side = np.minimum(boxes["x2"] - boxes["x1"], boxes["y2"] - boxes["y1"])
    boxes["bin"] = pd.cut(side, BIN_EDGES, right=False, labels=BIN_LABELS)
    images = image_paths(flood / "images" / split)
    rows = []
    for path in images:
        with Image.open(path) as img:
            size = f"{img.width}×{img.height}"
        rows.append({"image": path.name, "video": path.stem.rsplit("_", 1)[0], "source": group_of(path.stem, cluster),
                     "size": size})
    frames = pd.DataFrame(rows)
    counts = boxes.groupby("image").size()
    frames["n"] = frames["image"].map(counts).fillna(0).astype(int)
    out = ["| Video | Khung | Độ phân giải | Người | " + " | ".join(BIN_LABELS) + " | Khung không có người |",
           "|---|---|---|---|" + "---|" * len(BIN_LABELS) + "---|"]
    for video, g in frames.groupby("video", sort=True):
        b = boxes[boxes["image"].isin(g["image"])]
        per_bin = b["bin"].value_counts()
        out.append(f"| {video} | {len(g)} | {', '.join(sorted(g['size'].unique()))} | {len(b)} | "
                   + " | ".join(str(int(per_bin.get(lab, 0))) for lab in BIN_LABELS) + f" | {int((g['n'] == 0).sum())} |")
    per_bin = boxes["bin"].value_counts()
    out.append(f"| **Tổng** ({frames['source'].nunique()} nguồn, {frames['video'].nunique()} video) | {len(frames)} | | "
               f"{len(boxes)} | " + " | ".join(str(int(per_bin.get(lab, 0))) for lab in BIN_LABELS)
               + f" | {int((frames['n'] == 0).sum())} |")
    tags = pd.read_csv(flood / f"tags_{split}.csv")
    attr = [c for c in ("partly_submerged", "occluded") if c in boxes.columns]
    extra = [f"{SUBSET_NAMES[c]}: {int(boxes[c].astype(bool).sum())} người" for c in attr]
    extra += [f"{SUBSET_NAMES.get(c, c)}: {int(tags[c].astype(bool).sum())} khung" for c in tags.columns if c != "image"]
    return out + ["", "Thuộc tính và thẻ: " + "; ".join(extra) + "."]


def size_table(runs_dir: Path, names: list[str], missing: list[str]) -> list[str]:
    """AP50 (KTC 95%) và recall vận hành theo nhóm cỡ ở IoU 0,5, thêm nhóm < 8 px ở IoU 0,3."""
    out = ["| Mô hình | Chỉ số | " + " | ".join("Tất cả" if b == "all" else f"{b} px".replace("-", "–") for b in BINS)
           + " | < 8 px, IoU 0,3 |", "|---|---|" + "---|" * (len(BINS) + 1)]
    for name in names:
        f05 = runs_dir / f"eval_{name}_iou0.5" / "eval_by_size.csv"
        f03 = runs_dir / f"eval_{name}_iou0.3" / "eval_by_size.csv"
        if not f05.exists():
            missing.append(str(f05))
            continue
        t05 = pd.read_csv(f05).set_index("size_bin")
        t03 = pd.read_csv(f03).set_index("size_bin") if f03.exists() else None
        if t03 is None:
            missing.append(str(f03))
        for metric, lo, hi, title in (("AP", "AP_lo", "AP_hi", "AP50"), ("recall", "recall_lo", "recall_hi", "Recall (conf 0,25)")):
            cells = []
            for tab, b in [(t05, b) for b in BINS] + [(t03, "<8")]:
                if tab is None or b not in tab.index or int(tab.loc[b, "n_gt"]) == 0:
                    cells.append("–")
                else:
                    r = tab.loc[b]
                    cells.append(f"{num(r[metric])} ({num(r[lo])}–{num(r[hi])})")
            out.append(f"| {label(name) if metric == 'AP' else ''} | {title} | " + " | ".join(cells) + " |")
    first = next((runs_dir / f"eval_{n}_iou0.5" / "eval_by_size.csv" for n in names
                  if (runs_dir / f"eval_{n}_iou0.5" / "eval_by_size.csv").exists()), None)
    if first is not None:
        n_gt = pd.read_csv(first).set_index("size_bin")["n_gt"]
        out.append("| | Số người | " + " | ".join(str(int(n_gt.get(b, 0))) for b in BINS) + f" | {int(n_gt.get('<8', 0))} |")
    return out


def compare_table(runs_dir: Path, names: list[str]) -> list[str]:
    """Hiệu B − A (KTC 95%, p) của mọi cặp đã chấm giữa các mô hình được chọn; * có ý nghĩa."""
    out = ["| So sánh (B − A) | IoU | Nhóm | Hiệu AP50 | p | Hiệu recall (conf 0,25) | p |", "|---|---|---|---|---|---|---|"]
    for path in sorted(runs_dir.glob("compare_*_iou*/compare.csv")):
        m = re.match(r"compare_(.+?)_(.+)_iou(0\.\d)$", path.parent.name)
        if not m or m.group(1) not in names or m.group(2) not in names:
            continue
        a, b, iou = m.groups()
        tab = pd.read_csv(path)
        for bin_ in ("all", "<8", "8-16"):
            rows = tab[tab["size_bin"] == bin_].set_index("metric")
            if rows.empty or not {"AP", "recall"} <= set(rows.index):
                continue
            cells = []
            for metric in ("AP", "recall"):
                r = rows.loc[metric]
                star = " *" if bool(r["significant"]) else ""
                cells += [f"{signed(r['diff'])} ({signed(r['diff_lo'])} đến {signed(r['diff_hi'])}){star}", num(r["p_value"])]
            group = "Tất cả" if bin_ == "all" else f"{bin_} px".replace("-", "–")
            out.append(f"| {label(b)} − {label(a)} | {iou.replace('.', ',')} | {group} | " + " | ".join(cells) + " |")
    return out


def tag_table(runs_dir: Path, main: str, missing: list[str]) -> list[str]:
    """Recall và báo nhầm mỗi ảnh của mô hình chính theo thẻ ảnh và thuộc tính người, KTC 95% theo nguồn."""
    path = runs_dir / "eval_tags" / "recall_by_tag.csv"
    if not path.exists():
        missing.append(str(path))
        return []
    tab = pd.read_csv(path)
    tab = tab[tab["run"].map(lambda r: Path(r).name) == main]
    out = ["| Tập con | Số người | Recall (conf 0,25) | Số khung | Báo nhầm mỗi khung |", "|---|---|---|---|---|"]
    for _, r in tab.iterrows():
        recall = f"{num(r['recall'])} ({num(r['recall_lo'])}–{num(r['recall_hi'])})" if r["n_gt"] else "–"
        fp = f"{num(r['fp_per_image'])} ({num(r['fp_per_image_lo'])}–{num(r['fp_per_image_hi'])})" if r["n_images"] else "–"
        out.append(f"| {SUBSET_NAMES.get(r['subset'], r['subset'])} | {int(r['n_gt'])} | {recall} | {int(r['n_images'])} | {fp} |")
    return out


def main() -> None:
    args = parse_args_with_config(build_parser())
    cluster = args.cluster_pattern or eval_flood_cluster()
    missing: list[str] = []
    parts = ["# Bảng kết quả tập test lũ", "",
             "Sinh bằng `eval/flood_tables.py` từ file trong `runs/flood/` và `data/processed/flood/`; chép sang "
             "`docs/results/flood.md` và luận văn, không sửa số.", "",
             "## Bảng 4.4. Thống kê tập ảnh lũ", "", *dataset_table(args.flood, args.split, cluster), "",
             "## AP50 và recall theo nhóm cỡ (IoU 0,5; bootstrap theo nguồn)", "", *size_table(args.runs_dir, args.names, missing), "",
             "## So cặp (bootstrap cặp theo nguồn; * có ý nghĩa thống kê)", "", *compare_table(args.runs_dir, args.names), "",
             f"## Theo loại nhiễu, {label(args.main)}", "", *tag_table(args.runs_dir, args.main, missing)]
    if missing:
        parts += ["", "Chưa có (bỏ qua): " + ", ".join(f"`{m}`" for m in missing)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Đã ghi {args.output}" + (f"; thiếu {len(missing)} file" if missing else ""))


if __name__ == "__main__":
    main()
