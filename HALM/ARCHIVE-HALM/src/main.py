
import pygame
import random
import math
import sys
import time
import json
import os
from datetime import datetime
from utils import constant
from function.Logger  import Logger
from function.Simulation import Simulation
# Initialisation de Pygame
pygame.init()

def main():
    global  afficher_cercles_communication
    ecran = pygame.display.set_mode((constant.LARGEUR, constant.HAUTEUR))
    pygame.display.set_caption("Simulation de Drones - Recherche de l'Homme à la mer")
    horloge = pygame.time.Clock()
    
    nb_drones_surface = 0
    nb_drones_aerien = 10
    spawn_x = constant.LARGEUR_SIMULATION/2
    spawn_y = constant.HAUTEUR_SIMULATION/2
    pourcentage_zone_brouillee = 10 
    mode = sys.argv[1] if len(sys.argv) > 1 else "classic"
    
    logger = Logger()
    simulation = Simulation(nb_drones_surface, nb_drones_aerien, spawn_x, spawn_y, logger, pourcentage_zone_brouillee, mode)
    afficher_cercles_communication = True
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                simulation.temps_fin = time.time()
                logger.save_logs()
                simulation.sauvegarder_statistiques()
                pygame.quit()
                sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                simulation.handleClick(event.pos[0], event.pos[1] - constant.HAUTEUR_ENTETE)
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    logger = Logger()
                    simulation = Simulation(nb_drones_surface, nb_drones_aerien, spawn_x, spawn_y, logger, pourcentage_zone_brouillee)

                elif event.key == pygame.K_1:
                    if simulation.nb_drones_surface < 30:
                        nb_drones_surface += 1
                        nouvelle_creature = simulation.ajouter_creature("drone_de_surface")
                        
                        if logger:
                            logger.log_event("creature_added", {
                                "id": nouvelle_creature.creature_id, "type": "drone_de_surface",
                                "total_count": nb_drones_surface, "position": [spawn_x, spawn_y]
                            })
                
                elif event.key == pygame.K_2:
                    if simulation.nb_drones_aerien < 30:
                        nb_drones_aerien += 1
                        nouvelle_creature = simulation.ajouter_creature("drone_aerien")
                        
                        if logger:
                            logger.log_event("creature_added", {
                                "id": nouvelle_creature.creature_id, "type": "drone_aerien",
                                "total_count": nb_drones_aerien, "position": [spawn_x, spawn_y]
                            })
                
                elif event.key == pygame.K_q:
                    if simulation.nb_drones_surface > 0:
                        if simulation.retirer_creature("drone_de_surface"):
                            nb_drones_surface -= 1
                            if logger:
                                logger.log_event("creature_removed", {
                                    "type": "drone_de_surface", "total_count": nb_drones_surface
                                })
                
                elif event.key == pygame.K_w:
                    if simulation.nb_drones_aerien > 0:
                        if simulation.retirer_creature("drone_aerien"):
                            nb_drones_aerien -= 1
                            if logger:
                                logger.log_event("creature_removed", {
                                    "type": "drone_aerien", "total_count": nb_drones_aerien
                                })

                elif event.key == pygame.K_b:
                    simulation.spawn_boat()
                
                elif event.key == pygame.K_SPACE:
                    constant.en_pause = not constant.en_pause
                    if logger:
                        logger.log_event("pause_toggled", {"paused": constant.en_pause})
                
                elif event.key == pygame.K_c:
                    afficher_cercles_communication = not afficher_cercles_communication
                
                elif event.key == pygame.K_s:
                    simulation.temps_fin = time.time()
                    fichier = simulation.sauvegarder_statistiques()
                    if fichier:
                        print(f"Statistiques sauvegardées: {fichier}")
                
                elif event.key == pygame.K_l:
                    fichier_log = logger.save_logs()
                    if fichier_log:
                        print(f"Logs sauvegardés: {fichier_log}")

        if not constant.en_pause and not simulation.pause_automatique:
            simulation.mettre_a_jour()
        elif mode == "boat":
            simulation.mettre_a_jour()
        
        simulation.dessiner(ecran, afficher_cercles_communication)
        
        if constant.en_pause:
            font = pygame.font.Font(None, 72)
            text = font.render("PAUSE", True, constant.ROUGE)
            ecran.blit(text, (constant.LARGEUR_SIMULATION // 2 - 80, constant.HAUTEUR // 2 - 36))
        
        pygame.display.flip()
        horloge.tick(constant.FPS)

if __name__ == "__main__":
    main()