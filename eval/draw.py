"""Vẽ box phát hiện và chữ (có dấu tiếng Việt) lên ảnh BGR."""

from __future__ import annotations

import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BOX_COLOR_BGR = (0, 0, 255)
# Font có dấu tiếng Việt; không có font nào thì put_text bỏ dấu và vẽ bằng cv2.putText (Jetson thiếu font vẫn chạy).
FONT_PATHS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
)


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


@lru_cache(maxsize=32)
def _font(size_px: int) -> ImageFont.FreeTypeFont | None:
    for path in FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, size_px)
    return None


def strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt (kể cả đ), dùng khi không có font Unicode."""
    text = text.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def text_size(text: str, size_px: int, stroke_px: int = 0) -> tuple[int, int]:
    """Rộng, cao (px) của dòng chữ khi vẽ bằng put_text."""
    font = _font(size_px)
    if font is None:
        (w, h), base = cv2.getTextSize(strip_accents(text), cv2.FONT_HERSHEY_SIMPLEX, size_px / 30, max(1, stroke_px))
        return w, h + base
    x0, y0, x1, y1 = font.getbbox(text, stroke_width=stroke_px)
    return x1, y1


def put_text(
    image: np.ndarray, text: str, top_left: tuple[int, int], size_px: int, color_bgr: tuple[int, int, int],
    stroke_px: int = 0, stroke_bgr: tuple[int, int, int] = (0, 0, 0),
) -> np.ndarray:
    """Vẽ một dòng chữ lên ảnh BGR tại chỗ (góc trên trái), có viền để đọc được trên mọi nền; trả lại chính ảnh đó.

    Chỉ chuyển sang PIL vùng nhỏ quanh dòng chữ, không chuyển cả khung 4K.
    """
    font = _font(size_px)
    x, y = top_left
    if font is None:
        plain, scale = strip_accents(text), size_px / 30
        base_y = y + text_size(text, size_px, stroke_px)[1]
        if stroke_px:
            cv2.putText(image, plain, (x, base_y), cv2.FONT_HERSHEY_SIMPLEX, scale, stroke_bgr, 2 * stroke_px + 2, cv2.LINE_AA)
        cv2.putText(image, plain, (x, base_y), cv2.FONT_HERSHEY_SIMPLEX, scale, color_bgr, max(1, stroke_px), cv2.LINE_AA)
        return image
    w, h = text_size(text, size_px, stroke_px)
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w + stroke_px, image.shape[1]), min(y + h + stroke_px, image.shape[0])
    if x1 <= x0 or y1 <= y0:
        return image
    patch = Image.fromarray(np.ascontiguousarray(image[y0:y1, x0:x1, ::-1]))
    ImageDraw.Draw(patch).text(
        (x - x0, y - y0), text, font=font, fill=tuple(reversed(color_bgr)),
        stroke_width=stroke_px, stroke_fill=tuple(reversed(stroke_bgr)),
    )
    image[y0:y1, x0:x1] = np.asarray(patch)[:, :, ::-1]
    return image
