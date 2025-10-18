import pygame
import random
import math
from utils import constant
from .Drone import Drone


class Boat:
    def __init__(self, speed=2):
        """
        Boat that moves across the map in a random direction and can drop a man overboard.
        """

        # Randomize direction vector
        angle = random.uniform(-math.pi / 6, math.pi / 6)  # small tilt up or down

        # Randomly start from left or right side
        if random.choice(["left", "right"]) == "left":
            self.x = -40
            self.direction_vector = (math.cos(angle), math.sin(angle))
        else:
            self.x = constant.LARGEUR_SIMULATION + 40
            # Flip direction horizontally
            self.direction_vector = (-math.cos(angle), math.sin(angle))
            angle = math.pi - angle

        # Random Y spawn (avoid edges)
        self.y = random.randint(100, constant.HAUTEUR_SIMULATION - 100)

        self.speed = speed
        self.sizeX = 40
        self.sizeY = 20
        self.color = constant.NOIR

        # "Man overboard" control
        self.has_dropped_man = False
        self.man_overboard_pos = None
        self.detached = False

        # Store current travel angle (for rotation / direction)
        self.angle = angle
        # Assuming you already have: boat, Drone class, vx, vy, drone_type, logger, etc.

        self.drones = []

        # 1️⃣ Create the base drone at the boat center
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
            0  # creature_id or any ID system you use
        )

        # 2️⃣ Create the 4 corner drones around the boat
        half_width = self.sizeX / 2
        half_height = self.sizeY / 2

        # Define the four corner offsets (before rotation)
        offsets = [
            (-half_width, -half_height),  # back-left
            (half_width, -half_height),   # back-right
            (-half_width, half_height),   # front-left
            (half_width, half_height),    # front-right
        ]

        for i, (ox, oy) in enumerate(offsets, start=1):
            # Rotate offset by boat’s angle to match its heading
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


    # ------------------------------------------------------------ #
    def move(self):
        """Move boat according to its direction vector and update attached drones."""
        # --- Move the boat ---

        if (not self.detached):
            self.x += self.direction_vector[0] * self.speed
            self.y += self.direction_vector[1] * self.speed

        # --- Update base and drone positions relative to boat ---
        half_width = self.sizeX / 2
        half_height = self.sizeY / 2

        # Define the 4 relative offsets again (before rotation)
        offsets = [
            (-half_width, -half_height),  # back-left
            (half_width, -half_height),   # back-right
            (-half_width, half_height),   # front-left
            (half_width, half_height),    # front-right
        ]

        # Update the base position (center of the boat)
        self.base.x = self.x
        self.base.y = self.y

        # Update corner drones positions (respect rotation)
        for drone, (ox, oy) in zip(self.drones, offsets):
            if not self.detached:
                rotated_x = ox * math.cos(self.angle) - oy * math.sin(self.angle)
                rotated_y = ox * math.sin(self.angle) + oy * math.cos(self.angle)
                drone.x = self.x + rotated_x
                drone.y = self.y + rotated_y

        # --- Handle out-of-bounds and respawn ---
        if (
            self.x < -self.sizeX
            or self.x > constant.LARGEUR_SIMULATION + self.sizeX
            or self.y < -self.sizeY
            or self.y > constant.HAUTEUR_SIMULATION + self.sizeY
        ):
            self.respawn()


    # ------------------------------------------------------------ #
    def respawn(self):
        """Reset boat to the opposite side with a new random direction and Y."""
        self.__init__(speed=self.speed)

    # ------------------------------------------------------------ #
    def create_man_overboard(self):
        """Randomly create a man overboard once per journey."""
        if not self.has_dropped_man:
            self.has_dropped_man = True
            # Drop man slightly behind the boat
            drop_distance = 30
            drop_x = self.x - self.direction_vector[0] * drop_distance
            drop_y = self.y - self.direction_vector[1] * drop_distance
            self.man_overboard_pos = (drop_x, drop_y)
            print(f"[EVENT] Man overboard at {self.man_overboard_pos}")
            self.send_drones()
            return self.man_overboard_pos
        return None

    def send_drones(self):
        self.detached = True

    # ------------------------------------------------------------ #
    def display(self, screen):
        """Draw the boat, its base, its drones, and the man overboard if any."""
        # --- draw the boat ---
        boat_surface = pygame.Surface((self.sizeX, self.sizeY), pygame.SRCALPHA)
        pygame.draw.rect(boat_surface, self.color, (0, 0, self.sizeX, self.sizeY))

        # Rotate and draw the boat
        rotated_surface = pygame.transform.rotate(boat_surface, -math.degrees(self.angle))
        rect = rotated_surface.get_rect(center=(self.x, self.y))
        screen.blit(rotated_surface, rect.topleft)

        # --- draw base drone (center) ---
        pygame.draw.circle(
            screen,
            (0, 255, 0),  # bright green for visibility
            (int(self.base.x), int(self.base.y)),
            6
        )
        pygame.draw.circle(
            screen,
            (0, 180, 0),
            (int(self.base.x), int(self.base.y)),
            3
        )

        # --- draw 4 corner drones ---
        for drone in self.drones:
            pygame.draw.circle(
                screen,
                (0, 100, 255),  # blue drones
                (int(drone.x), int(drone.y)),
                5
            )
            pygame.draw.circle(
                screen,
                (0, 50, 180),
                (int(drone.x), int(drone.y)),
                2
            )

        # --- draw the man overboard, if present ---
        if self.has_dropped_man and self.man_overboard_pos:
            mx, my = self.man_overboard_pos

            # Red life jacket + skin center
            pygame.draw.circle(screen, (255, 0, 0), (int(mx), int(my)), 6)
            pygame.draw.circle(screen, (255, 220, 200), (int(mx), int(my)), 3)

            # Optional: small waves around the person
            for r in (10, 16):
                pygame.draw.circle(screen, (100, 150, 255), (int(mx), int(my)), r, 1)
