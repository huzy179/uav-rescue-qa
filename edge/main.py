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

from edge.alerts import FakeTransport, HttpTransport, Outbox, Transport, crop_jpeg_base64, make_alert
from edge.confirm import GeoConfirmer
from edge.detector import Detector, ReplayDetector, YoloDetector
from edge.georef import Camera, gps_to_pixel, locate
from edge.sampler import iter_timed_frames
from edge.telemetry import SampledTelemetry, TelemetrySource
from eval.draw import draw_boxes
from shared.config import parse_args_with_config
from shared.provenance import write_run_config
from shared.schema import AlertCrop, Confirmation
from sim.flight import StraightFlight
from sim.netem import NetemTransport

CONFIRMED_COLOR_BGR = (0, 200, 0)
SYNTHETIC_NOTE = "TELEMETRY GIA LAP - vi tri chi minh hoa"  # cv2.putText không vẽ được dấu tiếng Việt


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, required=True, help="File video hoặc thư mục chuỗi khung")
    parser.add_argument("--source-fps", type=float, default=None, help="FPS của chuỗi khung (bắt buộc khi nguồn là thư mục)")
    parser.add_argument("--fps", type=float, default=2.0, help="Số khung xử lý mỗi giây")
    parser.add_argument("--max-frames", type=int, default=None, help="Giới hạn số khung xử lý")
    parser.add_argument("--model", default="yolo26s.pt", help="Trọng số .pt, .onnx hoặc .engine")
    parser.add_argument("--replay", type=Path, default=None, help="Đọc lại detections.jsonl thay cho chạy mô hình (RQ3)")
    parser.add_argument("--mode", choices=["full", "tiled"], default="tiled", help="Toàn ảnh hay cắt ô")
    parser.add_argument("--imgsz", type=int, default=1280, help="Kích thước suy luận khi mode=full")
    parser.add_argument("--tile", type=int, default=640, help="Cạnh ô khi mode=tiled")
    parser.add_argument("--overlap", type=float, default=0.2, help="Độ chồng giữa các ô")
    parser.add_argument("--conf", type=float, default=0.1, help="Ngưỡng conf của detector (thấp vì có xác nhận nhiều khung)")
    parser.add_argument("--max-det", type=int, default=1000, help="Số box tối đa mỗi lần suy luận")
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
    parser.add_argument("--radius-m", type=float, default=3.0, help="Bán kính gom của confirm")
    parser.add_argument("--n-confirm", type=int, default=3, help="Số lần thấy để xác nhận")
    parser.add_argument("--window-s", type=float, default=5.0, help="Cửa sổ đếm lần thấy (giây)")
    parser.add_argument("--expire-s", type=float, default=6.0, help="Xoá cụm không được thấy quá số giây này")
    parser.add_argument("--uav-id", default="uav1", help="Mã UAV, đứng đầu alert_id")
    parser.add_argument("--position-error-m", type=float, default=5.0, help="Sai số định vị ghi vào cảnh báo (GPS thường chiếm phần lớn)")
    parser.add_argument("--ground-url", default=None, help="Địa chỉ trạm mặt đất; không có thì dùng transport giả luôn ack")
    parser.add_argument("--net-loss", type=float, default=0.0, help="Giả lập: xác suất mất mỗi lần gửi")
    parser.add_argument("--net-outage", type=float, nargs=2, action="append", default=None, metavar=("START", "END"), help="Giả lập: khoảng mất sóng (giây), lặp được")
    parser.add_argument("--drain-s", type=float, default=60.0, help="Sau khung cuối, tiếp tục gửi bù thêm số giây này")
    parser.add_argument("--seed", type=int, default=0, help="Seed cho giả lập mạng và nhiễu thời gian chờ gửi lại")
    parser.add_argument("--output", type=Path, default=Path("runs/edge/demo"), help="Thư mục log")
    parser.add_argument("--save-video", action="store_true", help="Ghi annotated.mp4: box đỏ là phát hiện, vòng xanh là người đã xác nhận")
    return parse_args_with_config(parser)


def write_jsonl(f: IO[str], record: dict[str, Any]) -> None:
    f.write(json.dumps(record, ensure_ascii=False) + "\n")


def annotate(
    frame: Any, boxes: list[Any], confs: list[float], confirmed: list[Confirmation], tel: Any, cam: Camera, synthetic: bool
) -> Any:
    """Vẽ phát hiện của khung và vị trí các người đã xác nhận chiếu lại vào khung hiện tại."""
    canvas = draw_boxes(frame, boxes, confs)
    if synthetic:
        # Ghi thẳng lên video để không ai lấy nhầm video demo làm bằng chứng định vị.
        cv2.putText(canvas, SYNTHETIC_NOTE, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
    for c in confirmed:
        u, v = gps_to_pixel(c.lat, c.lon, tel, cam)
        if 0 <= u < cam.width and 0 <= v < cam.height:
            cv2.circle(canvas, (int(u), int(v)), 20, CONFIRMED_COLOR_BGR, 2, cv2.LINE_AA)
            cv2.putText(canvas, f"#{c.cluster_id}", (int(u) + 22, int(v)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, CONFIRMED_COLOR_BGR, 2)
    return canvas


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
    confirmer = GeoConfirmer(args.radius_m, args.n_confirm, args.window_s, args.expire_s)
    transport: Transport = HttpTransport(args.ground_url) if args.ground_url else FakeTransport()
    if args.net_loss > 0 or args.net_outage:
        transport = NetemTransport(transport, args.net_loss, [tuple(o) for o in args.net_outage or []], args.seed)
    # Outbox của lần chạy trước trong cùng thư mục là của thí nghiệm khác: xoá để lần chạy tái lập được.
    for suffix in ("", "-wal", "-shm"):
        (args.output / f"outbox.sqlite{suffix}").unlink(missing_ok=True)
    outbox = Outbox(args.output / "outbox.sqlite", transport, seed=args.seed)
    model_name = Path(args.replay or args.model).name
    run_args = {**vars(args), "telemetry_source": "synthetic StraightFlight" if synthetic else str(args.telemetry)}
    write_run_config(args.output, "edge/main.py", None if args.replay else args.model, getattr(detector, "device", None), run_args)
    if synthetic:
        print("[cảnh báo] Telemetry giả lập: toạ độ GPS và vòng xác nhận trên video chỉ để minh hoạ, không phải vị trí thật.")

    cam: Camera | None = None
    video: cv2.VideoWriter | None = None
    confirmed: list[Confirmation] = []
    n_frames, t = 0, 0.0
    with (
        (args.output / "detections.jsonl").open("w", encoding="utf-8") as det_log,
        (args.output / "confirmations.jsonl").open("w", encoding="utf-8") as conf_log,
        (args.output / "alerts.jsonl").open("w", encoding="utf-8") as alert_log,
        (args.output / "alerts_sent.jsonl").open("w", encoding="utf-8") as sent_log,
        (args.output / "timings.jsonl").open("w", encoding="utf-8") as time_log,
    ):
        for frame_id, t, frame in iter_timed_frames(args.source, args.fps, args.source_fps, args.max_frames):
            if cam is None:
                cam = Camera.from_fov(args.fov_deg, args.fov_type, frame.shape[1], frame.shape[0])
            tel = telemetry.at(t)
            dets, timings = detector.detect(frame, frame_id, t)
            start = time.perf_counter()
            dets = [locate(d, tel, cam) for d in dets]
            timings["georef_ms"] = (time.perf_counter() - start) * 1000.0
            start = time.perf_counter()
            new_confirmed = confirmer.update(dets, t)
            timings["confirm_ms"] = (time.perf_counter() - start) * 1000.0

            for d in dets:
                write_jsonl(det_log, d.model_dump())
            for c in new_confirmed:
                write_jsonl(conf_log, c.model_dump())
                alert = make_alert(c, args.uav_id, len(confirmed) + 1, tel, args.position_error_m, model_name)
                outbox.enqueue(alert, AlertCrop(alert_id=alert.alert_id, jpeg_base64=crop_jpeg_base64(frame, c.box_px)), t)
                write_jsonl(alert_log, alert.model_dump())
                confirmed.append(c)
            for record in outbox.pump(t):
                write_jsonl(sent_log, record)
            write_jsonl(time_log, {"frame_id": frame_id, "t": t, "n_dets": len(dets), **timings})
            n_frames += 1

            if args.save_video:
                if video is None:
                    path = str(args.output / "annotated.mp4")
                    video = cv2.VideoWriter(path, cv2.VideoWriter.fourcc(*"mp4v"), args.fps, (cam.width, cam.height))
                video.write(annotate(frame, [d.box_px for d in dets], [d.conf for d in dets], confirmed, tel, cam, synthetic))
        # Hết video: tiếp tục gửi bù mỗi giây, như UAV vẫn bay tiếp và giữ kết nối.
        for k in range(1, int(args.drain_s) + 1):
            if outbox.pending() == 0:
                break
            for record in outbox.pump(t + k):
                write_jsonl(sent_log, record)
    if video is not None:
        video.release()
    pending = outbox.pending()
    outbox.close()
    print(f"Đã xử lý {n_frames} khung, xác nhận {len(confirmed)} người, còn {pending} thông điệp chưa gửi được. Log tại: {args.output}")


if __name__ == "__main__":
    main()
