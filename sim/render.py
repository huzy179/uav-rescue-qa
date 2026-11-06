"""Ảnh tổng hợp cho chuyến bay mô phỏng: vùng ngập nhìn từ trên xuống, để video demo không chỉ là khung đen.

Dựng một lần một "mặt đất" phẳng (ảnh texture, mỗi pixel `res_m` mét) quanh điểm gốc: nước lũ đục có vân, mái nhà
nhô lên (một phần người đứng trên mái), cây. Mỗi khung lấy đúng vùng camera nhìn theo telemetry THẬT bằng một phép
affine cùng hình học với edge.georef.pixel_to_gps (camera nhìn thẳng xuống), rồi vẽ người ở vị trí của họ tại thời
điểm đó. Người vẽ thành chấm áo và đầu cỡ PERSON_WIDTH_M, đúng box mà detector giả (sim/scenario.py) dùng.

Chỉ để trình bày: ảnh không dùng để đo độ chính xác của detector (phát hiện vẫn là detector giả theo recall).
"""

from __future__ import annotations

import math
import random

import cv2
import numpy as np

from edge.georef import Camera, ground_offset_m, gps_to_pixel
from shared.schema import Telemetry
from sim.scenario import PERSON_WIDTH_M, Person

# BGR
WATER = (62, 104, 128)  # nước lũ màu phù sa
ROOFS = [(48, 70, 170), (60, 84, 150), (140, 130, 120), (150, 150, 145), (110, 90, 70)]  # ngói đỏ, tôn xám, tôn xanh
TREE = (40, 80, 45)
ROOF_GAP_M = 16.0  # khoảng cách tối thiểu giữa tâm hai mái
CLOTHES = [(0, 120, 255), (30, 30, 200), (200, 90, 20), (40, 200, 230), (230, 230, 230), (120, 40, 140)]


class FloodScene:
    """Mặt đất ngập lụt dựng sẵn quanh (lat0, lon0) trong khung [north_min, north_max] × [east_min, east_max] (mét)."""

    def __init__(
        self, lat0: float, lon0: float, extent_m: tuple[float, float, float, float], people: list[Person],
        res_m: float = 0.1, seed: int = 0, roof_share: float = 0.4,
    ) -> None:
        self.lat0, self.lon0, self.res_m = lat0, lon0, res_m
        self.n_min, self.n_max, self.e_min, self.e_max = extent_m
        self.people = people
        rng = random.Random(seed)
        np_rng = np.random.default_rng(seed)
        h = int(math.ceil((self.n_max - self.n_min) / res_m))
        w = int(math.ceil((self.e_max - self.e_min) / res_m))
        # Nước: màu nền cộng vân to (dòng chảy) và vân nhỏ (sóng), làm mờ cho mượt.
        big = cv2.resize(np_rng.normal(0, 1, (max(2, h // 400), max(2, w // 400))).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
        small = cv2.GaussianBlur(np_rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 6)
        # Vệt dòng chảy: nhiễu làm mờ mạnh theo một chiều, chỉ làm sáng (bọt, váng).
        streak = cv2.GaussianBlur(np_rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), sigmaX=40, sigmaY=2)
        streak = np.clip(streak / (streak.std() + 1e-6) - 1.2, 0, None)
        shade = 12 * big + 40 * small + 28 * streak
        self.texture = np.clip(np.array(WATER, np.float32)[None, None, :] + shade[..., None], 0, 255).astype(np.uint8)
        self.roof_people: set[int] = set()
        self.roofs: list[tuple[float, float]] = []  # tâm mái (bắc, đông), để mái không chồng nhau
        # Mái nhà dưới một phần người (người trú trên mái chờ cứu) và rải thêm nhà, cây cho cảnh có chi tiết. Người
        # đứng sát một mái đã có thì coi là ở trên mái đó (không vẽ gợn nước).
        area = (self.n_max - self.n_min) * (self.e_max - self.e_min)
        for person in people:
            if rng.random() < roof_share:
                self._roof(*self._local(person.lat, person.lon), rng)
        self.roof_people = {
            p.person_id for p in people if any(math.dist(self._local(p.lat, p.lon), c) < ROOF_GAP_M / 2 for c in self.roofs)
        }
        for _ in range(int(area / 2500)):
            self._roof(rng.uniform(self.n_min, self.n_max), rng.uniform(self.e_min, self.e_max), rng, avoid=people)
        for _ in range(int(area / 900)):
            self._tree(rng.uniform(self.n_min, self.n_max), rng.uniform(self.e_min, self.e_max), rng, avoid=people)
        for _ in range(int(area / 300)):
            self._debris(rng.uniform(self.n_min, self.n_max), rng.uniform(self.e_min, self.e_max), rng, avoid=people)

    def _local(self, lat: float, lon: float) -> tuple[float, float]:
        return ground_offset_m(self.lat0, self.lon0, lat, lon)

    def _px(self, north: float, east: float) -> tuple[float, float]:
        return (east - self.e_min) / self.res_m, (self.n_max - north) / self.res_m

    def _clear_of(self, north: float, east: float, people: list[Person] | None, radius_m: float) -> bool:
        return not people or all(math.hypot(*np.subtract(self._local(p.lat, p.lon), (north, east))) > radius_m for p in people)

    def _roof(self, north: float, east: float, rng: random.Random, avoid: list[Person] | None = None) -> bool:
        """Mái nhà chữ nhật 6–10 m × 8–14 m, xoay ngẫu nhiên, có bóng đổ và đường nóc; False nếu chỗ đó đã chật."""
        if not self._clear_of(north, east, avoid, 10.0) or any(math.dist((north, east), c) < ROOF_GAP_M for c in self.roofs):
            return False
        self.roofs.append((north, east))
        size = (rng.uniform(6, 10) / self.res_m, rng.uniform(8, 14) / self.res_m)
        angle = rng.uniform(0, 180)
        center = self._px(north, east)
        shadow = cv2.boxPoints(((center[0] + 0.8 / self.res_m, center[1] + 0.8 / self.res_m), size, angle)).astype(np.int32)
        cv2.fillPoly(self.texture, [shadow], (35, 60, 75), cv2.LINE_AA)
        box = cv2.boxPoints((center, size, angle)).astype(np.int32)
        color = rng.choice(ROOFS)
        cv2.fillPoly(self.texture, [box], color, cv2.LINE_AA)
        mid = [(box[0] + box[1]) // 2, (box[2] + box[3]) // 2]
        cv2.line(self.texture, tuple(int(x) for x in mid[0]), tuple(int(x) for x in mid[1]),
                 tuple(max(0, c - 35) for c in color), max(1, int(0.3 / self.res_m)), cv2.LINE_AA)
        return True

    def _tree(self, north: float, east: float, rng: random.Random, avoid: list[Person] | None = None) -> None:
        if not self._clear_of(north, east, avoid, 5.0) or any(math.dist((north, east), c) < ROOF_GAP_M / 2 for c in self.roofs):
            return
        center = tuple(int(x) for x in self._px(north, east))
        radius = int(rng.uniform(1.5, 3.5) / self.res_m)
        cv2.circle(self.texture, center, radius, tuple(max(0, c - 15) for c in TREE), -1, cv2.LINE_AA)
        cv2.circle(self.texture, (center[0] - radius // 4, center[1] - radius // 4), int(radius * 0.7), TREE, -1, cv2.LINE_AA)

    def _debris(self, north: float, east: float, rng: random.Random, avoid: list[Person] | None = None) -> None:
        """Rác trôi (gỗ, thùng, túi nilon) 0,3–1,5 m: vật nổi dễ bị báo nhầm là người."""
        if not self._clear_of(north, east, avoid, 3.0):
            return
        size = (rng.uniform(0.3, 1.5) / self.res_m, rng.uniform(0.2, 0.6) / self.res_m)
        box = cv2.boxPoints((self._px(north, east), size, rng.uniform(0, 180))).astype(np.int32)
        color = rng.choice([(40, 60, 80), (200, 200, 200), (60, 140, 200), (30, 30, 30), (90, 110, 60)])
        cv2.fillPoly(self.texture, [box], color, cv2.LINE_AA)

    def render(self, tel: Telemetry, cam: Camera, t: float) -> np.ndarray:
        """Khung ảnh camera nhìn thấy theo telemetry `tel` (thật, không nhiễu) tại thời điểm t."""
        s = tel.alt_agl_m / cam.f_px
        yaw = math.radians(tel.yaw_deg)
        n0, e0 = self._local(tel.lat, tel.lon)
        # pixel (u, v) → (bắc, đông): như edge.georef.pixel_to_gps, viết thành hàm tuyến tính của u, v.
        a1, a2 = -s * math.sin(yaw), -s * math.cos(yaw)
        a0 = s * (math.cos(yaw) * cam.height / 2 + math.sin(yaw) * cam.width / 2) + n0
        b1, b2 = s * math.cos(yaw), -s * math.sin(yaw)
        b0 = s * (math.sin(yaw) * cam.height / 2 - math.cos(yaw) * cam.width / 2) + e0
        r = self.res_m
        matrix = np.array([[b1 / r, b2 / r, (b0 - self.e_min) / r], [-a1 / r, -a2 / r, (self.n_max - a0) / r]], np.float64)
        frame = cv2.warpAffine(self.texture, matrix, (cam.width, cam.height), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                               borderMode=cv2.BORDER_CONSTANT, borderValue=WATER)
        half = PERSON_WIDTH_M / 2.0 / s
        for person in self.people:
            u, v = gps_to_pixel(*person.at(t), tel, cam)
            if -half <= u < cam.width + half and -half <= v < cam.height + half:
                self._person(frame, u, v, half, person.person_id)
        return frame

    def _person(self, frame: np.ndarray, u: float, v: float, half: float, person_id: int) -> None:
        """Người nhìn từ trên: vai và áo (màu theo người), đầu tối; người dưới nước có gợn sóng quanh."""
        center = (int(round(u)), int(round(v)))
        if person_id not in self.roof_people:
            cv2.circle(frame, center, int(half * 1.6), (150, 175, 185), max(1, int(half * 0.15)), cv2.LINE_AA)
        cv2.ellipse(frame, center, (max(2, int(half)), max(1, int(half * 0.6))), (person_id * 37) % 180, 0, 360,
                    CLOTHES[person_id % len(CLOTHES)], -1, cv2.LINE_AA)
        cv2.circle(frame, center, max(1, int(half * 0.42)), (40, 50, 60), -1, cv2.LINE_AA)


def scene_extent(points: list[tuple[float, float]], margin_m: float) -> tuple[float, float, float, float]:
    """Khung (bắc min, bắc max, đông min, đông max) bao các điểm (bắc, đông), nới thêm margin_m mỗi phía."""
    north = [p[0] for p in points]
    east = [p[1] for p in points]
    return min(north) - margin_m, max(north) + margin_m, min(east) - margin_m, max(east) + margin_m
