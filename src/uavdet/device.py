"""Chọn thiết bị suy luận."""

from __future__ import annotations


def pick_device(requested: str | None = None) -> str:
    """Trả về thiết bị người dùng yêu cầu; nếu không có thì ưu tiên CUDA, rồi MPS, cuối cùng là CPU."""
    if requested:
        return requested
    import torch

    if torch.cuda.is_available():
        return "cuda:0"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"
