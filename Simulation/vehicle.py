import math
from typing import Tuple, Literal, List
import pygame
from rect import Rect


class TurnInfo:
    turning: bool
    destination: float
    turnRate: float

    def __init__(self, turning: bool, destination: float, turnRate: float):
        self.turning = turning
        self.destination = destination
        self.turnRate = turnRate


class Vehicle:
    type: Literal["car", "bus", "bike"]
    direction: Literal["up", "down", "left", "right"]
    # left - sharp turn, right - moderate turn
    turnDirection: Literal["left", "right", "straight"]
    speed: float
    angle: float
    turn: TurnInfo
    location: Tuple[float, float]
    image: pygame.Surface
    rect: Rect
    projection: Rect

    def __init__(
        self,
        type: Literal["car", "bus", "bike"],
        direction: Literal["up", "down", "left", "right"],
        lane: Literal[1, 2, -1, -2],
        turnDirection: Literal["left", "right", "straight"] = "straight",
    ):
        direction_to_angle = {"right": 0, "up": 90, "left": 180, "down": 270}

        self.type = type
        self.direction = direction
        self.turnDirection = turnDirection
        self.speed = 0
        self.angle = direction_to_angle[direction]
        self.turn = TurnInfo(False, 0, 0)
        self.setStartLocation(lane)
        self.image = pygame.image.load(f"images/right/{type}.png")
        width, height = {"car": (22, 54), "bus": (26, 76), "bike": (17, 38)}[self.type]
        self.rect = Rect(self.location, width, height, self.angle)

    def getMaxSpeed(self):
        maxSpeed = {"car": 75, "bus": 45, "bike": 105}
        return maxSpeed[self.type]

    def getAcceleration(self) -> float:
        acceleration: dict[str, float] = {"car": 20, "bus": 12, "bike": 28}
        return acceleration[self.type]

    def setStartLocation(self, lane: Literal[1, 2, -1, -2]):
        screen_info = (1280, 720)
        offsets = {1: 25, 2: 50, -1: 0, -2: -25}
        startLocation = {
            "up": (screen_info[0] // 2 - offsets[lane] + 5, screen_info[1]),
            "down": (screen_info[0] // 2 + offsets[lane] - 20, 0),
            "left": (screen_info[0], screen_info[1] // 2 + offsets[lane] - 35),
            "right": (0, screen_info[1] // 2 - offsets[lane] - 10),
        }
        self.setLocation(startLocation[self.direction])

    def setLocation(self, location: Tuple[int, int]):
        size = self.getSize()
        center = (size[0] // 2, size[1] // 2)
        if self.direction == "left" or self.direction == "right":
            center = (center[1], center[0])
        self.location = (location[0] - center[0], location[1] - center[1])

    def getSize(self):
        size = {"car": (22, 54), "bus": (26, 76), "bike": (17, 38)}
        return size[self.type]

    def move(self, dt: float, vehicles: "List[Vehicle]"):
        def performMovement() -> None:
            angle_rad = math.radians(self.angle)
            # Calculate the change in x and y coordinates
            delta_x = self.speed * dt * math.cos(angle_rad)
            delta_y = self.speed * dt * math.sin(angle_rad)
            # Update the location
            self.location = (self.location[0] + delta_x, self.location[1] - delta_y)

        def performAcceleration() -> None:
            rectCollision: bool = False
            projectionCollision: bool = False

            for vehicle in vehicles:
                if self != vehicle and self.rect.isCollision(vehicle.rect):
                    rectCollision = True
                if self != vehicle and self.projection.isCollision(vehicle.rect):
                    projectionCollision = True

            # if rectCollision and projectionCollision:
            #     self._reverse(dt)
            if rectCollision:
                # self._brake(dt)
                self.speed = 0
            if projectionCollision:
                self._reverse(dt)
            if not rectCollision and not projectionCollision:
                self._accelerate(dt)

        performMovement()
        performAcceleration()

        # self.rect.topleft = self.location

        # Turning Logic
        if self.turn.turning:
            angle_diff = (self.turn.destination - self.angle) % 360
            if angle_diff > 180:
                angle_diff -= 360

            # Determine the turn rate
            turn_rate = self.turn.turnRate * dt * self.speed / self.getMaxSpeed()

            # Adjust the angle
            if angle_diff > 0:
                self.angle += min(turn_rate, angle_diff)
            else:
                self.angle -= min(turn_rate, -angle_diff)

            # Normalize the angle to be within [0, 360)
            self.angle %= 360

            # Check if the angle has reached the destination
            if abs(angle_diff) <= turn_rate:
                self.angle = self.turn.destination
                self.turn.turning = False

        # # Check for collisions
        # for vehicle in vehicles:
        #     if self != vehicle and self.rect.isCollision(vehicle.rect):
        #         print(f"Collision detected between {self.type} and {vehicle.type}")
        #         # Handle collision (e.g., stop the vehicle, bounce back, etc.)
        #         self.speed = (
        #             -abs(self.speed) / 2
        #         )  # Example: stop the vehicle on collision

    def setTurn(self, angle: int, turnRate: int = 3):
        self.turn = TurnInfo(True, self.angle + angle, turnRate)

    def _accelerate(self, dt: float): # if no rect or projection collision
        acceleration = self.getAcceleration()
        if self.speed < 0:
            acceleration *= 3
        self.speed += acceleration * dt
        if self.speed > self.getMaxSpeed():
            self.speed = self.getMaxSpeed()

    def _brake(self, dt: float, force: float = 10):
        self.speed -= self.getAcceleration() * dt * force
        if self.speed < 0:
            self.speed = 0

    def _reverse(self, dt: float):
        if self.speed > 0:
            print("Reverse needs to break first")
            self._brake(dt)
        elif self.speed > -self.getMaxSpeed() :
            self.speed -= self.getAcceleration() * dt * 10

        if self.speed < -self.getMaxSpeed():
            self.speed = -self.getMaxSpeed()
