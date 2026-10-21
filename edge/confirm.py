"""Xác nhận người qua nhiều khung trước khi cảnh báo (TECHNICAL mục 9)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

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


class GeoConfirmer:
    """Gom phát hiện theo vị trí mặt đất (chiến lược `geo`, TECHNICAL mục 9.4).

    Ghép một-một để hai người đứng gần nhau trong cùng khung không nhập thành một cụm.
    shortcut: ghép tham lam theo khoảng cách tăng dần thay cho Hungary (chưa có scipy);
    chỉ khác Hungary khi nhiều người cách nhau dưới r, đổi nếu RQ3 thấy gộp/tách nhầm đáng kể.
    """

    def __init__(self, radius_m: float = 3.0, n_confirm: int = 3, window_s: float = 5.0, expire_s: float = 6.0) -> None:
        self.radius_m, self.n_confirm, self.window_s, self.expire_s = radius_m, n_confirm, window_s, expire_s
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

        confirmed: list[Confirmation] = []
        for cluster in self._clusters:
            if cluster.alerted:
                continue
            recent = [conf for seen_t, conf in cluster.sightings if t - seen_t <= self.window_s]
            if len(recent) >= self.n_confirm:
                cluster.alerted = True
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
