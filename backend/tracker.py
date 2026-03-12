import math


class Tracker:

    def __init__(self):

        # Current tracked object centers
        self.center_points = {}

        # Frames since last seen
        self.disappeared = {}

        # Unique ID counter
        self.id_count = 0

        # Remove object if not seen for this many updates
        self.max_disappeared = 8


    def update(self, objects_rect):

        objects_bbs_ids = []
        new_center_points = {}

        # Process detections
        for rect in objects_rect:

            x1, y1, x2, y2 = rect

            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2

            matched_id = None

            for obj_id, pt in self.center_points.items():

                dist = math.hypot(cx - pt[0], cy - pt[1])

                if dist < 60:
                    matched_id = obj_id
                    break

            # Existing object
            if matched_id is not None:

                new_center_points[matched_id] = (cx, cy)

                objects_bbs_ids.append([x1, y1, x2, y2, matched_id])

                self.disappeared[matched_id] = 0

            # New object
            else:

                new_center_points[self.id_count] = (cx, cy)

                objects_bbs_ids.append([x1, y1, x2, y2, self.id_count])

                self.disappeared[self.id_count] = 0

                self.id_count += 1

        # Handle disappeared objects
        for obj_id in list(self.center_points.keys()):

            if obj_id not in new_center_points:

                self.disappeared[obj_id] += 1

                if self.disappeared[obj_id] <= self.max_disappeared:

                    new_center_points[obj_id] = self.center_points[obj_id]

                else:

                    del self.disappeared[obj_id]

        self.center_points = new_center_points

        return objects_bbs_ids