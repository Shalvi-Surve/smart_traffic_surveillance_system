import math


class SpeedEstimator:

    def __init__(self, fps=30, pixel_to_kmh=0.3):

        # Store last position of each vehicle
        self.last_position = {}

        # Store last speed for smoothing
        self.prev_speed = {}

        # Video FPS
        self.fps = fps

        # Conversion factor (pixels → km/h)
        self.pixel_to_kmh = pixel_to_kmh


    def calculate_speed(self, object_id, bbox):

        x1, y1, x2, y2 = bbox

        # Calculate center
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        current_center = (cx, cy)

        # First time seeing this vehicle
        if object_id not in self.last_position:

            self.last_position[object_id] = current_center
            self.prev_speed[object_id] = 0

            return 0

        prev_center = self.last_position[object_id]

        dx = current_center[0] - prev_center[0]
        dy = current_center[1] - prev_center[1]

        distance_pixels = math.hypot(dx, dy)

        # Convert pixels/frame → km/h
        speed_kmh = distance_pixels * self.fps * self.pixel_to_kmh

        # Smooth speed
        speed_kmh = (speed_kmh + self.prev_speed[object_id]) / 2

        # Update storage
        self.last_position[object_id] = current_center
        self.prev_speed[object_id] = speed_kmh

        return int(speed_kmh)