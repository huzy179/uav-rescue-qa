"""Ghi CSV, bảng tóm tắt, histogram và thông tin tái lập cho mỗi lần chạy."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

PERSON_CLASS_ID = 0

BOX_COLUMNS = ["image", "method", "imgsz", "conf", "width_px", "height_px", "x1", "y1", "x2", "y2"]
IMAGE_COLUMNS = ["image", "method", "imgsz", "n_persons", "infer_ms"]

# Nhóm kích thước theo cạnh ngắn của box (pixel trên ảnh gốc): [cận dưới, cận trên).
SIZE_BIN_EDGES = [0.0, 8.0, 16.0, 32.0, float("inf")]
SIZE_BIN_LABELS = ["<8", "8-16", "16-32", ">32"]

# Bảng màu phân loại, gán theo thứ tự cố định cho từng cấu hình.
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SURFACE_COLOR = "#fcfcfb"
TEXT_COLOR = "#1a1a19"
MUTED_COLOR = "#6b6a63"
GRID_COLOR = "#e4e3dc"


def box_rows(
    image_name: str,
    method: str,
    imgsz: int,
    boxes_xyxy: Sequence[Sequence[float]],
    confs: Sequence[float],
) -> list[dict[str, Any]]:
    """Chuyển các box (toạ độ pixel trên ảnh gốc) thành các dòng của CSV theo box."""
    rows = []
    for (x1, y1, x2, y2), conf in zip(boxes_xyxy, confs):
        rows.append(
            {
                "image": image_name,
                "method": method,
                "imgsz": imgsz,
                "conf": round(float(conf), 4),
                "width_px": round(float(x2 - x1), 2),
                "height_px": round(float(y2 - y1), 2),
                "x1": round(float(x1), 2),
                "y1": round(float(y1), 2),
                "x2": round(float(x2), 2),
                "y2": round(float(y2), 2),
            }
        )
    return rows


def write_csvs(
    out_dir: Path, box_records: list[dict[str, Any]], image_records: list[dict[str, Any]]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ghi boxes.csv (mỗi dòng một box) và per_image.csv (mỗi dòng một ảnh)."""
    boxes = pd.DataFrame(box_records, columns=BOX_COLUMNS)
    images = pd.DataFrame(image_records, columns=IMAGE_COLUMNS)
    boxes.to_csv(out_dir / "boxes.csv", index=False)
    images.to_csv(out_dir / "per_image.csv", index=False)
    return boxes, images


def short_side(boxes: pd.DataFrame) -> pd.Series:
    """Cạnh ngắn của từng box (pixel)."""
    return boxes[["width_px", "height_px"]].min(axis=1)


def summarize(boxes: pd.DataFrame, images: pd.DataFrame) -> pd.DataFrame:
    """Tóm tắt theo (method, imgsz): số ảnh, tổng số phát hiện, thời gian trung bình, số box theo nhóm kích thước."""
    rows = []
    for (method, imgsz), img_group in images.groupby(["method", "imgsz"], sort=False):
        group = boxes[(boxes["method"] == method) & (boxes["imgsz"] == imgsz)]
        bins = pd.cut(short_side(group), bins=SIZE_BIN_EDGES, labels=SIZE_BIN_LABELS, right=False)
        counts = bins.value_counts()
        row: dict[str, Any] = {
            "method": method,
            "imgsz": imgsz,
            "n_images": len(img_group),
            "total_dets": len(group),
            "mean_ms_per_image": round(float(img_group["infer_ms"].mean()), 1),
        }
        for label in SIZE_BIN_LABELS:
            row[f"n_{label}px"] = int(counts.get(label, 0))
        rows.append(row)
    return pd.DataFrame(rows)


def print_and_save_summary(out_dir: Path, summary: pd.DataFrame) -> None:
    """In bảng tóm tắt ra màn hình và lưu summary.csv."""
    summary.to_csv(out_dir / "summary.csv", index=False)
    print("\nTóm tắt (nhóm kích thước tính theo cạnh ngắn của box, pixel trên ảnh gốc):")
    print(summary.to_string(index=False))


def plot_size_histogram(boxes: pd.DataFrame, out_path: Path) -> None:
    """Vẽ phân bố cạnh ngắn của box và số box theo nhóm kích thước, so sánh giữa các cấu hình."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.ticker import FormatStrFormatter, MaxNLocator

    groups = [
        (f"{method} imgsz={imgsz}", short_side(group).to_numpy())
        for (method, imgsz), group in boxes.groupby(["method", "imgsz"], sort=False)
    ]
    fig, (ax_hist, ax_bins) = plt.subplots(1, 2, figsize=(12, 4.5), facecolor=SURFACE_COLOR)
    for ax in (ax_hist, ax_bins):
        ax.set_facecolor(SURFACE_COLOR)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color(GRID_COLOR)
        ax.tick_params(colors=MUTED_COLOR)
        ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    if not groups:
        fig.suptitle("Không có box nào được phát hiện", color=TEXT_COLOR)
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return

    # Trái: histogram dạng đường bậc thang, trục x logarit để thấy rõ vùng vật thể nhỏ.
    all_sizes = np.concatenate([sizes for _, sizes in groups])
    low = max(float(all_sizes.min()), 1.0)
    high = max(float(all_sizes.max()), 64.0)
    edges = np.logspace(np.log2(low * 0.9), np.log2(high * 1.1), 25, base=2)
    for (label, sizes), color in zip(groups, SERIES_COLORS):
        ax_hist.hist(sizes, bins=edges, histtype="step", linewidth=2, color=color, label=label)
    for edge in SIZE_BIN_EDGES[1:-1]:
        ax_hist.axvline(edge, color=MUTED_COLOR, linewidth=0.8, linestyle=":")
    ax_hist.set_xscale("log", base=2)
    ax_hist.xaxis.set_major_formatter(FormatStrFormatter("%g"))
    ax_hist.set_xlabel("Cạnh ngắn của box (px trên ảnh gốc)", color=TEXT_COLOR)
    ax_hist.set_ylabel("Số box", color=TEXT_COLOR)
    ax_hist.set_title("Phân bố kích thước box", color=TEXT_COLOR, loc="left")

    # Phải: số box theo nhóm kích thước, các cột đặt cạnh nhau cho từng cấu hình.
    x = np.arange(len(SIZE_BIN_LABELS))
    bar_width = 0.8 / len(groups)
    for i, ((label, sizes), color) in enumerate(zip(groups, SERIES_COLORS)):
        counts, _ = np.histogram(sizes, bins=SIZE_BIN_EDGES)
        bars = ax_bins.bar(
            x - 0.4 + (i + 0.5) * bar_width,
            counts,
            width=bar_width,
            color=color,
            edgecolor=SURFACE_COLOR,
            linewidth=2,
            label=label,
        )
        if len(groups) <= 4:
            ax_bins.bar_label(bars, color=TEXT_COLOR, fontsize=8, padding=2)
    ax_bins.set_xticks(x, [f"{label} px" for label in SIZE_BIN_LABELS])
    ax_bins.set_xlabel("Nhóm kích thước theo cạnh ngắn", color=TEXT_COLOR)
    ax_bins.set_ylabel("Số box", color=TEXT_COLOR)
    ax_bins.set_title("Số box theo nhóm kích thước", color=TEXT_COLOR, loc="left")
    ax_bins.legend(frameon=False, labelcolor=TEXT_COLOR)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=SURFACE_COLOR)
    plt.close(fig)


def _package_version(name: str) -> str | None:
    """Phiên bản của gói đã cài, hoặc None nếu chưa cài."""
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _sha256(path: Path) -> str | None:
    """Mã băm SHA-256 của file trọng số, để biết chính xác đã dùng file nào."""
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_run_config(
    out_dir: Path, script: str, model: str | None, device: str | None, args: dict[str, Any]
) -> Path:
    """Ghi run_config.json: phiên bản thư viện, tên model, thiết bị và toàn bộ tham số của lần chạy."""
    config = {
        "script": script,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": " ".join(sys.argv),
        "model": model,
        "model_sha256": _sha256(Path(model)) if model else None,
        "device": device,
        "args": args,
        "versions": {
            "python": platform.python_version(),
            "ultralytics": _package_version("ultralytics"),
            "torch": _package_version("torch"),
            "sahi": _package_version("sahi"),
            "opencv-python": _package_version("opencv-python"),
            "numpy": _package_version("numpy"),
        },
        "platform": platform.platform(),
    }
    path = out_dir / "run_config.json"
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path
