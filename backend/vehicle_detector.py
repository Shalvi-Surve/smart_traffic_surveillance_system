from ultralytics import YOLO
import cv2

class VehicleDetector:

    def __init__(self, model_path="models/yolov8n.pt", img_size=640):

        # Load YOLO model
        self.model = YOLO(model_path)

        # classes we care about
        self.vehicle_classes = ["car", "truck", "bus", "motorcycle"]

        # inference image size (smaller = faster)
        self.img_size = img_size


    def detect(self, frame):

        # Resize frame for faster inference
        resized = cv2.resize(frame, (self.img_size, self.img_size))

        results = self.model(resized, conf=0.3, iou=0.45, verbose=False)[0]

        vehicles = []

        names = results.names

        h_original, w_original = frame.shape[:2]

        x_scale = w_original / self.img_size
        y_scale = h_original / self.img_size

        if results.boxes is None:
            return vehicles

        for box in results.boxes:

            cls_id = int(box.cls[0])
            cls_name = names[cls_id]

            if cls_name not in self.vehicle_classes:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # scale back to original image
            x1 = int(x1 * x_scale)
            y1 = int(y1 * y_scale)
            x2 = int(x2 * x_scale)
            y2 = int(y2 * y_scale)

            vehicles.append({
                "bbox": [x1, y1, x2, y2],
                "type": cls_name
            })

        return vehicles

'''
from ultralytics import YOLO
import cv2

class VehicleDetector:

    def __init__(self, model_path="models/yolov8n.pt"):

        # Load fast YOLO model
        self.model = YOLO(model_path)

        # Only detect vehicle classes
        self.vehicle_classes = ["car", "truck", "bus", "motorcycle"]

    def detect(self, frame):

        # Save original dimensions
        h, w = frame.shape[:2]

        # Resize frame for faster inference
        resized = cv2.resize(frame, (640, 360))

        # Run YOLO
        results = self.model(
            resized,
            imgsz=640,
            conf=0.30,
            iou=0.45,
            device="cpu",
            verbose=False
        )[0]

        vehicles = []

        names = results.names

        if results.boxes is None:
            return vehicles

        for box in results.boxes:

            cls_id = int(box.cls[0])
            cls_name = names[cls_id]

            if cls_name not in self.vehicle_classes:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # Scale boxes back to original image
            x1 = int(x1 * w / 640)
            x2 = int(x2 * w / 640)
            y1 = int(y1 * h / 360)
            y2 = int(y2 * h / 360)

            vehicles.append({
                "bbox": [x1, y1, x2, y2],
                "type": cls_name
            })

        return vehicles
'''