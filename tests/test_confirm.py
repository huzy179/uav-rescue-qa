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
