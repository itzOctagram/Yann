import pygame
from typing import Literal, Tuple

class Vehicle:
    type: Literal['car', 'bus', 'bike']
    direction: Literal['up', 'down', 'left', 'right']
    # left - sharp turn, right - moderate turn
    turnDirection: Literal['left', 'right', 'straight']
    speed: Tuple[int, int]
    location: Tuple[int, int]
    image: pygame.Surface

    def __init__(self, type: Literal['car', 'bus', 'bike'], direction: Literal['up', 'down', 'left', 'right'], turnDirection: Literal['left', 'right', 'straight'] = 'straight'):
        self.type = type
        self.direction = direction
        self.turnDirection = turnDirection
        self.speed = 0
        self.setStartLocation()
        self.image = pygame.image.load(f'./images/{direction}/{type}.png')

    def getMaxSpeed(self):
        maxSpeed = {'car': 50, 'bus': 30, 'bike': 70}
        return maxSpeed[self.type]

    def getAcceleration(self):
        acceleration: dict[str, int] = {'car': 20, 'bus': 12, 'bike': 28}
        return acceleration[self.type]

    def setStartLocation(self):
        screen_info = (1280, 720)
        startLocation = {'up': (screen_info[0]//2, screen_info[1]), 'down': (screen_info[0]//2, 0),
                         'left': (screen_info[0], screen_info[1]//2), 'right': (0, screen_info[1]//2)}
        self.setLocation(startLocation[self.direction])

    def setLocation(self, location: Tuple[int, int]):
        size = self.getSize()
        center = (size[0]//2, size[1]//2)
        self.location = (location[0]-center[0], location[1]-center[1])
        # self.location = location

    def getSize(self):
        size = {'car': (22, 54), 'bus': (26, 76), 'bike': (17, 38)}
        reverse_size = {'car': (54, 22), 'bus': (76, 26), 'bike': (38, 17)}
        if (self.direction == 'up' or self.direction == 'down'):
            return size[self.type]
        else:
            return reverse_size[self.type]

    def move(self, dt: float):
        speed = self.speed
        acceleration = self.getAcceleration()
        self.speed += acceleration*dt

        if(self.speed > self.getMaxSpeed()):
            self.speed = self.getMaxSpeed()
        elif(self.speed < 0):
            self.speed = 0
        
        if self.direction == 'up':
            self.location = (self.location[0], self.location[1] - speed*dt)
        elif self.direction == 'down':
            self.location = (self.location[0], self.location[1] + speed*dt)
        elif self.direction == 'left':
            self.location = (self.location[0] - speed*dt, self.location[1])
        elif self.direction == 'right':
            self.location = (self.location[0] + speed*dt, self.location[1])

class Simulation:
    vehicles: list[Vehicle]

    


vehicles = [Vehicle('car', 'up'), Vehicle('car', 'down'),
            Vehicle('car', 'left'), Vehicle('car', 'right')]

if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    clock = pygame.time.Clock()
    running = True
    dt = 0

    # Load the background image
    background_image = pygame.image.load('./images/mod_int3.png')

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

        for vehicle in vehicles:
            screen.blit(vehicle.image, vehicle.location)

        pygame.display.flip()
        dt = clock.tick(60)/1000
        for vehicle in vehicles:
            vehicle.move(dt)
    pygame.quit()
