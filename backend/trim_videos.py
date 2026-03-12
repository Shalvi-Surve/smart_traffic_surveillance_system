import cv2
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

video_folder = os.path.join(BASE_DIR, "..", "data", "videos")
output_folder = os.path.join(BASE_DIR, "..", "data", "videos_trimmed")

os.makedirs(output_folder, exist_ok=True)

MAX_SECONDS = 90   # trim to 1.5 minutes

for video_name in os.listdir(video_folder):

    video_path = os.path.join(video_folder, video_name)

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("Could not open:", video_name)
        continue

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    max_frames = fps * MAX_SECONDS

    output_path = os.path.join(
        output_folder,
        os.path.splitext(video_name)[0] + "_trimmed.avi"
    )

    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_count = 0

    print("Trimming:", video_name)

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        if frame_count >= max_frames:
            break

        out.write(frame)

        frame_count += 1

    cap.release()
    out.release()

    print("Saved:", output_path)

print("\nAll videos trimmed successfully!")