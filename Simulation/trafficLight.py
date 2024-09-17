from rect import Rect
from typing import Tuple, Literal

class TrafficLight:
    location : Tuple[float, float]
    orientation : Literal['horizontal', 'vertical']
    state : Literal['red', 'yellow', 'green']
    color: Tuple[int, int, int]
    rect : Rect

    def __init__(self, location: Tuple[float, float], orientation: Literal['horizontal', 'vertical'], state: Literal['red', 'yellow', 'green']):
        self.location = location
        self.orientation = orientation
        self.state = state
        self.color = (255, 0, 0) if state == 'red' else (255, 255, 0) if state == 'yellow' else (0, 255, 0)
        self.rect = Rect(location, 100, 20, 0 if orientation == 'vertical' else 90)

    def changeState(self, state: Literal['red', 'yellow', 'green']):
        self.state = state
        self.color = (255, 0, 0) if state == 'red' else (255, 255, 0) if state == 'yellow' else (0, 255, 0)