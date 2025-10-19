import random
import pygame
import time
import os
import json
import threading
import math
from utils import constant
from datetime import datetime
from utils import constant
from .Drone import Drone
from .Obstacle import Obstacle
from .Brouillage import Brouillage
from .HommeALaMer import HommeALaMer
from .Boat import Boat

class Simulation:
    def __init__(self, nb_drones_surface=8, nb_drones_aerien=7, spawn_x=100, spawn_y=100, logger=None, pourcentage_brouillage=10, mode="classic"):
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
        self.boats = []
        self.mode = mode
        self.cone = None
        self.start_cone = []
        self.base_coord = None
        self.homme_coord = None
        # Nouveaux compteurs de communication
        self.comms_surface_surface = 0
        self.comms_surface_aerien = 0
        self.comms_aerien_aerien = 0
        
        self.generer_monde(mode)
        
        if self.logger:
            self.logger.log_event("simulation_started", {
                "configuration": {
                    "nb_drones_surface": nb_drones_surface,
                    "nb_drones_aerien": nb_drones_aerien,
                    "spawn_position": [spawn_x, spawn_y],
                    "screen_size": [constant.LARGEUR_SIMULATION, constant.HAUTEUR_SIMULATION],
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
        surface_carte = (constant.LARGEUR_SIMULATION // 10) * (constant.HAUTEUR_SIMULATION // 10)
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
                "homme_a_la_mer_position": [self.homme_a_la_mer.x if self.homme_a_la_mer else None, self.homme_a_la_mer.y if self.homme_a_la_mer else None],
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
        
        ont_trouve_homme_mer = sum(1 for c in creatures_type if (c.a_trouve_homme_mer and c.type_creature == "base"))
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

    def spawn_all_drones(self):
        threading.Timer( 0, self.spawn_drone, args=("base",0, 0)).start()
        for i in range(self.nb_drones_surface):
            angle = (2 * math.pi / self.nb_drones_surface) * i
            vx = math.cos(angle)
            vy = math.sin(angle)
            threading.Timer(0 * i, self.spawn_drone, args=("drone_de_surface", vx, vy)).start()

        offset = self.nb_drones_surface * 0.5
        for i in range(self.nb_drones_aerien):
            angle = (2 * math.pi / self.nb_drones_aerien) * i
            vx = math.cos(angle)
            vy = math.sin(angle)
            threading.Timer(0 * i, self.spawn_drone, args=("drone_aerien", vx, vy)).start()

    def handleClick(self, x, y):
        print("In handle click", x, " ", y)
        for boat in self.boats:
            print("Boat: ", boat.x, boat.y)
            rect = pygame.Rect(boat.x - boat.sizeX/2, boat.y - boat.sizeY/2, boat.sizeX, boat.sizeY)
            if rect.collidepoint(x, y):
                print(f"Clicked on boat at ({boat.x:.1f}, {boat.y:.1f})")
                if boat.has_dropped_man:

                    boat.send_drones()
                    
                    self.start_cone = boat.start_cone
                    self.cone = boat.cone
                    boat.base.start_cone = boat.start_cone
                    boat.base.cone = boat.cone
                    self.creatures.append(boat.base)

                    # Drones
                    for _ in range(len(boat.drones)):
                        drone = boat.drones.pop()
                        drone.start_cone = boat.start_cone
                        drone.cone = boat.cone
                        self.creatures.append(drone)
                    self.homme_a_la_mer = boat.man_overboard
                    for boat_temp in self.boats:
                        if self.homme_a_la_mer:
                            boat.send_drones()
                            for i in range(len(boat_temp.drones)):
                                drone = boat_temp.drones.pop()
                                drone.cone = self.cone
                                drone.start_cone = self.start_cone
                                print("Drone START corrd: ", drone.start_cone)
                                print("drone cone points: ", drone.cone)
                                self.creatures.append(drone)
                else:
                    boat.create_man_overboard()
        return None

    def spawn_drone(self, drone_type, vx, vy):
        creature_id = self.get_next_creature_id()
        self.creatures.append(Drone(self.spawn_x, self.spawn_y, self.spawn_x, self.spawn_y, vx, vy, drone_type, self.logger, creature_id))

    def spawn_boat(self):
        self.boats.append(Boat(speed=3))

    def generer_monde(self, mode):

        if (mode == "classic"):
            self.spawn_all_drones()
        
            for i in range(15):
                x = random.randint(0, constant.LARGEUR_SIMULATION - 100)
                y = random.randint(0, constant.HAUTEUR_SIMULATION - 100)
                constant.largeur = random.randint(20, 80)
                hauteur = random.randint(20, 80)
                self.obstacles.append(Obstacle(x, y, constant.largeur, hauteur))

        surface_totale = constant.LARGEUR_SIMULATION * constant.HAUTEUR_SIMULATION
        surface_brouillage_cible = surface_totale * (self.pourcentage_brouillage / 100.0)
        surface_brouillage_actuelle = 0
        max_zones = 200 
        while surface_brouillage_actuelle < surface_brouillage_cible and len(self.brouillages) < max_zones:
            constant.largeur = random.randint(40, 120)
            hauteur = random.randint(40, 120)
            x = random.randint(0, constant.LARGEUR_SIMULATION - constant.largeur)
            y = random.randint(0, constant.HAUTEUR_SIMULATION - hauteur)
            self.brouillages.append(Brouillage(x, y, constant.largeur, hauteur))
            surface_brouillage_actuelle += constant.largeur * hauteur
        if surface_totale > 0:
            self.pourcentage_brouillage_reel = (surface_brouillage_actuelle / surface_totale) * 100
        
        print(f"Génération du brouillage : Cible {self.pourcentage_brouillage}% ({surface_brouillage_cible:.0f} pixels²).")
        print(f"Résultat : {len(self.brouillages)} zones couvrant {surface_brouillage_actuelle:.0f} pixels² ({self.pourcentage_brouillage_reel:.2f}%).")
        
        homme_a_la_mer_x = 0
        homme_a_la_mer_y = 0
        while True:
            homme_a_la_mer_x = random.randint(0, constant.LARGEUR_SIMULATION - 15)
            homme_a_la_mer_y = random.randint(0, constant.HAUTEUR_SIMULATION - 15)
            test_rect = pygame.Rect(homme_a_la_mer_x, homme_a_la_mer_y, 15, 15)
            
            collision = False
            for obstacle in self.obstacles:
                if test_rect.colliderect(obstacle.rect):
                    collision = True
                    break
            
            if not collision:
                break
        
        if (mode == "classic"):
            self.homme_a_la_mer = HommeALaMer(homme_a_la_mer_x, homme_a_la_mer_y)
        
        if self.logger and self.homme_a_la_mer:
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
    
    def mettre_a_jour(self, ecran_simulation):

        self.zones_explorees = set()

        if self.mode == "boat":
            for boat in self.boats:
                boat.move()
                # if boat.detached:
                #     for drone in boat.drones:
                #         drone.deplacer(self.obstacles, boat.man_overboard, boat.drones, self.brouillages, self)


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
            if creature.a_trouve_homme_mer and creature.type_creature != "base":
                self.homme_a_la_mer.decouvert= True
                self.homme_a_la_mer.dessiner(ecran_simulation)
            if creature.a_trouve_homme_mer and creature.type_creature == "base":
                self.base_coord = (creature.spawn_x, creature.spawn_y)
                self.homme_coord = (creature.homme_positions_connues[0], creature.homme_positions_connues[1])
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
        ecran.fill(constant.GRIS)
        pygame.draw.rect(ecran, constant.NOIR, (0, 0, constant.LARGEUR, constant.HAUTEUR_ENTETE))
        ecran_simulation = pygame.Surface((constant.LARGEUR_SIMULATION, constant.HAUTEUR_SIMULATION))
        ecran_simulation.fill(constant.NOIR)


        if self.cone and len(self.cone) >= 3:
            left_pt = self.cone[1]
            right_pt = self.cone[2]

            pygame.draw.line(ecran_simulation, (255, 255, 0),
                            (int(self.start_cone[0]), int(self.start_cone[1])),
                            (int(left_pt[0]), int(left_pt[1])), 2)
            pygame.draw.line(ecran_simulation, (255, 255, 0), (int(self.start_cone[0]), int(self.start_cone[1])), (int(right_pt[0]), int(right_pt[1])), 2)

            cone_surface = pygame.Surface((constant.LARGEUR_SIMULATION, constant.HAUTEUR_SIMULATION), pygame.SRCALPHA)

            pygame.draw.polygon(cone_surface, (255, 255, 0, 60), self.cone)
            ecran_simulation.blit(cone_surface, (0, 0))

        for zone in self.zones_explorees:
            temp = sum(1 for creature in self.creatures if zone in creature.zones_decouvertes_uniques)
            total_drones = len(self.creatures)
            intensite = (temp / total_drones if total_drones > 0 else 0)
            intensite_effective = 0.5 + 0.5 * intensite
            r = int(constant.NOIR[0] * (1 - intensite_effective) + constant.BLEU[0] * intensite_effective)
            g = int(constant.NOIR[1] * (1 - intensite_effective) + constant.BLEU[1] * intensite_effective)
            b = int(constant.NOIR[2] * (1 - intensite_effective) + constant.BLEU[2] * intensite_effective)
            couleur = (r, g, b)

            x, y = zone[0] * 10, zone[1] * 10
            pygame.draw.circle(
                    ecran_simulation,
                    couleur,
                    (x, y),
                    10,
                    width=1
                )

        for obstacle in self.obstacles:
            obstacle.dessiner(ecran_simulation)

        for brouillage in self.brouillages:
            brouillage.dessiner(ecran_simulation)
        
        if self.homme_a_la_mer:
            self.homme_a_la_mer.dessiner(ecran_simulation)

        for boat in self.boats:
            boat.display(ecran_simulation)
        
        for creature in self.creatures:
            creature.dessiner(ecran_simulation, afficher_cercles_communication, self.brouillages)
        
        if not self.simulation_reussie and all(c.epuise for c in self.creatures) and self.mode == "classic":
            font = pygame.font.Font(None, 40)
            text = font.render("SIMULATION ÉCHOUÉE (Tous les drones sont épuisés) !", True, constant.ROUGE)
            ecran_simulation.blit(text, (constant.LARGEUR_SIMULATION // 2 - text.get_width() // 2, constant.HAUTEUR_SIMULATION // 2))

        if(self.base_coord and self.homme_coord):
            for creature in self.creatures:
                if creature.type_creature == "base":
                    pygame.draw.line(
                        ecran_simulation,
                        constant.ROUGE,
                        (creature.spawn_x, creature.spawn_y),
                        (self.homme_a_la_mer.x, self.homme_a_la_mer.y),
                        width=2
                    )
        ecran.blit(ecran_simulation, (0, constant.HAUTEUR_ENTETE))

        self.afficher_info(ecran)
    
    def afficher_info(self, ecran):
        font_section = pygame.font.Font(None, 24)
        font_info = pygame.font.Font(None, 20)
        
        y_stats = constant.HAUTEUR_ENTETE + 10
        pygame.draw.rect(ecran, constant.NOIR, (constant.LARGEUR_SIMULATION + 5, y_stats, constant.LARGEUR_BARRE_LATERALE - 10, (constant.HAUTEUR-constant.HAUTEUR_ENTETE)//2 - 15), 0, 5)
        pygame.draw.rect(ecran, constant.GRIS, (constant.LARGEUR_SIMULATION + 5, y_stats, constant.LARGEUR_BARRE_LATERALE - 10, (constant.HAUTEUR-constant.HAUTEUR_ENTETE)//2 - 15), 1, 5)

        text_stats_titre = font_section.render("Statistiques", True, constant.GRIS)
        ecran.blit(text_stats_titre, (constant.LARGEUR_SIMULATION + 15, y_stats + 5))
        y_stats += 30

        drones_surface_actifs = sum(1 for c in self.creatures if c.type_creature == "drone_de_surface" and not c.epuise)
        drones_surface_epuises = sum(1 for c in self.creatures if c.type_creature == "drone_de_surface" and c.epuise)
        drones_aerien_actifs = sum(1 for c in self.creatures if c.type_creature == "drone_aerien" and not c.epuise)
        drones_aerien_epuises = sum(1 for c in self.creatures if c.type_creature == "drone_aerien" and c.epuise)
        
        text = font_info.render(f"Drones de Surface: {drones_surface_actifs} (épuisés: {drones_surface_epuises})", True, constant.ROUGE)
        ecran.blit(text, (constant.LARGEUR_SIMULATION + 15, y_stats))
        y_stats += 20
        text = font_info.render(f"Drones Aériens: {drones_aerien_actifs} (épuisés: {drones_aerien_epuises})", True, constant.BLEU)
        ecran.blit(text, (constant.LARGEUR_SIMULATION + 15, y_stats))
        y_stats += 20
        total_zones = (constant.LARGEUR_SIMULATION // 10) * (constant.HAUTEUR_SIMULATION // 10)
        pourcentage = (len(self.zones_explorees) / total_zones) * 100
        text = font_info.render(f"Zones explorées: {pourcentage:.1f}%", True, constant.BLANC)
        ecran.blit(text, (constant.LARGEUR_SIMULATION + 15, y_stats))
        y_stats += 20
        communications_reussies = self.comms_surface_surface + self.comms_surface_aerien + self.comms_aerien_aerien
        communications_echouees = sum(c.communications_echouees for c in self.creatures)
        elapsed_time = (self.temps_fin or time.time()) - self.temps_debut
        text = font_info.render(f"Communications réussies: {communications_reussies}", True, constant.VIOLET)
        ecran.blit(text, (constant.LARGEUR_SIMULATION + 15, y_stats))
        y_stats += 20
        text = font_info.render(f"Communications échouées: {communications_echouees}", True, constant.VIOLET)
        ecran.blit(text, (constant.LARGEUR_SIMULATION + 15, y_stats))
        y_stats += 30
        text = font_info.render(f"Durée depuis le début: {elapsed_time}", True, constant.VIOLET)
        ecran.blit(text, (constant.LARGEUR_SIMULATION + 15, y_stats))
        y_stats += 30

        if self.homme_a_la_mer_decouvert:
            text = font_info.render("HOMME À LA MER DÉCOUVERT !", True, constant.VERT)
            ecran.blit(text, (constant.LARGEUR_SIMULATION + 15, y_stats))
            y_stats += 20
        
        if constant.en_pause:
            constant.font = pygame.font.Font(None, 72)

