"""Kịch bản RQ3 hoàn toàn giả lập: người trên mặt nước, nhãn theo thời gian, nhiễu GPS, phát hiện giả (TECHNICAL mục 11.3).

Ba lớp tách biệt, vì mỗi lớp là một nguồn sai số riêng trong RQ3:
1. Sự thật: vị trí người và đường bay THẬT → nhãn theo thời gian bằng gps_to_pixel.
2. Cảm biến: telemetry mà UAV THẤY = đường bay thật + nhiễu GPS (Gauss–Markov). Pipeline chỉ thấy lớp này.
3. Detector: mỗi người trong khung được phát hiện với xác suất recall; thêm báo nhầm theo phân phối Poisson.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from edge.georef import Camera, gps_to_pixel, offset_gps
from shared.schema import Detection, Telemetry
from sim.flight import StraightFlight

PERSON_WIDTH_M = 0.5  # như scripts/gsd_calc.py


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


def noisy_telemetry(tel: Telemetry, gps: GaussMarkovGps) -> Telemetry:
    """Telemetry UAV thấy: vị trí thật cộng sai số GPS."""
    north, east = gps.step(tel.t)
    lat, lon = offset_gps(tel.lat, tel.lon, north, east)
    return tel.model_copy(update={"lat": lat, "lon": lon})


def simulate_detections(
    frame_id: int,
    t: float,
    boxes: list[tuple[int, tuple[float, float, float, float]]],
    cam: Camera,
    recall: float,
    fp_per_frame: float,
    rng: random.Random,
) -> list[Detection]:
    """Phát hiện giả của một khung: mỗi người thấy với xác suất recall (conf 0,3–0,9), cộng báo nhầm Poisson (conf 0,1–0,4).

    shortcut: recall không phụ thuộc kích thước người và điều kiện ảnh; thay bằng recall theo nhóm kích thước đo ở RQ1.
    """
    dets = []
    for _, box in boxes:
        if rng.random() < recall:
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
