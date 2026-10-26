"""Kiểm tra chuyển nhãn CVAT (CVAT for images 1.1) sang YOLO với một file XML dựng theo cấu trúc CVAT xuất ra."""

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from eval.metrics import load_yolo_labels

SPEC = importlib.util.spec_from_file_location("convert_cvat", Path("tools/convert_cvat.py"))
convert_cvat = importlib.util.module_from_spec(SPEC)
sys.modules["convert_cvat"] = convert_cvat  # @dataclass cần module có trong sys.modules
SPEC.loader.exec_module(convert_cvat)

XML = """<?xml version="1.0" encoding="utf-8"?>
<annotations>
  <version>1.1</version>
  <meta><task><name>flood</name></task></meta>
  <image id="0" name="lu_a_000120.jpg" width="400" height="200">
    <box label="person" source="manual" occluded="0" xtl="10.5" ytl="20" xbr="30.5" ybr="60" z_order="0">
      <attribute name="partly_submerged">true</attribute>
      <attribute name="occluded">false</attribute>
    </box>
    <box label="person" source="manual" occluded="0" xtl="390" ytl="180" xbr="420" ybr="210" z_order="0">
      <attribute name="partly_submerged">false</attribute>
      <attribute name="occluded">true</attribute>
    </box>
    <box label="ignore" source="manual" occluded="0" xtl="100" ytl="100" xbr="150" ybr="140" z_order="0"></box>
    <tag label="glare" source="manual"></tag>
  </image>
  <image id="1" name="lu_a_000180.jpg" width="400" height="200">
    <tag label="floating_debris" source="manual"></tag>
  </image>
</annotations>
"""


def test_parse_boxes_attributes_tags_and_clipping() -> None:
    images = convert_cvat.parse_cvat(XML)
    assert [i.name for i in images] == ["lu_a_000120.jpg", "lu_a_000180.jpg"]
    first = images[0]
    assert first.persons[0] == (10.5, 20.0, 30.5, 60.0, {"partly_submerged": True, "occluded": False})
    assert first.persons[1][:4] == (390.0, 180.0, 400.0, 200.0)  # cắt theo mép ảnh
    assert first.ignores == [(100.0, 100.0, 150.0, 140.0)] and first.tags == {"glare"}
    assert images[1].persons == [] and images[1].tags == {"floating_debris"}


@pytest.mark.parametrize(
    "bad, message",
    [
        (XML.replace('label="ignore"', 'label="nguoi"'), "nhãn lạ"),
        (XML.replace('label="glare"', 'label="fog"'), "thẻ lạ"),
        (XML.replace('name="occluded">true', 'name="swimming">true'), "thuộc tính lạ"),
        ("<annotations><version>1.1</version></annotations>", "không có ảnh"),
    ],
)
def test_rejects_unknown_labels(bad: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        convert_cvat.parse_cvat(bad)


def test_end_to_end_writes_yolo_compatible_with_eval(tmp_path: Path) -> None:
    import cv2

    frames = tmp_path / "frames"
    frames.mkdir()
    for name in ("lu_a_000120.jpg", "lu_a_000180.jpg", "lu_a_000240.jpg"):
        cv2.imwrite(str(frames / name), np.zeros((200, 400, 3), np.uint8))
    (tmp_path / "annotations.xml").write_text(XML, encoding="utf-8")
    dst = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, "tools/convert_cvat.py", "--xml", str(tmp_path / "annotations.xml"), "--images", str(frames), "--dst", str(dst)],
        capture_output=True, text=True, check=True,
    )
    assert "lu_a_000240.jpg" in result.stdout  # ảnh chưa gán nhãn được cảnh báo
    boxes = load_yolo_labels(dst / "labels/test/lu_a_000120.txt", 400, 200, [0])
    assert boxes == pytest.approx(np.array([[10.5, 20, 30.5, 60], [390, 180, 400, 200]]), abs=0.01)
    assert load_yolo_labels(dst / "ignore/test/lu_a_000120.txt", 400, 200, [0]) == pytest.approx(np.array([[100, 100, 150, 140]]), abs=0.01)
    assert (dst / "labels/test/lu_a_000180.txt").read_text() == ""
    assert (dst / "images/test/lu_a_000120.jpg").is_file()
    tags = list(csv.DictReader((dst / "tags_test.csv").open()))
    assert tags[0]["glare"] == "1" and tags[1]["floating_debris"] == "1"
    stats = json.loads((dst / "stats_test.json").read_text())
    assert stats["n_persons"] == 2 and stats["n_images_without_person"] == 1
    assert stats["persons_by_attribute"] == {"partly_submerged": 1, "occluded": 1}


def test_gop_nhieu_task_va_doc_zip(tmp_path: Path) -> None:
    import zipfile

    with zipfile.ZipFile(tmp_path / "task1.zip", "w") as archive:
        archive.writestr("annotations.xml", XML)
    images = convert_cvat.parse_many([tmp_path / "task1.zip"])
    assert len(images) == len(convert_cvat.parse_cvat(XML))
    (tmp_path / "task2.xml").write_text(XML, encoding="utf-8")
    with pytest.raises(ValueError, match="có ở cả"):
        convert_cvat.parse_many([tmp_path / "task1.zip", tmp_path / "task2.xml"])
