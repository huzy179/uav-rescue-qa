from __future__ import annotations

from pathlib import Path

from eval.rq2_report import (
    KIND_ALT, KIND_QUANT, KIND_TILE, accuracy_rows, compare_dir, conf_rows, comparison_pairs, markdown_accuracy, pareto_flags, signed, speed_rows,
)

VARIANTS = [
    {"name": "pt_full1280", "precision": "pt", "mode": "full", "imgsz": 1280},
    {"name": "fp16_full1280", "precision": "fp16", "mode": "full", "imgsz": 1280},
    {"name": "pt_tiled", "precision": "pt", "mode": "tiled"},
    {"name": "fp16_tiled", "precision": "fp16", "mode": "tiled"},
    {"name": "int8_tiled", "precision": "int8", "mode": "tiled"},
    {"name": "pt_tiled_px10", "precision": "pt", "mode": "tiled", "target_person_px": 10},
    {"name": "fp16_tiled_px10", "precision": "fp16", "mode": "tiled", "target_person_px": 10},
]


def test_comparison_pairs() -> None:
    pairs = set(comparison_pairs(VARIANTS))
    assert pairs == {
        ("pt_full1280", "fp16_full1280", KIND_QUANT),
        ("pt_tiled", "fp16_tiled", KIND_QUANT),
        ("pt_tiled", "int8_tiled", KIND_QUANT),
        ("pt_tiled_px10", "fp16_tiled_px10", KIND_QUANT),
        ("pt_tiled", "pt_tiled_px10", KIND_ALT),
        ("fp16_tiled", "fp16_tiled_px10", KIND_ALT),
        ("pt_full1280", "pt_tiled", KIND_TILE),
        ("fp16_full1280", "fp16_tiled", KIND_TILE),
    }


def test_speed_rows_speedup_against_same_shape() -> None:
    timing = [
        {"run": "runs/rq2/speed/pt_tiled", "total_ms_p95": "400", "n_tiles": "32", "fps_at_p95": "2.5", "gpu": "Tesla T4"},
        {"run": "runs/rq2/speed/fp16_tiled", "total_ms_p95": "100", "n_tiles": "32", "fps_at_p95": "10", "gpu": "Tesla T4"},
        {"run": "runs/rq2/speed/fp16_full1280", "total_ms_p95": "50", "n_tiles": "1", "fps_at_p95": "20", "gpu": "Tesla T4"},
    ]
    rows = {r["variant"]: r for r in speed_rows(VARIANTS, timing)}
    assert set(rows) == {"pt_tiled", "fp16_tiled", "fp16_full1280"}
    assert rows["pt_tiled"]["speedup_p95_vs_pt"] == 1.0
    assert rows["fp16_tiled"]["speedup_p95_vs_pt"] == 4.0
    assert rows["fp16_full1280"]["speedup_p95_vs_pt"] is None  # pt_full1280 chưa có thời gian


def test_accuracy_rows_and_markdown(tmp_path: Path) -> None:
    out = compare_dir(tmp_path, "sds_det", "pt_tiled", "fp16_tiled", "0.5")
    out.mkdir(parents=True)
    (out / "compare.csv").write_text(
        "size_bin,metric,A,B,diff,diff_lo,diff_hi,p_value,significant\n"
        "all,AP,0.2345,0.2339,-0.0006,-0.004,0.002,0.7,False\n"
        "8-16,AP,0.3,0.3,0,0,0,1,False\n"
        "<8,recall,0.1,0.05,-0.05,-0.08,-0.01,0.01,True\n",
        encoding="utf-8",
    )
    rows = accuracy_rows(tmp_path, ["sds_det"], [("pt_tiled", "fp16_tiled", KIND_QUANT)])
    assert [(r["size_bin"], r["metric"]) for r in rows] == [("all", "AP"), ("<8", "recall")]
    table = markdown_accuracy(rows, "0.5")
    assert "| sds_det | nén | fp16_tiled − pt_tiled | −0,001 (−0,004 đến +0,002) | – | −0,050 (−0,080 đến −0,010) * |" in table


def test_signed() -> None:
    assert signed(0.0123) == "+0,012"
    assert signed(-0.5) == "−0,500"
    assert signed(None) == "–"


def test_group_count_summary() -> None:
    from eval.group_count_eval import summarize

    s = summarize([(1, 1), (2, 1), (1, 3)])
    assert s["n_alerts_matched"] == 3 and s["exact"] == round(1 / 3, 4)
    assert (s["n_over"], s["n_under"]) == (1, 1)
    assert s["error_mean"] == round((0 + 1 - 2) / 3, 4)


def test_markdown_accuracy_keeps_pairs_with_same_b_apart(tmp_path: Path) -> None:
    # fp16_tiled được so với hai mốc (pt_tiled, fp16_full1280): mỗi dòng phải lấy số của đúng cặp của nó.
    for a, diff in (("pt_tiled", "-0.0008"), ("fp16_full1280", "-0.2229")):
        out = compare_dir(tmp_path, "sds_det", a, "fp16_tiled", "0.5")
        out.mkdir(parents=True)
        (out / "compare.csv").write_text(
            "size_bin,metric,A,B,diff,diff_lo,diff_hi,p_value,significant\n"
            f"all,AP,0.3,0.3,{diff},-0.3,0.1,0.5,False\n", encoding="utf-8")
    pairs = [("pt_tiled", "fp16_tiled", KIND_QUANT), ("fp16_full1280", "fp16_tiled", KIND_TILE)]
    table = markdown_accuracy(accuracy_rows(tmp_path, ["sds_det"], pairs), "0.5")
    assert "| fp16_tiled − pt_tiled | −0,001 (" in table
    assert "| fp16_tiled − fp16_full1280 | −0,223 (" in table


def test_pareto_flags() -> None:
    rows = [
        {"dataset": "d", "variant": "fast", "fps_at_p95": "40", "recall": "0.45", "AP50": "0.4"},
        {"dataset": "d", "variant": "slow_better", "fps_at_p95": "10", "recall": "0.58", "AP50": "0.5"},
        {"dataset": "d", "variant": "dominated", "fps_at_p95": "18", "recall": "0.44", "AP50": "0.4"},
        {"dataset": "e", "variant": "alone", "fps_at_p95": "1", "recall": "0.1", "AP50": "0.1"},
    ]
    front = {r["variant"]: r["on_front"] for r in pareto_flags(rows)}
    assert front == {"fast": True, "slow_better": True, "dominated": False, "alone": True}


def test_conf_rows(tmp_path: Path) -> None:
    run = tmp_path / "d" / "int8_tiled"
    run.mkdir(parents=True)
    (run / "boxes.csv").write_text("image,conf\na.jpg,0.05\na.jpg,0.2\nb.jpg,0.3\nb.jpg,0.6\n", encoding="utf-8")
    rows = conf_rows(tmp_path, ["d"], [{"name": "int8_tiled"}, {"name": "missing"}])
    assert rows == [{"dataset": "d", "variant": "int8_tiled", "n_boxes": 4, "n_conf_ge_025": 2, "n_conf_ge_010": 3,
                     "conf_q99": 0.6, "conf_max": 0.6}]
