import cv2
import base64
import numpy as np

from flask import Flask, request, jsonify
from flask_cors import CORS

from vehicle_detector import VehicleDetector
from plate_detector import PlateDetector
from ocr_reader import OCRReader
from tracker import Tracker
from speed_estimator import SpeedEstimator
from violation_detector import ViolationDetector


app = Flask(__name__)
CORS(app)


# Load models once at startup
vehicle_detector = VehicleDetector("models/yolov8n.pt")
plate_detector = PlateDetector("models/plate_detector.pt")
ocr_reader = OCRReader()

tracker = Tracker()
speed_estimator = SpeedEstimator()
violation_detector = ViolationDetector()


@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "message": "Smart Traffic Surveillance Backend Running"
    })


def process_frame(frame):

    vehicles = vehicle_detector.detect(frame)

    boxes = [v["bbox"] for v in vehicles]

    tracked_objects = tracker.update(boxes)

    results = []

    for obj in tracked_objects:

        x1, y1, x2, y2, obj_id = obj

        vehicle_crop = frame[y1:y2, x1:x2]

        plate_boxes = plate_detector.detect(vehicle_crop)

        plate_text = ""

        for p in plate_boxes:

            px1, py1, px2, py2 = p["bbox"]

            plate_img = vehicle_crop[py1:py2, px1:px2]

            detected_text = ocr_reader.read_plate(plate_img)

            if detected_text:
                plate_text = detected_text
                break

        speed = speed_estimator.calculate_speed(obj_id, [x1, y1, x2, y2])

        violation_info = violation_detector.check_violation(speed)

        results.append({
            "vehicle_id": obj_id,
            "plate": plate_text,
            "speed": speed,
            "violation": violation_info
        })

        # Draw boxes only for demo visualization
        color = (0,255,0)

        if violation_info["violation"]:
            color = (0,0,255)

        cv2.rectangle(frame,(x1,y1),(x2,y2),color,2)

    return frame, results


@app.route("/analyze", methods=["POST"])
def analyze():

    if "file" not in request.files:

        return jsonify({
            "error": "No file uploaded"
        }),400

    file = request.files["file"]

    file_bytes = np.frombuffer(file.read(), np.uint8)

    frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if frame is None:

        return jsonify({
            "error": "Invalid image"
        }),400

    processed_frame, results = process_frame(frame)

    _, buffer = cv2.imencode(".jpg", processed_frame)

    encoded_image = base64.b64encode(buffer).decode("utf-8")

    return jsonify({
        "processed_image": encoded_image,
        "vehicles": results
    })


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5000, debug=True)