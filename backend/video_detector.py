import cv2
import os

from vehicle_detector import VehicleDetector
from plate_detector import PlateDetector
from ocr_reader import OCRReader
from tracker import Tracker
from speed_estimator import SpeedEstimator
from violation_detector import ViolationDetector
from violation_logger import ViolationLogger


# Load models
vehicle_detector = VehicleDetector("models/yolov8n.pt")
plate_detector = PlateDetector("models/plate_detector.pt")
ocr_reader = OCRReader()

tracker = Tracker()
speed_estimator = SpeedEstimator()
violation_detector = ViolationDetector()
logger = ViolationLogger()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

video_folder = os.path.join(BASE_DIR, "..", "data", "videos_trimmed")
output_folder = os.path.join(BASE_DIR, "..", "data", "output_videos")

os.makedirs(output_folder, exist_ok=True)


for video_name in os.listdir(video_folder):

    if not video_name.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        continue

    video_path = os.path.join(video_folder, video_name)

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("Could not open:", video_name)
        continue

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    output_path = os.path.join(
        output_folder,
        os.path.splitext(video_name)[0] + "_processed.avi"
    )

    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    print("\nProcessing:", video_name)

    frame_count = 0

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        frame_count += 1

        # skip frames for speed
        if frame_count % 10 != 0:
            out.write(frame)
            continue

        vehicles = vehicle_detector.detect(frame)

        detections = []

        for v in vehicles:

            x1, y1, x2, y2 = v["bbox"]
            detections.append([x1, y1, x2, y2])

        boxes_ids = tracker.update(detections)

        for box in boxes_ids:

            x1, y1, x2, y2, obj_id = box

            speed = speed_estimator.calculate_speed(obj_id, [x1, y1, x2, y2])

            violation = violation_detector.check_violation(speed)

            if violation:

                color = (0, 0, 255)

                vehicle_crop = frame[y1:y2, x1:x2]

                plates = plate_detector.detect(vehicle_crop)

                plate_text = ""

                for p in plates:

                    px1, py1, px2, py2 = p["bbox"]

                    plate_crop = vehicle_crop[py1:py2, px1:px2]

                    text = ocr_reader.read_plate(plate_crop)

                    if text:
                        plate_text = text
                        break

                logger.log(obj_id, plate_text, speed)

            else:

                color = (0, 255, 0)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        out.write(frame)

        if frame_count % 100 == 0:
            print("Processed frame:", frame_count)

    cap.release()
    out.release()

    print("Saved:", output_path)

print("\nAll videos processed successfully!")

'''
import cv2
import os

from vehicle_detector import VehicleDetector
from tracker import Tracker
from speed_estimator import SpeedEstimator
from violation_detector import ViolationDetector


# Load fast YOLO model
vehicle_detector = VehicleDetector("models/yolov8n.pt")

tracker = Tracker()
speed_estimator = SpeedEstimator()
violation_detector = ViolationDetector()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

video_folder = os.path.join(BASE_DIR, "..", "data", "videos_trimmed")
output_folder = os.path.join(BASE_DIR, "..", "data", "output_videos")

os.makedirs(output_folder, exist_ok=True)


# CONFIGURATION (speed tuning)
FRAME_SKIP = 10
INFERENCE_WIDTH = 640


for video_name in os.listdir(video_folder):

    if not video_name.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        continue

    video_path = os.path.join(video_folder, video_name)

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("Could not open:", video_name)
        continue

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    output_path = os.path.join(
        output_folder,
        os.path.splitext(video_name)[0] + "_processed.avi"
    )

    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    print("\nProcessing:", video_name)

    frame_count = 0

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        frame_count += 1

        # Skip frames for faster processing
        if frame_count % FRAME_SKIP != 0:
            out.write(frame)
            continue

        # Resize frame for faster YOLO inference
        h, w = frame.shape[:2]

        scale = INFERENCE_WIDTH / w
        resized_frame = cv2.resize(frame, (INFERENCE_WIDTH, int(h * scale)))

        vehicles = vehicle_detector.detect(resized_frame)

        detections = []

        for v in vehicles:

            x1, y1, x2, y2 = v["bbox"]

            # Scale bbox back to original frame size
            x1 = int(x1 / scale)
            y1 = int(y1 / scale)
            x2 = int(x2 / scale)
            y2 = int(y2 / scale)

            detections.append([x1, y1, x2, y2])

        boxes_ids = tracker.update(detections)

        for box in boxes_ids:

            x1, y1, x2, y2, obj_id = box

            speed = speed_estimator.calculate_speed(obj_id, [x1, y1, x2, y2])

            violation = violation_detector.check_violation(speed)

            if violation["violation"]:
                color = (0, 0, 255)
            else:
                color = (0, 255, 0)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        out.write(frame)

        if frame_count % 100 == 0:
            print("Processed frame:", frame_count)

    cap.release()
    out.release()

    print("Saved:", output_path)


print("\nAll videos processed successfully!")
'''