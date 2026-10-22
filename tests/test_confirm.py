"""Kiểm tra xác nhận kiểu `geo` với chuỗi phát hiện định sẵn."""

from edge.confirm import GeoConfirmer
from edge.georef import offset_gps
from shared.schema import Detection

LAT0, LON0 = 21.0, 105.8


def det(frame_id: int, north_m: float, east_m: float = 0.0, conf: float = 0.5) -> Detection:
    lat, lon = offset_gps(LAT0, LON0, north_m, east_m)
    return Detection(frame_id=frame_id, t=frame_id * 0.5, box_px=(0, 0, 10, 10), conf=conf, lat=lat, lon=lon)


def test_confirms_once_after_n_frames() -> None:
    """Cùng một người lệch 1 m mỗi khung: xác nhận đúng ở khung thứ 3, sau đó không lặp lại."""
    confirmer = GeoConfirmer(radius_m=3.0, n_confirm=3)
    results = [confirmer.update([det(i, north_m=float(i))], i * 0.5) for i in range(6)]
    assert [len(r) for r in results] == [0, 0, 1, 0, 0, 0]
    assert results[2][0].frames_seen == 3


def test_two_people_close_together_stay_separate() -> None:
    """Hai người cách 1 m trong cùng khung (dưới bán kính) không bị nhập vì ghép một-một."""
    confirmer = GeoConfirmer(radius_m=3.0, n_confirm=2)
    confirmer.update([det(0, 0.0), det(0, 1.0)], 0.0)
    confirmed = confirmer.update([det(1, 0.0), det(1, 1.0)], 0.5)
    assert len(confirmed) == 2
    assert len({c.cluster_id for c in confirmed}) == 2


def test_far_detection_and_expiry_make_new_cluster() -> None:
    """Phát hiện xa hơn bán kính, hoặc sau thời gian xoá cụm, không cộng dồn vào cụm cũ."""
    confirmer = GeoConfirmer(radius_m=3.0, n_confirm=2, expire_s=2.0)
    confirmer.update([det(0, 0.0)], 0.0)
    assert confirmer.update([det(1, 10.0)], 0.5) == []
    assert confirmer.update([det(10, 0.0)], 5.0) == []


def test_detection_without_location_is_ignored() -> None:
    confirmer = GeoConfirmer(n_confirm=1)
    assert confirmer.update([Detection(frame_id=0, t=0.0, box_px=(0, 0, 1, 1), conf=0.9)], 0.0) == []


class FakeTracker:
    """Trả track_id định sẵn cho từng khung: ids[k] là danh sách track_id theo thứ tự phát hiện ở lần gọi thứ k."""

    def __init__(self, ids: list[list[int]]) -> None:
        self.ids, self.calls, self.warps = ids, 0, []

    def update(self, boxes, confs, warp=None):
        self.warps.append(warp)
        result = [(i, track_id) for i, track_id in enumerate(self.ids[self.calls])]
        self.calls += 1
        return result


def test_track_confirmer_confirms_same_track_once() -> None:
    from edge.confirm import TrackConfirmer

    tracker = FakeTracker([[7], [7], [8], [7], [7]])
    confirmer = TrackConfirmer(tracker, n_confirm=3, motion=lambda t0, t1: f"warp {t0}->{t1}")
    results = [confirmer.update([det(i, 0.0)], i * 0.5) for i in range(5)]
    assert [len(r) for r in results] == [0, 0, 0, 1, 0]
    assert results[3][0].cluster_id == 7
    assert tracker.warps == [None, "warp 0.0->0.5", "warp 0.5->1.0", "warp 1.0->1.5", "warp 1.5->2.0"]


def _flyover_detections() -> tuple[list[list[Detection]], list[float]]:
    """Một người đứng yên cách điểm xuất phát 18 m về phía trước; UAV bay 10 m/s ở 50 m, 2 FPS, camera 4K 74,3°.

    Người rộng 0,5 m ≈ 25 px; mặt đất dịch ≈ 254 px giữa hai khung (TECHNICAL mục 5.2).
    """
    from edge.georef import Camera, gps_to_pixel, offset_gps, pixel_to_gps
    from sim.flight import StraightFlight

    cam = Camera(3840, 2160, 74.3)
    flight = StraightFlight(LAT0, LON0, 50.0, 10.0, yaw_deg=0.0)
    person = offset_gps(LAT0, LON0, 18.0, 0.0)
    frames, times = [], []
    for k in range(6):
        t = k * 0.5
        tel = flight.at(t)
        u, v = gps_to_pixel(*person, tel, cam)
        half = 0.25 * cam.f_px / tel.alt_agl_m  # nửa bề ngang người tính bằng pixel
        lat, lon = pixel_to_gps(u, v, tel, cam)
        frames.append([Detection(frame_id=k, t=t, box_px=(u - half, v - half, u + half, v + half), conf=0.9, lat=lat, lon=lon)])
        times.append(t)
    return frames, times


def test_bytetrack_breaks_at_2fps_and_camera_motion_compensation_fixes_it() -> None:
    """Luận điểm của RQ3 (TECHNICAL mục 9.2–9.3), với ByteTrack thật của ultralytics, không cần mô hình."""
    import pytest

    pytest.importorskip("ultralytics")
    from edge.confirm import TrackConfirmer
    from edge.detector import ByteTracker
    from edge.georef import Camera, frame_motion
    from sim.flight import StraightFlight

    frames, times = _flyover_detections()
    plain = TrackConfirmer(ByteTracker(), n_confirm=3)
    assert sum(len(plain.update(d, t)) for d, t in zip(frames, times)) == 0  # mỗi khung một track mới

    cam, flight = Camera(3840, 2160, 74.3), StraightFlight(LAT0, LON0, 50.0, 10.0, yaw_deg=0.0)
    cmc = TrackConfirmer(ByteTracker(), n_confirm=3, motion=lambda t0, t1: frame_motion(flight.at(t0), flight.at(t1), cam))
    confirmed = [c for d, t in zip(frames, times) for c in cmc.update(d, t)]
    assert len(confirmed) == 1 and confirmed[0].t == 1.0  # xác nhận ở khung thứ 3

    geo = GeoConfirmer(radius_m=3.0, n_confirm=3)
    assert sum(len(geo.update(d, t)) for d, t in zip(frames, times)) == 1


def test_track_confirmer_giu_id_cua_khung_gan_nhat() -> None:
    """TrackConfirmer ghi lại (box, track_id) của khung vừa cập nhật để vẽ video demo."""
    from edge.confirm import TrackConfirmer

    class FakeTracker:
        def update(self, boxes, confs, warp=None):  # type: ignore[no-untyped-def]
            return [(i, 100 + i) for i in range(len(boxes))]

    confirmer = TrackConfirmer(FakeTracker(), n_confirm=3)
    confirmer.update([det(0, 0.0), det(0, 5.0)], 0.0)
    assert [tid for _, tid in confirmer.last_assignments] == [100, 101]
    confirmer.update([], 0.5)
    assert confirmer.last_assignments == []
