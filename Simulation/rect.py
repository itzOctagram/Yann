from typing import Tuple,List
import math


class Rect:
    center: Tuple[float, float]
    topLeft: Tuple[float, float]
    topRight: Tuple[float, float]
    bottomLeft: Tuple[float, float]
    bottomRight: Tuple[float, float]

    def __init__(self, center: Tuple[float, float], width: int, height: int, angle: float):
        self.center = center
        self.width = width
        self.height = height
        self.angle = -angle+90
        self._calculate_corners()

    def _calculate_corners(self):
        cx, cy = self.center
        angle_rad = math.radians(self.angle)

        # Calculate the other corners without rotation
        topLeft = (cx - self.width / 2, cy - self.height / 2)
        topRight = (cx + self.width / 2, cy - self.height / 2)
        bottomLeft = (cx - self.width / 2, cy + self.height / 2)
        bottomRight = (cx + self.width / 2, cy + self.height / 2)

        # Apply rotation to each corner
        self.topLeft = self._rotate_point(topLeft, cx, cy, angle_rad)
        self.topRight = self._rotate_point(topRight, cx, cy, angle_rad)
        self.bottomLeft = self._rotate_point(bottomLeft, cx, cy, angle_rad)
        self.bottomRight = self._rotate_point(bottomRight, cx, cy, angle_rad)

    def _rotate_point(self, point: Tuple[int, int], cx: int, cy: int, angle_rad: float) -> Tuple[float, float]:
        x, y = point
        x_new = cx + (x - cx) * math.cos(angle_rad) - \
            (y - cy) * math.sin(angle_rad)
        y_new = cy + (x - cx) * math.sin(angle_rad) + \
            (y - cy) * math.cos(angle_rad)
        return (x_new, y_new)

    def get_points(self):
        return (self.topLeft, self.topRight, self.bottomRight, self.bottomLeft)
    
    def isCollision(self, other: 'Rect') -> bool:
        """Uses the Separating Axis Theorem to determine if two rectangles collide."""

        def get_edges(points):
            """Returns the edges as vectors of the rectangle."""
            return [(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]) for i in range(4)]

        def project_polygon(axis, points):
            """Projects a polygon's points onto the given axis and returns the min and max scalar values."""
            projections = [(p[0] * axis[0] + p[1] * axis[1]) for p in points]
            return min(projections), max(projections)

        def is_separating_axis(axis, points1, points2):
            """Checks if an axis is a separating axis between two polygons."""
            min1, max1 = project_polygon(axis, points1)
            min2, max2 = project_polygon(axis, points2)
            return max1 < min2 or max2 < min1

        # Get the points of both rectangles
        points1 = [self.topLeft, self.topRight, self.bottomRight, self.bottomLeft]
        points2 = [other.topLeft, other.topRight, other.bottomRight, other.bottomLeft]

        # Get the edge normals (axes to test) from both rectangles
        edges1 = get_edges(points1)
        edges2 = get_edges(points2)

        # Calculate axes (normals to the edges)
        axes = [(e[1], -e[0]) for e in edges1 + edges2]  # Perpendicular vectors to the edges

        # Check for separation on any axis
        for axis in axes:
            if is_separating_axis(axis, points1, points2):
                return False  # If there's a separating axis, the rectangles do not collide

        return True  # No separating axis found, so the rectangles must be colliding