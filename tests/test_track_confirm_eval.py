"""Kiểm tra chấm khối xác nhận theo track bằng ví dụ tính tay."""

from __future__ import annotations

from eval.track_confirm_eval import match_track, score


def person(tid: int, x: float) -> dict:
    return {"box": [x, 100.0, x + 10.0, 120.0], "track_id": tid}


TRUTH = {0: [person(1, 0), person(2, 200)], 1: [person(1, 2), person(2, 202)], 2: [person(1, 4)], 3: [person(1, 6)]}
TIMES = {0: 0.0, 1: 0.5, 2: 1.0, 3: 1.5}


def conf(frame: int, x: float, t: float) -> dict:
    return {"frame_id": frame, "t": t, "box_px": [x, 100.0, x + 10.0, 120.0]}


def test_match_theo_iou_hoac_tam_trong_box() -> None:
    people = [person(1, 0), person(2, 200)]
    assert match_track((1, 100, 11, 120), people, 0.3) == 1
    assert match_track((185, 70, 225, 150), people, 0.3) == 2  # IoU 0,06 nhưng tâm (205, 110) nằm trong box người 2
    assert match_track((500, 100, 510, 120), people, 0.3) is None


def test_score_dem_dung_cac_loai_canh_bao() -> None:
    confirmations = [conf(2, 4, 1.0), conf(3, 6, 1.5), conf(1, 600, 0.5)]  # người 1 hai lần, một cảnh báo không khớp ai
    r = score(confirmations, TRUTH, [0, 1, 2, 3], TIMES, 0.3, 3)
    assert r["people_seen"] == 2
    assert r["people_eligible"] == 1  # người 2 chỉ thấy 2 khung
    assert r["people_alerted"] == 1 and r["alert_rate"] == 1.0
    assert r["false_alerts"] == 1
    assert r["duplicate_alerts"] == 1
    assert r["time_to_alert_median_s"] == 1.0  # thấy từ t = 0, cảnh báo ở t = 1


def test_score_chi_tinh_khung_da_xu_ly() -> None:
    r = score([], TRUTH, [0, 2], TIMES, 0.3, 3)  # xử lý 2 khung: không ai đủ 3 lần thấy
    assert r["people_eligible"] == 0 and r["alert_rate"] is None
