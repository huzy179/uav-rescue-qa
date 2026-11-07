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
from sim.flight import StraightFlight, ZigzagFlight

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

    def scaled(self, factor: float) -> RecallCurve:
        """Đường recall khi khung bị thu nhỏ factor lần trước khi phát hiện: người px trên ảnh gốc còn px/factor."""
        return RecallCurve(
            tuple(lo * factor for lo in self.lo), tuple(hi * factor for hi in self.hi), self.recall
        )


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
    flight: StraightFlight | ZigzagFlight, n: int, along_m: tuple[float, float], lateral_m: float, drift_mps: float,
    seed: int, right_m: tuple[float, float] | None = None, group_size: int = 1, group_spread_m: float = 2.0,
) -> list[Person]:
    """Rải n người: cách điểm xuất phát along_m (mét, theo hướng bay), lệch ngang tối đa ±lateral_m.

    right_m (bay zig-zag): lệch ngang lấy đều trong khoảng này thay cho ±lateral_m, để phủ cả vùng quét.
    group_size > 1: rải tâm nhóm như trên, mỗi nhóm group_size người (nhóm cuối có thể ít hơn) nằm đều trong hình tròn
    bán kính group_spread_m quanh tâm, trôi cùng vận tốc. group_size = 1 giữ đúng chuỗi ngẫu nhiên cũ.
    """
    if group_size > 1:
        centers = place_people(flight, math.ceil(n / group_size), along_m, lateral_m, drift_mps, seed, right_m)
        rng = random.Random(seed + 7)
        people = []
        for center in centers:
            for _ in range(min(group_size, n - len(people))):
                r = group_spread_m * math.sqrt(rng.random())
                a = rng.uniform(0.0, 2.0 * math.pi)
                lat, lon = offset_gps(center.lat, center.lon, r * math.cos(a), r * math.sin(a))
                people.append(Person(len(people), lat, lon, center.drift_n_mps, center.drift_e_mps))
        return people
    rng = random.Random(seed)
    yaw = math.radians(flight.yaw_deg)
    people = []
    for i in range(n):
        forward = rng.uniform(*along_m)
        right = rng.uniform(*right_m) if right_m is not None else rng.uniform(-lateral_m, lateral_m)
        north = forward * math.cos(yaw) - right * math.sin(yaw)
        east = forward * math.sin(yaw) + right * math.cos(yaw)
        lat, lon = offset_gps(flight.lat0, flight.lon0, north, east)
        heading = rng.uniform(0.0, 2.0 * math.pi)
        people.append(Person(i, lat, lon, drift_mps * math.cos(heading), drift_mps * math.sin(heading)))
    return people


def visible_boxes(
    people: list[Person], tel: Telemetry, cam: Camera, t: float, person_m: float = PERSON_WIDTH_M
) -> list[tuple[int, tuple[float, float, float, float]]]:
    """(person_id, box) của những người có tâm nằm trong khung, theo telemetry THẬT; box vuông cạnh bằng person_m.

    person_m là cỡ box người THẬT trong cảnh (box nhãn SeaDronesSee lớn hơn 0,5 m khoảng 1,8–2,6 lần,
    docs/results/person_px_check.md); pipeline vẫn ước lượng theo 0,5 m của nó.
    """
    half = person_m / 2.0 * cam.f_px / tel.alt_agl_m
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

    def __init__(self, sigma_m: float, tau_s: float, seed: int, profile: Callable[[float], float] | None = None) -> None:
        """profile: σ theo thời gian (sim.flight.SigmaProfile) thay cho σ cố định. Khi đó sai số = σ(t)·z(t), z là quá
        trình Gauss–Markov đơn vị cùng τ: độ lớn sai số đổi ngay theo σ(t), như khi GPS mất vệ tinh."""
        self.sigma_m, self.tau_s, self.profile = sigma_m, tau_s, profile
        self._rng = random.Random(seed)
        self._unit = profile is not None
        scale = 1.0 if self._unit else sigma_m
        self._error = (self._rng.gauss(0, scale), self._rng.gauss(0, scale)) if scale > 0 else (0.0, 0.0)
        self._t: float | None = None

    def sigma_at(self, t: float) -> float:
        """σ mỗi trục tại t (cái mà bộ thu GPS lý tưởng sẽ báo)."""
        return self.profile(t) if self.profile is not None else self.sigma_m

    def step(self, t: float) -> tuple[float, float]:
        """Sai số (bắc, đông) tại t; phải gọi với t tăng dần."""
        scale = 1.0 if self._unit else self.sigma_m
        if self._t is not None and scale > 0:
            decay = math.exp(-(t - self._t) / self.tau_s)
            spread = scale * math.sqrt(1.0 - decay**2)
            north, east = self._error
            self._error = (north * decay + spread * self._rng.gauss(0, 1), east * decay + spread * self._rng.gauss(0, 1))
        self._t = t
        if self._unit:
            sigma = self.sigma_at(t)
            return (self._error[0] * sigma, self._error[1] * sigma)
        return self._error


def noisy_telemetry(tel: Telemetry, gps: GaussMarkovGps, yaw_bias_deg: float = 0.0, alt_bias_m: float = 0.0) -> Telemetry:
    """Telemetry UAV thấy: vị trí thật cộng sai số GPS, hướng và độ cao thật cộng sai số cố định.

    alt_bias_m: độ cao đo (khí áp kế, so với điểm cất cánh) lệch so với độ cao thật trên mặt nước; làm vị trí xa tâm
    ảnh lệch theo tỉ lệ d·δh/h và làm sai hệ số thu nhỏ theo độ cao (TECHNICAL 8.4).
    """
    north, east = gps.step(tel.t)
    lat, lon = offset_gps(tel.lat, tel.lon, north, east)
    return tel.model_copy(update={
        "lat": lat, "lon": lon, "yaw_deg": (tel.yaw_deg + yaw_bias_deg) % 360.0, "alt_agl_m": tel.alt_agl_m + alt_bias_m,
    })


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
