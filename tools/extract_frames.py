"""Trích khung từ video lũ để gán nhãn, theo quy tắc ở mục 1 của docs/LABELING.md.

- Hai khung cùng video cách nhau ít nhất `--min-gap-s` giây.
- Khung phải khác rõ mọi khung đã giữ của cùng video: dHash lệch ít nhất `--min-hamming` bit (eval/splits.py).
- Bỏ khung gần như một màu (màn đen, chữ chuyển cảnh): độ lệch chuẩn độ xám dưới `--min-std`.
- Giữ tối đa `--max-frames` khung mỗi video, rải đều theo thời gian.
- Tên file `<video_id>_<số khung 6 chữ số>.jpg`, khớp quy ước chia tập theo video (eval/splits.py).

Không lọc theo có người hay không: khung không có người cũng cần cho tập test (đo báo động giả).

Ví dụ:
    .venv/bin/python tools/extract_frames.py --videos data/raw/flood/videos/*.mp4
    .venv/bin/python tools/extract_frames.py --videos clip.mp4 --video-id yagi-haiphong-01 --max-frames 20
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from eval.frames import make_video_id, save_frames, scan_video, select_frames
from shared.config import parse_args_with_config

MANIFEST_FIELDS = ["video_id", "video", "frame", "t_s", "dhash", "file"]


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--videos", type=Path, nargs="+", required=True, help="Các file video")
    parser.add_argument("--video-id", default=None, help="Mã video (chỉ khi có một video); mặc định lấy từ tên file")
    parser.add_argument("--out", type=Path, default=Path("data/raw/flood/frames"), help="Thư mục ghi khung")
    parser.add_argument("--manifest", type=Path, default=Path("data/raw/flood/frames_manifest.csv"), help="CSV ghi lại khung đã trích")
    parser.add_argument("--sources", type=Path, default=Path("data/raw/flood/sources.csv"), help="sources.csv để kiểm tra video đã ghi nguồn")
    parser.add_argument("--min-gap-s", type=float, default=2.0, help="Khoảng cách tối thiểu giữa hai khung (giây)")
    parser.add_argument("--max-frames", type=int, default=30, help="Số khung tối đa mỗi video")
    parser.add_argument("--min-hamming", type=int, default=10, help="Số bit dHash tối thiểu khác mọi khung đã giữ")
    parser.add_argument("--min-std", type=float, default=5.0, help="Bỏ khung có độ lệch chuẩn độ xám nhỏ hơn (màn một màu)")
    parser.add_argument("--jpeg-quality", type=int, default=100, help="Chất lượng JPEG khi lưu (giữ gần nguyên chất lượng gốc)")
    parser.add_argument("--overwrite", action="store_true", help="Cho phép ghi đè khung đã có của video")
    return parse_args_with_config(parser)


def read_manifest(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: (r["video_id"], int(r["frame"])))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def known_sources(path: Path) -> set[str] | None:
    """Các video_id đã có trong sources.csv; None nếu chưa có file."""
    if not path.is_file():
        return None
    with path.open(newline="", encoding="utf-8") as f:
        return {row.get("video_id", "").strip() for row in csv.DictReader(f)}


def main() -> None:
    """Trích khung cho từng video, cập nhật manifest, nhắc ghi nguồn còn thiếu."""
    args = parse_args()
    if args.video_id and len(args.videos) > 1:
        raise SystemExit("--video-id chỉ dùng được khi có một video")
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = read_manifest(args.manifest)
    sources = known_sources(args.sources)
    missing_sources: list[str] = []

    for path in args.videos:
        video_id = make_video_id(args.video_id or path.stem)
        existing = sorted(args.out.glob(f"{video_id}_[0-9][0-9][0-9][0-9][0-9][0-9].jpg"))
        if existing and not args.overwrite:
            print(f"[bỏ qua] {path.name}: đã có {len(existing)} khung của {video_id} (dùng --overwrite để trích lại)")
            continue
        for file in existing:
            file.unlink()

        candidates, fps = scan_video(path, args.min_gap_s, args.min_std)
        chosen = select_frames(candidates, args.max_frames, args.min_hamming)
        if not chosen:
            print(f"[cảnh báo] {path.name}: không có khung nào đạt điều kiện")
            continue
        files = save_frames(path, chosen, args.out, video_id, args.jpeg_quality)

        manifest = [r for r in manifest if r["video_id"] != video_id]
        manifest += [
            {"video_id": video_id, "video": path.name, "frame": str(c.frame), "t_s": f"{c.t_s:.3f}",
             "dhash": f"{c.hash:016x}", "file": f.name}
            for c, f in zip(chosen, files)
        ]
        print(f"{path.name} → {video_id}: {fps:.2f} FPS, {len(candidates)} ứng viên, giữ {len(chosen)} khung")
        if sources is not None and video_id not in sources:
            missing_sources.append(video_id)

    write_manifest(args.manifest, manifest)
    print(f"Khung lưu tại: {args.out}; manifest: {args.manifest}")
    if sources is None:
        print(f"[nhắc] Chưa có {args.sources}: mỗi video cần một dòng nguồn (docs/LABELING.md mục 1)")
    elif missing_sources:
        print(f"[nhắc] Chưa ghi nguồn trong {args.sources}: {', '.join(missing_sources)}")


if __name__ == "__main__":
    main()
