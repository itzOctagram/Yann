import pygame
from rect import Rect
import asyncio
from vehicle import Vehicle
from trafficLight import TrafficLight


class Simulation:
    vehicles: list[Vehicle]
    trafficLights: list[TrafficLight]

    def __init__(self):
        locations = {
            "left": (520, 340),
            "right": (740, 340),
            "up": (630, 250),
            "down": (630, 430),
        }

        self.vehicles = [
            Vehicle("car", "right", 1, "right"),
            # Vehicle("car", "right", 2, "left"),
            Vehicle("car", "left", 1, "left"),
            # Vehicle("car", "left", 2),
            Vehicle("car", "up", 1, "right"),
            # Vehicle("car", "up", 2),
            Vehicle("car", "down", 1, "right"),
            # Vehicle("car", "down", 2),
        ]
        # self.vehicles = [Vehicle('car', 'right', -2), Vehicle(
        #     'car', 'left', 1), Vehicle('car', 'up', 1), Vehicle('car', 'down', 1)]
        # self.vehicles[0].setTurn(90, 13)
        # self.vehicles[1].setTurn(-90, 13)
        # self.vehicles[2].setTurn(180, 13)
        # self.vehicles[3].setTurn(0, 13)
        # self.trafficLights = [
        #     TrafficLight(locations["left"], "vertical", "red"),
        #     TrafficLight(locations["right"], "vertical", "red"),
        #     TrafficLight(locations["up"], "horizontal", "red"),
        #     TrafficLight(locations["down"], "horizontal", "red"),
        # ]

        self.turnLocations = {
            "left": (560, 340),
            "right": (700, 340),
            "up": (630, 270),
            "down": (630, 400),
        }

    def update(self, dt):
        for vehicle in self.vehicles:
            vehicle.move(dt, self.vehicles)

    def draw(self, screen: pygame.Surface):

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

    def showLights(self, screen: pygame.Surface):
        for light in self.trafficLights:
            pygame.draw.polygon(screen, light.color, light.rect.get_points(), 0)
            pygame.draw.circle(screen, (255, 255, 255), light.rect.topLeft, 2)

    def showTurnLocations(self, screen: pygame.Surface):
        inverse = {"left": "right", "right": "left", "up": "down", "down": "up"}
        for turnLocationKey in self.turnLocations:
            turnLocation = self.turnLocations[turnLocationKey]
            rect = Rect(
                turnLocation,
                100,
                1,
                0 if turnLocationKey == "left" or turnLocationKey == "right" else 90,
            )
            pygame.draw.polygon(screen, (255, 0, 0), rect.get_points(), 2)
            for vehicle in self.vehicles:
                if (
                    not vehicle.turn.turning
                    and turnLocationKey == inverse[vehicle.direction]
                    and vehicle.rect.isCollision(rect)
                    and not vehicle.turnDirection == "straight"
                ):
                    if vehicle.turnDirection == "left":
                        vehicle.setTurn(90, 50)
                    elif vehicle.turnDirection == "right":
                        vehicle.setTurn(-90, 32)

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

        screen.blit(scaled_background, (0, 0))
        # simulation.showLights(screen)
        simulation.draw(screen)
        simulation.showTurnLocations(screen)
        simulation.update(dt)
        simulation.clean()
        await asyncio.sleep(0)
    pygame.quit()
    print(simulation.vehicles)


if __name__ == "__main__":
    asyncio.run(main())
