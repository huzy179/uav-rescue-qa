"""Kiểm tra giao diện thử nghiệm: so khớp lỗi từng ảnh, API xem lỗi trên một tập giả, nguồn chạy thử bị giới hạn."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from console.app import create_app
from console.errors import match_errors
from console.runs import RunRequest, build_command


def test_so_khop_thay_bo_sot_bao_nham_va_vung_bo_qua() -> None:
    gts = np.array([[0, 0, 10, 10], [50, 50, 60, 60]], float)
    preds = np.array([[1, 1, 10, 10], [100, 100, 110, 110], [200, 200, 205, 205]], float)
    confs = np.array([0.9, 0.5, 0.4])
    ignore = np.array([[195, 195, 215, 215]], float)
    err = match_errors(preds, confs, gts, 0.5, ignore)
    assert err.tp == [(0, 0)] and err.fn == [1] and err.fp == [1] and err.ignored == [2]


def test_uu_tien_nhan_trong_nhom() -> None:
    # Dự đoán 14×16 chồng hai nhãn: IoU với nhãn 20×20 là 224/400 = 0,56, với nhãn 6×12 là 72/224 ≈ 0,32 (đều ≥ 0,3).
    # Mặc định ghép nhãn IoU cao (nhãn to); khi xét nhóm nhỏ thì phải ghép nhãn nhỏ.
    gts = np.array([[0, 0, 20, 20], [0, 0, 6, 12]], float)
    preds = np.array([[0, 0, 14, 16]], float)
    assert match_errors(preds, np.array([0.9]), gts, 0.3).tp == [(0, 0)]
    assert match_errors(preds, np.array([0.9]), gts, 0.3, prefer=np.array([False, True])).tp == [(0, 1)]


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    images, labels, runs = tmp_path / "images", tmp_path / "labels", tmp_path / "runs" / "R1"
    for d in (images, labels, runs):
        d.mkdir(parents=True)
    Image.new("RGB", (100, 100)).save(images / "a.jpg")
    (labels / "a.txt").write_text("0 0.05 0.05 0.1 0.1\n0 0.55 0.55 0.1 0.1\n", encoding="utf-8")
    (runs / "boxes.csv").write_text(
        "image,method,imgsz,conf,width_px,height_px,x1,y1,x2,y2\n"
        "a.jpg,full,640,0.9,10,10,0,0,10,10\na.jpg,full,640,0.6,10,10,80,80,90,90\na.jpg,full,640,0.1,10,10,50,50,60,60\n",
        encoding="utf-8",
    )
    config = tmp_path / "console.yaml"
    config.write_text(
        f"datasets:\n  - {{name: t, title: Thử, runs: {tmp_path / 'runs'}, images: {images}, labels: {labels}}}\n"
        f"  - {{name: khoa, runs: {tmp_path / 'runs'}, images: {images}, labels: {labels}, require_lock: {tmp_path / 'MANIFEST'}}}\n"
        f"videos: []\nsequences: {tmp_path / 'none'}\nweights: []\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("console.errors.CONFIG", config)
    monkeypatch.setattr("console.runs.CONFIG", config)
    from console import errors

    monkeypatch.setattr(errors.load_datasets, "__defaults__", (config,))
    return TestClient(create_app(None, tmp_path / "console_runs", tmp_path / "reports"))


def test_api_xem_loi(client: TestClient) -> None:
    datasets = client.get("/api/datasets").json()
    assert [d["name"] for d in datasets] == ["t"]  # tập chưa khoá không hiện
    assert datasets[0]["runs"] == [{"name": "R1", "configs": ["full imgsz=640"]}]
    q = {"dataset_name": "t", "run": "R1", "config": "full imgsz=640", "conf": 0.25}
    total = client.get("/api/errors", params=q).json()["total"]
    # conf 0,25: thấy người thứ nhất, bỏ sót người thứ hai (dự đoán của nó chỉ 0,1), một báo nhầm.
    assert (total["tp"], total["fn"], total["fp"]) == (1, 1, 1)
    detail = client.get("/api/errors/image", params={**q, "image": "a.jpg"}).json()
    assert detail["fn"][0]["box"] == [50.0, 50.0, 60.0, 60.0] and detail["fp"][0]["conf"] == 0.6
    assert client.get("/api/errors", params={**q, "dataset_name": "khoa"}).status_code == 404
    assert client.get("/api/image", params={"dataset_name": "t", "image": "../labels/a.txt"}).status_code == 404


def test_chi_chay_nguon_trong_danh_sach(tmp_path: Path) -> None:
    sources = [{"path": "data/raw/demo/a.mp4", "kind": "video", "telemetry": None, "fps": None}]
    cmd = build_command(RunRequest(source="data/raw/demo/a.mp4", target_person_px=10), tmp_path, sources, None)
    assert "--target-person-px" in cmd and "--save-frames" in cmd and "--alt-m" in cmd
    with pytest.raises(ValueError):
        build_command(RunRequest(source="/etc/passwd"), tmp_path, sources, None)


def test_xuat_bao_cao(client: TestClient, tmp_path: Path) -> None:
    r = client.post("/api/reports", json={"dataset_name": "t", "run": "R1", "config": "full imgsz=640"})
    assert r.status_code == 200
    html = client.get(r.json()["url"]).text
    assert "Bỏ sót tiêu biểu" in html and "crops/fn_" in html
    assert client.get("/reports/x/../../console.yaml").status_code == 404


def test_hieu_du_an_ban_do_tai_lieu_thuat_ngu() -> None:
    import os

    from console.learn import load_glossary, project_map

    client = TestClient(create_app(None))
    data = client.get("/api/learn/map").json()
    assert len(data["stages"]) == 6
    for stage in data["stages"] + data["side"]:
        # Bản đồ không được trỏ tới file đã đổi tên hay xoá.
        assert all(os.path.isfile(f) for f in stage["files"]), stage["id"]
        assert all(os.path.isfile(r["doc"]) for r in stage["results"] + stage["docs"]), stage["id"]
    docs = client.get("/api/learn/docs").json()
    assert docs[0]["path"] == "docs/TONG_QUAN.md" and any(d["path"].startswith("docs/results/") for d in docs)
    assert client.get("/api/learn/doc", params={"path": "docs/THUAT_NGU.md"}).status_code == 200
    assert client.get("/api/learn/doc", params={"path": "CLAUDE.md"}).status_code == 404
    glossary = {e["term"]: e for e in load_glossary()}
    assert "fine-tune" in glossary["tinh chỉnh"]["aliases"] and "khung bao" in glossary["box (khung bao)"]["aliases"]
    assert project_map()["stages"][1]["id"] == "detect"


def test_hieu_du_an_chi_doc_ma_nguon_va_anh_tai_lieu() -> None:
    client = TestClient(create_app(None))
    assert client.get("/api/learn/source", params={"path": "edge/confirm.py"}).status_code == 200
    for bad in ("data/raw/flood/sources.csv", "../.bashrc", "edge/../../etc/passwd", ".venv/pyvenv.cfg", "runs/x.py"):
        assert client.get("/api/learn/source", params={"path": bad}).status_code == 404, bad
    assert client.get("/api/learn/asset", params={"path": "docs/results/visdrone_E0_E1_E4.png"}).status_code == 200
    assert client.get("/api/learn/asset", params={"path": "edge/main.py"}).status_code == 404
    assert client.get("/static/learn.js").status_code == 200 and client.get("/static/x.js").status_code == 404
