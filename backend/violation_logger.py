import json
import datetime
import os


class ViolationLogger:

    def __init__(self, file_path="violations_log.json"):

        self.file_path = file_path

        # Create file if it doesn't exist
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                json.dump([], f)

    def log(self, vehicle_id, plate, speed, violation_type="speeding", speed_limit=60, vehicle_type=None):

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        entry = {
            "vehicle_id": vehicle_id,
            "plate": plate,
            "speed": speed,
            "speed_limit": speed_limit,
            "violation_type": violation_type,
            "vehicle_type": vehicle_type,
            "timestamp": timestamp
        }

        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)
        except Exception:
            data = []

        data.append(entry)

        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=4)
