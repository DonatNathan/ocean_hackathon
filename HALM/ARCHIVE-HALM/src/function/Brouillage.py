
import pygame
from utils import constant

class Brouillage:
    def __init__(self, x, y, largeur, hauteur):
        self.x = x
        self.y = y
        self.largeur = largeur
        self.hauteur = hauteur
        self.rect = pygame.Rect(x, y, largeur, hauteur)
    
    def dessiner(self, ecran_simulation):
        pygame.draw.rect(ecran_simulation, constant.VIOLET, self.rect)

