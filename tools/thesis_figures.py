"""Vẽ lại các hình số liệu cho quyển tiếng Anh từ đúng CSV trong `runs/` (nhãn tiếng Anh, in đen trắng vẫn phân biệt).

Hình trong `docs/results/` và `runs/` ghi nhãn tiếng Việt và mã nội bộ (E1, E2c, pt_tiled_px10); quyển cần tên mô tả
tiếng Anh. Script không tính số mới: chỉ đọc CSV và vẽ.

- Hình 7.1 `fig7_1_recall_by_pixels.png`: recall vận hành theo cạnh ngắn người trên SeaDronesSee thu nhỏ
  (`runs/e6_sds/eval/recall_by_pixels.csv`, `eval/recall_by_pixels.py`; cùng cách đặt điểm trên trục log).
- Hình 7.2 `fig7_2_pareto.png`: recall vận hành theo tốc độ trên T4, SeaDronesSee val, biên Pareto
  (`runs/rq2/report/pareto.csv`, `scripts/after_rq2.py`).
- Hình 3.1, 3.2 (sơ đồ): vẽ tay bằng SVG trong `docs/thesis/figures/src/`; `--diagrams` dựng PNG bằng Chrome không giao
  diện (bản cài kèm Playwright, hoặc `--chrome`). PNG được commit nên dựng file Word không cần Chrome.

Ví dụ:
    .venv/bin/python tools/thesis_figures.py
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from shared.config import parse_args_with_config  # noqa: E402

MODEL_NAMES = {"E1": "Base model (YOLO26s)", "E2c": "Main model (fine-tuned)"}
PRECISION_NAMES = {"pt": "PyTorch", "fp16": "TensorRT FP16", "int8": "TensorRT INT8"}
MARKERS = {"pt": "o", "fp16": "^", "int8": "D"}
SETTING_COLORS = {"full": "#1f6fb2", "tiled": "#888888", "tiled_px10": "#d4572a"}
SETTING_NAMES = {"full": "full image, 1280 px", "tiled": "tiles at original resolution",
                 "tiled_px10": "tiles after altitude-based downscaling"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--recall-by-pixels", type=Path, default=Path("runs/e6_sds/eval/recall_by_pixels.csv"))
    parser.add_argument("--pareto", type=Path, default=Path("runs/rq2/report/pareto.csv"))
    parser.add_argument("--pareto-dataset", default="sds_det")
    parser.add_argument("--output", type=Path, default=Path("docs/thesis/figures"))
    parser.add_argument("--diagrams", action="store_true", help="Chỉ dựng PNG cho các sơ đồ SVG trong <output>/src")
    parser.add_argument("--chrome", default=None, help="Chrome không giao diện (mặc định tìm bản của Playwright)")
    return parser


def svg_size(svg: Path) -> tuple[int, int]:
    """Cỡ khung vẽ từ thuộc tính width, height của thẻ <svg>."""
    head = svg.read_text(encoding="utf-8")[:400]
    w = re.search(r'width="(\d+)"', head)
    h = re.search(r'height="(\d+)"', head)
    if not (w and h):
        raise ValueError(f"{svg}: thẻ <svg> thiếu width hoặc height")
    return int(w.group(1)), int(h.group(1))


def find_chrome(explicit: str | None) -> str:
    candidates = [explicit] if explicit else sorted(
        str(p) for p in Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/"
                                         "chrome-headless-shell")) + [shutil.which("chromium") or "", shutil.which("google-chrome") or ""]
    for c in candidates:
        if c and Path(c).exists():
            return c
    raise SystemExit("Không tìm thấy Chrome không giao diện (cài Playwright hoặc truyền --chrome)")


def render_diagrams(src_dir: Path, out_dir: Path, chrome: str, scale: float = 1.5) -> list[Path]:
    """Chụp mỗi file SVG thành PNG cùng tên ở out_dir, phóng scale lần cho rõ khi in."""
    written = []
    for svg in sorted(src_dir.glob("*.svg")):
        w, h = svg_size(svg)
        png = out_dir / f"{svg.stem}.png"
        subprocess.run([chrome, "--headless", "--disable-gpu", "--hide-scrollbars", f"--window-size={w},{h}",
                        f"--force-device-scale-factor={scale}", f"--screenshot={png.resolve()}", svg.resolve().as_uri()],
                       check=True, capture_output=True, timeout=60)
        written.append(png)
    return written


def style(ax: plt.Axes) -> None:
    ax.grid(alpha=0.25, linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)


def group_centres(group: pd.DataFrame) -> np.ndarray:
    """Tâm nhóm trên trục log, như eval/recall_by_pixels.plot: nhóm cuối không có cận trên thì lấy thêm một bậc √2."""
    lo = group["lo"].clip(lower=2).to_numpy(dtype=float)
    hi = np.where(np.isinf(group["hi"].to_numpy(dtype=float)), lo * 1.41, group["hi"].to_numpy(dtype=float))
    return np.sqrt(lo * hi)


def plot_recall_by_pixels(table: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.3, 3.8))
    for (model, group), color, marker, line in zip(table.groupby("model", sort=False), ["#1f6fb2", "#d4572a"], ["o", "s"],
                                                   ["-", "--"]):
        x = group_centres(group)
        ax.fill_between(x, group["recall_lo"], group["recall_hi"], color=color, alpha=0.13, linewidth=0)
        ax.plot(x, group["recall"], color=color, linestyle=line, linewidth=2, marker=marker, markersize=5,
                label=MODEL_NAMES.get(model, model))
    ax.set_xscale("log")
    ax.set_xticks([4, 8, 16, 32, 64, 128], labels=["4", "8", "16", "32", "64", "128"])
    ax.set_ylim(0, 1)
    ax.set_xlabel("Short side of the person after downscaling (px, log scale)")
    ax.set_ylabel("Operating recall (confidence 0.25)")
    style(ax)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def setting_of(variant: str) -> str:
    return "tiled_px10" if variant.endswith("_px10") else ("tiled" if "_tiled" in variant else "full")


def plot_pareto(table: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.3, 4.0))
    for row in table.itertuples():
        precision, setting = row.variant.split("_")[0], setting_of(row.variant)
        ax.scatter(row.fps_at_p95, row.recall, marker=MARKERS[precision], s=55, color=SETTING_COLORS[setting],
                   edgecolors="black" if row.on_front else "none", linewidths=1.2, zorder=3)
    front = table[table["on_front"]].sort_values("fps_at_p95")
    ax.plot(front["fps_at_p95"], front["recall"], color="black", linewidth=0.8, linestyle=":", zorder=2)
    ax.axvline(8, color="grey", linestyle="--", linewidth=1)
    ax.text(8.4, ax.get_ylim()[1], "8 frames/s needed (Section 7.3.1)", color="grey", fontsize=7.5, va="top")
    handles = [plt.Line2D([], [], marker=MARKERS[p], linestyle="none", color="black", markerfacecolor="white",
                          label=PRECISION_NAMES[p]) for p in MARKERS]
    handles += [plt.Line2D([], [], marker="s", linestyle="none", color=c, label=SETTING_NAMES[s])
                for s, c in SETTING_COLORS.items()]
    handles.append(plt.Line2D([], [], color="black", linestyle=":", label="Pareto front (outlined points)"))
    ax.legend(handles=handles, frameon=False, fontsize=7.5, loc="lower right")
    ax.set_xlabel("Whole-pipeline frames per second at p95, Tesla T4 (relative comparison only)")
    ax.set_ylabel("Operating recall (conf. 0.25, IoU 0.5)")
    style(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main() -> int:
    args = parse_args_with_config(build_parser())
    args.output.mkdir(parents=True, exist_ok=True)
    if args.diagrams:
        for png in render_diagrams(args.output / "src", args.output, find_chrome(args.chrome)):
            print(f"Đã dựng {png}")
        return 0
    pixels = pd.read_csv(args.recall_by_pixels)
    plot_recall_by_pixels(pixels, args.output / "fig7_1_recall_by_pixels.png")
    pareto = pd.read_csv(args.pareto)
    pareto = pareto[pareto["dataset"] == args.pareto_dataset]
    if pareto.empty:
        raise SystemExit(f"Không có dòng nào của tập {args.pareto_dataset} trong {args.pareto}")
    plot_pareto(pareto, args.output / "fig7_2_pareto.png")
    print(f"Đã vẽ hình vào {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
