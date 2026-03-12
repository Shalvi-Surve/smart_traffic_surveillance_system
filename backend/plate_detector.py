from ultralytics import YOLO
import cv2

class PlateDetector:

    def __init__(self, model_path="models/plate_detector.pt", conf=0.4):

        # Load YOLO plate detection model
        self.model = YOLO(model_path)

        self.conf = conf


    def detect(self, frame):

        h, w = frame.shape[:2]

        # Resize for faster inference
        resized = cv2.resize(frame, (320, 320))

        results = self.model(
            resized,
            imgsz=320,
            conf=self.conf,
            device="cpu",
            verbose=False
        )[0]

        plates = []

        if results.boxes is None:
            return plates

        for box in results.boxes:

            confidence = float(box.conf[0])

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # Scale bounding boxes back to original size
            x1 = int(x1 * w / 320)
            x2 = int(x2 * w / 320)
            y1 = int(y1 * h / 320)
            y2 = int(y2 * h / 320)

            plates.append({
                "bbox": [x1, y1, x2, y2],
                "confidence": confidence
            })

        return plates