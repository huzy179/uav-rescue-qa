"""Đổi cỡ khung bằng torch (--gpu-resize, edge/detector.py resize_torch): chạy trên CPU, không cần GPU hay mô hình."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from edge.detector import YoloDetector, resize_torch, torch_device


def smooth_frame(h: int = 360, w: int = 640) -> np.ndarray:
    rng = np.random.default_rng(0)
    return cv2.GaussianBlur(rng.integers(0, 256, (h, w, 3)).astype(np.uint8), (0, 0), 3)


def test_torch_device() -> None:
    assert torch_device("0") == "cuda:0"
    assert torch_device("cuda:1") == "cuda:1"
    assert torch_device("cpu") == "cpu"


@pytest.mark.parametrize(("size", "interp"), [((270, 152), cv2.INTER_AREA), ((213, 120), cv2.INTER_AREA), ((960, 540), cv2.INTER_LINEAR)])
def test_resize_torch_gan_cv2(size: tuple[int, int], interp: int) -> None:
    frame = smooth_frame()
    out, ref = resize_torch(frame, size), cv2.resize(frame, size, interpolation=interp)
    assert out.shape == ref.shape and out.dtype == np.uint8
    diff = np.abs(out.astype(int) - ref.astype(int))
    assert diff.mean() < 1.0 and diff.max() <= 8


class _RecordingDetector(YoloDetector):
    """YoloDetector không nạp mô hình: _predict ghi lại ảnh đầu vào, trả một box ở giữa mỗi ảnh."""

    def __init__(self, gpu_resize: bool) -> None:  # noqa: D107 - không gọi YoloDetector.__init__
        self.mode, self.imgsz, self.tile, self.overlap, self.full_pass = "full", 640, 640, 0.2, False
        self.tile_cache, self.allow_tile_reuse, self._warmed_up = None, False, True
        self.resize_device = "cpu" if gpu_resize else None
        self.seen: list[np.ndarray] = []

    def _predict(self, images: list[np.ndarray], imgsz: int) -> list[tuple[np.ndarray, np.ndarray]]:
        self.seen.extend(images)
        return [(np.array([[10.0, 10.0, 20.0, 20.0]], dtype=np.float32), np.array([0.9], dtype=np.float32)) for _ in images]


def test_tat_thi_nhu_cu() -> None:
    frame = smooth_frame()
    det = _RecordingDetector(gpu_resize=False)
    dets, _ = det.detect(frame, 0, 0.0, scale=2.5)
    expected = cv2.resize(frame, (256, 144), interpolation=cv2.INTER_AREA)
    assert np.array_equal(det.seen[0], expected)
    assert dets[0].box_px == pytest.approx((25.0, 25.0, 50.0, 50.0))


def test_bat_thi_dung_torch_box_van_ve_anh_goc() -> None:
    frame = smooth_frame()
    det = _RecordingDetector(gpu_resize=True)
    dets, _ = det.detect(frame, 0, 0.0, scale=2.5)
    assert np.array_equal(det.seen[0], resize_torch(frame, (256, 144), "cpu"))
    assert dets[0].box_px == pytest.approx((25.0, 25.0, 50.0, 50.0))


def test_per_image_timing_summarize() -> None:
    import pandas as pd

    from eval.per_image_timing import summarize

    row = summarize(pd.DataFrame({"tile_ms": [1.0, 2.0, 9.0], "infer_ms": [10.0, 20.0, 30.0]}))
    assert row["n_images"] == 3 and row["tile_ms_median"] == 2.0 and row["infer_ms_mean"] == 20.0
    assert "tile_ms_p95" in summarize(pd.DataFrame({"tile_ms": [1.0]})) and "infer_ms_median" not in summarize(pd.DataFrame({"tile_ms": [1.0]}))
