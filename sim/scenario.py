"""Kịch bản RQ3 hoàn toàn giả lập: người trên mặt nước, nhãn theo thời gian, nhiễu GPS, phát hiện giả (TECHNICAL mục 11.3).

Ba lớp tách biệt, vì mỗi lớp là một nguồn sai số riêng trong RQ3:
1. Sự thật: vị trí người và đường bay THẬT → nhãn theo thời gian bằng gps_to_pixel.
2. Cảm biến: telemetry mà UAV THẤY = đường bay thật + nhiễu GPS (Gauss–Markov). Pipeline chỉ thấy lớp này.
3. Detector: mỗi người trong khung được phát hiện với xác suất recall (cố định, hoặc theo cỡ người tính bằng px từ
   một đường recall đo được, RecallCurve); thêm báo nhầm theo phân phối Poisson.
"""

from __future__ import annotations

import csv
import math
import random
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from edge.georef import Camera, gps_to_pixel, offset_gps
from shared.schema import Detection, Telemetry
from sim.flight import StraightFlight

PERSON_WIDTH_M = 0.5  # như scripts/gsd_calc.py


@dataclass(frozen=True)
class RecallCurve:
    """Recall theo cạnh ngắn người (px), dạng bậc thang theo nhóm [lo, hi) như eval/recall_by_pixels.py.

    Cỡ người ngoài mọi nhóm lấy recall của nhóm gần nhất.
    """

    lo: tuple[float, ...]
    hi: tuple[float, ...]
    recall: tuple[float, ...]

    @classmethod
    def from_csv(cls, path: Path, model: str | None = None) -> RecallCurve:
        """Đọc recall_by_pixels.csv (cột model, lo, hi, recall); model=None khi file chỉ có một mô hình."""
        with path.open(encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if model is None or r.get("model") == model]
        if not rows:
            raise ValueError(f"{path} không có dòng nào cho mô hình {model!r}")
        rows.sort(key=lambda r: float(r["lo"]))
        return cls(tuple(float(r["lo"]) for r in rows), tuple(float(r["hi"]) for r in rows), tuple(float(r["recall"]) for r in rows))

    def __call__(self, px: float) -> float:
        for lo, hi, r in zip(self.lo, self.hi, self.recall):
            if lo <= px < hi:
                return r
        return self.recall[0] if px < self.lo[0] else self.recall[-1]


@dataclass(frozen=True)
class Person:
    """Một người thật: đứng yên hoặc trôi theo dòng nước với vận tốc không đổi."""

    person_id: int
    lat: float
    lon: float
    drift_n_mps: float = 0.0
    drift_e_mps: float = 0.0

    def at(self, t: float) -> tuple[float, float]:
        return offset_gps(self.lat, self.lon, self.drift_n_mps * t, self.drift_e_mps * t)


def place_people(
    flight: StraightFlight, n: int, along_m: tuple[float, float], lateral_m: float, drift_mps: float, seed: int
) -> list[Person]:
    """Rải n người dọc đường bay: cách điểm xuất phát along_m (mét, theo hướng bay), lệch ngang tối đa ±lateral_m."""
    rng = random.Random(seed)
    yaw = math.radians(flight.yaw_deg)
    people = []
    for i in range(n):
        forward, right = rng.uniform(*along_m), rng.uniform(-lateral_m, lateral_m)
        north = forward * math.cos(yaw) - right * math.sin(yaw)
        east = forward * math.sin(yaw) + right * math.cos(yaw)
        lat, lon = offset_gps(flight.lat0, flight.lon0, north, east)
        heading = rng.uniform(0.0, 2.0 * math.pi)
        people.append(Person(i, lat, lon, drift_mps * math.cos(heading), drift_mps * math.sin(heading)))
    return people


def visible_boxes(people: list[Person], tel: Telemetry, cam: Camera, t: float) -> list[tuple[int, tuple[float, float, float, float]]]:
    """(person_id, box) của những người có tâm nằm trong khung, theo telemetry THẬT; box vuông cạnh bằng bề ngang người."""
    half = PERSON_WIDTH_M / 2.0 * cam.f_px / tel.alt_agl_m
    boxes = []
    for person in people:
        u, v = gps_to_pixel(*person.at(t), tel, cam)
        if 0 <= u < cam.width and 0 <= v < cam.height:
            boxes.append((person.person_id, (u - half, v - half, u + half, v + half)))
    return boxes


class GaussMarkovGps:
    """Nhiễu GPS tương quan theo thời gian (Gauss–Markov bậc 1, mỗi trục Bắc/Đông), TECHNICAL mục 8.4.

    e(t+dt) = e(t)·exp(−dt/τ) + σ·√(1 − exp(−2dt/τ))·N(0, 1): độ lệch chuẩn dừng là σ, sai số "trôi chậm" với thời
    gian tương quan τ. GPS thật lệch chậm như vậy, không nhảy ngẫu nhiên độc lập mỗi khung.
    """

    def __init__(self, sigma_m: float, tau_s: float, seed: int) -> None:
        self.sigma_m, self.tau_s = sigma_m, tau_s
        self._rng = random.Random(seed)
        self._error = (self._rng.gauss(0, sigma_m), self._rng.gauss(0, sigma_m)) if sigma_m > 0 else (0.0, 0.0)
        self._t: float | None = None

    def step(self, t: float) -> tuple[float, float]:
        """Sai số (bắc, đông) tại t; phải gọi với t tăng dần."""
        if self._t is not None and self.sigma_m > 0:
            decay = math.exp(-(t - self._t) / self.tau_s)
            spread = self.sigma_m * math.sqrt(1.0 - decay**2)
            north, east = self._error
            self._error = (north * decay + spread * self._rng.gauss(0, 1), east * decay + spread * self._rng.gauss(0, 1))
        self._t = t
        return self._error


def noisy_telemetry(tel: Telemetry, gps: GaussMarkovGps, yaw_bias_deg: float = 0.0) -> Telemetry:
    """Telemetry UAV thấy: vị trí thật cộng sai số GPS, hướng thật cộng sai số la bàn cố định."""
    north, east = gps.step(tel.t)
    lat, lon = offset_gps(tel.lat, tel.lon, north, east)
    return tel.model_copy(update={"lat": lat, "lon": lon, "yaw_deg": (tel.yaw_deg + yaw_bias_deg) % 360.0})


def tilted_view(tel: Telemetry, tilt_deg: float) -> Telemetry:
    """Telemetry "ảo" nhìn thẳng xuống có cùng vùng chụp với camera thật nghiêng tilt_deg về phía trước.

    Camera nghiêng θ thì tâm ảnh nhìn vào điểm cách điểm dưới UAV h·tanθ về phía trước; pipeline vẫn giả định
    nhìn thẳng xuống nên mọi toạ độ lệch khoảng đó (TECHNICAL mục 8.4).
    shortcut: chỉ dời tâm vùng chụp, bỏ méo phối cảnh (vùng xa camera to hơn); đủ cho θ vài độ, dùng phép chiếu
    tổng quát ở mục 8.3 nếu cần góc lớn.
    """
    if tilt_deg == 0:
        return tel
    forward = tel.alt_agl_m * math.tan(math.radians(tilt_deg))
    yaw = math.radians(tel.yaw_deg)
    lat, lon = offset_gps(tel.lat, tel.lon, forward * math.cos(yaw), forward * math.sin(yaw))
    return tel.model_copy(update={"lat": lat, "lon": lon})


def simulate_detections(
    frame_id: int,
    t: float,
    boxes: list[tuple[int, tuple[float, float, float, float]]],
    cam: Camera,
    recall: float | Callable[[float], float],
    fp_per_frame: float,
    rng: random.Random,
) -> list[Detection]:
    """Phát hiện giả của một khung: mỗi người thấy với xác suất recall (conf 0,3–0,9), cộng báo nhầm Poisson (conf 0,1–0,4).

    recall là số cố định, hoặc hàm của cạnh ngắn box người (px), ví dụ RecallCurve đo ở E6.
    shortcut: các khung độc lập với nhau (người khó thấy ở khung này không khó hơn ở khung sau); điều kiện ảnh bỏ qua.
    """
    dets = []
    for _, box in boxes:
        p = recall(min(box[2] - box[0], box[3] - box[1])) if callable(recall) else recall
        if rng.random() < p:
            dets.append(Detection(frame_id=frame_id, t=t, box_px=box, conf=rng.uniform(0.3, 0.9)))
    side = boxes[0][1][2] - boxes[0][1][0] if boxes else 25.0
    for _ in range(_poisson(fp_per_frame, rng)):
        x, y = rng.uniform(0, cam.width - side), rng.uniform(0, cam.height - side)
        dets.append(Detection(frame_id=frame_id, t=t, box_px=(x, y, x + side, y + side), conf=rng.uniform(0.1, 0.4)))
    return dets


def _poisson(mean: float, rng: random.Random) -> int:
    """Rút số nguyên theo phân phối Poisson (thuật toán Knuth; đủ nhanh với trung bình nhỏ)."""
    limit, k, p = math.exp(-mean), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1
