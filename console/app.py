"""Giao diện thử nghiệm FloodEye: xem lỗi của mô hình trên các tập đã chấm, chạy thử pipeline, xem trạm mặt đất.

Chạy: .venv/bin/python -m console   (mở http://localhost:8501). Chỉ dùng trên máy cá nhân: không có đăng nhập.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from fastapi.responses import FileResponse, HTMLResponse

from console.errors import load_datasets, image_errors, list_runs, short_side, summarize
from console.report import ROOT as REPORTS, build_report
from console.runs import RunManager, RunRequest, list_sources
from eval.metrics import SIZE_RANGES

INDEX_HTML = Path(__file__).with_name("index.html")


class ReportRequest(BaseModel):
    dataset_name: str
    run: str
    config: str
    iou: float = 0.5
    conf: float = 0.25


def create_app(ground_url: str | None = None, runs_root: Path | None = None, reports_root: Path = REPORTS) -> FastAPI:
    """Tạo ứng dụng; ground_url là trạm mặt đất để nhúng và để lần chạy thử gửi cảnh báo tới (None: không có)."""
    app = FastAPI(title="FloodEye – giao diện thử nghiệm")
    manager = RunManager(runs_root) if runs_root is not None else RunManager()

    def dataset(name: str) -> Any:
        ds = load_datasets().get(name)
        if ds is None or not ds.available:
            raise HTTPException(404, f"Không có tập {name} (hoặc tập test lũ chưa khoá)")
        return ds

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return INDEX_HTML.read_text(encoding="utf-8")

    @app.get("/api/info")
    def info() -> dict[str, Any]:
        return {"ground_url": ground_url, "size_bins": list(SIZE_RANGES)}

    # --- Xem lỗi -------------------------------------------------------------------------------------------------

    @app.get("/api/datasets")
    def datasets() -> list[dict[str, Any]]:
        """Tập có ảnh (tập lũ chỉ khi đã khoá) và các lần chạy trên nó."""
        return [
            {"name": d.name, "title": d.title, "runs": list_runs(d)}
            for d in load_datasets().values() if d.available
        ]

    @app.get("/api/errors")
    def errors(
        dataset_name: str, run: str, config: str, iou: float = 0.5, conf: float = 0.25, size: str = "all",
        tag: str | None = None,
    ) -> dict[str, Any]:
        """Số người thấy, bỏ sót, báo nhầm của từng ảnh và của cả tập."""
        if size not in SIZE_RANGES:
            raise HTTPException(400, f"size phải là một trong {list(SIZE_RANGES)}")
        return summarize(dataset(dataset_name), run, config, iou, conf, size, tag or None)

    @app.get("/api/errors/image")
    def errors_image(dataset_name: str, run: str, config: str, image: str, iou: float = 0.5, conf: float = 0.25) -> dict[str, Any]:
        """Box của một ảnh để vẽ: thấy (xanh), bỏ sót (đỏ), báo nhầm (cam), nằm trong vùng bỏ qua (xám)."""
        ds = dataset(dataset_name)
        try:
            err, preds, confs, gts, ignore, (width, height) = image_errors(ds, run, config, image, iou, conf)
        except KeyError as error:
            raise HTTPException(404, f"Không có ảnh {image}") from error
        gt_side, pred_side = short_side(gts), short_side(preds)

        def box(b: Any) -> list[float]:
            return [round(float(v), 1) for v in b]

        return {
            "width": width, "height": height,
            "tp": [{"box": box(gts[j]), "pred": box(preds[i]), "conf": round(float(confs[i]), 3),
                    "px": round(float(gt_side[j]), 1)} for i, j in err.tp],
            "fn": [{"box": box(gts[j]), "px": round(float(gt_side[j]), 1)} for j in err.fn],
            "fp": [{"box": box(preds[i]), "conf": round(float(confs[i]), 3), "px": round(float(pred_side[i]), 1)} for i in err.fp],
            "ignored_preds": [{"box": box(preds[i])} for i in err.ignored],
            "ignore_regions": [box(b) for b in (ignore if ignore is not None else [])],
        }

    @app.get("/api/image")
    def image_file(dataset_name: str, image: str) -> FileResponse:
        ds = dataset(dataset_name)
        path = ds.images / Path(image).name  # chỉ tên file: không cho đi ra ngoài thư mục ảnh
        if not path.is_file():
            raise HTTPException(404, "Không có ảnh")
        return FileResponse(path)

    @app.post("/api/reports")
    def make_report(req: ReportRequest) -> dict[str, str]:
        """Báo cáo phân tích lỗi (console/report.py): bảng theo nhóm kích thước, ảnh cắt các lỗi tiêu biểu."""
        out = build_report(dataset(req.dataset_name), req.run, req.config, req.iou, req.conf, root=reports_root)
        return {"url": f"/reports/{out.name}/report.html", "path": str(out / "report.md")}

    @app.get("/reports/{name}/{file:path}")
    def report_file(name: str, file: str) -> FileResponse:
        base = (reports_root / Path(name).name).resolve()
        path = (base / file).resolve()
        if base not in path.parents or not path.is_file():
            raise HTTPException(404, "Không có file")
        return FileResponse(path)

    # --- Chạy thử ------------------------------------------------------------------------------------------------

    @app.get("/api/sources")
    def sources() -> dict[str, Any]:
        return list_sources()

    @app.post("/api/runs")
    def start_run(req: RunRequest) -> dict[str, str]:
        try:
            return {"id": manager.start(req, ground_url)}
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @app.get("/api/runs")
    def runs() -> list[dict[str, Any]]:
        return manager.list()

    def run_dir(run_id: str) -> Path:
        d = manager.root / Path(run_id).name
        if not (d / "console_request.json").is_file():
            raise HTTPException(404, "Không có lần chạy này")
        return d

    @app.get("/api/runs/{run_id}")
    def run_detail(run_id: str) -> dict[str, Any]:
        run_dir(run_id)
        return manager.detail(Path(run_id).name)

    @app.get("/api/runs/{run_id}/frame/{frame}")
    def run_frame(run_id: str, frame: str) -> FileResponse:
        path = run_dir(run_id) / "frames" / f"{Path(frame).name}.jpg"
        if not path.is_file():
            raise HTTPException(404, "Không có khung")
        return FileResponse(path)

    @app.get("/api/runs/{run_id}/crop/{alert_id}")
    def run_crop(run_id: str, alert_id: str) -> Response:
        run_dir(run_id)
        jpeg = manager.crop(Path(run_id).name, alert_id)
        if jpeg is None:
            raise HTTPException(404, "Không có ảnh cắt")
        return Response(jpeg, media_type="image/jpeg")

    return app
