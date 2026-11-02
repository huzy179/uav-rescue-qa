"""Kiểm tra ghép độ chính xác và thời gian của RQ2 từ các file kết quả giả."""

from __future__ import annotations

from pathlib import Path

from eval.rq2_tradeoff import tradeoff_rows

HEADER = "config,size_bin,n_images,n_gt,AP,recall,precision,recall_max,AP_lo,AP_hi,recall_lo,recall_hi\n"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_ghep_theo_ten_bien_the(tmp_path: Path) -> None:
    write(tmp_path / "sds" / "eval_fp16_tiled_iou0.5" / "eval_by_size.csv",
          HEADER + "tiled imgsz=640,all,10,50,0.5,0.6,0.7,0.8,,,,\ntiled imgsz=640,<8,10,5,0.1,0.2,0.3,0.4,,,,\n")
    write(tmp_path / "sds" / "eval_fp16_tiled_iou0.3" / "eval_by_size.csv",
          HEADER + "tiled imgsz=640,all,10,50,0.6,0.7,0.8,0.9,,,,\ntiled imgsz=640,<8,10,5,0.2,0.4,0.5,0.6,,,,\n")
    write(tmp_path / "timing.csv",
          "run,gpu,infer_ms_p95,total_ms_p50,total_ms_p95,fps_at_p95,n_tiles\n"
          "runs/rq2/speed/fp16_tiled,Tesla T4,80,90,100,10.0,32\n")
    variants = [{"name": "fp16_tiled", "precision": "fp16"}, {"name": "int8_tiled", "precision": "int8"}]

    rows = tradeoff_rows(tmp_path, variants, ["sds"])

    assert len(rows) == 1  # int8 chưa có kết quả độ chính xác: bỏ
    r = rows[0]
    assert (r["AP50"], r["recall"], r["recall_lt8_iou03"]) == (0.5, 0.6, 0.4)
    assert (r["fps_at_p95"], r["total_ms_p95"], r["gpu"], r["mode"]) == (10.0, 100.0, "Tesla T4", "tiled")
