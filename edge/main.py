"""Chạy pipeline trên UAV với video phát lại: lấy mẫu → phát hiện → định vị → xác nhận → cảnh báo; ghi log JSONL.

Ví dụ:
    .venv/bin/python -m edge.main --config configs/edge.yaml --source video.mp4 --output runs/edge/demo
    # gửi về trạm mặt đất, mất 20% gói và mất sóng từ giây 30 đến 90:
    ... --ground-url http://localhost:8000 --net-loss 0.2 --net-outage 30 90
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import IO, Any

import cv2
import numpy as np

from edge.alerts import FakeTransport, HttpTransport, Outbox, Transport, crop_jpeg_base64, make_alert
from edge.confirm import Confirmer, GeoConfirmer, TrackConfirmer
from edge.detector import ByteTracker, Detector, ReplayDetector, YoloDetector, person_scale
from edge.device_sim import BusyDevice, inference_counts, load_profile
from edge.georef import (
    Camera, ErrorModel, expected_person_px, frame_motion, gps_to_pixel, ground_distance_m, locate, position_error_m,
)
from edge.pacing import RealtimePacer
from edge.sampler import iter_timed_frames, views_fps
from edge.status import LiveView, StatusReporter
from edge.telemetry import SampledTelemetry, TelemetrySource
from eval.draw import draw_boxes
from shared.config import parse_args_with_config
from shared.provenance import write_run_config
from shared.schema import AlertCrop, Confirmation
from sim.flight import StraightFlight
from sim.netem import NetemTransport

CONFIRMED_COLOR_BGR = (0, 200, 0)
SYNTHETIC_NOTE = "TELEMETRY GIA LAP - vi tri chi minh hoa"  # cv2.putText không vẽ được dấu tiếng Việt


def build_parser() -> argparse.ArgumentParser:
    """Khai báo tham số dòng lệnh; tách riêng để sim/sweep_rq3.py kiểm tra tên khoá trước khi chạy."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, required=True, help="File video hoặc thư mục chuỗi khung")
    parser.add_argument("--source-fps", type=float, default=None, help="FPS của chuỗi khung (bắt buộc khi nguồn là thư mục)")
    parser.add_argument("--fps", type=float, default=2.0, help="Số khung xử lý mỗi giây; với --min-views là mức trần")
    parser.add_argument("--min-views", type=float, default=None,
                        help="Đổi tần số theo độ cao và vận tốc để mỗi người được thấy khoảng số lần này (giữa --fps-min và --fps); không đặt hoặc 0 thì cố định --fps")
    parser.add_argument("--fps-min", type=float, default=0.5, help="Tần số xử lý tối thiểu khi dùng --min-views")
    parser.add_argument("--max-frames", type=int, default=None, help="Giới hạn số khung xử lý")
    parser.add_argument("--model", default="yolo26s.pt", help="Trọng số .pt, .onnx hoặc .engine")
    parser.add_argument("--replay", type=Path, default=None, help="Đọc lại detections.jsonl thay cho chạy mô hình (RQ3)")
    parser.add_argument("--mode", choices=["full", "tiled"], default="tiled", help="Toàn ảnh hay cắt ô")
    parser.add_argument("--imgsz", type=int, default=1280, help="Kích thước suy luận khi mode=full")
    parser.add_argument("--tile", type=int, default=640, help="Cạnh ô khi mode=tiled")
    parser.add_argument("--overlap", type=float, default=0.2, help="Độ chồng giữa các ô")
    parser.add_argument("--conf", type=float, default=0.1, help="Ngưỡng conf của detector (thấp vì có xác nhận nhiều khung)")
    parser.add_argument("--max-det", type=int, default=1000, help="Số box tối đa mỗi lần suy luận")
    parser.add_argument("--target-person-px", type=float, default=None,
                        help="Thu nhỏ khung theo độ cao để người dự kiến còn khoảng số px này (docs/results/e6_sds_pilot.md); không đặt thì giữ nguyên")
    parser.add_argument("--person-m", type=float, default=0.5, help="Cỡ người nhìn từ trên xuống (m), để tính số px dự kiến")
    parser.add_argument("--device", default=None, help="cuda:0, mps, cpu (mặc định: tự chọn)")
    parser.add_argument("--telemetry", type=Path, default=None, help="File .csv hoặc .srt (DJI); không có thì dùng chuyến bay thẳng giả lập")
    parser.add_argument("--alt-offset-m", type=float, default=0.0, help="SRT: cộng vào độ cao tương đối để ra độ cao so với mặt nước")
    parser.add_argument("--lat0", type=float, default=21.0285, help="Giả lập: vĩ độ điểm xuất phát")
    parser.add_argument("--lon0", type=float, default=105.8542, help="Giả lập: kinh độ điểm xuất phát")
    parser.add_argument("--alt-m", type=float, default=50.0, help="Giả lập: độ cao so với mặt nước (m)")
    parser.add_argument("--speed-mps", type=float, default=10.0, help="Giả lập: vận tốc (m/s)")
    parser.add_argument("--yaw-deg", type=float, default=0.0, help="Giả lập: hướng bay (0 = Bắc)")
    parser.add_argument("--fov-deg", type=float, default=82.0, help="Góc nhìn camera (độ)")
    parser.add_argument("--fov-type", choices=["horizontal", "diagonal"], default="diagonal", help="--fov-deg là góc ngang hay chéo")
    parser.add_argument("--confirm", choices=["geo", "bytetrack", "bytetrack_cmc"], default="geo", help="Chiến lược xác nhận (TECHNICAL mục 9)")
    parser.add_argument("--radius-m", type=float, default=3.0, help="Bán kính gom của confirm geo")
    parser.add_argument("--n-confirm", type=int, default=3, help="Số lần thấy để xác nhận")
    parser.add_argument("--suppress-s", type=float, default=0.0, help="Không cảnh báo lại trong --radius-m quanh vị trí đã cảnh báo trong số giây này (0: tắt)")
    parser.add_argument("--track-thresh", type=float, default=0.25,
                        help="ByteTrack: ngưỡng conf để mở track mới và ghép vòng đầu (mặc định 0,25 như bytetrack.yaml); đặt bằng --conf để cùng đầu vào với geo (ROADMAP quyết định #9)")
    parser.add_argument("--window-s", type=float, default=5.0, help="Cửa sổ đếm lần thấy (giây)")
    parser.add_argument("--expire-s", type=float, default=6.0, help="Xoá cụm không được thấy quá số giây này")
    parser.add_argument("--uav-id", default="uav1", help="Mã UAV, đứng đầu alert_id")
    parser.add_argument("--position-error-m", type=float, default=None,
                        help="Sai số định vị cố định ghi vào cảnh báo; không đặt thì tính theo vị trí trong ảnh và độ cao (TECHNICAL 8.4)")
    parser.add_argument("--gps-sigma-m", type=float, default=3.0, help="Sai số GPS của UAV (1σ, m); RTK thì khoảng 0,05")
    parser.add_argument("--alt-sigma-m", type=float, default=2.0, help="Sai số độ cao so với mặt nước (1σ, m)")
    parser.add_argument("--yaw-sigma-deg", type=float, default=2.0, help="Sai số hướng (1σ, độ)")
    parser.add_argument("--tilt-sigma-deg", type=float, default=1.0, help="Lệch khỏi nhìn thẳng xuống (1σ, độ)")
    parser.add_argument("--ground-url", default=None, help="Địa chỉ trạm mặt đất; không có thì dùng transport giả luôn ack")
    parser.add_argument("--net-loss", type=float, default=0.0, help="Giả lập: xác suất mất mỗi lần gửi")
    parser.add_argument("--net-outage", type=float, nargs=2, action="append", default=None, metavar=("START", "END"), help="Giả lập: khoảng mất sóng (giây), lặp được")
    parser.add_argument("--link-probe-s", type=float, default=None, help="Gửi cảnh báo: khi mọi gói đang chờ gửi lại, cứ mỗi số giây này thử một gói toạ độ; gửi được thì gửi ngay mọi gói đang chờ (mặc định tắt)")
    parser.add_argument("--state-every-s", type=float, default=None, help="Gửi trạng thái drone (vị trí, vùng camera nhìn, cảnh báo đang chờ) về trạm mỗi số giây này, qua cùng giả lập mạng; mặc định tắt (edge/status.py)")
    parser.add_argument("--simulated-flight", action="store_true", help="Nguồn là chuyến bay mô phỏng (sim/make_rq3.py --render): ghi 'ảnh tổng hợp' lên video và báo trạm telemetry không phải thật")
    parser.add_argument("--live-port", type=int, default=None, help="Demo: phát video đã vẽ dạng MJPEG ở cổng này để trang bản đồ nhúng (http://localhost:<cổng>/); drone thật không gửi video")
    parser.add_argument("--drain-s", type=float, default=60.0, help="Sau khung cuối, tiếp tục gửi bù thêm số giây này")
    parser.add_argument("--seed", type=int, default=0, help="Seed cho giả lập mạng và nhiễu thời gian chờ gửi lại")
    parser.add_argument("--output", type=Path, default=Path("runs/edge/demo"), help="Thư mục log")
    parser.add_argument("--save-video", action="store_true", help="Ghi annotated.mp4: box đỏ là phát hiện, vòng xanh là người đã xác nhận")
    parser.add_argument("--device-profile", type=Path, default=None,
                        help="Giả lập thời gian xử lý của thiết bị biên (configs/devices/*.yaml): bỏ khung tới trong lúc bận, cảnh báo gửi lúc xử lý xong (edge/device_sim.py)")
    parser.add_argument("--realtime", action="store_true", help="Demo: giữ nhịp thời gian thực để cảnh báo hiện trên trạm mặt đất đúng lúc (không đổi kết quả)")
    parser.add_argument("--realtime-speed", type=float, default=1.0, help="Với --realtime: tốc độ phát (2 = nhanh gấp đôi)")
    parser.add_argument("--show", action="store_true", help="Demo: mở cửa sổ phát video đã vẽ trong lúc chạy (dùng cùng --realtime)")
    parser.add_argument("--save-frames", action="store_true", help="Ghi từng khung đã xử lý (vẽ như --save-video) thành frames/<frame_id>.jpg, cạnh dài tối đa 1920 px; giao diện console đọc")
    return parser


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    return parse_args_with_config(build_parser())


def write_jsonl(f: IO[str], record: dict[str, Any]) -> None:
    f.write(json.dumps(record, ensure_ascii=False) + "\n")


def track_color(track_id: int) -> tuple[int, int, int]:
    """Màu cố định cho mỗi track (BGR), để mắt theo được một người qua các khung."""
    hue = (track_id * 47) % 180
    return tuple(int(c) for c in cv2.cvtColor(np.uint8([[[hue, 220, 255]]]), cv2.COLOR_HSV2BGR)[0, 0])


def save_frame(image: Any, path: Path, max_side: int = 1920) -> None:
    """Ghi một khung đã vẽ thành JPEG, thu cạnh dài về max_side để trình duyệt tải nhanh."""
    path.parent.mkdir(parents=True, exist_ok=True)
    scale = max_side / max(image.shape[:2])
    if scale < 1:
        image = cv2.resize(image, (round(image.shape[1] * scale), round(image.shape[0] * scale)), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, 85])


def annotate(
    frame: Any, boxes: list[Any], confs: list[float], confirmed: list[Confirmation], tel: Any, cam: Camera, synthetic: bool,
    tracks: list[tuple[Any, int]] | None = None, t_now: float | None = None, recent_s: float | None = None,
) -> Any:
    """Vẽ phát hiện của khung và vị trí các người đã xác nhận chiếu lại vào khung hiện tại.

    Với chiến lược bytetrack, `tracks` là (box, track_id) của khung: vẽ khung màu theo track kèm số ID thay cho khung đỏ.
    recent_s: chỉ vẽ vòng của xác nhận trong số giây gần nhất. Vòng chiếu từ GPS của xác nhận cũ lệch dần khi GPS của
    drone trôi (docs/results/sds_mot_confirm.md), nằm trên chỗ trống và trông như báo nhầm; trạm mặt đất vẫn giữ đủ.
    """
    k = max(1.0, frame.shape[1] / 1920)  # khung 4K thu nhỏ khi chiếu: nét và chữ to theo
    if tracks is not None:
        # Track đã xác nhận (cluster_id của TrackConfirmer là track_id): khung đậm, nhãn "#id". Không vẽ vòng chiếu từ GPS:
        # với telemetry giả lập, vòng đó không trùng người và che mất khung.
        confirmed_ids = {c.cluster_id for c in confirmed}
        canvas = frame.copy()
        for box, track_id in tracks:
            x1, y1, x2, y2 = (int(round(v)) for v in box)
            color, done = track_color(track_id), track_id in confirmed_ids
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 3 if done else 1)
            label = f"#{track_id}" if done else str(track_id)
            cv2.putText(canvas, label, (x1, max(12, y1 - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
        if synthetic:
            cv2.putText(canvas, SYNTHETIC_NOTE, (10, int(30 * k)), cv2.FONT_HERSHEY_SIMPLEX, 0.8 * k, (0, 255, 255), int(2 * k), cv2.LINE_AA)
        return canvas
    canvas = draw_boxes(frame, boxes, confs)
    if synthetic:
        # Ghi thẳng lên video để không ai lấy nhầm video demo làm bằng chứng định vị.
        cv2.putText(canvas, SYNTHETIC_NOTE, (10, int(30 * k)), cv2.FONT_HERSHEY_SIMPLEX, 0.8 * k, (0, 255, 255), int(2 * k), cv2.LINE_AA)
    for c in confirmed:
        if recent_s is not None and t_now is not None and t_now - c.t > recent_s:
            continue
        u, v = gps_to_pixel(c.lat, c.lon, tel, cam)
        if 0 <= u < cam.width and 0 <= v < cam.height:
            cv2.circle(canvas, (int(u), int(v)), int(20 * k), CONFIRMED_COLOR_BGR, int(2 * k), cv2.LINE_AA)
            cv2.putText(canvas, f"#{c.cluster_id}", (int(u + 22 * k), int(v)), cv2.FONT_HERSHEY_SIMPLEX, 0.8 * k,
                        CONFIRMED_COLOR_BGR, int(2 * k))
    return canvas


def draw_status(canvas: Any, lines: list[str], banner: str | None = None) -> Any:
    """Ghi các dòng trạng thái (thiết bị giả lập, FPS, độ trễ) ở góc dưới trái; banner đỏ ở giữa trên (mất sóng)."""
    height, k = canvas.shape[0], max(1.0, canvas.shape[1] / 1920)
    font = cv2.FONT_HERSHEY_SIMPLEX
    for i, line in enumerate(reversed(lines)):
        y = int(height - 15 * k - 36 * k * i)
        cv2.putText(canvas, line, (int(10 * k), y), font, 0.9 * k, (0, 0, 0), int(6 * k), cv2.LINE_AA)
        cv2.putText(canvas, line, (int(10 * k), y), font, 0.9 * k, (255, 255, 255), int(2 * k), cv2.LINE_AA)
    if banner:
        (w, h), _ = cv2.getTextSize(banner, font, 1.2 * k, int(3 * k))
        x, top = (canvas.shape[1] - w) // 2, int(50 * k)
        cv2.rectangle(canvas, (x - int(12 * k), top), (x + w + int(12 * k), top + h + int(24 * k)), (0, 0, 200), -1)
        cv2.putText(canvas, banner, (x, top + h + int(10 * k)), font, 1.2 * k, (255, 255, 255), int(3 * k), cv2.LINE_AA)
    return canvas


def build_confirmer(args: argparse.Namespace, telemetry: TelemetrySource, cam: Camera) -> Confirmer:
    """Chọn chiến lược xác nhận; bytetrack_cmc bù chuyển động camera bằng telemetry của hai khung liên tiếp."""
    if args.confirm == "geo":
        return GeoConfirmer(args.radius_m, args.n_confirm, args.window_s, args.expire_s, args.suppress_s)
    motion = (lambda t0, t1: frame_motion(telemetry.at(t0), telemetry.at(t1), cam)) if args.confirm == "bytetrack_cmc" else None
    tracker = ByteTracker(track_high_thresh=args.track_thresh, new_track_thresh=args.track_thresh,
                          track_low_thresh=min(0.1, args.track_thresh))
    return TrackConfirmer(tracker, args.n_confirm, args.window_s, args.expire_s, motion, args.suppress_s, args.radius_m)


def main() -> None:
    """Nối các khối và chạy hết nguồn."""
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    telemetry: TelemetrySource
    synthetic = args.telemetry is None
    if synthetic:
        telemetry = StraightFlight(args.lat0, args.lon0, args.alt_m, args.speed_mps, args.yaw_deg)
    elif args.telemetry.suffix.lower() == ".srt":
        telemetry = SampledTelemetry.from_srt(args.telemetry, args.alt_offset_m, args.yaw_deg)
    else:
        telemetry = SampledTelemetry.from_csv(args.telemetry)
    detector: Detector = (
        ReplayDetector(args.replay)
        if args.replay
        else YoloDetector(args.model, args.mode, args.imgsz, args.tile, args.overlap, args.conf, args.max_det, args.device)
    )
    transport: Transport = HttpTransport(args.ground_url) if args.ground_url else FakeTransport()
    if args.net_loss > 0 or args.net_outage:
        transport = NetemTransport(transport, args.net_loss, [tuple(o) for o in args.net_outage or []], args.seed)
    # Outbox của lần chạy trước trong cùng thư mục là của thí nghiệm khác: xoá để lần chạy tái lập được.
    for suffix in ("", "-wal", "-shm"):
        (args.output / f"outbox.sqlite{suffix}").unlink(missing_ok=True)
    outbox = Outbox(args.output / "outbox.sqlite", transport, seed=args.seed, probe_s=args.link_probe_s)
    # Trạng thái drone đi đường riêng (không qua outbox), cùng khoảng mất sóng nhưng seed khác, để bật hay tắt không đổi
    # chuỗi sự kiện mạng của cảnh báo (kết quả RQ3d giữ nguyên).
    state_transport: Transport = HttpTransport(args.ground_url) if args.ground_url else FakeTransport()
    if args.net_loss > 0 or args.net_outage:
        state_transport = NetemTransport(state_transport, args.net_loss, [tuple(o) for o in args.net_outage or []], args.seed + 7919)
    live = LiveView(args.live_port) if args.live_port else None
    if live:
        print(f"Video trực tiếp: http://localhost:{live.port}/")
    drawing = args.save_video or args.save_frames or args.show or live is not None
    model_name = Path(args.replay or args.model).name
    device = BusyDevice(load_profile(args.device_profile)) if args.device_profile else None
    pacer = RealtimePacer(args.realtime_speed) if args.realtime else None
    outages = [tuple(o) for o in args.net_outage or []]
    run_args = {**vars(args), "telemetry_source": "synthetic StraightFlight" if synthetic else str(args.telemetry),
                "device_profile_data": device.profile.model_dump() if device else None}
    write_run_config(args.output, "edge/main.py", None if args.replay else args.model, getattr(detector, "device", None), run_args)
    if synthetic:
        print("[cảnh báo] Telemetry giả lập: toạ độ GPS và vòng xác nhận trên video chỉ để minh hoạ, không phải vị trí thật.")
    if device and not device.profile.calibrated:
        print(f"[cảnh báo] Hồ sơ thiết bị {args.device_profile} chưa hiệu chỉnh: độ trễ là ước lượng, không phải số đo.")

    next_t, fps_now = 0.0, args.fps
    error_model = ErrorModel(args.gps_sigma_m, args.alt_sigma_m, args.yaw_sigma_deg, args.tilt_sigma_deg)
    cam: Camera | None = None
    confirmer: Confirmer | None = None
    video: cv2.VideoWriter | None = None
    confirmed: list[Confirmation] = []
    last_dets: list[Any] = []
    n_frames, t = 0, 0.0

    def report(t_now: float, tel: Any, force: bool = False, done: bool = False) -> None:
        """Gửi trạng thái drone về trạm nếu tới hạn (--state-every-s)."""
        if reporter is None or cam is None:
            return
        if force and reporter.last_t is not None:
            # Gói ép gửi (hết chuyến) không được sớm hơn gói trước, nếu không trạm coi là gói tới muộn và bỏ qua.
            t_now = max(t_now, reporter.last_t)
        prev = telemetry.at(max(t_now - 1.0, 0.0))
        speed = ground_distance_m(prev.lat, prev.lon, tel.lat, tel.lon) / min(t_now, 1.0) if t_now > 0 else None
        reporter.maybe_send(
            t_now, tel, cam, force=force, speed_mps=speed, fps=device.achieved_fps(t_now) if device else fps_now,
            pending_alerts=outbox.pending(), alerts_total=len(confirmed),
            device=device.profile.name if device else None, telemetry_real=not (synthetic or args.simulated_flight), done=done,
        )

    def status(t_now: float) -> tuple[list[str], str | None]:
        """Dòng trạng thái và banner vẽ lên video demo."""
        lines = ["ANH TONG HOP - chuyen bay mo phong"] if args.simulated_flight else []
        if device:
            lines.append(f"Thiet bi gia lap: {device.profile.name}")
            lines.append(f"{device.achieved_fps(t_now):.1f} khung/s, tre {device.last_latency_ms:.0f} ms/khung, bo {device.n_skipped} khung")
        banner = "MAT SONG - canh bao cho gui bu" if any(a <= t_now < b for a, b in outages) else None
        return lines, banner

    def skip_frame(frame: Any, frame_id: Any, t_now: float, tel: Any) -> None:
        """Khung không chạy detector (tần số theo độ cao, thiết bị bận): video demo vẫn ghi để phát đúng nhịp."""
        assert cam is not None
        report(t_now, tel)
        if drawing:
            write_frame(annotate(frame, [d.box_px for d in last_dets], [d.conf for d in last_dets], confirmed, tel, cam,
                                 synthetic, None, t_now, args.expire_s), frame_id, t_now)
        if pacer:
            pacer.wait_until(t_now)

    def write_frame(drawn: Any, frame_id: Any, t_now: float) -> None:
        nonlocal video
        assert cam is not None
        drawn = draw_status(drawn, *status(t_now))
        if live:
            live.publish(drawn)
        if args.show:
            scale = min(1.0, 1280 / drawn.shape[1])
            cv2.imshow("FloodEye - UAV", cv2.resize(drawn, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA))
            cv2.waitKey(1)
        if args.save_video:
            if video is None:
                path = str(args.output / "annotated.mp4")
                video = cv2.VideoWriter(path, cv2.VideoWriter.fourcc(*"mp4v"), args.fps, (cam.width, cam.height))
            video.write(drawn)
        if args.save_frames:
            save_frame(drawn, args.output / "frames" / f"{frame_id:06d}.jpg")
    with (
        (args.output / "detections.jsonl").open("w", encoding="utf-8") as det_log,
        (args.output / "confirmations.jsonl").open("w", encoding="utf-8") as conf_log,
        (args.output / "alerts.jsonl").open("w", encoding="utf-8") as alert_log,
        (args.output / "alerts_sent.jsonl").open("w", encoding="utf-8") as sent_log,
        (args.output / "timings.jsonl").open("w", encoding="utf-8") as time_log,
        (args.output / "states_sent.jsonl").open("w", encoding="utf-8") as state_log,
    ):
        reporter = StatusReporter(state_transport, args.uav_id, args.state_every_s, state_log) if args.state_every_s else None
        for frame_id, t, frame in iter_timed_frames(args.source, args.fps, args.source_fps, args.max_frames):
            if cam is None or confirmer is None:
                cam = Camera.from_fov(args.fov_deg, args.fov_type, frame.shape[1], frame.shape[0])
                confirmer = build_confirmer(args, telemetry, cam)
            tel = telemetry.at(t)
            if args.min_views:  # 0 để tắt từ dòng lệnh khi file cấu hình đã đặt
                # Bỏ khung tới hạn kế tiếp; hạn tính lại mỗi khung xử lý theo độ cao và vận tốc hiện tại.
                if t + 1e-9 < next_t:
                    skip_frame(frame, frame_id, t, tel)
                    continue
                prev = telemetry.at(max(t - 1.0, 0.0))
                speed = ground_distance_m(prev.lat, prev.lon, tel.lat, tel.lon) / max(min(t, 1.0), 1e-9) if t > 0 else 0.0
                footprint_m = cam.height * tel.alt_agl_m / cam.f_px
                # Khung đầu chưa có vận tốc (không nhìn trước telemetry): dùng tần số trần thay vì sàn.
                fps_now = views_fps(footprint_m, speed, args.min_views, args.fps_min, args.fps) if t > 0 else args.fps
                # Cộng dồn từ hạn trước (không từ t) để làm tròn theo khung nguồn không kéo tần số thực xuống.
                next_t = max(next_t + 1.0 / fps_now, t + 0.5 / fps_now)
                # Xử lý thưa thì N lần thấy trải dài hơn: cửa sổ đếm phải phủ thời gian một người nằm trong khung,
                # nếu không bay cao (ít khung) lại bỏ sót nhiều hơn (runs/rq3/adaptive, lần quét đầu).
                in_frame_s = footprint_m / speed if speed > 0 else args.window_s
                confirmer.window_s = max(args.window_s, in_frame_s)
                confirmer.expire_s = max(args.expire_s, confirmer.window_s + 1.0 / fps_now)
            scale = person_scale(expected_person_px(tel, cam, args.person_m), args.target_person_px)
            if device and not device.ready(t):
                # Thiết bị còn bận với khung trước: khung này bị bỏ, video demo vẽ kết quả gần nhất.
                skip_frame(frame, frame_id, t, tel)
                continue
            if pacer:
                pacer.wait_until(t)
            dets, timings = detector.detect(frame, frame_id, t, scale)
            t_done = t
            if device:
                n_tiles, n_full = inference_counts(frame.shape[1], frame.shape[0], scale, args.mode, args.tile, args.overlap)
                t_done = device.run(t, n_tiles, n_full)
                timings.update({"sim_n_tiles": n_tiles, "sim_latency_ms": device.last_latency_ms, "t_done": t_done})
            start = time.perf_counter()
            dets = [locate(d, tel, cam) for d in dets]
            timings["georef_ms"] = (time.perf_counter() - start) * 1000.0
            timings["fps_target"] = fps_now
            start = time.perf_counter()
            new_confirmed = confirmer.update(dets, t)
            timings["confirm_ms"] = (time.perf_counter() - start) * 1000.0
            last_dets = dets
            if pacer:
                pacer.wait_until(t_done)

            for d in dets:
                write_jsonl(det_log, d.model_dump())
            for c in new_confirmed:
                write_jsonl(conf_log, c.model_dump())
                error_m = args.position_error_m
                if error_m is None:
                    x1, _, x2, y2 = c.box_px
                    error_m = position_error_m((x1 + x2) / 2.0, y2, tel, cam, error_model)
                alert = make_alert(c, args.uav_id, len(confirmed) + 1, tel, round(error_m, 2), model_name)
                # Có thiết bị giả lập thì quyết định chỉ có khi xử lý xong (t_done); không có thì coi xử lý tức thời.
                outbox.enqueue(alert, AlertCrop(alert_id=alert.alert_id, jpeg_base64=crop_jpeg_base64(frame, c.box_px)), t_done)
                write_jsonl(alert_log, alert.model_dump())
                confirmed.append(c)
            for record in outbox.pump(t_done):
                write_jsonl(sent_log, record)
            write_jsonl(time_log, {"frame_id": frame_id, "t": t, "n_dets": len(dets), **timings})
            n_frames += 1
            report(t_done, telemetry.at(t_done))

            if drawing:
                tracks = getattr(confirmer, "last_assignments", None)
                drawn = annotate(frame, [d.box_px for d in dets], [d.conf for d in dets], confirmed, tel, cam, synthetic, tracks,
                                 t, args.expire_s)
                write_frame(drawn, frame_id, t)
        # Hết video: tiếp tục gửi bù mỗi giây, như UAV vẫn bay tiếp và giữ kết nối.
        t_end = t
        for k in range(1, int(args.drain_s) + 1):
            if outbox.pending() == 0:
                break
            if pacer:
                pacer.wait_until(t + k)
            for record in outbox.pump(t + k):
                write_jsonl(sent_log, record)
            t_end = t + k
            report(t_end, telemetry.at(t))
        # Gói cuối báo hết chuyến, để trạm không hiểu im lặng sau đó là mất sóng.
        report(t_end, telemetry.at(t), force=True, done=True)
    if video is not None:
        video.release()
    if live:
        live.close()
    pending = outbox.pending()
    outbox.close()
    if device:
        print(f"Thiết bị giả lập {device.profile.name}: bỏ {device.n_skipped} khung vì bận, {device.achieved_fps(t):.2f} khung/giây.")
    print(f"Đã xử lý {n_frames} khung, xác nhận {len(confirmed)} người, còn {pending} thông điệp chưa gửi được. Log tại: {args.output}")


if __name__ == "__main__":
    main()
