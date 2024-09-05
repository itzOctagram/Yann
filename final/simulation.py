import pygame
from typing import Literal, Tuple


class Vehicle:
    type: Literal['car', 'bus', 'bike']
    direction: Literal['up', 'down', 'left', 'right']
    # left - sharp turn, right - moderate turn
    turnDirection: Literal['left', 'right', 'straight']
    speed: int
    location: Tuple[int, int]
    image: pygame.Surface

    def __init__(self, type: Literal['car', 'bus', 'bike'], direction: Literal['up', 'down', 'left', 'right'], turnDirection: Literal['left', 'right', 'straight'] = 'straight'):
        self.type = type
        self.direction = direction
        self.turnDirection = turnDirection
        self.speed = self.getMaxSpeed()
        self.location = self.getStartLocation()
        self.image = pygame.image.load(f'./images/{direction}/{type}.png')

    def getMaxSpeed(self):
        maxSpeed = {'car': 5, 'bus': 3, 'bike': 7}
        return maxSpeed[self.type]

    def getAcceleration(self):
        acceleration = {'car': 1, 'bus': 0.6, 'bike': 1.4}
        return acceleration[self.type]

    def getStartLocation(self):
        startLocation = {'up': (640, 720), 'down': (
            640, 0), 'left': (1250, 360), 'right': (0, 360)}
        return startLocation[self.direction]

    def getSize(self):
        size = {'car': (22, 54), 'bus': (26, 76), 'bike': (17, 38)}
        if (self.direction == 'up' or self.direction == 'down'):
            return size[self.type]
        else:
            return size[self.type][::-1]


if __name__ == "__main__":
    pygame.init()
    screen_info = pygame.display.Info()
    screen = pygame.display.set_mode((1280, 720))
    clock = pygame.time.Clock()
    running = True
    dt = 0

    # Load the background image
    background_image = pygame.image.load('./images/mod_int3.png')

    vehicle = Vehicle('car', 'left')
    while running:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

         # Get the current window size
        window_size = screen.get_size()

        # Scale the background image to the current window size
        scaled_background = pygame.transform.scale(
            background_image, window_size)

        # Draw the scaled background image
        screen.blit(scaled_background, (0, 0))

        screen.blit(vehicle.image, vehicle.location)

        pygame.display.flip()
        dt = clock.tick(60)/1000
    pygame.quit()
