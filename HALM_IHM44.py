import pygame
import random
import math
import sys
import time
import json
import os
from datetime import datetime

# Initialisation de Pygame
pygame.init()

# Configuration
LARGEUR = 1200
HAUTEUR = 900
FPS = 60
FACTEUR_ACCELERATION = 1

# Couleurs
NOIR = (0, 0, 0)
BLANC = (255, 255, 255)
ROUGE = (255, 0, 0)
VERT = (0, 255, 0)
BLEU = (0, 0, 255)
MARRON = (139, 69, 19)
JAUNE = (255, 255, 0)
GRIS = (128, 128, 128)
GRIS_CLAIR = (200, 200, 200)
ORANGE = (255, 165, 0)
CYAN = (0, 255, 255)
VIOLET = (255, 0, 255)
ROUGE_CLAIR = (255, 100, 100)
BLEU_CLAIR = (100, 100, 255)

# Dimensions de la nouvelle interface
HAUTEUR_ENTETE = 60
LARGEUR_BARRE_LATERALE = 300
LARGEUR_SIMULATION = LARGEUR - LARGEUR_BARRE_LATERALE
HAUTEUR_SIMULATION = HAUTEUR - HAUTEUR_ENTETE
COULEUR_UI_FOND = (200, 230, 255) # Bleu clair
COULEUR_UI_CONTOUR = (150, 150, 150) # Gris

class Logger:
    def __init__(self):
        self.logs = []
        self.frame_count = 0
        self.start_time = time.time()
        
    def log_event(self, event_type, data):
        """Enregistre un événement avec timestamp"""
        timestamp = time.time() - self.start_time
        log_entry = {
            "frame": self.frame_count,
            "timestamp": timestamp,
            "event_type": event_type,
            "data": data
        }
        self.logs.append(log_entry)
    
    def log_frame(self, creatures_states, simulation_state):
        """Enregistre l'état complet d'une frame"""
        frame_data = {
            "creatures": [],
            "simulation": simulation_state
        }
        
        for i, creature in enumerate(creatures_states):
            creature_data = {
                "id": i,
                "x": creature.x,
                "y": creature.y,
                "type": creature.type_creature,
                "a_trouve_homme_mer": creature.a_trouve_homme_mer,
                "en_repos": creature.en_repos,
                "retour_spawn": creature.retour_spawn,
                "epuise": creature.epuise,
                "angle": creature.angle,
                "couleur": creature.couleur,
                "zones_explorees_count": len(creature.zone_exploree),
                "communications_reçues": len(creature.communications_reçues),
                "communications_envoyees": creature.communications_envoyees
            }
            frame_data["creatures"].append(creature_data)
        
        self.log_event("frame_state", frame_data)
        self.frame_count += 1
    
    def save_logs(self, filename=None):
        """Sauvegarde les logs dans un fichier"""
        if not os.path.exists("logs"):
            os.makedirs("logs")
        
        if filename is None:
            filename = f"simulation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = os.path.join("logs", filename)
        
        log_data = {
            "metadata": {
                "total_frames": self.frame_count,
                "duration": time.time() - self.start_time,
                "fps": FPS,
                "screen_size": [LARGEUR_SIMULATION, HAUTEUR_SIMULATION],
                "created_at": datetime.now().isoformat()
            },
            "events": self.logs
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            print(f"Logs sauvegardés dans: {filepath}")
            return filepath
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des logs: {e}")
            return None

class Drone:
    def __init__(self, x, y, spawn_x, spawn_y, type_creature="drone_de_surface", logger=None, creature_id=0):
        self.x = x
        self.y = y
        self.spawn_x = spawn_x
        self.spawn_y = spawn_y
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(-1, 1)
        self.type_creature = type_creature
        self.creature_id = creature_id
        self.zone_exploree = set()
        self.a_trouve_homme_mer = False
        self.angle = random.uniform(0, 2 * math.pi)
        self.temps_changement_direction = 0
        self.logger = logger
        
        # Système de communication
        self.rayon_communication = 50
        self.communications_reçues = set()
        self.communications_envoyees = 0
        self.communications_echouees = 0
        self.derniere_communication = {}
        self.cooldown_communication = 1.0
        self.tentatives_communication = 0
        
        # États de repos
        self.temps_depuis_spawn = 0
        self.en_repos = False
        self.temps_repos_debut = 0
        self.retour_spawn = False
        self.epuise = False
        
        # Statistiques de trajet
        self.trajets_complets = 0
        self.temps_trajets = []
        self.temps_debut_trajet = time.time()
        self.distance_parcourue = 0
        self.derniere_position = (x, y)
        self.zones_decouvertes_uniques = set()
        self.temps_premiere_decouverte_homme_mer = None
        
        # Caractéristiques selon le type
        if type_creature == "drone_de_surface":
            self.vitesse = FACTEUR_ACCELERATION * 13.8 / FPS
            self.couleur = ROUGE
            self.couleur_trouve = ROUGE_CLAIR
            self.taille = 3
            self.zone_decouverte = 15
            self.temps_avant_repos = 40
            self.duree_repos = 20
            self.rayon_communication = 50
        elif type_creature == "drone_aerien":
            self.vitesse = FACTEUR_ACCELERATION * 27.7 / FPS
            self.couleur = BLEU
            self.couleur_trouve = BLEU_CLAIR
            self.taille = 4
            self.zone_decouverte = 30
            self.temps_avant_repos = 20
            self.duree_repos = 15
            self.rayon_communication = 80
        
        # Log de création
        if self.logger:
            self.logger.log_event("creature_created", {
                "id": creature_id,
                "type": type_creature,
                "spawn_position": [spawn_x, spawn_y],
                "initial_position": [x, y],
                "communication_radius": self.rayon_communication,
                "characteristics": {
                    "vitesse": self.vitesse,
                    "zone_decouverte": self.zone_decouverte,
                    "temps_avant_repos": self.temps_avant_repos,
                    "duree_repos": self.duree_repos
                }
            })
    
    def est_dans_zone_brouillage(self, brouillages):
        """Vérifie si le drone se trouve dans une zone de brouillage"""
        for brouillage in brouillages:
            if brouillage.rect.collidepoint(self.x, self.y):
                return True
        return False

    def communiquer_avec(self, autre_creature, brouillages, simulation):
        """Établit une communication avec une autre créature"""
        self.tentatives_communication += 1
        
        # Vérifier si l'un des drones est dans une zone de brouillage
        if self.est_dans_zone_brouillage(brouillages) or autre_creature.est_dans_zone_brouillage(brouillages):
            self.communications_echouees += 1
            if self.logger:
                self.logger.log_event("communication_failed_brouillage", {
                    "creature_1": {"id": self.creature_id, "position": [self.x, self.y]},
                    "creature_2": {"id": autre_creature.creature_id, "position": [autre_creature.x, autre_creature.y]},
                    "reason": "brouillage"
                })
            return False
        
        current_time = time.time()
        
        # Vérifier le cooldown pour éviter les communications répétées
        if autre_creature.creature_id in self.derniere_communication:
            temps_derniere = self.derniere_communication[autre_creature.creature_id]
            if current_time - temps_derniere < self.cooldown_communication:
                return False
        
        # Échanger les informations (numéros des créatures)
        self.communications_reçues.add(autre_creature.creature_id)
        autre_creature.communications_reçues.add(self.creature_id)
        
        self.communications_envoyees += 1
        autre_creature.communications_envoyees += 1
        
        # Mettre à jour le timestamp de dernière communication
        self.derniere_communication[autre_creature.creature_id] = current_time
        autre_creature.derniere_communication[self.creature_id] = current_time
        
        # Identifier les types pour éviter le double comptage
        type1 = self.type_creature
        type2 = autre_creature.type_creature

        if type1 == "drone_de_surface" and type2 == "drone_de_surface":
            simulation.comms_surface_surface += 1
        elif type1 == "drone_aerien" and type2 == "drone_aerien":
            simulation.comms_aerien_aerien += 1
        else: # Un de chaque type
            simulation.comms_surface_aerien += 1

        # Log de la communication
        if self.logger:
            distance = math.sqrt((self.x - autre_creature.x)**2 + (self.y - autre_creature.y)**2)
            self.logger.log_event("communication_established", {
                "creature_1": {
                    "id": self.creature_id,
                    "type": self.type_creature,
                    "position": [self.x, self.y]
                },
                "creature_2": {
                    "id": autre_creature.creature_id,
                    "type": autre_creature.type_creature,
                    "position": [autre_creature.x, autre_creature.y]
                },
                "distance": round(distance, 2),
                "communication_data": {
                    "creature_1_contacts": len(self.communications_reçues),
                    "creature_2_contacts": len(autre_creature.communications_reçues)
                }
            })
        
        return True
    
    def verifier_communications(self, autres_creatures, brouillages, simulation):
        """Vérifie les communications possibles avec les autres créatures"""
        communications_etablies = 0
        
        for autre in autres_creatures:
            if autre.creature_id != self.creature_id and not autre.epuise and not self.epuise:
                distance = math.sqrt((self.x - autre.x)**2 + (self.y - autre.y)**2)
                
                # Vérifier si les rayons de communication se croisent
                if distance <= (self.rayon_communication + autre.rayon_communication) / 2:
                    if self.communiquer_avec(autre, brouillages, simulation):
                        communications_etablies += 1
        
        return communications_etablies
    
    def deplacer(self, obstacles, homme_a_la_mer, autres_creatures, brouillages, simulation):
        old_state = {
            "en_repos": self.en_repos,
            "retour_spawn": self.retour_spawn,
            "epuise": self.epuise,
            "a_trouve_homme_mer": self.a_trouve_homme_mer
        }
        
        if self.epuise:
            return
        
        self.temps_depuis_spawn += 1/FPS

        if not self.en_repos:
            self.verifier_communications(autres_creatures, brouillages, simulation)
        
        if not self.en_repos and not self.retour_spawn and self.temps_depuis_spawn >= self.temps_avant_repos:
            self.retour_spawn = True
            if self.logger:
                self.logger.log_event("creature_state_change", {
                    "creature_id": self.creature_id,
                    "creature_type": self.type_creature,
                    "new_state": "retour_spawn",
                    "position": [self.x, self.y],
                    "communications_count": len(self.communications_reçues)
                })
        
        if self.retour_spawn:
            dist_spawn = math.sqrt((self.x - self.spawn_x)**2 + (self.y - self.spawn_y)**2)
            
            # Temps additionnel pour le retour (5 secondes)
            if self.temps_depuis_spawn > self.temps_avant_repos + 5 and dist_spawn > 10:
                self.epuise = True
                if self.logger:
                    self.logger.log_event("creature_exhausted", {
                        "creature_id": self.creature_id,
                        "creature_type": self.type_creature,
                        "position": [self.x, self.y],
                        "distance_from_spawn": dist_spawn
                    })
                return

            if dist_spawn < 5:
                self.en_repos = True
                self.retour_spawn = False
                self.temps_repos_debut = time.time()
                self.x = self.spawn_x
                self.y = self.spawn_y
                
                if self.logger:
                    self.logger.log_event("creature_state_change", {
                        "creature_id": self.creature_id,
                        "creature_type": self.type_creature,
                        "new_state": "en_repos",
                        "position": [self.x, self.y],
                        "communications_count": len(self.communications_reçues)
                    })
                
                if self.temps_debut_trajet:
                    duree_trajet = time.time() - self.temps_debut_trajet
                    self.temps_trajets.append(duree_trajet)
                    self.trajets_complets += 1
                    
                    if self.logger:
                        self.logger.log_event("trip_completed", {
                            "creature_id": self.creature_id,
                            "creature_type": self.type_creature,
                            "duration": duree_trajet,
                            "total_trips": self.trajets_complets,
                            "communications_during_trip": len(self.communications_reçues)
                        })
                return
            else:
                self.angle = math.atan2(self.spawn_y - self.y, self.spawn_x - self.x)
        
        elif self.en_repos:
            temps_repos_actuel = time.time() - self.temps_repos_debut
            if temps_repos_actuel >= self.duree_repos:
                self.en_repos = False
                self.temps_depuis_spawn = 0
                self.temps_debut_trajet = time.time()
                
                if self.logger:
                    self.logger.log_event("creature_state_change", {
                        "creature_id": self.creature_id,
                        "creature_type": self.type_creature,
                        "new_state": "exploration",
                        "position": [self.x, self.y],
                        "communications_count": len(self.communications_reçues)
                    })
            else:
                self.x = self.spawn_x
                self.y = self.spawn_y
                return
        
        else: # Exploration
            self.temps_changement_direction += 1
            if self.temps_changement_direction > 60:
                old_angle = self.angle
                self.angle += random.uniform(-0.5, 0.5)
                self.temps_changement_direction = 0
                
                if self.logger:
                    self.logger.log_event("direction_change", {
                        "creature_id": self.creature_id,
                        "creature_type": self.type_creature,
                        "old_angle": old_angle,
                        "new_angle": self.angle,
                        "position": [self.x, self.y]
                    })
            
            # Évitement des obstacles pour les Drones de Surface seulement
            if self.type_creature == "drone_de_surface":
                for obstacle in obstacles:
                    if obstacle.rect.collidepoint(self.x, self.y):
                        angle_evitement = math.atan2(self.y - obstacle.y, self.x - obstacle.x)
                        self.angle = angle_evitement
                        
                        if self.logger:
                            self.logger.log_event("obstacle_avoidance", {
                                "creature_id": self.creature_id,
                                "creature_type": self.type_creature,
                                "obstacle_position": [obstacle.x, obstacle.y],
                                "new_angle": self.angle,
                                "position": [self.x, self.y]
                            })
            
            if self.a_trouve_homme_mer:
                angle_homme_mer = math.atan2(homme_a_la_mer.y - self.y, homme_a_la_mer.x - self.x)
                self.angle = angle_homme_mer
        
        self.vx = math.cos(self.angle) * self.vitesse
        self.vy = math.sin(self.angle) * self.vitesse
        
        nouvelle_x = self.x + self.vx
        nouvelle_y = self.y + self.vy
        
        # Vérifier les limites de l'écran et les obstacles
        nouvelle_pos_ok = True
        if not (0 <= nouvelle_x < LARGEUR_SIMULATION and 0 <= nouvelle_y < HAUTEUR_SIMULATION):
            nouvelle_pos_ok = False
        else:
            if self.type_creature == "drone_de_surface":
                nouvelle_rect = pygame.Rect(nouvelle_x - self.taille, nouvelle_y - self.taille, self.taille * 2, self.taille * 2)
                for obstacle in obstacles:
                    if nouvelle_rect.colliderect(obstacle.rect):
                        nouvelle_pos_ok = False
                        # Recalculer l'angle d'évitement
                        angle_evitement = math.atan2(self.y - obstacle.y, self.x - obstacle.x)
                        self.angle = angle_evitement + random.uniform(-math.pi/4, math.pi/4) # Ajouter une variation
                        break
        
        if nouvelle_pos_ok:
            if not self.epuise and not self.en_repos:
                distance = math.sqrt((nouvelle_x - self.x)**2 + (nouvelle_y - self.y)**2)
                self.distance_parcourue += distance
            
            self.x = nouvelle_x
            self.y = nouvelle_y
        else:
            if not (0 <= nouvelle_x < LARGEUR_SIMULATION and 0 <= nouvelle_y < HAUTEUR_SIMULATION):
                self.angle += math.pi
            if self.logger:
                self.logger.log_event("boundary_hit", {
                    "creature_id": self.creature_id,
                    "creature_type": self.type_creature,
                    "position": [self.x, self.y],
                    "new_angle": self.angle
                })
        
        if not self.epuise and not self.en_repos:
            dist_homme_mer = math.sqrt((self.x - homme_a_la_mer.x)**2 + (self.y - homme_a_la_mer.y)**2)
            if dist_homme_mer < self.zone_decouverte and not self.a_trouve_homme_mer:
                self.a_trouve_homme_mer = True
                self.couleur = self.couleur_trouve
                self.temps_premiere_decouverte_homme_mer = time.time()
                
                if self.logger:
                    self.logger.log_event("homme_a_la_mer_discovered", {
                        "creature_id": self.creature_id,
                        "creature_type": self.type_creature,
                        "position": [self.x, self.y],
                        "homme_a_la_mer_position": [homme_a_la_mer.x, homme_a_la_mer.y],
                        "distance": dist_homme_mer,
                        "communications_at_discovery": len(self.communications_reçues)
                    })
            
            rayon_exploration = self.zone_decouverte // 10
            nouvelles_zones = set()
            for dx in range(-rayon_exploration, rayon_exploration + 1):
                for dy in range(-rayon_exploration, rayon_exploration + 1):
                    if dx*dx + dy*dy <= rayon_exploration*rayon_exploration:
                        zone_x = int((self.x + dx*10) // 10)
                        zone_y = int((self.y + dy*10) // 10)
                        if 0 <= zone_x < LARGEUR_SIMULATION//10 and 0 <= zone_y < HAUTEUR_SIMULATION//10:
                            zone = (zone_x, zone_y)
                            if zone not in self.zone_exploree:
                                nouvelles_zones.add(zone)
                            self.zone_exploree.add(zone)
            
            if nouvelles_zones and self.logger:
                self.logger.log_event("zones_explored", {
                    "creature_id": self.creature_id,
                    "creature_type": self.type_creature,
                    "new_zones_count": len(nouvelles_zones),
                    "total_zones": len(self.zone_exploree),
                    "position": [self.x, self.y]
                })
            
            self.zones_decouvertes_uniques.update(nouvelles_zones)
    
    def dessiner(self, ecran_simulation, afficher_cercles_communication, brouillages):
        if self.epuise:
            taille_croix = 6
            pygame.draw.line(ecran_simulation, NOIR, 
                           (self.x - taille_croix, self.y - taille_croix),
                           (self.x + taille_croix, self.y + taille_croix), 3)
            pygame.draw.line(ecran_simulation, NOIR, 
                           (self.x - taille_croix, self.y + taille_croix),
                           (self.x + taille_croix, self.y - taille_croix), 3)
        else:
            if afficher_cercles_communication and not self.est_dans_zone_brouillage(brouillages):
                surface_communication = pygame.Surface((self.rayon_communication * 2, self.rayon_communication * 2), pygame.SRCALPHA)
                pygame.draw.circle(surface_communication, (*CYAN, 30), (self.rayon_communication, self.rayon_communication), self.rayon_communication)
                ecran_simulation.blit(surface_communication, (self.x - self.rayon_communication, self.y - self.rayon_communication))
            
            if self.a_trouve_homme_mer:
                pygame.draw.circle(ecran_simulation, (*self.couleur_trouve, 50), (int(self.x), int(self.y)), self.zone_decouverte, 2)
            
            if self.type_creature == "drone_aerien":
                points = [
                    (self.x, self.y - self.taille),
                    (self.x - self.taille, self.y + self.taille),
                    (self.x + self.taille, self.y + self.taille)
                ]
                pygame.draw.polygon(ecran_simulation, self.couleur, points)
            else:
                pygame.draw.circle(ecran_simulation, self.couleur, (int(self.x), int(self.y)), self.taille)
            
            font_id = pygame.font.Font(None, 16)
            text_id = font_id.render(str(self.creature_id), True, NOIR)
            ecran_simulation.blit(text_id, (self.x - 5, self.y - 15))
            
            if self.en_repos:
                pygame.draw.circle(ecran_simulation, VERT, (int(self.x), int(self.y - 10)), 2)
            elif self.retour_spawn:
                pygame.draw.circle(ecran_simulation, ORANGE, (int(self.x), int(self.y - 10)), 2)
            
            if len(self.communications_reçues) > 0:
                font_com = pygame.font.Font(None, 14)
                text_com = font_com.render(f"C:{len(self.communications_reçues)}", True, VIOLET)
                ecran_simulation.blit(text_com, (self.x + 8, self.y + 8))

class Obstacle:
    def __init__(self, x, y, largeur, hauteur):
        self.x = x
        self.y = y
        self.largeur = largeur
        self.hauteur = hauteur
        self.rect = pygame.Rect(x, y, largeur, hauteur)
    
    def dessiner(self, ecran_simulation):
        pygame.draw.rect(ecran_simulation, MARRON, self.rect)


class Brouillage:
    def __init__(self, x, y, largeur, hauteur):
        self.x = x
        self.y = y
        self.largeur = largeur
        self.hauteur = hauteur
        self.rect = pygame.Rect(x, y, largeur, hauteur)
    
    def dessiner(self, ecran_simulation):
        pygame.draw.rect(ecran_simulation, VIOLET, self.rect)

class HommeALaMer:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.taille = 15
        self.decouvert = False
    
    def dessiner(self, ecran_simulation):
        if self.decouvert:
            pygame.draw.circle(ecran_simulation, JAUNE, (int(self.x), int(self.y)), self.taille)
            for i in range(8):
                angle = i * math.pi / 4
                end_x = self.x + math.cos(angle) * 25
                end_y = self.y + math.sin(angle) * 25
                pygame.draw.line(ecran_simulation, JAUNE, (self.x, self.y), (end_x, end_y), 2)

class Simulation:
    def __init__(self, nb_drones_surface=8, nb_drones_aerien=7, spawn_x=100, spawn_y=100, logger=None, pourcentage_brouillage=10):
        self.nb_drones_surface = nb_drones_surface
        self.nb_drones_aerien = nb_drones_aerien
        self.spawn_x = spawn_x
        self.spawn_y = spawn_y
        self.pourcentage_brouillage = pourcentage_brouillage
        self.pourcentage_brouillage_reel = 0 # Sera calculé dans generer_monde
        self.creatures = []
        self.obstacles = []
        self.brouillages = []
        self.homme_a_la_mer = None
        self.zones_explorees = set()
        self.homme_a_la_mer_decouvert = False
        self.temps_decouverte = 0
        self.logger = logger
        self.next_creature_id = 0
        self.temps_debut = time.time()
        self.temps_fin = None
        self.simulation_reussie = False
        self.premiere_decouverte_homme_mer = None
        self.qui_a_trouve_homme_mer = None
        self.pause_automatique = False
        
        # Nouveaux compteurs de communication
        self.comms_surface_surface = 0
        self.comms_surface_aerien = 0
        self.comms_aerien_aerien = 0
        
        self.generer_monde()
        
        if self.logger:
            self.logger.log_event("simulation_started", {
                "configuration": {
                    "nb_drones_surface": nb_drones_surface,
                    "nb_drones_aerien": nb_drones_aerien,
                    "spawn_position": [spawn_x, spawn_y],
                    "screen_size": [LARGEUR_SIMULATION, HAUTEUR_SIMULATION],
                    "communication_enabled": True,
                    "target_jamming_percentage": self.pourcentage_brouillage,
                }
            })
    
    def get_next_creature_id(self):
        current_id = self.next_creature_id
        self.next_creature_id += 1
        return current_id
    
    def sauvegarder_statistiques(self):
        if not os.path.exists("statistiques"):
            os.makedirs("statistiques")
        
        duree_simulation = (self.temps_fin or time.time()) - self.temps_debut
        
        stats_drones_surface = self._calculer_stats_type("drone_de_surface")
        stats_drones_aerien = self._calculer_stats_type("drone_aerien")

        # Calculer le total des communications à partir des compteurs détaillés
        communications_reussies_total = self.comms_surface_surface + self.comms_surface_aerien + self.comms_aerien_aerien
        
        communications_echouees = sum(c.communications_echouees for c in self.creatures)
        creatures_communicantes = sum(1 for c in self.creatures if len(c.communications_reçues) > 0)
        
        creatures_epuisees = sum(1 for c in self.creatures if c.epuise)
        creatures_actives = len(self.creatures) - creatures_epuisees
        zones_totales_explorees = len(self.zones_explorees)
        surface_carte = (LARGEUR_SIMULATION // 10) * (HAUTEUR_SIMULATION // 10)
        pourcentage_exploration = (zones_totales_explorees / surface_carte) * 100
        
        temps_decouverte_homme_mer = None
        if self.premiere_decouverte_homme_mer:
            temps_decouverte_homme_mer = self.premiere_decouverte_homme_mer - self.temps_debut
        
        statistiques = {
            "timestamp": datetime.now().isoformat(),
            "duree_simulation_secondes": round(duree_simulation, 2),
            "simulation_reussie": self.simulation_reussie,
            "temps_decouverte_homme_mer": round(temps_decouverte_homme_mer, 2) if temps_decouverte_homme_mer else None,
            "qui_a_trouve_homme_mer": self.qui_a_trouve_homme_mer,
            
            "configuration": {
                "nombre_drones_surface": self.nb_drones_surface,
                "nombre_drones_aerien": self.nb_drones_aerien,
                "spawn_position": [self.spawn_x, self.spawn_y],
                "homme_a_la_mer_position": [self.homme_a_la_mer.x, self.homme_a_la_mer.y],
                "nombre_obstacles": len(self.obstacles),
                "nombre_brouillages": len(self.brouillages),
                "pourcentage_brouillage_cible": self.pourcentage_brouillage,
                "pourcentage_brouillage_reel": round(self.pourcentage_brouillage_reel, 2),
            },
            
            "resultats_globaux": {
                "creatures_totales": len(self.creatures),
                "creatures_actives": creatures_actives,
                "creatures_epuisees": creatures_epuisees,
                "taux_epuisement": round((creatures_epuisees / len(self.creatures)) * 100, 2) if len(self.creatures) > 0 else 0,
                "zones_explorees": zones_totales_explorees,
                "pourcentage_exploration": round(pourcentage_exploration, 2)
            },
            
            "statistiques_communication": {
                "tentatives_totales": sum(c.tentatives_communication for c in self.creatures),
                "communications_reussies": communications_reussies_total,
                "communications_echouees": communications_echouees,
                "repartition_communications": {
                    "surface_avec_surface": self.comms_surface_surface,
                    "surface_avec_aerien": self.comms_surface_aerien,
                    "aerien_avec_aerien": self.comms_aerien_aerien
                },
                "taux_reussite_communication": round((communications_reussies_total / (sum(c.tentatives_communication for c in self.creatures))) * 100, 2) if (sum(c.tentatives_communication for c in self.creatures)) > 0 else 0,
                "communications_par_drone": round(communications_reussies_total / len(self.creatures), 2) if len(self.creatures) > 0 else 0,
                "drones_communicants": creatures_communicantes,
                "taux_drones_communicants": round((creatures_communicantes / len(self.creatures)) * 100, 2) if len(self.creatures) > 0 else 0
            },
            
            "statistiques_drones_surface": stats_drones_surface,
            "statistiques_drones_aerien": stats_drones_aerien,
            
            "comparaison": {
                "efficacite_drones_surface": round(stats_drones_surface["zones_decouverte_par_creature"], 2),
                "efficacite_drones_aerien": round(stats_drones_aerien["zones_decouverte_par_creature"], 2),
                "temps_decouverte_moyen_surface": round(stats_drones_surface["temps_moyen_decouverte_homme_mer"], 2) if stats_drones_surface["temps_moyen_decouverte_homme_mer"] else None,
                "temps_decouverte_moyen_aerien": round(stats_drones_aerien["temps_moyen_decouverte_homme_mer"], 2) if stats_drones_aerien["temps_moyen_decouverte_homme_mer"] else None,
                "taux_reussite_com_surface": round(stats_drones_surface["taux_reussite_communication"], 2),
                "taux_reussite_com_aerien": round(stats_drones_aerien["taux_reussite_communication"], 2)
            }
        }
        
        nom_fichier = f"simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        chemin_fichier = os.path.join("statistiques", nom_fichier)
        
        try:
            with open(chemin_fichier, 'w', encoding='utf-8') as f:
                json.dump(statistiques, f, indent=2, ensure_ascii=False)
            print(f"Statistiques sauvegardées dans: {chemin_fichier}")
            return chemin_fichier
        except Exception as e:
            print(f"Erreur lors de la sauvegarde: {e}")
            return None
    

    def _calculer_stats_type(self, type_creature):
        creatures_type = [c for c in self.creatures if c.type_creature == type_creature]
        
        if not creatures_type:
            return {
                "nombre": 0, "epuisees": 0, "trajets_complets_total": 0, "temps_trajet_moyen": 0,
                "distance_moyenne": 0, "zones_decouvertes_total": 0, "zones_decouverte_par_creature": 0,
                "vitesse_exploration": 0, "ont_trouve_homme_mer": 0, "temps_moyen_decouverte_homme_mer": None,
                "communications_reussies": 0, "communications_par_creature": 0, "tentatives_totales": 0,
                "communications_echouees": 0, "taux_reussite_communication": 0
            }
        
        epuisees = sum(1 for c in creatures_type if c.epuise)
        trajets_totaux = sum(c.trajets_complets for c in creatures_type)
        
        tous_temps_trajets = [t for c in creatures_type for t in c.temps_trajets]
        temps_trajet_moyen = sum(tous_temps_trajets) / len(tous_temps_trajets) if tous_temps_trajets else 0
        
        distance_moyenne = sum(c.distance_parcourue for c in creatures_type) / len(creatures_type)
        
        zones_decouvertes_total = sum(len(c.zones_decouvertes_uniques) for c in creatures_type)
        zones_decouverte_par_creature = zones_decouvertes_total / len(creatures_type)
        
        duree_simulation = (self.temps_fin or time.time()) - self.temps_debut
        vitesse_exploration = zones_decouvertes_total / duree_simulation if duree_simulation > 0 else 0
        
        ont_trouve_homme_mer = sum(1 for c in creatures_type if c.a_trouve_homme_mer)
        temps_decouverte_totaux = [c.temps_premiere_decouverte_homme_mer - self.temps_debut for c in creatures_type if c.a_trouve_homme_mer]
        temps_moyen_decouverte = sum(temps_decouverte_totaux) / len(temps_decouverte_totaux) if temps_decouverte_totaux else None
        
        communications_reussies_type = 0
        if type_creature == "drone_de_surface":
            communications_reussies_type = (2 * self.comms_surface_surface) + self.comms_surface_aerien
        else:
            communications_reussies_type = (2 * self.comms_aerien_aerien) + self.comms_surface_aerien
        
        communications_par_creature = communications_reussies_type / len(creatures_type)
        
        tentatives_totales = sum(c.tentatives_communication for c in creatures_type)
        communications_echouees = sum(c.communications_echouees for c in creatures_type)
        
        taux_reussite_communication = (communications_reussies_type / tentatives_totales) * 100 if tentatives_totales > 0 else 0
        
        return {
            "nombre": len(creatures_type),
            "epuisees": epuisees,
            "taux_epuisement": round((epuisees / len(creatures_type)) * 100, 2) if len(creatures_type) > 0 else 0,
            "trajets_complets_total": trajets_totaux,
            "trajets_par_creature": round(trajets_totaux / len(creatures_type), 2) if len(creatures_type) > 0 else 0,
            "temps_trajet_moyen": round(temps_trajet_moyen, 2),
            "distance_moyenne": round(distance_moyenne, 2),
            "zones_decouvertes_total": zones_decouvertes_total,
            "zones_decouverte_par_creature": round(zones_decouverte_par_creature, 2),
            "vitesse_exploration": round(vitesse_exploration, 2),
            "ont_trouve_homme_mer": ont_trouve_homme_mer,
            "taux_reussite_homme_mer": round((ont_trouve_homme_mer / len(creatures_type)) * 100, 2) if len(creatures_type) > 0 else 0,
            "temps_moyen_decouverte_homme_mer": round(temps_moyen_decouverte, 2) if temps_moyen_decouverte else None,
            "communications_reussies (liens)": communications_reussies_type,
            "communications_par_creature": round(communications_par_creature, 2),
            "tentatives_totales": tentatives_totales,
            "communications_echouees": communications_echouees,
            "taux_reussite_communication": round(taux_reussite_communication, 2)
        }

    def generer_monde(self):
        for i in range(self.nb_drones_surface):
            creature_id = self.get_next_creature_id()
            self.creatures.append(Drone(self.spawn_x, self.spawn_y, self.spawn_x, self.spawn_y, "drone_de_surface", self.logger, creature_id))
        
        for i in range(self.nb_drones_aerien):
            creature_id = self.get_next_creature_id()
            self.creatures.append(Drone(self.spawn_x, self.spawn_y, self.spawn_x, self.spawn_y, "drone_aerien", self.logger, creature_id))
        
        
        for i in range(15):
            x = random.randint(0, LARGEUR_SIMULATION - 100)
            y = random.randint(0, HAUTEUR_SIMULATION - 100)
            largeur = random.randint(20, 80)
            hauteur = random.randint(20, 80)
            self.obstacles.append(Obstacle(x, y, largeur, hauteur))

        # Génération des zones de brouillage par pourcentage
        surface_totale = LARGEUR_SIMULATION * HAUTEUR_SIMULATION
        surface_brouillage_cible = surface_totale * (self.pourcentage_brouillage / 100.0)
        surface_brouillage_actuelle = 0
        max_zones = 200 
        
        while surface_brouillage_actuelle < surface_brouillage_cible and len(self.brouillages) < max_zones:
            largeur = random.randint(40, 120)
            hauteur = random.randint(40, 120)
            x = random.randint(0, LARGEUR_SIMULATION - largeur)
            y = random.randint(0, HAUTEUR_SIMULATION - hauteur)
            
            self.brouillages.append(Brouillage(x, y, largeur, hauteur))
            surface_brouillage_actuelle += largeur * hauteur
        
        # Sauvegarder le pourcentage réel pour les statistiques
        if surface_totale > 0:
            self.pourcentage_brouillage_reel = (surface_brouillage_actuelle / surface_totale) * 100
        
        print(f"Génération du brouillage : Cible {self.pourcentage_brouillage}% ({surface_brouillage_cible:.0f} pixels²).")
        print(f"Résultat : {len(self.brouillages)} zones couvrant {surface_brouillage_actuelle:.0f} pixels² ({self.pourcentage_brouillage_reel:.2f}%).")
        
        homme_a_la_mer_x = 0
        homme_a_la_mer_y = 0
        while True:
            homme_a_la_mer_x = random.randint(0, LARGEUR_SIMULATION - 15)
            homme_a_la_mer_y = random.randint(0, HAUTEUR_SIMULATION - 15)
            test_rect = pygame.Rect(homme_a_la_mer_x, homme_a_la_mer_y, 15, 15)
            
            collision = False
            for obstacle in self.obstacles:
                if test_rect.colliderect(obstacle.rect):
                    collision = True
                    break
            
            if not collision:
                break
        
        self.homme_a_la_mer = HommeALaMer(homme_a_la_mer_x, homme_a_la_mer_y)
        
        if self.logger:
            self.logger.log_event("world_generated", {
                "obstacles": [[o.x, o.y, o.largeur, o.hauteur] for o in self.obstacles],
                "brouillages": [[o.x, o.y, o.largeur, o.hauteur] for o in self.brouillages],
                "homme_a_la_mer_position": [self.homme_a_la_mer.x, self.homme_a_la_mer.y],
                "creatures_created": len(self.creatures)
            })
        
        random.seed()
    
    def changer_spawn(self, x, y):
        old_spawn = [self.spawn_x, self.spawn_y]
        self.spawn_x = x
        self.spawn_y = y
        
        if self.logger:
            self.logger.log_event("spawn_changed", {
                "old_spawn": old_spawn,
                "new_spawn": [x, y]
            })
        
        for creature in self.creatures:
            creature.spawn_x = x
            creature.spawn_y = y
    
    def ajouter_creature(self, type_creature):
        creature_id = self.get_next_creature_id()
        nouvelle_creature = Drone(self.spawn_x, self.spawn_y, self.spawn_x, self.spawn_y, type_creature, self.logger, creature_id)
        self.creatures.append(nouvelle_creature)
        
        if type_creature == "drone_de_surface":
            self.nb_drones_surface += 1
        else:
            self.nb_drones_aerien += 1
        
        return nouvelle_creature
    
    def retirer_creature(self, type_creature):
        for i, creature in enumerate(self.creatures):
            if creature.type_creature == type_creature:
                self.creatures.pop(i)
                if type_creature == "drone_de_surface":
                    self.nb_drones_surface -= 1
                else:
                    self.nb_drones_aerien -= 1
                return True
        return False
    
    def mettre_a_jour(self):
        if not self.homme_a_la_mer_decouvert and all(c.epuise for c in self.creatures):
            if not self.pause_automatique:
                self.temps_fin = time.time()
                self.simulation_reussie = False
                self.pause_automatique = True
                self.logger.log_event("simulation_failed_exhaustion", {
                    "reason": "all_drones_exhausted",
                    "duration": self.temps_fin - self.temps_debut
                })
            return
            
        for creature in self.creatures:
            creature.deplacer(self.obstacles, self.homme_a_la_mer, self.creatures, self.brouillages, self)
            
            if creature.a_trouve_homme_mer and not self.homme_a_la_mer_decouvert:
                self.homme_a_la_mer_decouvert = True
                self.homme_a_la_mer.decouvert = True
                self.temps_decouverte = pygame.time.get_ticks()
                self.simulation_reussie = True
                self.premiere_decouverte_homme_mer = creature.temps_premiere_decouverte_homme_mer
                self.qui_a_trouve_homme_mer = f"{creature.type_creature}_{creature.creature_id}"
                self.pause_automatique = True
                
                if self.logger:
                    self.logger.log_event("simulation_completed", {
                        "winner": self.qui_a_trouve_homme_mer,
                        "winner_id": creature.creature_id,
                        "time_to_discovery": creature.temps_premiere_decouverte_homme_mer - self.temps_debut,
                        "homme_a_la_mer_position": [self.homme_a_la_mer.x, self.homme_a_la_mer.y],
                        "winner_communications": len(creature.communications_reçues)
                    })
                
        self.zones_explorees = set()
        for creature in self.creatures:
            self.zones_explorees.update(creature.zone_exploree)
        
        if self.logger and self.logger.frame_count % 30 == 0:
            simulation_state = {
                "homme_a_la_mer_decouvert": self.homme_a_la_mer_decouvert,
                "zones_explorees_count": len(self.zones_explorees),
                "spawn_position": [self.spawn_x, self.spawn_y],
                "total_communications": sum(c.communications_envoyees for c in self.creatures),
                "total_communications_reussies_events": self.comms_surface_surface + self.comms_surface_aerien + self.comms_aerien_aerien
            }
            self.logger.log_frame(self.creatures, simulation_state)
    
    def dessiner(self, ecran, afficher_cercles_communication):
        ecran.fill(BLANC)
        
        pygame.draw.rect(ecran, COULEUR_UI_FOND, (0, 0, LARGEUR, HAUTEUR_ENTETE))
        pygame.draw.rect(ecran, COULEUR_UI_CONTOUR, (0, 0, LARGEUR, HAUTEUR_ENTETE), 1)
        font_titre = pygame.font.Font(None, 40)
        text_titre = font_titre.render("Simulation de Drones", True, NOIR)
        ecran.blit(text_titre, (LARGEUR // 2 - text_titre.get_width() // 2, 15))
        pygame.draw.rect(ecran, ORANGE, (10, 10, 40, 40))
        
        pygame.draw.rect(ecran, COULEUR_UI_FOND, (LARGEUR_SIMULATION, HAUTEUR_ENTETE, LARGEUR_BARRE_LATERALE, HAUTEUR - HAUTEUR_ENTETE))
        pygame.draw.rect(ecran, COULEUR_UI_CONTOUR, (LARGEUR_SIMULATION, HAUTEUR_ENTETE, LARGEUR_BARRE_LATERALE, HAUTEUR - HAUTEUR_ENTETE), 1)
        
        ecran_simulation = pygame.Surface((LARGEUR_SIMULATION, HAUTEUR_SIMULATION))
        ecran_simulation.fill(BLANC)
        
        for zone in self.zones_explorees:
            x, y = zone[0] * 10, zone[1] * 10
            pygame.draw.rect(ecran_simulation, GRIS_CLAIR, (x, y, 10, 10))
        
        pygame.draw.circle(ecran_simulation, VERT, (int(self.spawn_x), int(self.spawn_y)), 10, 3)
        pygame.draw.circle(ecran_simulation, VERT, (int(self.spawn_x), int(self.spawn_y)), 2)
        
        for obstacle in self.obstacles:
            obstacle.dessiner(ecran_simulation)

        for brouillage in self.brouillages:
            brouillage.dessiner(ecran_simulation)
        
        self.homme_a_la_mer.dessiner(ecran_simulation)
        
        for creature in self.creatures:
            creature.dessiner(ecran_simulation, afficher_cercles_communication, self.brouillages)
        
        if not self.simulation_reussie and all(c.epuise for c in self.creatures):
            font = pygame.font.Font(None, 40)
            text = font.render("SIMULATION ÉCHOUÉE (Tous les drones sont épuisés) !", True, ROUGE)
            ecran_simulation.blit(text, (LARGEUR_SIMULATION // 2 - text.get_width() // 2, HAUTEUR_SIMULATION // 2))

        ecran.blit(ecran_simulation, (0, HAUTEUR_ENTETE))
        
        self.afficher_info(ecran)
    
    def afficher_info(self, ecran):
        font_section = pygame.font.Font(None, 24)
        font_info = pygame.font.Font(None, 20)
        
        y_stats = HAUTEUR_ENTETE + 10
        pygame.draw.rect(ecran, BLANC, (LARGEUR_SIMULATION + 5, y_stats, LARGEUR_BARRE_LATERALE - 10, (HAUTEUR-HAUTEUR_ENTETE)//2 - 15), 0, 5)
        pygame.draw.rect(ecran, COULEUR_UI_CONTOUR, (LARGEUR_SIMULATION + 5, y_stats, LARGEUR_BARRE_LATERALE - 10, (HAUTEUR-HAUTEUR_ENTETE)//2 - 15), 1, 5)

        text_stats_titre = font_section.render("Statistiques", True, NOIR)
        ecran.blit(text_stats_titre, (LARGEUR_SIMULATION + 15, y_stats + 5))
        y_stats += 30

        drones_surface_actifs = sum(1 for c in self.creatures if c.type_creature == "drone_de_surface" and not c.epuise)
        drones_surface_epuises = sum(1 for c in self.creatures if c.type_creature == "drone_de_surface" and c.epuise)
        drones_aerien_actifs = sum(1 for c in self.creatures if c.type_creature == "drone_aerien" and not c.epuise)
        drones_aerien_epuises = sum(1 for c in self.creatures if c.type_creature == "drone_aerien" and c.epuise)
        
        text = font_info.render(f"Drones de Surface: {drones_surface_actifs} (épuisés: {drones_surface_epuises})", True, ROUGE)
        ecran.blit(text, (LARGEUR_SIMULATION + 15, y_stats))
        y_stats += 20
        text = font_info.render(f"Drones Aériens: {drones_aerien_actifs} (épuisés: {drones_aerien_epuises})", True, BLEU)
        ecran.blit(text, (LARGEUR_SIMULATION + 15, y_stats))
        y_stats += 20
        text = font_info.render(f"Zones explorées: {len(self.zones_explorees)}", True, NOIR)
        ecran.blit(text, (LARGEUR_SIMULATION + 15, y_stats))
        y_stats += 20
        communications_reussies = self.comms_surface_surface + self.comms_surface_aerien + self.comms_aerien_aerien
        communications_echouees = sum(c.communications_echouees for c in self.creatures)
        text = font_info.render(f"Communications réussies: {communications_reussies}", True, VIOLET)
        ecran.blit(text, (LARGEUR_SIMULATION + 15, y_stats))
        y_stats += 20
        text = font_info.render(f"Communications échouées: {communications_echouees}", True, VIOLET)
        ecran.blit(text, (LARGEUR_SIMULATION + 15, y_stats))
        y_stats += 30
        
        if self.homme_a_la_mer_decouvert:
            text = font_info.render("HOMME À LA MER DÉCOUVERT !", True, VERT)
            ecran.blit(text, (LARGEUR_SIMULATION + 15, y_stats))
            y_stats += 20
        
        y_commandes = HAUTEUR_ENTETE + (HAUTEUR-HAUTEUR_ENTETE)//2 + 5
        pygame.draw.rect(ecran, BLANC, (LARGEUR_SIMULATION + 5, y_commandes, LARGEUR_BARRE_LATERALE - 10, (HAUTEUR-HAUTEUR_ENTETE)//2 - 10), 0, 5)
        pygame.draw.rect(ecran, COULEUR_UI_CONTOUR, (LARGEUR_SIMULATION + 5, y_commandes, LARGEUR_BARRE_LATERALE - 10, (HAUTEUR-HAUTEUR_ENTETE)//2 - 10), 1, 5)

        text_commandes_titre = font_section.render("Commandes et Légende", True, NOIR)
        ecran.blit(text_commandes_titre, (LARGEUR_SIMULATION + 15, y_commandes + 5))
        y_commandes += 30

        instructions = [
            "Clic - Changer point de départ", "R - Redémarrer", "1 - Ajouter Drone de Surface",
            "2 - Ajouter Drone Aérien", "Q - Retirer Drone de Surface", "W - Retirer Drone Aérien",
            "Espace - Pause", "L - Sauvegarder logs", "C - Activer/désactiver cercles",
            "S - Sauvegarder stats"
        ]
        
        for i, instruction in enumerate(instructions):
            text = font_info.render(instruction, True, NOIR)
            ecran.blit(text, (LARGEUR_SIMULATION + 15, y_commandes + i * 20))

        y_commandes += len(instructions) * 20 + 10
        
        legende = [
            "États des Drones:", "• Vert: En repos", "• Orange: Retour au départ",
            "• Croix: Épuisé", "• C:X: X contacts",
            "Drones de Surface: 40s exploration, 20s repos",
            "Drones Aériens: 20s exploration, 15s repos",
        ]
        
        for i, ligne in enumerate(legende):
            text = font_info.render(ligne, True, NOIR)
            ecran.blit(text, (LARGEUR_SIMULATION + 15, y_commandes + i * 20))
        
        if en_pause:
            font = pygame.font.Font(None, 72)
            text = font.render("PAUSE", True, ROUGE)
            ecran.blit(text, (LARGEUR_SIMULATION // 2 - 80, HAUTEUR // 2 - 36))

def main():
    global en_pause, afficher_cercles_communication
    ecran = pygame.display.set_mode((LARGEUR, HAUTEUR))
    pygame.display.set_caption("Simulation de Drones - Recherche de l'Homme à la mer")
    horloge = pygame.time.Clock()
    
    nb_drones_surface = 5
    nb_drones_aerien = 5
    spawn_x, spawn_y = 100, 100
    pourcentage_zone_brouillee = 10 
    
    logger = Logger()
    simulation = Simulation(nb_drones_surface, nb_drones_aerien, spawn_x, spawn_y, logger, pourcentage_zone_brouillee)
    en_pause = False
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
                if event.button == 1:
                    if event.pos[0] < LARGEUR_SIMULATION and event.pos[1] > HAUTEUR_ENTETE:
                        spawn_x, spawn_y = event.pos[0], event.pos[1] - HAUTEUR_ENTETE
                        simulation.changer_spawn(spawn_x, spawn_y)
            
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
                
                elif event.key == pygame.K_SPACE:
                    en_pause = not en_pause
                    if logger:
                        logger.log_event("pause_toggled", {"paused": en_pause})
                
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
        
        if not en_pause and not simulation.pause_automatique:
            simulation.mettre_a_jour()
        
        simulation.dessiner(ecran, afficher_cercles_communication)
        
        if en_pause:
            font = pygame.font.Font(None, 72)
            text = font.render("PAUSE", True, ROUGE)
            ecran.blit(text, (LARGEUR_SIMULATION // 2 - 80, HAUTEUR // 2 - 36))
        
        pygame.display.flip()
        horloge.tick(FPS)

if __name__ == "__main__":
    main()