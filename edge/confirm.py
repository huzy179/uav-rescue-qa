"""Xác nhận người qua nhiều khung trước khi cảnh báo (TECHNICAL mục 9)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

import numpy as np

from edge.detector import Tracker
from edge.georef import ground_distance_m
from shared.schema import Confirmation, Detection


class Confirmer(Protocol):
    def update(self, dets: list[Detection], t: float) -> list[Confirmation]: ...


@dataclass
class _Cluster:
    cluster_id: int
    lat: float
    lon: float
    weight: float
    last: Detection
    sightings: list[tuple[float, float]] = field(default_factory=list)  # (t, conf)
    alerted: bool = False

    def add(self, det: Detection) -> None:
        """Thêm lần thấy, dời tâm theo trung bình có trọng số conf."""
        assert det.lat is not None and det.lon is not None
        total = self.weight + det.conf
        self.lat = (self.lat * self.weight + det.lat * det.conf) / total
        self.lon = (self.lon * self.weight + det.lon * det.conf) / total
        self.weight = total
        self.last = det
        self.sightings.append((det.t, det.conf))


@dataclass
class AlertMemory:
    """Nhớ vị trí đã cảnh báo trong suppress_s giây để không cảnh báo lại trong bán kính radius_m quanh đó.

    Chữa cảnh báo lặp khi một người bị detector bỏ sót lâu hơn thời gian xoá cụm rồi được thấy lại thành cụm mới
    (SeaDronesSee, docs/results/sds_mot_confirm.md). Cái giá: người thật đứng trong bán kính đó của người đã cảnh báo
    cũng không được cảnh báo riêng. suppress_s = 0 là tắt.
    """

    suppress_s: float = 0.0
    radius_m: float = 3.0
    alerts: list[tuple[float, float, float]] = field(default_factory=list)  # (t, lat, lon)

    def blocks(self, t: float, lat: float, lon: float) -> bool:
        self.alerts = [a for a in self.alerts if t - a[0] <= self.suppress_s]
        return any(ground_distance_m(a_lat, a_lon, lat, lon) <= self.radius_m for _, a_lat, a_lon in self.alerts)

    def remember(self, t: float, lat: float, lon: float) -> None:
        if self.suppress_s > 0:
            self.alerts.append((t, lat, lon))


def _newly_confirmed(
    clusters: list[_Cluster], t: float, n_confirm: int, window_s: float, memory: AlertMemory | None = None
) -> list[Confirmation]:
    """Cụm chưa cảnh báo mà có ≥ n_confirm lần thấy trong window_s giây gần nhất; đánh dấu đã cảnh báo.

    Dùng chung cho mọi chiến lược, để chúng chỉ khác nhau ở cách ghép phát hiện vào cụm. Cụm đủ điều kiện nhưng nằm
    gần một cảnh báo còn trong bộ nhớ thì được đánh dấu đã cảnh báo mà không sinh cảnh báo mới.
    """
    confirmed: list[Confirmation] = []
    for cluster in clusters:
        if cluster.alerted:
            continue
        recent = [conf for seen_t, conf in cluster.sightings if t - seen_t <= window_s]
        if len(recent) >= n_confirm:
            cluster.alerted = True
            if memory is not None and memory.blocks(t, cluster.lat, cluster.lon):
                continue
            if memory is not None:
                memory.remember(t, cluster.lat, cluster.lon)
            confirmed.append(
                Confirmation(
                    cluster_id=cluster.cluster_id,
                    t=t,
                    lat=cluster.lat,
                    lon=cluster.lon,
                    frames_seen=len(recent),
                    confidence=sum(recent) / len(recent),
                    frame_id=cluster.last.frame_id,
                    box_px=cluster.last.box_px,
                )
            )
    return confirmed


class GeoConfirmer:
    """Gom phát hiện theo vị trí mặt đất (chiến lược `geo`, TECHNICAL mục 9.4).

    Ghép một-một để hai người đứng gần nhau trong cùng khung không nhập thành một cụm.
    shortcut: ghép tham lam theo khoảng cách tăng dần thay cho Hungary (chưa có scipy);
    chỉ khác Hungary khi nhiều người cách nhau dưới r, đổi nếu RQ3 thấy gộp/tách nhầm đáng kể.
    """

    def __init__(
        self, radius_m: float = 3.0, n_confirm: int = 3, window_s: float = 5.0, expire_s: float = 6.0, suppress_s: float = 0.0
    ) -> None:
        self.radius_m, self.n_confirm, self.window_s, self.expire_s = radius_m, n_confirm, window_s, expire_s
        self.memory = AlertMemory(suppress_s, radius_m)
        self._clusters: list[_Cluster] = []
        self._next_id = 0

    def update(self, dets: list[Detection], t: float) -> list[Confirmation]:
        """Cập nhật với phát hiện của một khung; trả về các cụm vừa đủ điều kiện ở khung này."""
        self._clusters = [c for c in self._clusters if t - c.last.t <= self.expire_s]
        located = [d for d in dets if d.lat is not None and d.lon is not None]

        pairs = sorted(
            (ground_distance_m(c.lat, c.lon, d.lat, d.lon), ci, di)  # type: ignore[arg-type]
            for ci, c in enumerate(self._clusters)
            for di, d in enumerate(located)
        )
        used_clusters: set[int] = set()
        used_dets: set[int] = set()
        for distance, ci, di in pairs:
            if distance > self.radius_m:
                break
            if ci in used_clusters or di in used_dets:
                continue
            used_clusters.add(ci)
            used_dets.add(di)
            self._clusters[ci].add(located[di])

        for di, det in enumerate(located):
            if di not in used_dets:
                cluster = _Cluster(self._next_id, det.lat, det.lon, 0.0, det)  # type: ignore[arg-type]
                cluster.add(det)
                self._clusters.append(cluster)
                self._next_id += 1

        return _newly_confirmed(self._clusters, t, self.n_confirm, self.window_s, self.memory)


class TrackConfirmer:
    """Xác nhận theo track trên ảnh: chiến lược `bytetrack` (motion=None) và `bytetrack_cmc` (TECHNICAL mục 9.2, 9.3).

    Tracker ghép phát hiện giữa hai khung bằng IoU của box trên ảnh. Ở 2 FPS, UAV bay 10 m/s làm mặt đất dịch
    hàng trăm pixel giữa hai khung trong khi box người chỉ vài chục pixel, nên IoU bằng 0 và mỗi khung sinh track
    mới: `bytetrack` gãy. `bytetrack_cmc` truyền motion(t_trước, t_này) trả về affine 2×3 (georef.frame_motion)
    để dời các track về khung này trước khi ghép.
    """

    def __init__(
        self,
        tracker: Tracker,
        n_confirm: int = 3,
        window_s: float = 5.0,
        expire_s: float = 6.0,
        motion: Callable[[float, float], np.ndarray] | None = None,
        suppress_s: float = 0.0,
        suppress_radius_m: float = 3.0,
    ) -> None:
        self.tracker, self.n_confirm, self.window_s, self.expire_s, self.motion = tracker, n_confirm, window_s, expire_s, motion
        self.memory = AlertMemory(suppress_s, suppress_radius_m)
        self._tracks: dict[int, _Cluster] = {}
        self._prev_t: float | None = None
        # (box, track_id) ghép được ở khung gần nhất; chỉ để vẽ video demo, không dùng để xác nhận.
        self.last_assignments: list[tuple[tuple[float, float, float, float], int]] = []

    def update(self, dets: list[Detection], t: float) -> list[Confirmation]:
        """Cập nhật với phát hiện của một khung; trả về các track vừa đủ điều kiện ở khung này."""
        warp = self.motion(self._prev_t, t) if self.motion is not None and self._prev_t is not None else None
        self._prev_t = t
        boxes = np.array([d.box_px for d in dets], dtype=float).reshape(-1, 4)
        confs = np.array([d.conf for d in dets], dtype=float)
        assignments = self.tracker.update(boxes, confs, warp)
        self.last_assignments = [(dets[i].box_px, track_id) for i, track_id in assignments]
        for det_index, track_id in assignments:
            det = dets[det_index]
            if det.lat is None or det.lon is None:
                continue
            cluster = self._tracks.get(track_id)
            if cluster is None:
                cluster = self._tracks[track_id] = _Cluster(track_id, det.lat, det.lon, 0.0, det)
            cluster.add(det)
        self._tracks = {k: c for k, c in self._tracks.items() if t - c.last.t <= self.expire_s}
        return _newly_confirmed(list(self._tracks.values()), t, self.n_confirm, self.window_s, self.memory)
