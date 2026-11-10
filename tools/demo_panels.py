"""Ảnh so sánh hai mô hình trên cùng một khung cho slide và demo bảo vệ (docs/DEMO_BAO_VE.md).

Mỗi khung một ảnh PNG: hai nửa trái phải (mô hình A, mô hình B), trên mỗi nửa:
- vòng xanh lá: người có nhãn và được mô hình thấy (khớp IoU ≥ --iou ở conf ≥ --conf);
- vòng đỏ: người có nhãn mà mô hình bỏ sót;
- vòng vàng: báo nhầm (dự đoán không khớp nhãn nào, không nằm trong vùng bỏ qua).
Vòng có bán kính tối thiểu để người vài pixel vẫn thấy được khi chiếu. Dòng đầu mỗi nửa ghi số thấy, bỏ sót, báo
nhầm. Thêm một ảnh phóng to vùng có nhiều người nhỏ nhất (cùng toạ độ cho cả hai mô hình).

Khung được chọn theo quy tắc cố định, đặt trước khi xem kết quả (--pick), để không chọn khung đẹp:
- nho_nhat: khung có nhiều người nhãn cạnh ngắn < 16 px nhất;
- tieu_bieu: trong các khung có ít nhất 3 người, khung có recall của B gần recall chung của B nhất;
- loi: khung B bỏ sót nhiều người nhất.
Hoà thì lấy tên file nhỏ nhất. So khớp như console/errors.py (cùng quy ước với eval/metrics).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from console.errors import ImageErrors, match_errors, short_side
from eval.metrics import load_yolo_labels
from eval.splits import image_paths
from shared.config import parse_args_with_config

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
GREEN, RED, YELLOW = (40, 220, 80), (255, 40, 40), (255, 210, 0)
RULES = ("nho_nhat", "tieu_bieu", "loi")


@dataclass
class Frame:
    name: str
    path: Path
    gts: np.ndarray
    ignore: np.ndarray | None
    a: ImageErrors
    b: ImageErrors
    preds_a: np.ndarray
    preds_b: np.ndarray


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--images", type=Path, required=True, help="Thư mục ảnh")
    parser.add_argument("--labels", type=Path, required=True, help="Thư mục nhãn YOLO")
    parser.add_argument("--ignore", type=Path, default=None, help="Thư mục vùng bỏ qua (nếu có)")
    parser.add_argument("--run-a", type=Path, required=True, help="Thư mục kết quả của mô hình A (boxes.csv)")
    parser.add_argument("--run-b", type=Path, required=True, help="Thư mục kết quả của mô hình B (boxes.csv)")
    parser.add_argument("--title-a", default="A", help="Tên hiển thị của A")
    parser.add_argument("--title-b", default="B", help="Tên hiển thị của B")
    parser.add_argument("--conf", type=float, default=0.25, help="Ngưỡng conf vận hành")
    parser.add_argument("--iou", type=float, default=0.5, help="Ngưỡng IoU khi so khớp")
    parser.add_argument("--pick", nargs="+", choices=RULES, default=list(RULES), help="Quy tắc chọn khung")
    parser.add_argument("--image", nargs="*", default=[], help="Thêm khung chỉ định theo tên file")
    parser.add_argument("--width", type=int, default=1600, help="Cạnh ngang mỗi nửa (px)")
    parser.add_argument("--output", type=Path, required=True, help="Thư mục ghi PNG và picks.csv")
    return parser


def load_preds(run: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Dự đoán theo ảnh từ boxes.csv (một cấu hình mỗi thư mục, như mọi lần chạy trong runs/)."""
    df = pd.read_csv(run / "boxes.csv")
    if df[["method", "imgsz"]].drop_duplicates().shape[0] > 1:
        raise SystemExit(f"{run}/boxes.csv có nhiều cấu hình; cần thư mục chỉ một cấu hình")
    return {n: (g[["x1", "y1", "x2", "y2"]].to_numpy(float), g["conf"].to_numpy(float)) for n, g in df.groupby("image")}


def match(preds: dict[str, tuple[np.ndarray, np.ndarray]], name: str, gts: np.ndarray, ignore: np.ndarray | None,
          conf: float, iou: float) -> tuple[ImageErrors, np.ndarray]:
    boxes, confs = preds.get(name, (np.zeros((0, 4)), np.zeros(0)))
    keep = confs >= conf
    return match_errors(boxes[keep], confs[keep], gts, iou, ignore), boxes[keep]


def load_frames(args: argparse.Namespace) -> list[Frame]:
    preds_a, preds_b = load_preds(args.run_a), load_preds(args.run_b)
    frames = []
    for path in image_paths(args.images):
        with Image.open(path) as img:
            w, h = img.size
        gts = load_yolo_labels(args.labels / f"{path.stem}.txt", w, h, [0])
        ign = load_yolo_labels(args.ignore / f"{path.stem}.txt", w, h, [0]) if args.ignore else None
        a, pa = match(preds_a, path.name, gts, ign, args.conf, args.iou)
        b, pb = match(preds_b, path.name, gts, ign, args.conf, args.iou)
        frames.append(Frame(path.name, path, gts, ign, a, b, pa, pb))
    return frames


def pick(frames: list[Frame], rule: str) -> Frame:
    """Chọn một khung theo quy tắc cố định; hoà thì tên nhỏ nhất."""
    frames = sorted(frames, key=lambda f: f.name)
    if rule == "nho_nhat":
        return max(frames, key=lambda f: int((short_side(f.gts) < 16).sum()))
    if rule == "loi":
        return max(frames, key=lambda f: len(f.b.fn))
    n_gt = sum(len(f.gts) for f in frames)
    overall = sum(len(f.b.tp) for f in frames) / n_gt if n_gt else 0.0
    pool = [f for f in frames if len(f.gts) >= 3] or frames
    return min(pool, key=lambda f: abs(len(f.b.tp) / max(len(f.gts), 1) - overall))


def zoom_box(frame: Frame, size: int) -> tuple[int, int, int, int]:
    """Vùng vuông cạnh `size` quanh trọng tâm các người nhỏ nhất (nửa số người có cạnh ngắn bé nhất)."""
    with Image.open(frame.path) as img:
        w, h = img.size
    if len(frame.gts) == 0:
        cx, cy = w / 2, h / 2
    else:
        side = short_side(frame.gts)
        small = frame.gts[np.argsort(side)[: max(1, len(side) // 2)]]
        cx, cy = float(((small[:, 0] + small[:, 2]) / 2).mean()), float(((small[:, 1] + small[:, 3]) / 2).mean())
    size = min(size, w, h)
    x0 = int(min(max(cx - size / 2, 0), w - size))
    y0 = int(min(max(cy - size / 2, 0), h - size))
    return x0, y0, x0 + size, y0 + size


def draw_half(image: Image.Image, frame: Frame, err: ImageErrors, preds: np.ndarray, title: str, crop: tuple[int, int, int, int] | None,
              width: int) -> Image.Image:
    """Một nửa: ảnh (hoặc vùng crop) thu về `width`, vòng đánh dấu, dòng tiêu đề."""
    x0, y0 = (crop[0], crop[1]) if crop else (0, 0)
    src = image.crop(crop) if crop else image
    scale = width / src.width
    canvas = src.resize((width, round(src.height * scale)), Image.Resampling.LANCZOS).convert("RGB")
    draw = ImageDraw.Draw(canvas)
    radius_min = max(10, width // 100)

    def ring(box: np.ndarray, color: tuple[int, int, int], thick: int) -> None:
        bx = [(box[0] - x0) * scale, (box[1] - y0) * scale, (box[2] - x0) * scale, (box[3] - y0) * scale]
        cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        r = max(radius_min, 0.6 * max(bx[2] - bx[0], bx[3] - bx[1]))
        if cx + r < 0 or cy + r < 0 or cx - r > canvas.width or cy - r > canvas.height:
            return
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=thick)

    for _, j in err.tp:
        ring(frame.gts[j], GREEN, 3)
    for j in err.fn:
        ring(frame.gts[j], RED, 4)
    for i in err.fp:
        ring(preds[i], YELLOW, 3)
    font = ImageFont.truetype(FONT, max(18, width // 45))
    text = f"{title}: thấy {len(err.tp)}/{len(frame.gts)}, bỏ sót {len(err.fn)}, báo nhầm {len(err.fp)}"
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.rectangle([0, 0, bbox[2] + 24, bbox[3] + 16], fill=(0, 0, 0))
    draw.text((12, 8), text, font=font, fill=(255, 255, 255))
    return canvas


def render(frame: Frame, args: argparse.Namespace, crop: tuple[int, int, int, int] | None) -> Image.Image:
    with Image.open(frame.path) as img:
        img = img.convert("RGB")
        left = draw_half(img, frame, frame.a, frame.preds_a, args.title_a, crop, args.width)
        right = draw_half(img, frame, frame.b, frame.preds_b, args.title_b, crop, args.width)
    legend_h = max(36, args.width // 36)
    out = Image.new("RGB", (left.width + right.width + 8, max(left.height, right.height) + legend_h), (0, 0, 0))
    out.paste(left, (0, 0))
    out.paste(right, (left.width + 8, 0))
    draw = ImageDraw.Draw(out)
    font = ImageFont.truetype(FONT, legend_h * 2 // 3)
    x, y = 12, max(left.height, right.height) + legend_h // 8
    for color, label in ((GREEN, "thấy"), (RED, "bỏ sót"), (YELLOW, "báo nhầm")):
        draw.ellipse([x, y + 4, x + legend_h * 2 // 3, y + 4 + legend_h * 2 // 3], outline=color, width=4)
        x += legend_h
        draw.text((x, y), label, font=font, fill=(255, 255, 255))
        x += int(draw.textlength(label, font=font)) + legend_h
    note = f"conf ≥ {args.conf:g}, IoU ≥ {args.iou:g}; {frame.name}".replace(".", ",", 2)
    draw.text((out.width - int(draw.textlength(note, font=font)) - 12, y), note, font=font, fill=(200, 200, 200))
    return out


def main() -> None:
    args = parse_args_with_config(build_parser())
    frames = load_frames(args)
    if not frames:
        raise SystemExit(f"Không có ảnh trong {args.images}")
    by_name = {f.name: f for f in frames}
    chosen = [(rule, pick(frames, rule)) for rule in args.pick]
    for name in args.image:
        if name not in by_name:
            raise SystemExit(f"Không có ảnh {name} trong {args.images}")
        chosen.append(("chi_dinh", by_name[name]))
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    for rule, frame in chosen:
        stem = f"{rule}_{Path(frame.name).stem}"
        render(frame, args, None).save(args.output / f"{stem}.png")
        render(frame, args, zoom_box(frame, 480)).save(args.output / f"{stem}_phong_to.png")
        rows.append({
            "rule": rule, "image": frame.name, "n_gt": len(frame.gts), "n_gt_lt16": int((short_side(frame.gts) < 16).sum()),
            "a_tp": len(frame.a.tp), "a_fn": len(frame.a.fn), "a_fp": len(frame.a.fp),
            "b_tp": len(frame.b.tp), "b_fn": len(frame.b.fn), "b_fp": len(frame.b.fp),
        })
    pd.DataFrame(rows).to_csv(args.output / "picks.csv", index=False)
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"Đã ghi {len(rows)} khung vào {args.output}")


if __name__ == "__main__":
    main()
