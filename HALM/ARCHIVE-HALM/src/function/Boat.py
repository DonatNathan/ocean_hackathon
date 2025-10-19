import pygame
import random
import math
from utils import constant
from .Drone import Drone
from .HommeALaMer import HommeALaMer


class Boat:
    def __init__(self, speed=2):
        """
        Boat that moves across the map in a random direction and can drop a man overboard.
        """

        angle = random.uniform(-math.pi / 6, math.pi / 6)

        if random.choice(["left", "right"]) == "left":
            self.x = -40
            self.direction_vector = (math.cos(angle), math.sin(angle))
        else:
            self.x = constant.LARGEUR_SIMULATION + 40
            self.direction_vector = (-math.cos(angle), math.sin(angle))
            angle = math.pi - angle

        self.y = random.randint(100, constant.HAUTEUR_SIMULATION - 100)

        self.speed = speed
        self.sizeX = 100
        self.sizeY = 30
        self.color = constant.BLANC
        self.has_dropped_man = False
        self.man_overboard = None
        self.man_found = False
        self.detached = False
        self.angle = angle
        self.drones = []
        self.cone = None
        self.start_cone = []

        boat_center_x = self.x
        boat_center_y = self.y

        self.base = Drone(
            boat_center_x,
            boat_center_y,
            boat_center_x,
            boat_center_y,
            self.direction_vector[0],
            self.direction_vector[1],
            "base",
            None,
            0
        )

        half_width = self.sizeX / 2
        half_height = self.sizeY / 2

        offsets = [
            (-half_width, -half_height),
            (half_width, -half_height),
            (-half_width, half_height),
            (half_width, half_height),
        ]

        for i, (ox, oy) in enumerate(offsets, start=1):
            rotated_x = ox * math.cos(self.angle) - oy * math.sin(self.angle)
            rotated_y = ox * math.sin(self.angle) + oy * math.cos(self.angle)

            drone_x = self.x + rotated_x
            drone_y = self.y + rotated_y

            drone = Drone(
                drone_x,
                drone_y,
                boat_center_x,
                boat_center_y,
                self.direction_vector[0],
                self.direction_vector[1],
                "drone_aerien",
                None,
                i
            )
            self.drones.append(drone)

    def move(self):
        """Move boat according to its direction vector and update attached drones."""

        if (not self.detached):
            self.x += self.direction_vector[0] * self.speed
            self.y += self.direction_vector[1] * self.speed

        half_width = self.sizeX / 2
        half_height = self.sizeY / 2

        offsets = [
            (-half_width, -half_height),
            (half_width, -half_height),
            (-half_width, half_height),
            (half_width, half_height),
        ]

        self.base.x = self.x
        self.base.y = self.y

        for drone, (ox, oy) in zip(self.drones, offsets):
            if not self.detached:
                rotated_x = ox * math.cos(self.angle) - oy * math.sin(self.angle)
                rotated_y = ox * math.sin(self.angle) + oy * math.cos(self.angle)
                drone.x = self.x + rotated_x
                drone.y = self.y + rotated_y
                drone.spawn_x = self.base.x
                drone.spawn_y = self.base.y

    def create_man_overboard(self):
        """Randomly create a man overboard once per journey."""
        search_length = math.hypot(constant.LARGEUR_SIMULATION, constant.HAUTEUR_SIMULATION)
        search_angle = math.radians(25)

        left_angle = self.angle + math.pi - search_angle
        right_angle = self.angle + math.pi + search_angle

        left_x = self.x + math.cos(left_angle) * search_length
        left_y = self.y + math.sin(left_angle) * search_length
        right_x = self.x + math.cos(right_angle) * search_length
        right_y = self.y + math.sin(right_angle) * search_length
        cone_points = [
            (int(self.x), int(self.y)),
            (int(left_x), int(left_y)),
            (int(right_x), int(right_y))
        ]
        self.cone = cone_points
        if not self.has_dropped_man:
            self.has_dropped_man = True
            drop_distance = 30
            drop_x = self.x - self.direction_vector[0] * drop_distance
            drop_y = self.y - self.direction_vector[1] * drop_distance
            self.man_overboard = HommeALaMer(drop_x, drop_y)
            return self.man_overboard
        return None

    def send_drones(self):
        self.detached = True
        self.start_cone = (self.x, self.y)

    def display(self, screen):
        """Draw the boat, its base, its drones, and the man overboard if any."""
        boat_surface = pygame.Surface((self.sizeX, self.sizeY), pygame.SRCALPHA)
        pygame.draw.rect(boat_surface, self.color, (0, 0, self.sizeX, self.sizeY))

        rotated_surface = pygame.transform.rotate(boat_surface, -math.degrees(self.angle))
        rect = rotated_surface.get_rect(center=(self.x, self.y))
        screen.blit(rotated_surface, rect.topleft)

        pygame.draw.circle(
            screen,
            (0, 255, 0),
            (int(self.base.x), int(self.base.y)),
            6
        )
        pygame.draw.circle(
            screen,
            (0, 180, 0),
            (int(self.base.x), int(self.base.y)),
            3
        )

        for drone in self.drones:
            pygame.draw.circle(
                screen,
                (0, 100, 255),
                (int(drone.x), int(drone.y)),
                5
            )
            pygame.draw.circle(
                screen,
                (0, 50, 180),
                (int(drone.x), int(drone.y)),
                2
            )

        if self.has_dropped_man and self.man_overboard and self.man_found:
            mx = self.man_overboard.x
            my = self.man_overboard.y

            pygame.draw.circle(screen, (255, 0, 0), (int(mx), int(my)), 6)
            pygame.draw.circle(screen, (255, 220, 200), (int(mx), int(my)), 3)

            for r in (10, 16):
                pygame.draw.circle(screen, (100, 150, 255), (int(mx), int(my)), r, 1)