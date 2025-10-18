
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
        surface_transparente = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(surface_transparente, (*constant.GRIS_CLAIR, 100), (0, 0, self.rect.width, self.rect.height), border_radius=30)
        pygame.draw.rect(surface_transparente, constant.GRIS_CLAIR, (0, 0, self.rect.width, self.rect.height),width=2, border_radius=30)
        ecran_simulation.blit(surface_transparente, (self.rect.x, self.rect.y))