class ViolationDetector:

    def __init__(self, default_speed_limit=60, tolerance=5):

        # Default road speed limit
        self.default_speed_limit = default_speed_limit

        # Speed tolerance to avoid false detection
        self.tolerance = tolerance

        # Optional road-specific speed limits
        self.road_limits = {}


    def set_speed_limit(self, road_name, limit):
        """
        Set speed limit for a specific road
        """
        self.road_limits[road_name] = limit


    def get_speed_limit(self, road_name=None):
        """
        Get speed limit for a given road
        """

        if road_name and road_name in self.road_limits:
            return self.road_limits[road_name]

        return self.default_speed_limit


    def check_violation(self, speed, road_name=None):
        """
        Check if speed violation occurred
        """

        limit = self.get_speed_limit(road_name)

        if speed > (limit + self.tolerance):

            return {
                "violation": True,
                "type": "speeding",
                "speed": speed,
                "limit": limit
            }

        return {
            "violation": False
        }