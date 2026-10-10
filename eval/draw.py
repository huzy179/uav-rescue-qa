"""Vẽ box phát hiện lên ảnh."""

from __future__ import annotations

from typing import Sequence

import cv2
import numpy as np

BOX_COLOR_BGR = (0, 0, 255)


def draw_boxes(
    image: np.ndarray, boxes_xyxy: Sequence[Sequence[float]], confs: Sequence[float]
) -> np.ndarray:
    """Trả về bản sao của ảnh có vẽ box và độ tin cậy; nét mảnh để không che mất vật thể nhỏ."""
    canvas = image.copy()
    thickness = 2 if max(canvas.shape[:2]) >= 2000 else 1
    font_scale = 0.5 * thickness
    for (x1, y1, x2, y2), conf in zip(boxes_xyxy, confs):
        p1 = (int(round(x1)), int(round(y1)))
        p2 = (int(round(x2)), int(round(y2)))
        cv2.rectangle(canvas, p1, p2, BOX_COLOR_BGR, thickness, cv2.LINE_AA)
        cv2.putText(
            canvas,
            f"{conf:.2f}",
            (p1[0], max(p1[1] - 3, 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            BOX_COLOR_BGR,
            thickness,
            cv2.LINE_AA,
        )
    return canvas
