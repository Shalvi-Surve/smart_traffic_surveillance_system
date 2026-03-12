from vehicle_detector import VehicleDetector
from plate_detector import PlateDetector
import cv2
import os

# Load models
vehicle_detector = VehicleDetector("models/yolov8m.pt")
plate_detector = PlateDetector("models/plate_detector.pt")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

image_folder = os.path.join(BASE_DIR, "..", "data", "images")
output_folder = os.path.join(BASE_DIR, "..", "data", "output")

os.makedirs(output_folder, exist_ok=True)

for img_name in os.listdir(image_folder):

    path = os.path.join(image_folder, img_name)

    img = cv2.imread(path)

    if img is None:
        print("Could not read:", img_name)
        continue

    # Slight upscale to help small detections
    img = cv2.resize(img, None, fx=1.2, fy=1.2)

    vehicles = vehicle_detector.detect(img)
    plates = plate_detector.detect(img)

    print("Vehicles:", vehicles)
    print("Plates:", plates)

    h, w = img.shape[:2]
    thickness = max(2, int(min(w, h) / 400))

    # Draw vehicle boxes
    for v in vehicles:

        x1, y1, x2, y2 = v["bbox"]
        label = v["type"]

        cv2.rectangle(img, (x1,y1), (x2,y2), (0,255,0), thickness)

        cv2.putText(
            img,
            label,
            (x1, y1-10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0,255,0),
            thickness
        )

    # Draw plate boxes
    for p in plates:

        x1, y1, x2, y2 = p["bbox"]

        cv2.rectangle(img, (x1,y1), (x2,y2), (0,255,255), thickness)

        cv2.putText(
            img,
            "Plate",
            (x1, y1-10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0,255,255),
            thickness
        )

    name_without_ext = os.path.splitext(img_name)[0]

    output_path = os.path.join(output_folder, name_without_ext + "_result.jpg")

    success = cv2.imwrite(output_path, img)

    print("Saved:", output_path)
    print("Write success:", success)