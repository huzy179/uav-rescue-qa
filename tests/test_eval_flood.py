"""Kiểm tra regex gom cụm video của scripts/eval_flood.sh cho bootstrap theo video trên tập test lũ."""

import re
from pathlib import Path

from eval.splits import group_of

CLUSTER = re.search(r"^CLUSTER='(.+)'", Path("scripts/eval_flood.sh").read_text(), re.M).group(1)


def test_san_angelo_videos_share_one_cluster() -> None:
    assert group_of("sanangelo-police_000480", CLUSTER) == group_of("texas-xBvDRr6vy-k_000180", CLUSTER)


def test_other_videos_keep_own_cluster() -> None:
    stems = ["washington-D4xd0xNP9Gg_000780", "duvall-2HE-TIf4Lk0_000060", "hue-short-Ak83K9FSBTY_002600", "nidarx-flood-1_000540"]
    clusters = [group_of(s, CLUSTER) for s in stems]
    assert clusters == ["washington-D4xd0xNP9Gg", "duvall-2HE-TIf4Lk0", "hue-short-Ak83K9FSBTY", "nidarx-flood-1"]
    assert group_of("sanangelo-police_000480", CLUSTER) not in clusters
