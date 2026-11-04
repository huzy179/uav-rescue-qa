"""Báo cáo phân tích lỗi cho chương 5: bảng theo nhóm kích thước và ảnh cắt các ca bỏ sót, báo nhầm tiêu biểu.

Ghi vào runs/console/reports/<tập>_<lần chạy>_iou<..>_conf<..>/: report.md (bảng, đường dẫn ảnh) và crops/*.jpg. Số
trong bảng tính bằng cùng cách so khớp với eval_by_size ở một ngưỡng conf, nên khớp eval_by_size.csv; báo cáo ghi rõ
tập, lần chạy, cấu hình, ngưỡng để tái lập. Ảnh cắt phóng to quanh box (người vài pixel mới nhìn thấy được).

Chọn ca tiêu biểu: bỏ sót xếp theo cỡ người giảm dần trong từng nhóm (người to mà vẫn bị bỏ sót đáng xem nhất), báo
nhầm xếp theo conf giảm dần (mô hình tin nhất mà sai). Không chọn tay, để không "chọn ảnh đẹp".
"""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from console.errors import Dataset, _ground_truth, image_errors, short_side, summarize
from eval.metrics import SIZE_RANGES

ROOT = Path("runs/console/reports")
CROP_PX = 192  # cạnh ảnh cắt sau phóng to
COLORS = {"fn": (214, 39, 40), "fp": (255, 140, 0), "tp": (44, 160, 44)}


def _crop(image_path: Path, box: list[float], kind: str, out: Path, context: float = 4.0) -> None:
    """Cắt vùng quanh box (cạnh = context × cạnh dài box, tối thiểu 48 px), phóng về CROP_PX, vẽ box."""
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        x1, y1, x2, y2 = box
        side = min(max(48.0, context * max(x2 - x1, y2 - y1)), img.width, img.height)  # không vượt khung ảnh
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        left = min(max(cx - side / 2, 0), max(img.width - side, 0))
        top = min(max(cy - side / 2, 0), max(img.height - side, 0))
        region = img.crop((round(left), round(top), round(left + side), round(top + side)))
        scale = CROP_PX / side
        region = region.resize((CROP_PX, CROP_PX), Image.Resampling.NEAREST if scale > 2 else Image.Resampling.BILINEAR)
        draw = ImageDraw.Draw(region)
        draw.rectangle([(x1 - left) * scale, (y1 - top) * scale, (x2 - left) * scale, (y2 - top) * scale], outline=COLORS[kind], width=2)
        out.parent.mkdir(parents=True, exist_ok=True)
        region.save(out, quality=90)


def _vn(x: float | None, digits: int = 3) -> str:
    return "–" if x is None else f"{x:.{digits}f}".replace(".", ",")


def build_report(
    dataset: Dataset, run: str, config: str, iou_thr: float, conf_thr: float, per_bin: int = 4, root: Path = ROOT
) -> Path:
    """Ghi báo cáo, trả thư mục chứa nó."""
    name = f"{dataset.name}_{run}_iou{iou_thr:g}_conf{conf_thr:g}".replace("/", "-")
    out = root / name
    images = _ground_truth(dataset.images, dataset.labels, dataset.ignore)
    rows = []
    for size in SIZE_RANGES:
        t = summarize(dataset, run, config, iou_thr, conf_thr, size)["total"]
        rows.append((size, t))

    # Thu thập mọi lỗi một lượt (không theo nhóm, ưu tiên nhãn như "all").
    fns: list[dict[str, Any]] = []
    fps: list[dict[str, Any]] = []
    for image in images:
        err, preds, confs, gts, _, _ = image_errors(dataset, run, config, image, iou_thr, conf_thr)
        gt_side, pred_side = short_side(gts), short_side(preds)
        fns += [{"image": image, "box": gts[j].tolist(), "px": float(gt_side[j])} for j in err.fn]
        fps += [{"image": image, "box": preds[i].tolist(), "px": float(pred_side[i]), "conf": float(confs[i])} for i in err.fp]

    title = f"Phân tích lỗi: {dataset.title}, {run}"
    intro = (
        f"Cấu hình `{config}`, IoU {_vn(iou_thr, 1)}, ngưỡng conf {_vn(conf_thr, 2)}. Tạo bằng giao diện thử nghiệm "
        f"(`console/report.py`) lúc {datetime.now():%d/%m/%Y %H:%M} từ `{dataset.runs / run / 'boxes.csv'}`. "
        "Recall, precision ở đúng ngưỡng này, cùng cách so khớp với `eval_by_size.py`."
    )
    table = [("tất cả" if size == "all" else f"{size} px", t) for size, t in rows]

    # Chọn ca tiêu biểu và cắt ảnh.
    fn_sections = []
    for size, (lo, hi) in SIZE_RANGES.items():
        if size == "all":
            continue
        in_bin = [f for f in fns if lo <= f["px"] < hi]
        chosen = sorted(in_bin, key=lambda f: -f["px"])[:per_bin]
        for k, f in enumerate(chosen):
            f["crop"] = f"crops/fn_{size.replace('<', 'lt').replace('>', 'gt')}_{k}.jpg"
            _crop(dataset.images / f["image"], f["box"], "fn", out / f["crop"])
        if chosen:
            fn_sections.append((size, len(in_bin), chosen))
    fp_chosen = sorted(fps, key=lambda f: -f["conf"])[: per_bin * 3]
    for k, f in enumerate(fp_chosen):
        f["crop"] = f"crops/fp_{k}.jpg"
        _crop(dataset.images / f["image"], f["box"], "fp", out / f["crop"])
    notes = [
        "Ảnh cắt phóng to quanh box; người dưới 8 px vốn chỉ vài pixel, nhìn mờ là đúng như mô hình thấy.",
        "Phân loại nguyên nhân (lóa, vật trôi, che khuất, nhãn sai...) làm bằng mắt từ các ảnh trên; ghi vào luận văn kèm số ảnh đã xem.",
    ]

    md = [f"# {title}", "", intro, "", "| Nhóm | Người | Thấy | Bỏ sót | Báo nhầm | Recall | Precision |", "|---|---|---|---|---|---|---|"]
    md += [f"| {label} | {t['n_gt']} | {t['tp']} | {t['fn']} | {t['fp']} | {_vn(t['recall'])} | {_vn(t['precision'])} |" for label, t in table]
    md += ["", "## Bỏ sót tiêu biểu", "", "Mỗi nhóm kích thước, người to nhất trong số bị bỏ sót (khung đỏ).", ""]
    for size, n, chosen in fn_sections:
        md += [f"**{size} px** ({n} người bị bỏ sót)", "", " ".join(f"![{f['image']}]({f['crop']})" for f in chosen), "",
               ", ".join(f"`{f['image']}` ({_vn(f['px'], 1)} px)" for f in chosen), ""]
    md += ["## Báo nhầm tiêu biểu", "", f"Báo nhầm có conf cao nhất (khung cam), trong {len(fps)} báo nhầm.", "",
           " ".join(f"![{f['image']}]({f['crop']})" for f in fp_chosen), "",
           ", ".join(f"`{f['image']}` (conf {_vn(f['conf'], 2)}, {_vn(f['px'], 1)} px)" for f in fp_chosen), "",
           "## Ghi chú", "", *[f"- {n}" for n in notes]]
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    def figure(f: dict[str, Any], caption: str) -> str:
        return f'<figure><img src="{f["crop"]}"><figcaption>{escape(f["image"])}<br>{caption}</figcaption></figure>'

    body = [f"<h1>{escape(title)}</h1>", f"<p>{escape(intro)}</p>", "<table><tr><th>Nhóm</th><th>Người</th><th>Thấy</th>"
            "<th>Bỏ sót</th><th>Báo nhầm</th><th>Recall</th><th>Precision</th></tr>"]
    body += [f"<tr><td>{escape(label)}</td><td>{t['n_gt']}</td><td>{t['tp']}</td><td>{t['fn']}</td><td>{t['fp']}</td>"
             f"<td>{_vn(t['recall'])}</td><td>{_vn(t['precision'])}</td></tr>" for label, t in table]
    body += ["</table>", "<h2>Bỏ sót tiêu biểu</h2><p>Mỗi nhóm kích thước, người to nhất trong số bị bỏ sót (khung đỏ).</p>"]
    for size, n, chosen in fn_sections:
        body += [f"<h3>{escape(size)} px ({n} người bị bỏ sót)</h3><div class=g>",
                 *[figure(f, f"{_vn(f['px'], 1)} px") for f in chosen], "</div>"]
    body += [f"<h2>Báo nhầm tiêu biểu</h2><p>Conf cao nhất (khung cam), trong {len(fps)} báo nhầm.</p><div class=g>",
             *[figure(f, f"conf {_vn(f['conf'], 2)} · {_vn(f['px'], 1)} px") for f in fp_chosen], "</div>",
             "<h2>Ghi chú</h2><ul>", *[f"<li>{escape(n)}</li>" for n in notes], "</ul>"]
    (out / "report.html").write_text(
        '<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>' + escape(title) + "</title><style>"
        "body{font:14px/1.45 system-ui,sans-serif;max-width:1100px;margin:24px auto;padding:0 16px;color:#1d2430}"
        "table{border-collapse:collapse}td,th{border-bottom:1px solid #ddd;padding:4px 10px;text-align:right}"
        "td:first-child,th:first-child{text-align:left}.g{display:flex;flex-wrap:wrap;gap:10px}"
        "figure{margin:0;width:192px;font-size:12px}img{width:192px;height:192px;image-rendering:pixelated}"
        "</style></head><body>" + "".join(body) + "</body></html>",
        encoding="utf-8",
    )
    return out
