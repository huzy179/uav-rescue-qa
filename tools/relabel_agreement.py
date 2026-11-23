"""Độ nhất quán của người gán: so nhãn gán lại một số khung (không nhìn nhãn cũ) với nhãn gốc (LABELING mục 7).

Cả hai đầu vào là file xuất "CVAT for images 1.1" (.zip hoặc .xml) như tools/convert_cvat.py đọc. Chỉ so các khung
có trong lần gán lại. Người ghép tham lam theo IoU giảm dần (ngưỡng --iou, thêm một lần ở 0,3 như quy ước nhóm < 8 px).
Báo theo nhóm cỡ của nhãn gốc:
- số người ở lần gốc, ở lần gán lại, số ghép được; người chỉ có ở lần gốc (lần sau bỏ sót) và chỉ ở lần gán lại;
- IoU trung vị và độ lệch mép lớn nhất trung vị (px) của các cặp ghép được: người < 16 px lệch 1–2 px đã đủ tụt IoU;
- tỉ lệ trùng thuộc tính (ngập một phần, bị che) trên các cặp ghép, và tỉ lệ trùng từng thẻ ảnh.

Kết quả là số của chương 4 (kiểm tra chất lượng), không dùng để sửa nhãn sau khi khoá.

Ví dụ:
    .venv/bin/python tools/relabel_agreement.py --orig exports/*.zip --relabel exports_gan_lai/gan_lai.zip \\
        --output runs/flood/relabel_agreement
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Chạy dạng `python tools/relabel_agreement.py` thì thư mục tools/ đứng đầu sys.path, không phải gốc dự án.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.metrics import iou_matrix  # noqa: E402
from shared.config import parse_args_with_config  # noqa: E402
from tools.convert_cvat import BOX_ATTRIBUTES, IMAGE_TAGS, ImageLabels, parse_many  # noqa: E402

BIN_EDGES = [0, 8, 16, 32, math.inf]
BIN_NAMES = ["<8", "8-16", "16-32", ">32"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--orig", type=Path, nargs="+", required=True, help="File xuất CVAT của lần gán gốc")
    parser.add_argument("--relabel", type=Path, nargs="+", required=True, help="File xuất CVAT của lần gán lại")
    parser.add_argument("--iou", type=float, default=0.5, help="Ngưỡng IoU để coi hai box là một người")
    parser.add_argument("--output", type=Path, required=True, help="Thư mục ghi CSV")
    return parser


def greedy_match(a: np.ndarray, b: np.ndarray, thr: float) -> list[tuple[int, int, float]]:
    """Ghép một-một theo IoU giảm dần, chỉ giữ cặp IoU ≥ thr."""
    iou = iou_matrix(a, b)
    pairs = []
    used_a, used_b = set(), set()
    for flat in np.argsort(-iou, axis=None):
        i, j = np.unravel_index(flat, iou.shape)
        if iou[i, j] < thr:
            break
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        pairs.append((int(i), int(j), float(iou[i, j])))
    return pairs


def size_bin(box: np.ndarray) -> str:
    side = min(box[2] - box[0], box[3] - box[1])
    return BIN_NAMES[int(np.searchsorted(BIN_EDGES, side, side="right")) - 1]


def compare(orig: dict[str, ImageLabels], relabel: dict[str, ImageLabels], thr: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Một dòng mỗi người của lần gốc (ghép được không, IoU, lệch mép, thuộc tính) và mỗi người thừa của lần gán lại."""
    rows, extra = [], []
    for name, again in sorted(relabel.items()):
        if name not in orig:
            raise SystemExit(f"Khung {name} của lần gán lại không có trong nhãn gốc")
        first = orig[name]
        a = np.array([p[:4] for p in first.persons], dtype=float).reshape(-1, 4)
        b = np.array([p[:4] for p in again.persons], dtype=float).reshape(-1, 4)
        pairs = {i: (j, v) for i, j, v in greedy_match(a, b, thr)}
        loose = {i for i, _, _ in greedy_match(a, b, 0.3)}
        for i, box in enumerate(a):
            row = {"image": name, "bin": size_bin(box), "matched": i in pairs, "matched_iou03": i in loose,
                   "iou": np.nan, "max_edge_px": np.nan}
            if i in pairs:
                j, v = pairs[i]
                row["iou"], row["max_edge_px"] = v, float(np.abs(box - b[j]).max())
                for attr in BOX_ATTRIBUTES:
                    row[f"{attr}_same"] = first.persons[i][4][attr] == again.persons[j][4][attr]
            rows.append(row)
        matched_b = {j for j, _ in pairs.values()}
        extra += [{"image": name, "bin": size_bin(box)} for j, box in enumerate(b) if j not in matched_b]
    return pd.DataFrame(rows), pd.DataFrame(extra, columns=["image", "bin"])


def summarize(people: pd.DataFrame, extra: pd.DataFrame) -> pd.DataFrame:
    out = []
    for bin_ in ["all", *BIN_NAMES]:
        p = people if bin_ == "all" else people[people["bin"] == bin_]
        e = extra if bin_ == "all" else extra[extra["bin"] == bin_]
        m = p[p["matched"]] if len(p) else p
        row = {"size_bin": bin_, "n_orig": len(p), "n_matched": int(p["matched"].sum()) if len(p) else 0,
               "n_matched_iou03": int(p["matched_iou03"].sum()) if len(p) else 0,
               "n_only_orig": int((~p["matched"]).sum()) if len(p) else 0, "n_only_relabel": len(e),
               "iou_median": float(m["iou"].median()) if len(m) else np.nan,
               "max_edge_px_median": float(m["max_edge_px"].median()) if len(m) else np.nan}
        for attr in BOX_ATTRIBUTES:
            col = f"{attr}_same"
            row[f"{attr}_agree"] = float(m[col].mean()) if len(m) and col in m else np.nan
        out.append(row)
    return pd.DataFrame(out)


def tag_agreement(orig: dict[str, ImageLabels], relabel: dict[str, ImageLabels]) -> pd.DataFrame:
    rows = []
    for tag in IMAGE_TAGS:
        same = [(tag in orig[n].tags) == (tag in relabel[n].tags) for n in relabel]
        rows.append({"tag": tag, "n_images": len(same), "agree": float(np.mean(same)) if same else np.nan,
                     "n_orig": sum(tag in orig[n].tags for n in relabel), "n_relabel": sum(tag in relabel[n].tags for n in relabel)})
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args_with_config(build_parser())
    orig = {Path(i.name).name: i for i in parse_many(args.orig)}
    relabel = {Path(i.name).name: i for i in parse_many(args.relabel)}
    people, extra = compare(orig, relabel, args.iou)
    summary, tags = summarize(people, extra), tag_agreement(orig, relabel)
    args.output.mkdir(parents=True, exist_ok=True)
    people.to_csv(args.output / "people.csv", index=False)
    summary.to_csv(args.output / "agreement.csv", index=False)
    tags.to_csv(args.output / "tags.csv", index=False)
    print(f"{len(relabel)} khung gán lại")
    print(summary.round(3).to_string(index=False))
    print(tags.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
