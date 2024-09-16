import pygame
from typing import Literal, Tuple, List
import math
from rect import Rect
import asyncio
import random


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

    def getAcceleration(self) -> int:
        acceleration: dict[str, int] = {"car": 20, "bus": 12, "bike": 28}
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
        speed = self.speed
        acceleration = self.getAcceleration()
        self.speed += acceleration * dt

        if self.speed > self.getMaxSpeed():
            self.speed = self.getMaxSpeed()
        elif self.speed < 0:
            self.speed = 0

        angle_rad = math.radians(self.angle)
        # Calculate the change in x and y coordinates
        delta_x = speed * dt * math.cos(angle_rad)
        delta_y = speed * dt * math.sin(angle_rad)

        # Update the location
        self.location = (self.location[0] + delta_x, self.location[1] - delta_y)
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

        # Check for collisions
        for vehicle in vehicles:
            if self != vehicle and self.rect.isCollision(vehicle.rect):
                print(f"Collision detected between {self.type} and {vehicle.type}")
                # Handle collision (e.g., stop the vehicle, bounce back, etc.)
                self.speed = 0  # Example: stop the vehicle on collision

        # Check for projection collisions
        for vehicle in vehicles:
            if self != vehicle and self.projection.isCollision(vehicle.rect):
                print(
                    f"Projection collision detected between {self.type} and {vehicle.type}"
                )
                self.speed = self.speed - self.getAcceleration() * dt * 10
                if self.speed < 0:
                    self.speed *= 3

    def setTurn(self, angle: int, turnRate: int = 3):
        self.turn = TurnInfo(True, self.angle + angle, turnRate)


class Simulation:
    def __init__(self):
        self.vehicles = [
            Vehicle("car", "right", 1),
            Vehicle("car", "right", 2),
            Vehicle("car", "left", 1),
            Vehicle("car", "left", 2),
            Vehicle("car", "up", 1),
            Vehicle("car", "up", 2),
            Vehicle("car", "down", 1),
            Vehicle("car", "down", 2),
        ]
        # self.vehicles = [Vehicle('car', 'right', -2), Vehicle(
        #     'car', 'left', 1), Vehicle('car', 'up', 1), Vehicle('car', 'down', 1)]
        # self.vehicles[0].setTurn(90, 13)
        # self.vehicles[1].setTurn(-90, 13)
        # self.vehicles[2].setTurn(180, 13)
        # self.vehicles[3].setTurn(0, 13)

    def update(self, dt):
        for vehicle in self.vehicles:
            vehicle.move(dt, self.vehicles)

    def draw(self, screen: pygame.Surface, background_image: pygame.Surface):
        screen.blit(background_image, (0, 0))

        for vehicle in self.vehicles:
            rotated_image = pygame.transform.rotate(vehicle.image, vehicle.angle)
            screen.blit(rotated_image, vehicle.location)
            rect = rotated_image.get_rect(topleft=vehicle.location)
            pygame.draw.circle(screen, (0, 255, 0), rect.center, 5)

            size = vehicle.getSize()
            vehicle.rect = Rect(rect.center, size[0], size[1], vehicle.angle)
            pygame.draw.polygon(screen, (255, 0, 0), vehicle.rect.get_points(), 2)

            pygame.draw.circle(screen, (255, 255, 255), vehicle.rect.topLeft, 2)
            pygame.draw.circle(screen, (0, 0, 255), vehicle.rect.topRight, 2)
            pygame.draw.circle(screen, (0, 0, 255), vehicle.rect.bottomLeft, 2)
            pygame.draw.circle(screen, (0, 0, 255), vehicle.rect.bottomRight, 2)

            # Rect projection
            vehicle.projection = vehicle.rect.project_rect()
            pygame.draw.polygon(screen, (0, 255, 0), vehicle.projection.get_points(), 2)

    def clean(self):
        for vehicle in self.vehicles:
            if (
                vehicle.location[0] < 0
                or vehicle.location[0] > 1280
                or vehicle.location[1] < 0
                or vehicle.location[1] > 720
            ) and vehicle.speed == vehicle.getMaxSpeed():
                self.vehicles.remove(vehicle)
                print("Vehicle removed")


async def generateVehicle(key: int, simulation: Simulation):
    print("Generating vehicle")
    while True:
        vehicle: Vehicle
        if key == pygame.K_UP:
            vehicle = Vehicle("car", "up", 1)
        elif key == pygame.K_DOWN:
            vehicle = Vehicle("car", "down", 1)
        elif key == pygame.K_LEFT:
            vehicle = Vehicle("car", "left", 1)
        elif key == pygame.K_RIGHT:
            vehicle = Vehicle("car", "right", 1)

        for v in simulation.vehicles:
            if vehicle.rect.isCollision(v.rect):
                await asyncio.sleep(0.3)
                continue
        simulation.vehicles.append(vehicle)
        break


async def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    clock = pygame.time.Clock()
    running = True
    dt: float = 0

    # Load the background image
    background_image = pygame.image.load("./images/mod_int3.png")

    simulation = Simulation()

    tasks = []

    while running:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYUP and event.key in (
                pygame.K_UP,
                pygame.K_DOWN,
                pygame.K_LEFT,
                pygame.K_RIGHT,
            ):
                tasks.append(
                    asyncio.create_task(generateVehicle(event.key, simulation))
                )
        # Get the current window size
        window_size = screen.get_size()

        # Scale the background image to the current window size
        scaled_background = pygame.transform.scale(background_image, window_size)

        pygame.display.flip()
        dt = clock.tick(60) / 1000
        simulation.draw(screen, scaled_background)
        simulation.update(dt)
        simulation.clean()
        await asyncio.sleep(0)
    pygame.quit()
    print(simulation.vehicles)


if __name__ == "__main__":
    asyncio.run(main())
