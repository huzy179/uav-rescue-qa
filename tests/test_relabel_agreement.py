"""So nhãn gán lại với nhãn gốc (tools/relabel_agreement.py), ví dụ tính tay."""

from __future__ import annotations

import math

from tools.convert_cvat import ImageLabels
from tools.relabel_agreement import compare, summarize, tag_agreement

NO = {"partly_submerged": False, "occluded": False}
SUB = {"partly_submerged": True, "occluded": False}


def test_ghep_bo_sot_va_thua() -> None:
    orig = {"a.jpg": ImageLabels("a.jpg", 100, 100, persons=[(0, 0, 40, 40, SUB), (50, 50, 56, 56, NO), (80, 0, 84, 4, NO)],
                                 tags={"glare"}),
            "b.jpg": ImageLabels("b.jpg", 100, 100, persons=[(0, 0, 20, 20, NO)])}
    # Người to: lệch 2 px một mép (IoU 0,95). Người 6 px: lệch 2 px ngang, 1 px dọc (IoU 20/52 ≈ 0,385: chỉ ghép ở 0,3).
    # Người 4 px ở a bị bỏ sót; b có thêm một người.
    relabel = {"a.jpg": ImageLabels("a.jpg", 100, 100, persons=[(0, 0, 40, 38, NO), (52, 51, 58, 57, NO)]),
               "b.jpg": ImageLabels("b.jpg", 100, 100, persons=[(0, 0, 20, 20, NO), (60, 60, 70, 70, NO)])}
    people, extra = compare(orig, relabel, 0.5)
    s = summarize(people, extra).set_index("size_bin")
    assert s.loc["all", "n_orig"] == 4 and s.loc["all", "n_matched"] == 2 and s.loc["all", "n_matched_iou03"] == 3
    # Ở IoU 0,5: người 6 px không ghép nên tính một lần ở mỗi bên; cộng người 4 px bỏ sót và người thừa ở b.
    assert s.loc["all", "n_only_orig"] == 2 and s.loc["all", "n_only_relabel"] == 2
    assert s.loc["<8", "n_orig"] == 2 and s.loc["<8", "n_matched"] == 0
    big = people[(people["image"] == "a.jpg") & (people["bin"] == ">32")].iloc[0]
    assert math.isclose(big["iou"], 0.95) and big["max_edge_px"] == 2.0
    assert not big["partly_submerged_same"]
    assert s.loc["all", "occluded_agree"] == 1.0 and s.loc["all", "partly_submerged_agree"] == 0.5
    tags = tag_agreement(orig, relabel).set_index("tag")
    assert tags.loc["glare", "agree"] == 0.5 and tags.loc["blur", "agree"] == 1.0
