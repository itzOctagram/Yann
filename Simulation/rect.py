from typing import Tuple, List, Literal
import math


class Rect:
    center: Tuple[float, float]
    topLeft: Tuple[float, float]
    topRight: Tuple[float, float]
    bottomLeft: Tuple[float, float]
    bottomRight: Tuple[float, float]

    def __init__(self, center: Tuple[float, float], width: float, height: float, angle: float):
        self.center = center
        self.width = width
        self.height = height
        self.angle = angle
        self._calculate_corners()

    @classmethod
    def from_corners(cls, topLeft: Tuple[float, float], topRight: Tuple[float, float], bottomRight: Tuple[float, float], bottomLeft: Tuple[float, float]):
        # Calculate the center, width, height, and angle from the corners
        center = ((topLeft[0] + bottomRight[0]) / 2,
                  (topLeft[1] + bottomRight[1]) / 2)
        width = math.dist(topLeft, topRight)
        height = math.dist(topLeft, bottomLeft)
        angle = math.degrees(math.atan2(
            topRight[1] - topLeft[1], topRight[0] - topLeft[0]))
        rect = cls(center, width, height, angle)
        rect.topLeft = topLeft
        rect.topRight = topRight
        rect.bottomRight = bottomRight
        rect.bottomLeft = bottomLeft
        return rect

    def _calculate_corners(self):
        cx, cy = self.center
        angle_rad = math.radians(self.angle)

        # Calculate the other corners without rotation
        topLeft = (cx + self.height / 2, cy - self.width / 2)
        topRight = (cx + self.height / 2, cy + self.width / 2)
        bottomLeft = (cx - self.height / 2, cy - self.width / 2)
        bottomRight = (cx - self.height / 2, cy + self.width / 2)

        # Apply rotation to each corner
        self.topLeft = self._rotate_point(topLeft, cx, cy, angle_rad)
        self.topRight = self._rotate_point(topRight, cx, cy, angle_rad)
        self.bottomLeft = self._rotate_point(bottomLeft, cx, cy, angle_rad)
        self.bottomRight = self._rotate_point(bottomRight, cx, cy, angle_rad)

    def _rotate_point(self, point: Tuple[float, float], cx: float, cy: float, angle_rad: float) -> Tuple[float, float]:
        x, y = point
        # Invert the y-coordinates to reflect the inverted y-axis
        inverted_y = -y
        inverted_cy = -cy

        # Translate point to origin (for both x and inverted y)
        translated_x = x - cx
        translated_y = inverted_y - inverted_cy

        # Rotate around the origin
        rotated_x = translated_x * \
            math.cos(angle_rad) - translated_y * math.sin(angle_rad)
        rotated_y = translated_x * \
            math.sin(angle_rad) + translated_y * math.cos(angle_rad)

        # Translate back and re-invert the y-axis
        final_x = rotated_x + cx
        final_y = -(rotated_y + inverted_cy)

        return (final_x, final_y)  # Return as a tuple

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
        points1 = [self.topLeft, self.topRight,
                   self.bottomRight, self.bottomLeft]
        points2 = [other.topLeft, other.topRight,
                   other.bottomRight, other.bottomLeft]

        # Get the edge normals (axes to test) from both rectangles
        edges1 = get_edges(points1)
        edges2 = get_edges(points2)

        # Calculate axes (normals to the edges)
        # Perpendicular vectors to the edges
        axes = [(e[1], -e[0]) for e in edges1 + edges2]

        # Check for separation on any axis
        for axis in axes:
            if is_separating_axis(axis, points1, points2):
                return False  # If there's a separating axis, the rectangles do not collide

        return True  # No separating axis found, so the rectangles must be colliding

    def project_rect(rect, length=10,fov=0):
        length = length * 5
        direction = rect._rotate_point((1,0),0,0,math.radians(rect.angle))

        new_bottomLeft = rect.topLeft
        new_bottomRight = rect.topRight
        new_topLeft = (rect.topLeft[0] + direction[0] * length, rect.topLeft[1] + direction[1] * length)
        new_topRight = (rect.topRight[0] + direction[0] * length , rect.topRight[1] + direction[1] * length)

        new_topLeft = rect._rotate_point(new_topLeft,*new_bottomLeft,math.radians(fov))
        new_topRight = rect._rotate_point(new_topRight,*new_bottomRight,math.radians(-fov))
        return Rect.from_corners(new_topLeft, new_topRight, new_bottomRight, new_bottomLeft)
# testRect = Rect((0, 0), 1, 1, 90)
# points = testRect.get_points()
# direction = testRect._rotate_point((1, 0), 0, 0, math.radians(testRect.angle))
# moved_points = []
# for point in points:
#     moved_points.append((point[0] + direction[0], point[1] + direction[1]))

# print(points)
# print(direction)
# print(moved_points)
