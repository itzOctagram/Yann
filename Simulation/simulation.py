import pygame
from typing import Literal, Tuple, List
import math
from rect import Rect


class TurnInfo:
    turning: bool
    destination: int
    turnRate: int

    def __init__(self, turning: bool, destination: int, turnRate: int):
        self.turning = turning
        self.destination = destination
        self.turnRate = turnRate


class Vehicle:
    type: Literal['car', 'bus', 'bike']
    direction: Literal['up', 'down', 'left', 'right']
    # left - sharp turn, right - moderate turn
    turnDirection: Literal['left', 'right', 'straight']
    speed: float
    angle: int
    turn: TurnInfo
    location: Tuple[int, int]
    image: pygame.Surface
    rect: Rect

    def __init__(self, type: Literal['car', 'bus', 'bike'], direction: Literal['up', 'down', 'left', 'right'], lane: Literal[1, 2, -1, -2], turnDirection: Literal['left', 'right', 'straight'] = 'straight'):
        direction_to_angle = {'right': 0, 'up': 90, 'left': 180, 'down': 270}

        self.type = type
        self.direction = direction
        self.turnDirection = turnDirection
        self.speed = 0
        self.angle = direction_to_angle[direction]
        self.turn = TurnInfo(False, 0, 0)
        self.setStartLocation(lane)
        self.image = pygame.image.load(f'images/right/{type}.png')
        width, height = {'car': (22, 54), 'bus': (
            26, 76), 'bike': (17, 38)}[self.type]
        self.rect = Rect(self.location, width, height, self.angle)

    def getMaxSpeed(self):
        maxSpeed = {'car': 75, 'bus': 45, 'bike': 105}
        return maxSpeed[self.type]

    def getAcceleration(self) -> int:
        acceleration: dict[str, int] = {'car': 20, 'bus': 12, 'bike': 28}
        return acceleration[self.type]

    def setStartLocation(self, lane: Literal[1, 2, -1, -2]):
        screen_info = (1280, 720)
        offsets = {1: 25, 2: 50, -1: 0, -2: -25}
        startLocation = {'up': (screen_info[0]//2, screen_info[1]), 'down': (screen_info[0]//2, 0),
                         'left': (screen_info[0], screen_info[1]//2 - offsets[lane] + 40), 'right': (0, screen_info[1]//2 - offsets[lane] - 10)}
        self.setLocation(startLocation[self.direction])

    def setLocation(self, location: Tuple[int, int]):
        size = self.getSize()
        center = (size[0]//2, size[1]//2)
        self.location = (location[0]-center[0], location[1]-center[1])

    def getSize(self):
        size = {'car': (22, 54), 'bus': (26, 76), 'bike': (17, 38)}
        reverse_size = {'car': (54, 22), 'bus': (76, 26), 'bike': (38, 17)}
        if (self.direction == 'up' or self.direction == 'down'):
            return size[self.type]
        else:
            return reverse_size[self.type]

    def move(self, dt: float, vehicles: 'List[Vehicle]'):
        speed = self.speed
        acceleration = self.getAcceleration()
        self.speed += acceleration*dt

        if (self.speed > self.getMaxSpeed()):
            self.speed = self.getMaxSpeed()
        elif (self.speed < 0):
            self.speed = 0

        angle_rad = math.radians(self.angle)
        # Calculate the change in x and y coordinates
        delta_x = speed * dt * math.cos(angle_rad)
        delta_y = speed * dt * math.sin(angle_rad)

        # Update the location
        self.location = (round(self.location[0] + delta_x),
                         round(self.location[1] - delta_y))
        # self.rect.topleft = self.location

        # Turning Logic
        if (self.turn.turning):
            angle_diff = (self.turn.destination - self.angle) % 360
            if angle_diff > 180:
                angle_diff -= 360

            # Determine the turn rate
            turn_rate = self.turn.turnRate * dt

            # Adjust the angle
            if angle_diff > 0:
                self.angle += round(min(turn_rate, angle_diff))
            else:
                self.angle -= round(min(turn_rate, -angle_diff))

            # Normalize the angle to be within [0, 360)
            self.angle %= 360
            print("turned", turn_rate)

            # Check if the angle has reached the destination
            if abs(angle_diff) <= turn_rate:
                self.angle = self.turn.destination
                self.turn.turning = False

        # # Check for collisions
        # for vehicle in vehicles:
        #     if self != vehicle and self.rect.colliderect(vehicle.rect):
        #         print(
        #             f"Collision detected between {self.type} and {vehicle.type}")
        #         # Handle collision (e.g., stop the vehicle, bounce back, etc.)
        #         self.speed = 0  # Example: stop the vehicle on collision

    def setTurn(self, angle: int, turnRate: int = 3):
        self.turn = TurnInfo(True, self.angle + angle, turnRate)


# def rotate_point(point: Tuple[int, int], pivot: Tuple[int, int], angle: float) -> Tuple[int, int]:
#     px, py = pivot
#     x, y = point
#     angle_rad = math.radians(angle)
#     x_new = px + (x - px) * math.cos(angle_rad) - \
#         (y - py) * math.sin(angle_rad)
#     y_new = py + (x - px) * math.sin(angle_rad) + \
#         (y - py) * math.cos(angle_rad)
#     return (x_new, y_new)


class Simulation:
    def __init__(self):
        # self.vehicles = [Vehicle('car', 'right', 1), Vehicle('car', 'right', 2), Vehicle('car', 'right', -1), Vehicle('car', 'right', -2),
        #                  Vehicle('car', 'left', 1), Vehicle('car', 'left', 2), Vehicle(
        #                      'car', 'left', -1), Vehicle('car', 'left', -2),
        #                  Vehicle('car', 'up', 1)]
        self.vehicles = [Vehicle('car', 'right', 1), Vehicle(
            'car', 'left', 1), Vehicle('car', 'up', 1), Vehicle('car', 'down', 1)]
        self.vehicles[0].setTurn(90, 30)

    def update(self, dt):
        for vehicle in self.vehicles:
            vehicle.move(dt, self.vehicles)

    def draw(self, screen: pygame.Surface, background_image: pygame.Surface):
        screen.blit(background_image, (0, 0))
        for vehicle in self.vehicles:
            # Rotate the vehicle image
            rotated_image = pygame.transform.rotate(
                vehicle.image, vehicle.angle)

            # Blit the rotated image
            screen.blit(rotated_image, vehicle.location)

            # # Draw the rect outline for debugging
            size = vehicle.getSize()
            topLeft = (vehicle.location[0], vehicle.location[1])
            topRight = (vehicle.location[0] + size[0], vehicle.location[1])
            bottomRight = (
                vehicle.location[0] + size[0], vehicle.location[1] + size[1])
            bottomLeft = (vehicle.location[0], vehicle.location[1] + size[1])
            # angle = {'up': 0, 'down': 0, 'left': 0,
            #          'right': 0}[vehicle.direction]

            points = (topLeft, topRight,
                      bottomRight, bottomLeft)
            pygame.draw.polygon(screen, (255, 0, 0), points, 2)


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    clock = pygame.time.Clock()
    running = True
    dt: float = 0

    # Load the background image
    background_image = pygame.image.load('./images/mod_int3.png')

    simulation = Simulation()

    while running:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

         # Get the current window size
        window_size = screen.get_size()

        # Scale the background image to the current window size
        scaled_background = pygame.transform.scale(
            background_image, window_size)

        pygame.display.flip()
        dt = clock.tick(60)/1000
        simulation.update(dt)
        simulation.draw(screen, scaled_background)
    pygame.quit()
