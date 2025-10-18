
import pygame
from utils import constant

class Obstacle:
    def __init__(self, x, y, largeur, hauteur):
        self.x = x
        self.y = y
        self.largeur = largeur
        self.hauteur = hauteur
        self.rect = pygame.Rect(x, y, largeur, hauteur)
    
    def dessiner(self, ecran_simulation):
        pygame.draw.rect(ecran_simulation, constant.MARRON, self.rect)