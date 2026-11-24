"""Kiểm tra công cụ chụp số liệu kiểm thử (tools/qa_snapshot.py) trên file JUnit và gói mã dựng sẵn."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.qa_snapshot import code_lines, count_tests_per_file


def test_dem_test_theo_file(tmp_path: Path) -> None:
    xml = tmp_path / "pytest.xml"
    xml.write_text(
        '<testsuites><testsuite tests="3">'
        '<testcase classname="tests.test_ground" name="a" /><testcase classname="tests.test_ground" name="b" />'
        '<testcase classname="tests.test_alerts.TestOutbox" name="c" /></testsuite></testsuites>',
        encoding="utf-8",
    )
    assert count_tests_per_file(xml) == [{"file": "test_alerts.py", "tests": 1}, {"file": "test_ground.py", "tests": 2}]


def test_classname_la_bao_loi(tmp_path: Path) -> None:
    xml = tmp_path / "pytest.xml"
    xml.write_text('<testsuites><testcase classname="tests.helpers" name="a" /></testsuites>', encoding="utf-8")
    with pytest.raises(ValueError):
        count_tests_per_file(xml)


def test_dem_dong_bo_pycache(tmp_path: Path) -> None:
    (tmp_path / "edge" / "__pycache__").mkdir(parents=True)
    (tmp_path / "edge" / "a.py").write_text("x = 1\n\ny = 2\n", encoding="utf-8")
    (tmp_path / "edge" / "__pycache__" / "b.py").write_text("z = 3\n", encoding="utf-8")
    assert code_lines(tmp_path, ["edge"]) == [{"package": "edge", "python_files": 1, "lines": 3}]
