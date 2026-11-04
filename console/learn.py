"""Tab "Hiểu dự án" của giao diện: bản đồ dự án, đọc tài liệu có giải thích thuật ngữ, xem mã nguồn.

Không có nội dung riêng ngoài bản đồ (STAGES): tài liệu đọc thẳng từ docs/, bảng thuật ngữ đọc từ docs/THUAT_NGU.md,
nên sửa tài liệu là trang tự cập nhật. Số trong STAGES chép từ file kết quả ghi ngay cạnh, như quy ước của tài liệu.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
GLOSSARY = ROOT / "docs" / "THUAT_NGU.md"
# Thứ tự hiện trong danh sách tài liệu: đọc từ tổng quan tới chi tiết.
DOC_ORDER = [
    "docs/TONG_QUAN.md", "docs/THUAT_TOAN.md", "docs/THUAT_NGU.md", "docs/ROADMAP.md", "docs/TECHNICAL.md",
    "docs/LABELING.md", "docs/DEMO_BAO_VE.md", "README.md",
]
SOURCE_DIRS = ("edge", "ground", "shared", "eval", "sim", "scripts", "tools", "training", "console", "configs", "tests")
SOURCE_SUFFIXES = {".py", ".sh", ".yaml", ".yml", ".html", ".toml", ".md"}

STAGES: list[dict[str, Any]] = [
    {
        "id": "camera", "title": "1. Camera và lấy khung",
        "icon": "📷", "color": "#3772cf", "summary": "Lấy vài khung mỗi giây từ video 4K",
        "metrics": [],
        "what": "Camera trên UAV quay video 4K, 30 khung/giây. Máy trên UAV không xử lý kịp mọi khung, nên chỉ lấy vài khung mỗi giây; bay thấp thì lấy nhiều hơn, bay cao lấy ít hơn (tần số theo độ cao).",
        "why": "Người trong ảnh rất nhỏ nên phải giữ ảnh 4K; máy nhỏ chỉ chạy được vài khung mỗi giây. Cần chứng minh vài khung mỗi giây là đủ để không bỏ sót người.",
        "results": [
            ("Tần số theo độ cao: nhìn mỗi người khoảng 12 lần, tối đa 8 khung/giây, không kém 2 khung/giây cố định ở độ cao nào và tốt hơn hẳn ở 30 m (mô phỏng)", "docs/results/rq3_adaptive.md"),
            ("Người rộng 0,5 m chỉ chiếm 25,3 px ở 50 m và 12,7 px ở 100 m trên video 4K", "docs/TONG_QUAN.md"),
        ],
        "files": ["edge/sampler.py", "scripts/gsd_calc.py"],
        "docs": [("Tổng quan, mục 1.2 và 3.1", "docs/TONG_QUAN.md"), ("Thuật toán từng bước", "docs/THUAT_TOAN.md")],
        "rq": "Câu hỏi 3 (hệ thống)",
    },
    {
        "id": "detect", "title": "2. Phát hiện người",
        "icon": "🔍", "color": "#00a37f", "summary": "Tìm và vẽ box quanh từng người",
        "metrics": [
            {"label": "AP50 trên VisDrone val, mọi cỡ người", "a_label": "mô hình nền", "a": 0.497, "b_label": "tinh chỉnh", "b": 0.758, "max": 1, "doc": "docs/results/visdrone_E2.md"},
            {"label": "AP50 với người dưới 8 px", "a_label": "mô hình nền", "a": 0.167, "b_label": "tinh chỉnh", "b": 0.554, "max": 1, "doc": "docs/results/visdrone_E2.md"},
            {"label": "AP50 với người dưới nước (AFO test)", "a_label": "chỉ VisDrone", "a": 0.103, "b_label": "VisDrone + AFO", "b": 0.568, "max": 1, "doc": "docs/results/E2c.md"},
            {"label": "AP50 trên SeaDronesSee 4K", "a_label": "cắt ô gốc", "a": 0.235, "b_label": "thu nhỏ theo độ cao", "b": 0.531, "max": 1, "doc": "docs/results/scale_by_altitude.md"},
        ],
        "what": "Mô hình YOLO26s tìm người trong khung và vẽ box quanh mỗi người. Mô hình được tinh chỉnh thêm trên ảnh drone (VisDrone) và ảnh người dưới nước (AFO). Ảnh 4K được cắt thành ô 640 px để người nhỏ không bị mất; có thể thu nhỏ khung theo độ cao bay trước khi cắt.",
        "why": "Mô hình gốc học trên ảnh chụp ngang, người to; ảnh drone nhìn từ trên xuống, người chỉ vài pixel. Đây là câu hỏi 1: phát hiện người nhỏ chính xác tới đâu, kỹ thuật nào giúp được bao nhiêu.",
        "results": [
            ("Tinh chỉnh trên VisDrone: AP50 trên VisDrone val từ 0,497 lên 0,758; người dưới 8 px từ 0,167 lên 0,554", "docs/results/visdrone_E2.md"),
            ("Thêm AFO (mô hình chính E2c): người dưới nước, AP50 trên AFO test từ 0,103 lên 0,568", "docs/results/E2c.md"),
            ("Thu nhỏ theo độ cao bay rồi cắt ô: SeaDronesSee 4K, AP50 từ 0,235 lên 0,531", "docs/results/scale_by_altitude.md"),
            ("Nhánh phát hiện P2: người dưới 8 px chỉ thêm 0,012–0,013 AP50, không đáng chi phí", "docs/results/E3.md"),
        ],
        "files": ["edge/detector.py", "training/train.py", "scripts/run_tiled.py", "eval/eval_by_size.py"],
        "docs": [("Tổng quan, mục 3", "docs/TONG_QUAN.md"), ("Kỹ thuật, mục 4–5", "docs/TECHNICAL.md")],
        "rq": "Câu hỏi 1 (độ chính xác)",
    },
    {
        "id": "georef", "title": "3. Định vị",
        "icon": "📍", "color": "#7c4dcc", "summary": "Đổi pixel trên ảnh thành toạ độ GPS",
        "metrics": [],
        "what": "Đổi vị trí box trên ảnh (pixel) thành toạ độ GPS trên mặt đất, dùng dữ liệu bay: vị trí, độ cao, hướng của UAV và góc nhìn camera.",
        "why": "Đội cứu hộ cần biết người ở đâu ngoài thực địa, không phải ở pixel nào. Toạ độ mặt đất cũng là nền cho bước xác nhận.",
        "results": [
            ("Sai số vị trí tính theo vị trí trong ảnh và độ cao, gửi kèm mỗi cảnh báo", "docs/TECHNICAL.md"),
        ],
        "files": ["edge/georef.py", "edge/telemetry.py"],
        "docs": [("Kỹ thuật, mục 8", "docs/TECHNICAL.md"), ("Thuật toán từng bước", "docs/THUAT_TOAN.md")],
        "rq": "Câu hỏi 3 (hệ thống)",
    },
    {
        "id": "confirm", "title": "4. Xác nhận",
        "icon": "✅", "color": "#d97706", "summary": "Thấy đủ 3 lần mới tin là người",
        "metrics": [
            {"label": "Người được xác nhận trên video thật (SeaDronesSee v21, 2 khung/giây)", "a_label": "ByteTrack", "a": 2, "b_label": "theo toạ độ mặt đất", "b": 12, "max": 19, "unit": "/19", "doc": "docs/results/sds_mot_confirm.md"},
        ],
        "what": "Chỉ cảnh báo khi một người được thấy đủ 3 lần trong 5 giây. Các lần thấy được gom theo toạ độ mặt đất (cách `geo`), không theo vị trí trên ảnh.",
        "why": "Một lần thấy có thể là báo nhầm (sóng, rác trôi). Cách theo dõi thông thường (ByteTrack) ghép box theo độ chồng lấn trên ảnh, nhưng ở 2 khung/giây box hai khung liền nhau gần như không chồng nhau nên gãy.",
        "results": [
            ("Video thật SeaDronesSee, 2 khung/giây: gom theo toạ độ xác nhận 12/19 người, ByteTrack 2/19", "docs/results/sds_mot_confirm.md"),
            ("Vì sao bản ByteTrack có bù chuyển động camera vẫn bỏ sót", "docs/results/rq3_cmc_cause.md"),
        ],
        "files": ["edge/confirm.py"],
        "docs": [("Kỹ thuật, mục 9", "docs/TECHNICAL.md"), ("Tổng quan, mục 3.9", "docs/TONG_QUAN.md")],
        "rq": "Câu hỏi 3 (hệ thống)",
    },
    {
        "id": "send", "title": "5. Gửi cảnh báo",
        "icon": "📡", "color": "#d45656", "summary": "Gửi toạ độ trước, ảnh sau, không mất khi mất sóng",
        "metrics": [],
        "what": "Mỗi cảnh báo gồm toạ độ (vài trăm byte, gửi trước) và ảnh cắt nhỏ (gửi sau). Cảnh báo được lưu vào hàng đợi trên UAV trước khi gửi; mất mạng thì gửi lại khi có sóng, trạm bỏ qua bản trùng.",
        "why": "Vùng lũ thường mất sóng; không gửi được video về. Không được mất cảnh báo nào khi mạng chập chờn.",
        "results": [
            ("Giả lập mất gói và mất sóng theo đồng hồ mô phỏng; demo có banner mất sóng và gửi bù", "docs/DEMO_BAO_VE.md"),
        ],
        "files": ["edge/alerts.py", "sim/netem.py"],
        "docs": [("Kỹ thuật, mục 10–11", "docs/TECHNICAL.md")],
        "rq": "Câu hỏi 3 (hệ thống)",
    },
    {
        "id": "ground", "title": "6. Trạm mặt đất và bản đồ",
        "icon": "🗺️", "color": "#0e7490", "summary": "Gộp cảnh báo thành sự cố, hiện trên bản đồ",
        "metrics": [],
        "what": "Máy của đội cứu hộ nhận cảnh báo, gộp các cảnh báo gần nhau thành một sự cố, xếp ưu tiên và hiện trên bản đồ. Người vận hành gắn thẻ (dưới nước, trên mái) và đóng sự cố.",
        "why": "GPS trôi làm một người sinh nhiều cảnh báo; gộp lại để người vận hành không bị ngợp. Bản đồ phải chạy được khi mất mạng.",
        "results": [
            ("Gộp cảnh báo thành sự cố, bán kính 5 m", "docs/results/alert_memory.md"),
            ("Hai drone cùng gửi về một trạm", "docs/results/multi_uav_demo.md"),
        ],
        "files": ["ground/app.py", "ground/incidents.py", "ground/priority.py", "ground/map.html"],
        "docs": [("Kỹ thuật, mục 12", "docs/TECHNICAL.md")],
        "rq": "Câu hỏi 3 (hệ thống)",
    },
]

# Hai mảng nằm cạnh đường đi của dữ liệu.
SIDE_TOPICS: list[dict[str, Any]] = [
    {
        "id": "edge", "title": "Chạy trên thiết bị biên",
        "icon": "⚡", "color": "#b45309", "summary": "Nhanh tới đâu trên máy nhỏ gắn trên drone",
        "metrics": [],
        "what": "Đo mô hình chạy nhanh tới đâu khi nén bằng TensorRT (FP16, INT8) trên GPU T4 của Kaggle, và giả lập thời gian của Jetson để xem pipeline theo kịp bao nhiêu khung/giây.",
        "why": "Không có Jetson thật; T4 cùng nền tảng NVIDIA nên thứ hạng giữa các cấu hình vẫn đúng. Đây là câu hỏi 2.",
        "results": [
            ("Mã đo đã xong, chưa chạy trên T4", "docs/TECHNICAL.md"),
            ("Giả lập thời gian thiết bị (ước lượng, chưa hiệu chỉnh)", "docs/TECHNICAL.md"),
        ],
        "files": ["scripts/run_rq2.py", "edge/device_sim.py", "configs/devices/orin_nano_super.yaml", "tools/fit_device_profile.py"],
        "docs": [("Kỹ thuật, mục 14", "docs/TECHNICAL.md")],
        "rq": "Câu hỏi 2 (tốc độ)",
    },
    {
        "id": "data", "title": "Dữ liệu và cách đánh giá",
        "icon": "🗂️", "color": "#475569", "summary": "Huấn luyện, đánh giá và tập ảnh lũ tự gán",
        "metrics": [],
        "what": "Huấn luyện trên VisDrone và AFO; đánh giá trên VisDrone, AFO, SeaDronesSee và tập ảnh lũ tự gán nhãn (188 khung, chưa khoá). Kết quả chia theo nhóm cỡ người, có khoảng tin cậy.",
        "why": "Chưa có bộ công khai nào chụp người trong lũ từ UAV có nhãn; tập tự gán là nơi duy nhất trả lời câu hỏi về cảnh lũ thật.",
        "results": [
            ("Kiểm tra trùng ảnh trước khi khoá: không trùng với 5 tập huấn luyện", "docs/results/flood_truoc_khoa.md"),
        ],
        "files": ["eval/eval_by_size.py", "eval/metrics.py", "tools/check_leakage.py", "scripts/eval_flood.sh"],
        "docs": [("Hướng dẫn gán nhãn", "docs/LABELING.md"), ("Kỹ thuật, mục 15", "docs/TECHNICAL.md")],
        "rq": "Câu hỏi 1 (độ chính xác)",
    },
]


def project_map() -> dict[str, Any]:
    """Các khâu của bản đồ dự án, mỗi khâu kèm đường dẫn tài liệu và mã nguồn."""

    def out(stage: dict[str, Any]) -> dict[str, Any]:
        return {
            **stage,
            "results": [{"text": t, "doc": d} for t, d in stage["results"]],
            "docs": [{"text": t, "doc": d} for t, d in stage["docs"]],
        }

    return {"stages": [out(s) for s in STAGES], "side": [out(s) for s in SIDE_TOPICS]}


def list_docs() -> list[dict[str, str]]:
    """Tài liệu đọc được: tổng quan trước, rồi từng file kết quả."""
    names = [d for d in DOC_ORDER if (ROOT / d).is_file()]
    names += sorted(str(p.relative_to(ROOT)) for p in (ROOT / "docs" / "results").glob("*.md"))
    return [{"path": n, "title": doc_title(ROOT / n)} for n in names]


def doc_title(path: Path) -> str:
    """Dòng tiêu đề đầu tiên (# ...) của file markdown, không có thì tên file."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.name


def read_doc(path: str) -> str:
    """Nội dung một tài liệu trong danh sách; tên khác thì ValueError (không đọc file tuỳ ý)."""
    if path not in {d["path"] for d in list_docs()}:
        raise ValueError(f"Không có tài liệu {path}")
    return (ROOT / path).read_text(encoding="utf-8")


def read_source(path: str) -> str:
    """Một file mã nguồn hay cấu hình của dự án, chỉ đọc; không cho đọc data/, runs/ hay ra ngoài kho."""
    target = (ROOT / path).resolve()
    rel = target.relative_to(ROOT) if ROOT in target.parents else None
    if rel is None or rel.parts[0] not in SOURCE_DIRS or target.suffix not in SOURCE_SUFFIXES or not target.is_file():
        raise ValueError(f"Không xem được {path}")
    return target.read_text(encoding="utf-8")


def asset_path(path: str) -> Path:
    """Ảnh nhúng trong tài liệu (docs/…/*.png, *.jpg, *.svg); đường dẫn khác thì ValueError."""
    target = (ROOT / path).resolve()
    docs_dir = (ROOT / "docs").resolve()
    if docs_dir not in target.parents or target.suffix.lower() not in {".png", ".jpg", ".jpeg", ".svg"} or not target.is_file():
        raise ValueError(f"Không có ảnh {path}")
    return target


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _aliases(cell: str) -> list[str]:
    """Các cách viết của một thuật ngữ: tách theo dấu phẩy và ngoặc, bỏ dấu `; bỏ mảnh quá ngắn hay chỉ là chữ số."""
    cell = cell.replace("`", "")
    parts = re.split(r",|\(|\)", cell)
    out = []
    for part in parts:
        part = part.strip()
        if len(part) >= 2 and not part.isdigit() and part not in out:
            out.append(part)
    return out


def load_glossary(path: Path = GLOSSARY) -> list[dict[str, Any]]:
    """Mọi dòng bảng trong THUAT_NGU.md thành mục giải thích: tên, tiếng Anh, nghĩa, ghi chú, mục, các cách viết."""
    entries: list[dict[str, Any]] = []
    section, header = "", None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## ") or line.startswith("### "):
            section, header = line.lstrip("#").strip(), None
            continue
        if not line.startswith("|"):
            header = None
            continue
        cells = _cells(line)
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set(line.replace("|", "").strip()) <= {"-", " "}:
            continue
        row = dict(zip(header, cells))
        name = row.get("dùng trong tài liệu") or row.get("mã") or row.get("ký hiệu")
        if not name:
            continue
        english = row.get("tiếng anh", "")
        meaning = row.get("nghĩa") or row.get("tên mô tả") or ""
        aliases = _aliases(name) + [a for a in _aliases(english) if a.lower() not in name.lower()]
        # Loại để tô màu gạch chân: thuật ngữ ngành, khái niệm dự án đặt tên tiếng Việt, ký hiệu nội bộ.
        kind = "nganh" if section.startswith("1.") else "du_an" if section.startswith("2.") else "noi_bo"
        entries.append({
            "kind": kind,
            "term": name.replace("`", ""), "english": english, "meaning": meaning, "note": row.get("ghi chú", ""),
            "section": section, "aliases": aliases,
        })
    return entries
