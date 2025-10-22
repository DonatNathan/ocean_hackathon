
import pygame
import random
import math
import time
from utils import constant

class Drone:
    def __init__(self, x, y, spawn_x, spawn_y, vx, vy, type_creature="drone_de_surface", logger=None, creature_id=0):
        self.x = x
        self.y = y
        self.spawn_x = spawn_x
        self.spawn_y = spawn_y
        self.vx = vx
        self.vy = vy
        self.type_creature = type_creature
        self.creature_id = creature_id
        self.zone_exploree = set()
        self.a_trouve_homme_mer = False
        self.angle = random.uniform(0, 2 * math.pi)
        self.temps_changement_direction = 0
        self.logger = logger
        self.target = set()
        self.link = []
        # Système de communication
        # Dans __init__ de ta classe (ex: Agent, Drone, etc.)
        self.radar_progression = 0.0  # en secondes ou en proportion (0 à 1)
        self.radar_duree = 1.5  # durée en secondes pour un cycle complet (ajuste selon envie)
        self.contournement_actif = False
        self.frames_contournement = 0
        self.direction_contournement = 0
        self.rayon_communication = 50
        self.distance_detection = 0
        self.communications_reçues = set()
        self.communications_envoyees = 0
        self.communications_echouees = 0
        self.derniere_communication = {}
        self.cooldown_communication = 1.0
        self.tentatives_communication = 0
        self.homme_positions_connues = None

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
        self.cone = None
        self.start_cone = []
        
        # Caractéristiques selon le type
        if type_creature == "drone_de_surface":
            self.vitesse = constant.FACTEUR_ACCELERATION * 138 / constant.FPS
            self.couleur = constant.ROUGE
            self.couleur_trouve = constant.ROUGE_CLAIR
            self.taille = 3
            self.zone_decouverte = 8
            self.temps_avant_repos = 24
            self.duree_repos = 2
            self.rayon_communication = 40
        elif type_creature == "drone_aerien":
            self.vitesse = constant.FACTEUR_ACCELERATION * 277 / constant.FPS
            self.couleur = constant.JAUNE
            self.couleur_trouve = constant.JAUNE
            self.taille = 4
            self.zone_decouverte = 16
            self.temps_avant_repos = 10
            self.duree_repos = 1
            self.rayon_communication = 20
        elif type_creature == "base":
            self.vitesse = 0
            self.couleur = constant.VERT
            self.couleur_trouve = constant.VERT
            self.taille = 6
            self.zone_decouverte = 0
            self.temps_avant_repos = float('inf')
            self.duree_repos = 0
            self.rayon_communication = 100

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
        # if autre_creature.creature_id in self.derniere_communication:
        #     temps_derniere = self.derniere_communication[autre_creature.creature_id]
        #     if current_time - temps_derniere < self.cooldown_communication:
        #         return False

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
        if not self.retour_spawn and  self.target:
            zone = (self.target[0], self.target[1])
            autre_creature.zone_exploree.update(zone)


        self.zones_decouvertes_uniques.update(nouvelles_zones_recues)
        autre_creature.zones_decouvertes_uniques.update(nouvelles_zones_envoyees)
        if self.a_trouve_homme_mer:
            autre_creature.a_trouve_homme_mer = True
            autre_creature.homme_positions_connues = self.homme_positions_connues
            autre_creature.temps_premiere_decouverte_homme_mer = self.temps_premiere_decouverte_homme_mer
        return True
    
    def verifier_communications(self, autres_creatures, brouillages, simulation):
        """Vérifie les communications et met à jour self.link (liste d'objets)"""
        self.link = []
        communications_etablies = 0

        for autre in autres_creatures:
            if autre.creature_id == self.creature_id or autre.epuise or self.epuise:
                continue

            distance = math.hypot(self.x - autre.x, self.y - autre.y)
            portee = (self.rayon_communication + autre.rayon_communication) / 2

            if distance <= portee:
                if self.communiquer_avec(autre, brouillages, simulation):
                    self.link.append(autre)
                    communications_etablies += 1

        return communications_etablies
    
    def deplacer(self, obstacles, homme_a_la_mer, autres_creatures, brouillages, simulation):

        self.target = None
        if self.epuise:
            return

        self.temps_depuis_spawn += 1 / constant.FPS

        if not self.en_repos:
            self.verifier_communications(autres_creatures, brouillages, simulation)

        dist_spawn = math.sqrt((self.x - self.spawn_x)**2 + (self.y - self.spawn_y)**2)
        if self.temps_depuis_spawn > self.temps_avant_repos and dist_spawn > 10:
                self.epuise = True
        if self.retour_spawn:
            if self.gerer_retour_spawn(autres_creatures):
                print(f"[LOG] Drone {self.creature_id} retourne au spawn.")
                return

        elif self.en_repos:
            if self.gerer_repos():
                print(f"[LOG] Drone {self.creature_id} reste en repos.")
                return
            else:
                print(f"[LOG] Drone {self.creature_id} sort du repos.")

        self.explorer(obstacles, homme_a_la_mer)

        if not self.en_repos and not self.retour_spawn and self.temps_depuis_spawn >= self.temps_avant_repos / 2:
            self.retour_spawn = True

        self.mettre_a_jour_zones_explorees()
        self.mettre_a_jour_position(obstacles)
        self.detecter_homme_a_la_mer(homme_a_la_mer)

    def passer_en_retour_spawn(self):
        if  self.target is None:
            return
        if self.vitesse == 0:
            return
        distance_vers_cible = math.dist((self.x, self.y), (self.target[0], self.target[1]))
        temps_necessaire = distance_vers_cible / self.vitesse
        if temps_necessaire >= self.temps_avant_repos - self.temps_depuis_spawn:
            self.retour_spawn = True
            print(f"[LOG] Drone {self.creature_id} passe en mode retour au spawn.")
            self.target = (self.spawn_x, self.spawn_y)
        else:
            return

        if self.logger:
            self.logger.log_event("creature_state_change", {
                "creature_id": self.creature_id,
                "creature_type": self.type_creature,
                "new_state": "retour_spawn",
                "position": [self.x, self.y],
                "communications_count": len(self.communications_reçues)
            })

    def gerer_retour_spawn(self, autres_creatures):
        base_la_plus_proche = None
        dist_base_min = float('inf')
        for creature in autres_creatures:
            if creature.type_creature == "base":
                dist = math.dist((self.x, self.y), (creature.x, creature.y))
                if dist < dist_base_min:
                    dist_base_min = dist
                    base_la_plus_proche = creature
        dist_spawn = math.dist((self.x, self.y), (self.spawn_x, self.spawn_y))
        if base_la_plus_proche is not None and dist_base_min < dist_spawn:
            cible_x, cible_y = base_la_plus_proche.x, base_la_plus_proche.y
        else:
            cible_x, cible_y = self.spawn_x, self.spawn_y
        if math.dist((self.x, self.y), (cible_x, cible_y)) < 5:
            self.entrer_en_repos()
            return True
        else:
            self.angle = math.atan2(cible_y - self.y, cible_x - self.x)
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
        print(f"[LOG] Drone {self.creature_id} en repos depuis {temps_repos_actuel:.2f}s., durée requise: {self.duree_repos}s.")
        if temps_repos_actuel >= self.duree_repos:
            self.en_repos = False
            self.retour_spawn = False
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
            return True

    def zone_contient_obstacle(self, tx, ty, obstacles):
        """Renvoie True si un obstacle occupe (même partiellement) la zone (tx, ty)."""
        zone_rect = pygame.Rect(tx * 10, ty * 10, 10, 10)
        for obstacle in obstacles:
            if obstacle.rect.colliderect(zone_rect):
                return True
        return False
    

    def point_in_triangle(self, pt, v1, v2, v3):
        """Vérifie si un point pt est dans le triangle (v1, v2, v3)"""
        x, y = pt
        x1, y1 = v1
        x2, y2 = v2
        x3, y3 = v3

        def sign(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

        b1 = sign((x, y), (x1, y1), (x2, y2)) < 0.0
        b2 = sign((x, y), (x2, y2), (x3, y3)) < 0.0
        b3 = sign((x, y), (x3, y3), (x1, y1)) < 0.0

        return (b1 == b2) and (b2 == b3)


    def a_star(self, start, goal, grid):
        """
        start, goal : tuple (x, y) en coordonnées de cellules
        grid : dict avec (x,y) : 0 (libre) ou 1 (obstacle)
        retourne une liste de cellules [(x1,y1), (x2,y2), ...] pour aller de start à goal
        """

        def heuristic(a, b):
            # Distance Euclidienne
            return ((a[0]-b[0])**2 + (a[1]-b[1])**2) ** 0.5

        open_set = []
        heapq.heappush(open_set, (0 + heuristic(start, goal), 0, start, [start]))  # (f, g, current, path)
        visited = set()

        while open_set:
            f, g, current, path = heapq.heappop(open_set)
            if current in visited:
                continue
            visited.add(current)

            if current == goal:
                return path[1:]  # renvoie le chemin à suivre, excluant la cellule actuelle

            x, y = current
            # Voisins 4 directions (haut, bas, gauche, droite)
            neighbors = [(x+1,y), (x-1,y), (x,y+1), (x,y-1)]
            for nx, ny in neighbors:
                if (nx, ny) in visited:
                    continue
                if grid.get((nx, ny), 1) == 1:  # 1 = obstacle ou zone interdite
                    continue
                heapq.heappush(open_set, (g+1 + heuristic((nx, ny), goal), g+1, (nx, ny), path + [(nx, ny)]))

        return [] 
    def explorer(self, obstacles, homme_a_la_mer):
        if self.a_trouve_homme_mer:
            self.retour_spawn = True
            return

        cell_size = 10
        max_range = 200
        cone_cells_to_explore = []

        if self.cone is not None and self.target is None:
            v1, v2, v3 = self.cone
            
            # Définir la zone de recherche comme le rectangle englobant du cône
            min_x = max(0, int(min(v1[0], v2[0], v3[0]) // cell_size))
            max_x = min(constant.LARGEUR_SIMULATION // cell_size, int(max(v1[0], v2[0], v3[0]) // cell_size) + 1)
            min_y = max(0, int(min(v1[1], v2[1], v3[1]) // cell_size))
            max_y = min(constant.HAUTEUR_SIMULATION // cell_size, int(max(v1[1], v2[1], v3[1]) // cell_size) + 1)
            
            # Créer toutes les directions possibles dans le rectangle englobant
            directions = []
            for tx in range(min_x, max_x):
                for ty in range(min_y, max_y):
                    directions.append((tx, ty))
            
            # Mélanger aléatoirement comme dans l'algo original
            random.shuffle(directions)
            
            best_dist = float("inf")
            best_targets = []
            
            for tx, ty in directions:
                # Vérifier si la cellule est dans le cône
                cx_cell = tx * cell_size + cell_size / 2
                cy_cell = ty * cell_size + cell_size / 2
                if not self.point_in_triangle((cx_cell, cy_cell), v1, v2, v3):
                    continue
                    
                zone = (tx, ty)
                if zone in self.zones_decouvertes_uniques:
                    continue
                    
                if self.zone_contient_obstacle(tx, ty, obstacles):
                    self.zones_decouvertes_uniques.add(zone)
                    continue
                    
                target_x = tx * cell_size + cell_size / 2
                target_y = ty * cell_size + cell_size / 2
                dist = math.hypot(target_x - self.x, target_y - self.y)
                
                if dist < best_dist - 1e-6:
                    best_dist = dist
                    best_targets = [(target_x, target_y)]
                elif abs(dist - best_dist) <= 1e-6:
                    best_targets.append((target_x, target_y))
                    
            if best_targets:
                self.target = random.choice(best_targets)

        if self.target is None:
            R = max_range // cell_size
            cx = int(self.x // cell_size)
            cy = int(self.y // cell_size)

            best_dist = float("inf")
            best_targets = []
            directions = [(dx, dy) for dx in range(-R, R) for dy in range(-R, R)]
            random.shuffle(directions)
            for dx, dy in directions:
                tx, ty = cx + dx, cy + dy
                if not (0 <= tx < constant.LARGEUR_SIMULATION // cell_size and
                        0 <= ty < constant.HAUTEUR_SIMULATION // cell_size):
                    continue
                zone = (tx, ty)
                if zone in self.zones_decouvertes_uniques:
                    continue
                if self.zone_contient_obstacle(tx, ty, obstacles):
                    self.zones_decouvertes_uniques.add(zone)
                    continue
                target_x = tx * cell_size + cell_size / 2
                target_y = ty * cell_size + cell_size / 2
                dist = math.hypot(target_x - self.x, target_y - self.y)
                if dist < best_dist - 1e-6:
                    best_dist = dist
                    best_targets = [(target_x, target_y)]
                elif abs(dist - best_dist) <= 1e-6:
                    best_targets.append((target_x, target_y))
            if best_targets:
                self.target = random.choice(best_targets)

        if not self.en_repos and not self.retour_spawn:
            if self.target is not None:
                self.angle = math.atan2(self.target[1] - self.y, self.target[0] - self.x)
            else:
                self.angle += random.uniform(-0.3, 0.3)

            if not self.en_repos and not self.retour_spawn:
                if self.target is not None:
                    self.angle = math.atan2(self.target[1] - self.y, self.target[0] - self.x)
                else:
                    self.angle += random.uniform(-0.3, 0.3)

            if self.type_creature == "drone_de_surface" and self.target is not None:
                if self.contournement_actif:
                    self.frames_contournement -= 1
                    if self.frames_contournement <= 0:
                        self.contournement_actif = False
                else:
                    dx = self.target[0] - self.x
                    dy = self.target[1] - self.y
                    distance_vers_cible = math.hypot(dx, dy)

                    if distance_vers_cible > 0:
                        pas = max(1, int(distance_vers_cible / 0.1))
                        obstacle_trouve = None
                        for i in range(1, pas + 1):
                            t = i / pas
                            check_x = self.x + dx * t
                            check_y = self.y + dy * t
                            for obstacle in obstacles:
                                if obstacle.rect.collidepoint(check_x, check_y):
                                    obstacle_trouve = obstacle
                                    break
                            if obstacle_trouve:
                                break

                        if obstacle_trouve:
                            self.demarrer_contournement(obstacle_trouve, obstacles)

    def demarrer_contournement(self, obstacle, obstacles_liste):
        """
        Contourne en choisissant le côté (gauche/droite) avec le plus d'espace.
        """
        dx = self.x - obstacle.x
        dy = self.y - obstacle.y
        direction = math.atan2(dy, dx)
        angle_gauche = direction + math.pi / 2
        angle_droite = direction - math.pi / 2 

        test_dist = 1
        point_gauche = (
            self.x + math.cos(angle_gauche) * test_dist,
            self.y + math.sin(angle_gauche) * test_dist
        )
        point_droite = (
            self.x + math.cos(angle_droite) * test_dist,
            self.y + math.sin(angle_droite) * test_dist
        )

        def point_dans_obstacle(px, py, liste_obs):
            for obs in liste_obs:
                if obs.rect.collidepoint(px, py):
                    return True
            return False

        gauche_libre = not point_dans_obstacle(point_gauche[0], point_gauche[1], obstacles_liste)
        droite_libre = not point_dans_obstacle(point_droite[0], point_droite[1], obstacles_liste)

        if gauche_libre and droite_libre:
            if hasattr(self, 'creature_id') and self.creature_id % 2 == 0:
                self.angle = angle_droite
            else:
                self.angle = angle_gauche
        elif gauche_libre:
            self.angle = angle_gauche
        elif droite_libre:
            self.angle = angle_droite
        else:
            self.angle = angle_droite
        self.angle = (self.angle + math.pi) % (2 * math.pi) - math.pi
        self.contournement_actif = True
        self.frames_contournement = 25

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
            self.homme_positions_connues = (homme_a_la_mer.x, homme_a_la_mer.y)
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
                self.radar_progression += self.temps_depuis_spawn / constant.FPS
                if self.radar_progression >= self.radar_duree:
                    self.radar_progression = 0.0
                pygame.draw.circle(
                    surface_communication,
                    (*constant.BLANC, 30), 
                    (self.rayon_communication, self.rayon_communication),
                    self.rayon_communication,
                    width=2
                )

                progression = self.radar_progression / self.radar_duree
                rayon_radar = progression * self.rayon_communication
                pygame.draw.circle(
                    surface_communication,
                    (*constant.BLANC, 180),
                    (self.rayon_communication, self.rayon_communication),
                    max(1, int(rayon_radar)),
                    width=2
                )

                ecran_simulation.blit(
                    surface_communication,
                    (self.x - self.rayon_communication, self.y - self.rayon_communication)
                )
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

            # if self.target:
            #     pygame.draw.line(
            #         ecran_simulation,
            #         (255, 0, 0),
            #         (int(self.x), int(self.y)),
            #         (int(self.target[0]), int(self.target[1])),
            #         width=2
            #     )
            for autre in self.link:
                pygame.draw.line(
                    ecran_simulation,
                    constant.VERT,
                    (int(self.x), int(self.y)),
                    (int(autre.x), int(autre.y)),
                    width=2
                )
            if len(self.communications_reçues) > 0:
                font_com = pygame.font.Font(None, 14)
                text_com = font_com.render(f"C:{len(self.communications_reçues)}", True, constant.VIOLET)
                ecran_simulation.blit(text_com, (self.x + 8, self.y + 8))
