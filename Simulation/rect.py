from typing import Tuple
import math


class Rect:
    location: Tuple[int, int]
    topLeft: Tuple[int, int]
    topRight: Tuple[int, int]
    bottomLeft: Tuple[int, int]
    bottomRight: Tuple[int, int]

    def __init__(self, center: Tuple[int, int], width: int, height: int, angle: int):
        self.center = center
        self.width = width
        self.height = height
        self.angle = angle+90
        self.calculate_corners()

    def calculate_corners(self):
        cx, cy = self.center
        angle_rad = math.radians(self.angle)

        # Calculate the other corners without rotation
        topLeft = (cx - self.width / 2, cy - self.height / 2)
        topRight = (cx + self.width / 2, cy - self.height / 2)
        bottomLeft = (cx - self.width / 2, cy + self.height / 2)
        bottomRight = (cx + self.width / 2, cy + self.height / 2)

        # Apply rotation to each corner
        self.topLeft = self.rotate_point(topLeft, cx, cy, angle_rad)
        self.topRight = self.rotate_point(topRight, cx, cy, angle_rad)
        self.bottomLeft = self.rotate_point(bottomLeft, cx, cy, angle_rad)
        self.bottomRight = self.rotate_point(bottomRight, cx, cy, angle_rad)

    def rotate_point(self, point: Tuple[int, int], cx: int, cy: int, angle_rad: float) -> Tuple[int, int]:
        x, y = point
        x_new = cx + (x - cx) * math.cos(angle_rad) - \
            (y - cy) * math.sin(angle_rad)
        y_new = cy + (x - cx) * math.sin(angle_rad) + \
            (y - cy) * math.cos(angle_rad)
        return (round(x_new), round(y_new))
    
    def get_points(self):
        return (self.topLeft, self.topRight, self.bottomRight, self.bottomLeft)
