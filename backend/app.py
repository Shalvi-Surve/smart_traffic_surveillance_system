import os
import cv2
import base64
import numpy as np
import json
import tempfile
import datetime
import zipfile

import pandas as pd
import matplotlib.pyplot as plt

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

from vehicle_detector import VehicleDetector
from plate_detector import PlateDetector
from ocr_reader import OCRReader
from tracker import Tracker
from speed_estimator import SpeedEstimator
from violation_detector import ViolationDetector
from violation_logger import ViolationLogger


app = Flask(__name__)
CORS(app)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed_videos")
REPORT_DIR = os.path.join(DATA_DIR, "reports")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)


# Load models once at startup
vehicle_detector = VehicleDetector("models/yolov8n.pt")
plate_detector = PlateDetector("models/plate_detector.pt")
ocr_reader = OCRReader()

tracker = Tracker()
speed_estimator = SpeedEstimator()
violation_detector = ViolationDetector()
violation_logger = ViolationLogger(os.path.join(BASE_DIR, "violations_log.json"))

# stable violation state per tracked vehicle id
vehicle_violation_state = {}

# remember last processed video path for reports
last_processed_video_path = None


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Smart Traffic Surveillance Backend Running"})


def process_frame(frame, for_video=False):
    """
    Run full pipeline on a single frame.

    for_video=True enables optimizations (OCR only for violating vehicles).
    """
    global vehicle_violation_state

    vehicles = vehicle_detector.detect(frame)
    boxes = [v["bbox"] for v in vehicles]

    tracked_objects = tracker.update(boxes)
    results = []

    for idx, obj in enumerate(tracked_objects):
        x1, y1, x2, y2, obj_id = obj

        vehicle_type = vehicles[idx]["type"] if idx < len(vehicles) else "car"

        # speed first so violation decision can gate OCR in video mode
        speed = speed_estimator.calculate_speed(obj_id, [x1, y1, x2, y2])
        violation_info = violation_detector.check_violation(speed)

        plate_text = ""
        run_ocr = (not for_video) or violation_info.get("violation", False)

        if run_ocr:
            vehicle_crop = frame[y1:y2, x1:x2]
            plate_boxes = plate_detector.detect(vehicle_crop)

            for p in plate_boxes:
                px1, py1, px2, py2 = p["bbox"]
                plate_img = vehicle_crop[py1:py2, px1:px2]
                detected_text = ocr_reader.read_plate(plate_img)
                if detected_text:
                    plate_text = detected_text
                    break

        if violation_info.get("violation", False):
            vehicle_violation_state[obj_id] = True
            violation_logger.log(
                vehicle_id=int(obj_id),
                plate=plate_text,
                speed=int(speed),
                violation_type=violation_info.get("type", "speeding"),
                speed_limit=violation_info.get("limit", violation_detector.default_speed_limit),
                vehicle_type=vehicle_type,
            )
        else:
            vehicle_violation_state.setdefault(obj_id, False)

        # stable color based on stored state, no red/green flicker
        color = (0, 255, 0)
        if vehicle_violation_state.get(obj_id, False):
            color = (0, 0, 255)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        results.append(
            {
                "vehicle_id": int(obj_id),
                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                "plate": plate_text,
                "vehicle_type": vehicle_type,
                "speed": int(speed),
                "violation": violation_info.get("violation", False),
                "violation_type": violation_info.get("type") if violation_info.get("violation", False) else None,
                "speed_limit": violation_info.get("limit", violation_detector.default_speed_limit),
            }
        )

    return frame, results


@app.route("/analyze_image", methods=["POST"])
def analyze_image():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    file_bytes = np.frombuffer(file.read(), np.uint8)
    frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if frame is None:
        return jsonify({"error": "Invalid image"}), 400

    processed_frame, results = process_frame(frame, for_video=False)

    _, buffer = cv2.imencode(".jpg", processed_frame)
    encoded_image = base64.b64encode(buffer).decode("utf-8")

    vehicles_detected = len(results)
    plates_detected = vehicles_detected  # for demo, one attempt per vehicle
    violations_detected = sum(1 for r in results if r["violation"])

    return jsonify(
        {
            "processed_image": encoded_image,
            "vehicles_detected": vehicles_detected,
            "plates_detected": plates_detected,
            "violations_detected": violations_detected,
            "vehicles": results,
        }
    )


@app.route("/analyze", methods=["POST"])
def analyze_legacy():
    """Backward compatible endpoint – delegates to analyze_image."""
    return analyze_image()


@app.route("/analyze_video", methods=["POST"])
def analyze_video():
    """
    Analyze an uploaded video, process frames efficiently,
    and return aggregated vehicle stats + processed video path.
    """
    global last_processed_video_path

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = file.filename or f"video_{ts}.mp4"
    upload_path = os.path.join(UPLOAD_DIR, f"{ts}_{safe_name}")
    file.save(upload_path)

    cap = cv2.VideoCapture(upload_path)
    if not cap.isOpened():
        return jsonify({"error": "Unable to open video"}), 400

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    speed_estimator.fps = fps

    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    processed_name = f"processed_{ts}.avi"
    processed_path = os.path.join(PROCESSED_DIR, processed_name)
    out = cv2.VideoWriter(processed_path, fourcc, fps, (width, height))

    FRAME_SKIP = 5
    frame_idx = 0

    vehicles_agg = {}

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % FRAME_SKIP == 0:
            processed_frame, frame_results = process_frame(frame, for_video=True)

            for v in frame_results:
                vid = v["vehicle_id"]
                if vid not in vehicles_agg:
                    vehicles_agg[vid] = {
                        "vehicle_id": vid,
                        "plate": v.get("plate") or "",
                        "vehicle_type": v.get("vehicle_type", "car"),
                        "speed": [],
                        "speed_limit": v.get("speed_limit", violation_detector.default_speed_limit),
                        "violation": v.get("violation", False),
                        "violation_type": v.get("violation_type"),
                    }

                vehicles_agg[vid]["speed"].append(v["speed"])
                if v.get("violation", False):
                    vehicles_agg[vid]["violation"] = True
                    vehicles_agg[vid]["violation_type"] = v.get("violation_type")

            out.write(processed_frame)
        else:
            # write unprocessed frame to keep video length and improve speed
            out.write(frame)

        frame_idx += 1

    cap.release()
    out.release()

    last_processed_video_path = processed_path

    vehicles_summary = []
    for v in vehicles_agg.values():
        speeds = v["speed"] or [0]
        avg_speed = int(sum(speeds) / len(speeds))
        vehicles_summary.append(
            {
                "vehicle_id": v["vehicle_id"],
                "plate": v["plate"],
                "vehicle_type": v["vehicle_type"],
                "avg_speed": avg_speed,
                "speed_limit": v["speed_limit"],
                "violation": v["violation"],
                "violation_type": v["violation_type"],
            }
        )

    vehicles_detected = len(vehicles_summary)
    plates_detected = vehicles_detected
    violations_detected = sum(1 for v in vehicles_summary if v["violation"])

    return jsonify(
        {
            "processed_video_path": processed_name,
            "vehicles_detected": vehicles_detected,
            "plates_detected": plates_detected,
            "violations_detected": violations_detected,
            "vehicles": vehicles_summary,
        }
    )


@app.route("/videos/<path:filename>")
def get_processed_video(filename):
    return send_from_directory(PROCESSED_DIR, filename, as_attachment=False)


@app.route("/dashboard_stats", methods=["GET"])
def dashboard_stats():
    """
    Aggregate statistics from violations_log.json for dashboard.
    """
    log_path = os.path.join(BASE_DIR, "violations_log.json")

    if not os.path.exists(log_path):
        return jsonify(
            {
                "total_vehicles": 0,
                "total_violations": 0,
                "average_speed": 0,
                "most_common_vehicle_type": None,
                "top_violating_plates": [],
                "speed_distribution": [],
                "violations_timeline": [],
                "vehicle_type_distribution": [],
            }
        )

    try:
        with open(log_path, "r") as f:
            data = json.load(f)
    except Exception:
        data = []

    if not data:
        return jsonify(
            {
                "total_vehicles": 0,
                "total_violations": 0,
                "average_speed": 0,
                "most_common_vehicle_type": None,
                "top_violating_plates": [],
                "speed_distribution": [],
                "violations_timeline": [],
                "vehicle_type_distribution": [],
            }
        )

    df = pd.DataFrame(data)

    total_violations = len(df)
    total_vehicles = df["vehicle_id"].nunique()
    average_speed = float(df["speed"].mean()) if "speed" in df else 0.0

    most_common_vehicle_type = None
    if "vehicle_type" in df:
        most_common_vehicle_type = df["vehicle_type"].mode().iloc[0]

    top_plates = []
    if "plate" in df:
        plate_counts = df["plate"].value_counts().head(5)
        top_plates = [{"plate": p, "count": int(c)} for p, c in plate_counts.items()]

    speed_distribution = []
    if "speed" in df:
        bins = [0, 20, 40, 60, 80, 100, 120, 200]
        labels = ["0-20", "20-40", "40-60", "60-80", "80-100", "100-120", "120+"]
        df["speed_bin"] = pd.cut(df["speed"], bins=bins, labels=labels, right=False)
        dist = df["speed_bin"].value_counts().sort_index()
        speed_distribution = [{"range": str(idx), "count": int(val)} for idx, val in dist.items()]

    violations_timeline = []
    if "timestamp" in df:
        df["timestamp_dt"] = pd.to_datetime(df["timestamp"])
        timeline = df.groupby(df["timestamp_dt"].dt.hour).size()
        violations_timeline = [{"hour": int(h), "count": int(c)} for h, c in timeline.items()]

    vehicle_type_distribution = []
    if "vehicle_type" in df:
        vt_counts = df["vehicle_type"].value_counts()
        vehicle_type_distribution = [{"type": t, "count": int(c)} for t, c in vt_counts.items()]

    return jsonify(
        {
            "total_vehicles": int(total_vehicles),
            "total_violations": int(total_violations),
            "average_speed": round(average_speed, 2),
            "most_common_vehicle_type": most_common_vehicle_type,
            "top_violating_plates": top_plates,
            "speed_distribution": speed_distribution,
            "violations_timeline": violations_timeline,
            "vehicle_type_distribution": vehicle_type_distribution,
        }
    )


def _build_report_structure(base_dir, df, video_path=None):
    """
    Build on-disk report/ folder with summary, visuals, per-vehicle JSON, and video.
    """
    report_root = os.path.join(base_dir, "report")
    visuals_dir = os.path.join(report_root, "visualizations")
    vehicle_reports_dir = os.path.join(report_root, "vehicle_reports")

    os.makedirs(visuals_dir, exist_ok=True)
    os.makedirs(vehicle_reports_dir, exist_ok=True)

    # summary.json
    summary_json_path = os.path.join(report_root, "summary.json")
    with open(summary_json_path, "w") as f:
        json.dump(df.to_dict(orient="records"), f, indent=4)

    # summary.xlsx
    excel_path = os.path.join(report_root, "summary.xlsx")
    excel_cols = [
        "vehicle_id",
        "plate",
        "vehicle_type",
        "speed",
        "speed_limit",
        "violation_type",
        "timestamp",
    ]
    for col in excel_cols:
        if col not in df:
            df[col] = None
    df[excel_cols].to_excel(excel_path, index=False)

    # speed distribution visualization
    if "speed" in df:
        plt.figure(figsize=(6, 4))
        df["speed"].hist(bins=10)
        plt.title("Speed Distribution")
        plt.xlabel("Speed (km/h)")
        plt.ylabel("Count")
        speed_dist_path = os.path.join(visuals_dir, "speed_distribution.png")
        plt.tight_layout()
        plt.savefig(speed_dist_path)
        plt.close()

    # violations chart by type
    if "violation_type" in df:
        plt.figure(figsize=(6, 4))
        df["violation_type"].value_counts().plot(kind="bar")
        plt.title("Violations by Type")
        plt.xlabel("Violation Type")
        plt.ylabel("Count")
        violations_chart_path = os.path.join(visuals_dir, "violations_chart.png")
        plt.tight_layout()
        plt.savefig(violations_chart_path)
        plt.close()

    # copy processed video
    if video_path and os.path.exists(video_path):
        dest = os.path.join(report_root, "processed_video.avi")
        with open(video_path, "rb") as src, open(dest, "wb") as dst:
            dst.write(src.read())

    # per-vehicle JSON
    for vid, group in df.groupby("vehicle_id"):
        vehicle_report_path = os.path.join(vehicle_reports_dir, f"vehicle_{vid}.json")
        with open(vehicle_report_path, "w") as f:
            json.dump(group.to_dict(orient="records"), f, indent=4)

    return report_root


@app.route("/export_report", methods=["GET"])
def export_report():
    """
    Export full system report ZIP based on violations log and last processed video.
    """
    log_path = os.path.join(BASE_DIR, "violations_log.json")
    if not os.path.exists(log_path):
        return jsonify({"error": "No violations_log.json found"}), 400

    try:
        with open(log_path, "r") as f:
            data = json.load(f)
    except Exception:
        data = []

    if not data:
        return jsonify({"error": "No data in violations_log.json"}), 400

    df = pd.DataFrame(data)

    with tempfile.TemporaryDirectory(dir=REPORT_DIR) as tmpdir:
        report_root = _build_report_structure(tmpdir, df, video_path=last_processed_video_path)
        zip_path = os.path.join(tmpdir, "traffic_report.zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for folder_name, subfolders, filenames in os.walk(report_root):
                for filename in filenames:
                    file_path = os.path.join(folder_name, filename)
                    arcname = os.path.relpath(file_path, report_root)
                    zipf.write(file_path, os.path.join("report", arcname))

        return send_file(zip_path, as_attachment=True, download_name="traffic_report.zip")


@app.route("/vehicle_report/<vehicle_id>", methods=["GET"])
def vehicle_report(vehicle_id):
    """
    Export individual vehicle report ZIP.
    """
    log_path = os.path.join(BASE_DIR, "violations_log.json")
    if not os.path.exists(log_path):
        return jsonify({"error": "No violations_log.json found"}), 400

    try:
        with open(log_path, "r") as f:
            data = json.load(f)
    except Exception:
        data = []

    if not data:
        return jsonify({"error": "No data in violations_log.json"}), 400

    df = pd.DataFrame(data)
    try:
        vid_int = int(vehicle_id)
        vehicle_df = df[df["vehicle_id"] == vid_int]
    except ValueError:
        vehicle_df = df[df["vehicle_id"].astype(str) == str(vehicle_id)]

    if vehicle_df.empty:
        return jsonify({"error": "No records found for this vehicle"}), 404

    with tempfile.TemporaryDirectory(dir=REPORT_DIR) as tmpdir:
        report_root = _build_report_structure(tmpdir, vehicle_df, video_path=last_processed_video_path)
        zip_path = os.path.join(tmpdir, f"vehicle_{vehicle_id}_report.zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for folder_name, subfolders, filenames in os.walk(report_root):
                for filename in filenames:
                    file_path = os.path.join(folder_name, filename)
                    arcname = os.path.relpath(file_path, report_root)
                    zipf.write(file_path, os.path.join("report", arcname))

        return send_file(zip_path, as_attachment=True, download_name=f"vehicle_{vehicle_id}_report.zip")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)