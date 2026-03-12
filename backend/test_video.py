import cv2
import os
from vehicle_detector import VehicleDetector

detector = VehicleDetector("models/yolov8m.pt")

video_path = "../data/videos/ua_detrac/MVI_20011.mp4"

cap = cv2.VideoCapture(video_path)

while True:

    ret, frame = cap.read()

    if not ret:
        break

    vehicles = detector.detect(frame)

    for v in vehicles:
        x1,y1,x2,y2 = v["bbox"]
        label = v["type"]

        cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)
        cv2.putText(frame,label,(x1,y1-5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,(0,255,0),2)

    cv2.imshow("Traffic Detection",frame)

    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()