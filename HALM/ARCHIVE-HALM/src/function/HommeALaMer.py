
import pygame
import math
from utils import constant

pygame.init()

class HommeALaMer:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.taille = 15
        self.decouvert = False
    
    def dessiner(self, ecran_simulation):
        if self.decouvert:
            pygame.draw.circle(ecran_simulation, constant.JAUNE, (int(self.x), int(self.y)), self.taille)
            for i in range(8):
                angle = i * math.pi / 4
                end_x = self.x + math.cos(angle) * 25
                end_y = self.y + math.sin(angle) * 25
                pygame.draw.line(ecran_simulation, constant.JAUNE, (self.x, self.y), (end_x, end_y), 2)
