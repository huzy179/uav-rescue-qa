"""Kiểm tra phần cắt ô và gộp box của detector (không nạp mô hình)."""

import numpy as np

from edge.detector import merge_boxes, tile_origins


def test_tile_origins_4k() -> None:
    """3840×2160, ô 640, chồng 0,2: 8 × 4 = 32 ô như TECHNICAL mục 4.2; ô cuối sát mép."""
    xs, ys = tile_origins(3840, 640, 0.2), tile_origins(2160, 640, 0.2)
    assert len(xs) * len(ys) == 32
    assert xs[0] == 0 and xs[-1] == 3840 - 640
    assert ys[-1] == 2160 - 640


def test_tile_origins_small_image() -> None:
    assert tile_origins(500, 640, 0.2) == [0]
    assert tile_origins(640, 640, 0.2) == [0]


def test_merge_half_box_into_full_box() -> None:
    """Box nửa người (IoU 0,5 nhưng IOS 1) bị box đầy đủ điểm cao hơn nuốt; box ở chỗ khác được giữ."""
    boxes = np.array([[0, 0, 10, 20], [0, 0, 10, 10], [100, 100, 110, 120.0]])
    confs = np.array([0.95, 0.9, 0.5])
    assert sorted(merge_boxes(boxes, confs).tolist()) == [0, 2]


def test_merge_empty() -> None:
    assert merge_boxes(np.zeros((0, 4)), np.zeros(0)).size == 0


def test_replay_detector_drops_old_location(tmp_path) -> None:
    from edge.detector import ReplayDetector
    from shared.schema import Detection

    path = tmp_path / "detections.jsonl"
    rows = [Detection(frame_id=15, t=0.5, box_px=(1, 2, 3, 4), conf=0.4, lat=21.0, lon=105.0)]
    path.write_text("".join(d.model_dump_json() + "\n" for d in rows), encoding="utf-8")
    replay = ReplayDetector(path)
    dets, _ = replay.detect(np.zeros((1, 1, 3)), 15, 0.5)
    assert [(d.box_px, d.lat) for d in dets] == [((1, 2, 3, 4), None)]
    assert replay.detect(np.zeros((1, 1, 3)), 16, 1.0)[0] == []
