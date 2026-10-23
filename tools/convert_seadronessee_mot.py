"""Chuyển SeaDronesSee-MOT (bản COCO có video_id, frame_index, track_id, metadata drone) thành chuỗi chạy pipeline.

Mỗi video ra một thư mục <dst>/<video>/ gồm:
- frames/<số thứ tự 6 chữ số>.jpg: khung theo đúng thứ tự trong video (liên kết cứng), để `edge.main --source` đọc;
- telemetry.csv: t, lat, lon, alt_agl_m, yaw_deg, pitch_deg từ metadata từng khung (t = số thứ tự / --fps);
- truth.json: người thật theo khung (box pixel, track_id), lớp swimmer và swimmer with life jacket; thuyền bỏ;
- info.json: độ cao, góc gimbal, tốc độ, để chọn video hợp giả định camera nhìn thẳng xuống.

Quy ước góc: metadata ghi gimbal_pitch 90 là nhìn thẳng xuống; telemetry của dự án dùng −90 (shared/schema.py).
Hướng đỉnh ảnh lấy gimbal_heading (hướng camera), không phải compass_heading (hướng thân máy).

Ví dụ:
    .venv/bin/python tools/convert_seadronessee_mot.py --src data/raw/seadronessee_mot --dst data/processed/sds_mot
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import statistics
from collections import defaultdict
from pathlib import Path

from shared.config import parse_args_with_config

PERSON_NAMES = {"swimmer", "swimmer with life jacket"}


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", type=Path, required=True, help="Thư mục có annotations/*.json và images/<split>/")
    parser.add_argument("--dst", type=Path, required=True, help="Thư mục đích, mỗi video một thư mục con")
    parser.add_argument("--splits", nargs="+", default=["train", "val"], help="Các file annotations/<split>.json")
    parser.add_argument("--fps", type=float, default=30.0, help="FPS gốc của video (metadata không ghi; DJI thường 30)")
    return parse_args_with_config(parser)


def signed(value: float, ref: str, negative: str) -> float:
    return -abs(value) if ref.upper() == negative else abs(value)


def link(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def video_name(image: dict) -> str:
    """Tên thư mục cho video: drone và tên file gốc, chỉ ký tự an toàn."""
    source = image.get("source", {})
    raw = f"{source.get('drone', 'drone')}-{Path(source.get('video', str(image['video_id']))).stem}-v{image['video_id']}"
    return "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in raw)


def main() -> None:
    """Gom ảnh theo video, sắp theo frame_index, ghi khung, telemetry, nhãn và thông tin từng video."""
    args = parse_args()
    summary = []
    for split in args.splits:
        data = json.loads((args.src / "annotations" / f"{split}.json").read_text(encoding="utf-8"))
        person_ids = {c["id"] for c in data["categories"] if c["name"] in PERSON_NAMES}
        boxes = defaultdict(list)
        for ann in data["annotations"]:
            if ann["category_id"] in person_ids:
                x, y, w, h = ann["bbox"]
                boxes[ann["image_id"]].append({"box": [x, y, x + w, y + h], "track_id": ann["track_id"]})
        videos = defaultdict(list)
        for image in data["images"]:
            videos[image["video_id"]].append(image)

        for images in videos.values():
            images.sort(key=lambda im: im["frame_index"])
            name = f"{split}-{video_name(images[0])}"
            out = args.dst / name
            (out / "frames").mkdir(parents=True, exist_ok=True)
            truth, rows = {}, []
            for i, image in enumerate(images):
                link(args.src / "images" / split / image["file_name"], out / "frames" / f"{i:06d}.jpg")
                meta = image["meta"]
                rows.append({
                    "t": f"{i / args.fps:.4f}",
                    "lat": signed(meta["gps_latitude"], meta.get("gps_latitude_ref", "N"), "S"),
                    "lon": signed(meta["gps_longitude"], meta.get("gps_longitude_ref", "E"), "W"),
                    "alt_agl_m": max(meta["altitude"], 0.1),
                    "yaw_deg": meta.get("gimbal_heading", meta.get("compass_heading", 0.0)),
                    "pitch_deg": -meta.get("gimbal_pitch", 90.0),
                })
                truth[str(i)] = boxes.get(image["id"], [])
            with (out / "telemetry.csv").open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
            (out / "truth.json").write_text(json.dumps(truth), encoding="utf-8")
            gaps = [b["frame_index"] - a["frame_index"] for a, b in zip(images, images[1:])]
            info = {
                "video": name, "source": images[0].get("source"), "frames": len(images),
                "frame_index": [images[0]["frame_index"], images[-1]["frame_index"]],
                "non_consecutive_steps": sum(g != 1 for g in gaps),
                "tracks": len({b["track_id"] for v in truth.values() for b in v}),
                "person_boxes": sum(len(v) for v in truth.values()),
                "altitude_m": [min(r["alt_agl_m"] for r in rows), max(r["alt_agl_m"] for r in rows)],
                "gimbal_pitch_deg": [min(-r["pitch_deg"] for r in rows), max(-r["pitch_deg"] for r in rows)],
                "speed_median_mps": statistics.median(im["meta"].get("speed", 0.0) for im in images),
                "width": images[0]["width"], "height": images[0]["height"],
            }
            (out / "info.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
            summary.append(info)
            print(f"{name}: {info['frames']} khung, {info['tracks']} người, cao {info['altitude_m'][0]:.0f}–{info['altitude_m'][1]:.0f} m, "
                  f"gimbal {info['gimbal_pitch_deg'][0]:.0f}–{info['gimbal_pitch_deg'][1]:.0f}°, tốc độ {info['speed_median_mps']:.1f} m/s")
    (args.dst / "videos.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
