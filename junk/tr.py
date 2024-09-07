import asyncio
import websockets
import json
import pygame
import random
import math
import time
import threading
from queue import Queue

# Initialize WebSocket URL
WEBSOCKET_URL = "ws://localhost:8765/receiver"  # Update with your WebSocket URL

# Initialize Pygame
pygame.init()
simulation = pygame.sprite.Group()

# Define constants
defaultRed = 150
defaultYellow = 5
defaultGreen = 20
defaultMinimum = 10
defaultMaximum = 60
carTime = 2
bikeTime = 1
rickshawTime = 2.25
busTime = 2.5
truckTime = 2.5
gap = 15
gap2 = 15
rotationAngle = 3
noOfSignals = 4
simTime = 300
timeElapsed = 0
currentGreen = 0
nextGreen = (currentGreen + 1) % noOfSignals
currentYellow = 0
vehicles = {'right': {0: [], 1: [], 2: [], 'crossed': 0},
            'down': {0: [], 1: [], 2: [], 'crossed': 0},
            'left': {0: [], 1: [], 2: [], 'crossed': 0},
            'up': {0: [], 1: [], 2: [], 'crossed': 0}}
vehicleTypes = {0: 'car', 1: 'bus', 2: 'truck', 3: 'rickshaw', 4: 'bike'}
directionNumbers = {0: 'right', 1: 'down', 2: 'left', 3: 'up'}
x = {'right': [0, 0, 0], 'down': [755, 727, 697],
     'left': [1400, 1400, 1400], 'up': [602, 627, 657]}
y = {'right': [348, 370, 398], 'down': [0, 0, 0],
     'left': [498, 466, 436], 'up': [800, 800, 800]}
stopLines = {'right': 590, 'down': 330, 'left': 800, 'up': 535}
defaultStop = {'right': 580, 'down': 320, 'left': 810, 'up': 545}
stops = {'right': [580, 580, 580], 'down': [320, 320, 320],
         'left': [810, 810, 810], 'up': [545, 545, 545]}
mid = {'right': {'x': 705, 'y': 445}, 'down': {'x': 695, 'y': 450},
       'left': {'x': 695, 'y': 425}, 'up': {'x': 695, 'y': 400}}
speeds = {'car': 2.25, 'bus': 1.8, 'truck': 1.8,
          'rickshaw': 2, 'bike': 2.5}


class TrafficSignal:
    def __init__(self, red, yellow, green, minimum, maximum):
        self.red = red
        self.yellow = yellow
        self.green = green
        self.minimum = minimum
        self.maximum = maximum
        self.signalText = "30"
        self.totalGreenTime = 0


class Vehicle(pygame.sprite.Sprite):
    def __init__(self, lane, vehicleClass, direction_number, direction, will_turn):
        pygame.sprite.Sprite.__init__(self)
        self.lane = lane
        self.vehicleClass = vehicleClass
        self.speed = speeds[vehicleClass]
        self.direction_number = direction_number
        self.direction = direction
        self.x = x[direction][lane]
        self.y = y[direction][lane]
        self.crossed = 0
        self.willTurn = will_turn
        self.turned = 0
        self.rotateAngle = 0
        vehicles[direction][lane].append(self)
        self.index = len(vehicles[direction][lane]) - 1
        path = "images/" + direction + "/" + vehicleClass + ".png"
        self.originalImage = pygame.image.load(path)
        self.currentImage = pygame.image.load(path)
        if direction == 'right':
            if len(vehicles[direction][lane]) > 1 and vehicles[direction][lane][self.index - 1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index -
                                                      1].stop - self.currentImage.get_rect().width - gap
            else:
                self.stop = defaultStop[direction]
            temp = self.currentImage.get_rect().width + gap
            x[direction][lane] -= temp
            stops[direction][lane] -= temp
        elif direction == 'left':
            if len(vehicles[direction][lane]) > 1 and vehicles[direction][lane][self.index - 1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index -
                                                      1].stop + self.currentImage.get_rect().width + gap
            else:
                self.stop = defaultStop[direction]
            temp = self.currentImage.get_rect().width + gap
            x[direction][lane] += temp
            stops[direction][lane] += temp
        elif direction == 'down':
            if len(vehicles[direction][lane]) > 1 and vehicles[direction][lane][self.index - 1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index -
                                                      1].stop - self.currentImage.get_rect().height - gap
            else:
                self.stop = defaultStop[direction]
            temp = self.currentImage.get_rect().height + gap
            y[direction][lane] -= temp
            stops[direction][lane] -= temp
        elif direction == 'up':
            if len(vehicles[direction][lane]) > 1 and vehicles[direction][lane][self.index - 1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index -
                                                      1].stop + self.currentImage.get_rect().height + gap
            else:
                self.stop = defaultStop[direction]
            temp = self.currentImage.get_rect().height + gap
            y[direction][lane] += temp
            stops[direction][lane] += temp
        simulation.add(self)

    def render(self, screen):
        screen.blit(self.currentImage, (self.x, self.y))

    def move(self):
        if self.direction == 'right':
            if self.crossed == 0 and self.x + self.currentImage.get_rect().width > stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            if self.willTurn == 1:
                if self.crossed == 0 or self.x + self.currentImage.get_rect().width < mid[self.direction]['x']:
                    if (self.x + self.currentImage.get_rect().width <= self.stop or (currentGreen == 0 and currentYellow == 0) or self.crossed == 1) and (self.index == 0 or self.x + self.currentImage.get_rect().width < (vehicles[self.direction][self.lane][self.index - 1].x - gap2) or vehicles[self.direction][self.lane][self.index - 1].turned == 1):
                        self.x += self.speed
                else:
                    if self.turned == 0:
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(
                            self.originalImage, -self.rotateAngle)
                        self.x += 2
                        self.y += 1.8
                        if self.rotateAngle == 90:
                            self.turned = 1
                    else:
                        if self.index == 0 or self.y + self.currentImage.get_rect().height < (vehicles[self.direction][self.lane][self.index - 1].y - gap2) or self.x + self.currentImage.get_rect().width < (vehicles[self.direction][self.lane][self.index - 1].x - gap2):
                            self.y += self.speed
            else:
                if (self.x + self.currentImage.get_rect().width <= self.stop or self.crossed == 1 or (currentGreen == 0 and currentYellow == 0)) and (self.index == 0 or self.x + self.currentImage.get_rect().width < (vehicles[self.direction][self.lane][self.index - 1].x - gap2) or vehicles[self.direction][self.lane][self.index - 1].turned == 1):
                    self.x += self.speed
        elif self.direction == 'down':
            if self.crossed == 0 and self.y + self.currentImage.get_rect().height > stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            if self.willTurn == 1:
                if self.crossed == 0 or self.y + self.currentImage.get_rect().height < mid[self.direction]['y']:
                    if (self.y + self.currentImage.get_rect().height <= self.stop or (currentGreen == 0 and currentYellow == 0) or self.crossed == 1) and (self.index == 0 or self.y + self.currentImage.get_rect().height < (vehicles[self.direction][self.lane][self.index - 1].y - gap2) or vehicles[self.direction][self.lane][self.index - 1].turned == 1):
                        self.y += self.speed
                else:
                    if self.turned == 0:
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(
                            self.originalImage, -self.rotateAngle)
                        self.y += 2
                        self.x -= 1.8
                        if self.rotateAngle == 90:
                            self.turned = 1
                    else:
                        if self.index == 0 or self.x + self.currentImage.get_rect().width < (vehicles[self.direction][self.lane][self.index - 1].x - gap2) or self.y + self.currentImage.get_rect().height < (vehicles[self.direction][self.lane][self.index - 1].y - gap2):
                            self.x -= self.speed
            else:
                if (self.y + self.currentImage.get_rect().height <= self.stop or self.crossed == 1 or (currentGreen == 0 and currentYellow == 0)) and (self.index == 0 or self.y + self.currentImage.get_rect().height < (vehicles[self.direction][self.lane][self.index - 1].y - gap2) or vehicles[self.direction][self.lane][self.index - 1].turned == 1):
                    self.y += self.speed
        elif self.direction == 'left':
            if self.crossed == 0 and self.x < stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            if self.willTurn == 1:
                if self.crossed == 0 or self.x > mid[self.direction]['x']:
                    if (self.x >= self.stop or (currentGreen == 0 and currentYellow == 0) or self.crossed == 1) and (self.index == 0 or self.x > (vehicles[self.direction][self.lane][self.index - 1].x + gap2) or vehicles[self.direction][self.lane][self.index - 1].turned == 1):
                        self.x -= self.speed
                else:
                    if self.turned == 0:
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(
                            self.originalImage, -self.rotateAngle)
                        self.x -= 2
                        self.y -= 1.8
                        if self.rotateAngle == 90:
                            self.turned = 1
                    else:
                        if self.index == 0 or self.y + self.currentImage.get_rect().height < (vehicles[self.direction][self.lane][self.index - 1].y - gap2) or self.x > (vehicles[self.direction][self.lane][self.index - 1].x + gap2):
                            self.y -= self.speed
            else:
                if (self.x >= self.stop or self.crossed == 1 or (currentGreen == 0 and currentYellow == 0)) and (self.index == 0 or self.x > (vehicles[self.direction][self.lane][self.index - 1].x + gap2) or vehicles[self.direction][self.lane][self.index - 1].turned == 1):
                    self.x -= self.speed
        elif self.direction == 'up':
            if self.crossed == 0 and self.y < stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
            if self.willTurn == 1:
                if self.crossed == 0 or self.y > mid[self.direction]['y']:
                    if (self.y >= self.stop or (currentGreen == 0 and currentYellow == 0) or self.crossed == 1) and (self.index == 0 or self.y > (vehicles[self.direction][self.lane][self.index - 1].y + gap2) or vehicles[self.direction][self.lane][self.index - 1].turned == 1):
                        self.y -= self.speed
                else:
                    if self.turned == 0:
                        self.rotateAngle += rotationAngle
                        self.currentImage = pygame.transform.rotate(
                            self.originalImage, -self.rotateAngle)
                        self.y -= 2
                        self.x += 1.8
                        if self.rotateAngle == 90:
                            self.turned = 1
                    else:
                        if self.index == 0 or self.x + self.currentImage.get_rect().width < (vehicles[self.direction][self.lane][self.index - 1].x - gap2) or self.y > (vehicles[self.direction][self.lane][self.index - 1].y + gap2):
                            self.x += self.speed
            else:
                if (self.y >= self.stop or self.crossed == 1 or (currentGreen == 0 and currentYellow == 0)) and (self.index == 0 or self.y > (vehicles[self.direction][self.lane][self.index - 1].y + gap2) or vehicles[self.direction][self.lane][self.index - 1].turned == 1):
                    self.y -= self.speed


def create_vehicle(data):
    direction = directionNumbers[data['direction']]
    lane = data['lane']
    vehicleClass = vehicleTypes[data['vehicleClass']]
    will_turn = data.get('willTurn', 0)  # Default to no turn
    Vehicle(lane, vehicleClass, data['direction_number'], direction, will_turn)


async def receive_data():
    async with websockets.connect(WEBSOCKET_URL) as websocket:
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"Received data: {data}")
            if 'direction' in data and 'lane' in data and 'vehicleClass' in data:
                create_vehicle(data)


def simulation_loop():
    global timeElapsed, currentGreen, currentYellow, nextGreen
    screen = pygame.display.set_mode((1200, 800))
    pygame.display.set_caption("Traffic Simulation")

    traffic_signal = TrafficSignal(
        defaultRed, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)

    running = True
    clock = pygame.time.Clock()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

        screen.fill((255, 255, 255))

        # Update traffic lights
        if currentGreen == 0 and currentYellow == 0:
            if timeElapsed >= traffic_signal.red:
                currentGreen = nextGreen
                nextGreen = (nextGreen + 1) % noOfSignals
                timeElapsed = 0
                traffic_signal.signalText = str(traffic_signal.green)
            else:
                traffic_signal.signalText = str(
                    traffic_signal.red - timeElapsed)

        elif currentYellow == 0:
            if timeElapsed >= traffic_signal.green:
                currentYellow = (currentGreen + 1) % noOfSignals
                timeElapsed = 0
                traffic_signal.signalText = str(traffic_signal.yellow)

        else:
            if timeElapsed >= traffic_signal.yellow:
                currentYellow = 0
                timeElapsed = 0
                traffic_signal.signalText = str(traffic_signal.red)

        timeElapsed += 1
        # Render all sprites
        simulation.update()
        simulation.draw(screen)

        pygame.display.flip()
        clock.tick(60)


# Run WebSocket receiver in a separate thread
threading.Thread(target=asyncio.run, args=(receive_data(),)).start()

# Run the simulation loop
simulation_loop()
