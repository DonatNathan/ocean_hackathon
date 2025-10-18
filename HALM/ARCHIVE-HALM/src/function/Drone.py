
import pygame
import random
import math
import time
from utils import constant

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
            self.vitesse = constant.FACTEUR_ACCELERATION * 13.8 / constant.FPS
            self.couleur = constant.ROUGE
            self.couleur_trouve = constant.ROUGE_CLAIR
            self.taille = 3
            self.zone_decouverte = 15
            self.temps_avant_repos = 100
            self.duree_repos = 20
            self.rayon_communication = 50
        elif type_creature == "drone_aerien":
            self.vitesse = constant.FACTEUR_ACCELERATION * 27.7 / constant.FPS
            self.couleur = constant.BLEU
            self.couleur_trouve = constant.BLEU_CLAIR
            self.taille = 4
            self.zone_decouverte = 30
            self.temps_avant_repos = 80
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
        if autre_creature.creature_id in self.derniere_communication:
            temps_derniere = self.derniere_communication[autre_creature.creature_id]
            if current_time - temps_derniere < self.cooldown_communication:
                return False

        self.communications_reçues.add(autre_creature.creature_id)
        autre_creature.communications_reçues.add(self.creature_id)

        self.communications_envoyees += 1
        autre_creature.communications_envoyees += 1

        self.derniere_communication[autre_creature.creature_id] = current_time
        autre_creature.derniere_communication[self.creature_id] = current_time

        type1 = self.type_creature
        type2 = autre_creature.type_creature

        if type1 == "drone_de_surface" and type2 == "drone_de_surface":
            simulation.comms_surface_surface += 1
        elif type1 == "drone_aerien" and type2 == "drone_aerien":
            simulation.comms_aerien_aerien += 1
        else:
            simulation.comms_surface_aerien += 1

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

        nouvelles_zones_recues = autre_creature.zone_exploree - self.zone_exploree
        nouvelles_zones_envoyees = self.zone_exploree - autre_creature.zone_exploree

        self.zone_exploree.update(autre_creature.zone_exploree)
        autre_creature.zone_exploree.update(self.zone_exploree)

        self.zones_decouvertes_uniques.update(nouvelles_zones_recues)
        autre_creature.zones_decouvertes_uniques.update(nouvelles_zones_envoyees)
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
        if self.epuise:
            print("[LOG] Créature épuisée, ne se déplace pas.")
            return

        self.temps_depuis_spawn += 1 / constant.FPS

        if not self.en_repos:
            print("[LOG] Vérification des communications.")
            self.verifier_communications(autres_creatures, brouillages, simulation)

        if not self.en_repos and not self.retour_spawn and self.temps_depuis_spawn >= self.temps_avant_repos / 2:
            print("[LOG] Demi-temps atteint, passage en retour vers spawn.")
            self.passer_en_retour_spawn()

        if self.retour_spawn:
            print("[LOG] Mode retour vers spawn.")
            if self.gerer_retour_spawn():
                print("[LOG] Retour spawn terminé, arrêt déplacement.")
                return

        elif self.en_repos:
            print("[LOG] Mode repos.")
            if self.gerer_repos():
                print("[LOG] Fin de repos, arrêt déplacement.")
                return

        else:
            print("[LOG] Mode exploration.")
            self.explorer(obstacles, homme_a_la_mer)

        self.mettre_a_jour_zones_explorees()
        self.mettre_a_jour_position(obstacles)
        self.detecter_homme_a_la_mer(homme_a_la_mer)

    def passer_en_retour_spawn(self):
        self.retour_spawn = True
        if self.logger:
            self.logger.log_event("creature_state_change", {
                "creature_id": self.creature_id,
                "creature_type": self.type_creature,
                "new_state": "retour_spawn",
                "position": [self.x, self.y],
                "communications_count": len(self.communications_reçues)
            })

    def gerer_retour_spawn(self):
        dist_spawn = math.dist((self.x, self.y), (self.spawn_x, self.spawn_y))

        if dist_spawn < 5:
            self.entrer_en_repos()
            return True
        else:
            self.angle = math.atan2(self.spawn_y - self.y, self.spawn_x - self.x)
        return False

    def entrer_en_repos(self):
        self.en_repos = True
        self.retour_spawn = False
        self.temps_repos_debut = time.time()
        self.x, self.y = self.spawn_x, self.spawn_y

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

    def gerer_repos(self):
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
            return False
        else:
            self.x, self.y = self.spawn_x, self.spawn_y
            return True

    def explorer(self, obstacles, homme_a_la_mer):
        # self.temps_changement_direction += 1
        # if self.temps_changement_direction > 60:
        #     old_angle = self.angle
        #     self.angle += random.uniform(-0.5, 0.5)
        #     self.temps_changement_direction = 0
        #     if self.logger:
        #         self.logger.log_event("direction_change", {
        #             "creature_id": self.creature_id,
        #             "old_angle": old_angle,
        #             "new_angle": self.angle,
        #             "position": [self.x, self.y]
        #         })

        print("ID Drone: ", self.creature_id)
        print("Communication: ", len(self.zones_decouvertes_uniques))

        if self.a_trouve_homme_mer:
            self.angle = math.atan2(homme_a_la_mer.y - self.y, homme_a_la_mer.x - self.x)
            return

        cell_size = 10
        max_range = 200
        cx, cy = int(self.x // cell_size), int(self.y // cell_size)

        target = None
        best_dist = float("inf")
        for dx in range(-int(max_range / cell_size), int(max_range / cell_size)):
            for dy in range(-int(max_range / cell_size), int(max_range / cell_size)):
                tx, ty = cx + dx, cy + dy
                if 0 <= tx < constant.LARGEUR_SIMULATION // 10 and 0 <= ty < constant.HAUTEUR_SIMULATION // 10:
                    zone = (tx, ty)
                    if zone not in self.zones_decouvertes_uniques:
                        dist = math.hypot(dx, dy)
                        if dist < best_dist:
                            best_dist = dist
                            target = (tx * cell_size, ty * cell_size)

        if target:
            self.angle = math.atan2(target[1] - self.y, target[0] - self.x)
        else:
            self.angle += random.uniform(-0.3, 0.3)

        if self.type_creature == "drone_de_surface":
            for obstacle in obstacles:
                if obstacle.rect.collidepoint(self.x, self.y):
                    self.eviter_obstacle(obstacle)

    def eviter_obstacle(self, obstacle):
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

    def mettre_a_jour_position(self, obstacles):
        self.vx = math.cos(self.angle) * self.vitesse
        self.vy = math.sin(self.angle) * self.vitesse
        nouvelle_x = self.x + self.vx
        nouvelle_y = self.y + self.vy

        nouvelle_pos_ok = 0 <= nouvelle_x < constant.LARGEUR_SIMULATION and 0 <= nouvelle_y < constant.HAUTEUR_SIMULATION

        if nouvelle_pos_ok and self.type_creature == "drone_de_surface":
            nouvelle_rect = pygame.Rect(nouvelle_x - self.taille, nouvelle_y - self.taille, self.taille * 2, self.taille * 2)
            for obstacle in obstacles:
                if nouvelle_rect.colliderect(obstacle.rect):
                    self.angle = math.atan2(self.y - obstacle.y, self.x - obstacle.x) + random.uniform(-math.pi/4, math.pi/4)
                    nouvelle_pos_ok = False
                    break

        if nouvelle_pos_ok:
            if not self.epuise and not self.en_repos:
                self.distance_parcourue += math.dist((self.x, self.y), (nouvelle_x, nouvelle_y))
            self.x, self.y = nouvelle_x, nouvelle_y
        else:
            self.angle += math.pi
            if self.logger:
                self.logger.log_event("boundary_hit", {
                    "creature_id": self.creature_id,
                    "creature_type": self.type_creature,
                    "position": [self.x, self.y],
                    "new_angle": self.angle
                })

    def detecter_homme_a_la_mer(self, homme_a_la_mer):
        dist = math.dist((self.x, self.y), (homme_a_la_mer.x, homme_a_la_mer.y))
        if dist < self.zone_decouverte and not self.a_trouve_homme_mer:
            self.a_trouve_homme_mer = True
            self.couleur = self.couleur_trouve
            self.temps_premiere_decouverte_homme_mer = time.time()

            if self.logger:
                self.logger.log_event("homme_a_la_mer_discovered", {
                    "creature_id": self.creature_id,
                    "creature_type": self.type_creature,
                    "position": [self.x, self.y],
                    "homme_a_la_mer_position": [homme_a_la_mer.x, homme_a_la_mer.y],
                    "distance": dist,
                    "communications_at_discovery": len(self.communications_reçues)
                })

    def mettre_a_jour_zones_explorees(self):
        rayon = self.zone_decouverte // 10
        nouvelles_zones = set()
        for dx in range(-rayon, rayon + 1):
            for dy in range(-rayon, rayon + 1):
                if dx*dx + dy*dy <= rayon*rayon:
                    zx, zy = int((self.x + dx*10) // 10), int((self.y + dy*10) // 10)
                    if 0 <= zx < constant.LARGEUR_SIMULATION//10 and 0 <= zy < constant.HAUTEUR_SIMULATION//10:
                        zone = (zx, zy)
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
            pygame.draw.line(ecran_simulation, constant.NOIR, 
                           (self.x - taille_croix, self.y - taille_croix),
                           (self.x + taille_croix, self.y + taille_croix), 3)
            pygame.draw.line(ecran_simulation, constant.NOIR, 
                           (self.x - taille_croix, self.y + taille_croix),
                           (self.x + taille_croix, self.y - taille_croix), 3)
        else:
            if afficher_cercles_communication and not self.est_dans_zone_brouillage(brouillages):
                surface_communication = pygame.Surface((self.rayon_communication * 2, self.rayon_communication * 2), pygame.SRCALPHA)
                pygame.draw.circle(surface_communication, (*constant.CYAN, 30), (self.rayon_communication, self.rayon_communication), self.rayon_communication)
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
            text_id = font_id.render(str(self.creature_id), True, constant.NOIR)
            ecran_simulation.blit(text_id, (self.x - 5, self.y - 15))

            if self.en_repos:
                pygame.draw.circle(ecran_simulation, constant.VERT, (int(self.x), int(self.y - 10)), 2)
            elif self.retour_spawn:
                pygame.draw.circle(ecran_simulation, constant.ORANGE, (int(self.x), int(self.y - 10)), 2)

            if len(self.communications_reçues) > 0:
                font_com = pygame.font.Font(None, 14)
                text_com = font_com.render(f"C:{len(self.communications_reçues)}", True, constant.VIOLET)
                ecran_simulation.blit(text_com, (self.x + 8, self.y + 8))
