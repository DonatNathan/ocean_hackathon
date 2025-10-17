# HALM_IHM_HEADLESS_V6.py
import random
import math
import sys
import time
import json
import os
from datetime import datetime
import concurrent.futures
from PIL import Image, ImageDraw

# =============================================================================
# SECTION 1: CONFIGURATION DE LA SIMULATION
# =============================================================================

# Configuration générale
LARGEUR_SIMULATION = 1200
HAUTEUR_SIMULATION = 840
FPS = 60
FACTEUR_ACCELERATION = 1

# Configuration pour les exécutions en parallèle
NOMBRE_SIMULATIONS_A_LANCER = 10
PROCESSUS_PARALLELES_MAX = 4

# Paramètres de la mission
TEMPS_MISSION_MAX_SECONDES = 60.0
GENERER_IMAGES_ZONE = True

# Paramètres par défaut pour chaque simulation
NB_DRONES_SURFACE_DEFAUT = 5
NB_DRONES_AERIEN_DEFAUT = 5
SPAWN_X_DEFAUT = 100
SPAWN_Y_DEFAUT = 100

# Bornes pour la génération aléatoire
MIN_OBSTACLE_PERCENT = 8.0
MAX_OBSTACLE_PERCENT = 12.0
MIN_BROUILLAGE_PERCENT = 10.0
MAX_BROUILLAGE_PERCENT = 20.0

# Couleurs
MARRON = (139, 69, 19)
VIOLET = (138, 43, 226)
JAUNE = (255, 255, 0)
VERT = (0, 255, 0)
ROUGE_CLAIR = (255, 100, 100)
BLEU_CLAIR = (100, 100, 255)

# =============================================================================
# SECTION 2: CLASSES DE LA SIMULATION
# =============================================================================

class Logger:
    def __init__(self, simulation_id):
        self.simulation_id = simulation_id
        self.logs = []
        self.frame_count = 0
        self.start_time = time.time()
        
    def log_event(self, event_type, data):
        timestamp = time.time() - self.start_time
        self.logs.append({
            "frame": self.frame_count, "timestamp": timestamp,
            "event_type": event_type, "data": data
        })
    
    def log_frame(self, creatures_states, simulation_state):
        frame_data = { "creatures": [], "simulation": simulation_state }
        for c in creatures_states:
            frame_data["creatures"].append({
                "id": c.creature_id, "x": c.x, "y": c.y, "type": c.type_creature,
                "a_trouve_homme_mer": c.a_trouve_homme_mer, "en_repos": c.en_repos,
                "retour_spawn": c.retour_spawn, "epuise": c.epuise,
                "zones_explorees_count": len(c.zone_exploree),
                "communications_reçues": len(c.communications_reçues),
            })
        self.log_event("frame_state", frame_data)
        self.frame_count += 1
    
    def save_logs(self):
        if not os.path.exists("logs"): os.makedirs("logs")
        filepath = os.path.join("logs", f"sim_{self.simulation_id}_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        log_data = {
            "metadata": {
                "simulation_id": self.simulation_id, "total_frames": self.frame_count,
                "duration": time.time() - self.start_time,
                "screen_size": [LARGEUR_SIMULATION, HAUTEUR_SIMULATION],
                "created_at": datetime.now().isoformat()
            }, "events": self.logs
        }
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            print(f"[{self.simulation_id}] Logs sauvegardés dans: {filepath}")
        except Exception as e:
            print(f"[{self.simulation_id}] Erreur lors de la sauvegarde des logs: {e}")

class Drone:
    def __init__(self, x, y, spawn_x, spawn_y, type_creature="drone_de_surface", logger=None, creature_id=0):
        self.x, self.y = x, y
        self.spawn_x, self.spawn_y = spawn_x, spawn_y
        self.type_creature, self.creature_id = type_creature, creature_id
        self.angle = random.uniform(0, 2 * math.pi)
        self.logger = logger
        
        self.communications_reçues = set()
        self.communications_envoyees, self.communications_echouees = 0, 0
        self.derniere_communication, self.cooldown_communication = {}, 1.0
        self.tentatives_communication = 0
        
        self.temps_depuis_spawn, self.en_repos = 0, False
        self.temps_repos_debut, self.retour_spawn, self.epuise = 0, False, False
        
        self.trajets_complets, self.temps_trajets = 0, []
        self.temps_debut_trajet = time.time()
        self.distance_parcourue = 0
        self.zone_exploree = set()
        self.zones_decouvertes_uniques = set()
        self.a_trouve_homme_mer = False
        self.temps_premiere_decouverte_homme_mer = None
        self.temps_changement_direction = 0
        
        # --- NOUVEAU MECANISME POUR LIMITER LA FRÉQUENCE DES COMMUNICATIONS ---
        self.last_comm_check_time = 0
        self.comm_check_interval = 1.0 / FPS  # On ne vérifie que 60 fois par seconde
        
        if type_creature == "drone_de_surface":
            self.vitesse = FACTEUR_ACCELERATION * 13.8 / FPS
            self.zone_decouverte = 15
            self.temps_avant_repos, self.duree_repos, self.rayon_communication = 40, 20, 50
        else: # drone_aerien
            self.vitesse = FACTEUR_ACCELERATION * 27.7 / FPS
            self.zone_decouverte = 30
            self.temps_avant_repos, self.duree_repos, self.rayon_communication = 20, 15, 80
        
        if self.logger:
             self.logger.log_event("creature_created", {"id": creature_id, "type": type_creature})

    def est_dans_zone_brouillage(self, brouillages):
        return any(b.x <= self.x < b.x + b.largeur and b.y <= self.y < b.y + b.hauteur for b in brouillages)

    def communiquer_avec(self, autre, brouillages, simulation):
        # --- CORRECTION: Logique de comptage alignée sur HALM_IHM44.py ---
        # La tentative est comptée même si le drone est en cooldown.
        self.tentatives_communication += 1
        
        if autre.creature_id in self.derniere_communication and time.time() - self.derniere_communication[autre.creature_id] < self.cooldown_communication:
            return False
        
        if self.est_dans_zone_brouillage(brouillages) or autre.est_dans_zone_brouillage(brouillages):
            self.communications_echouees += 1
            return False
        
        self.communications_reçues.add(autre.creature_id)
        autre.communications_reçues.add(self.creature_id)
        self.communications_envoyees += 1
        autre.communications_envoyees += 1
        
        now = time.time()
        self.derniere_communication[autre.creature_id] = now
        autre.derniere_communication[self.creature_id] = now
        
        t1, t2 = self.type_creature, autre.type_creature
        if t1 == "drone_de_surface" and t2 == "drone_de_surface": simulation.comms_surface_surface += 1
        elif t1 == "drone_aerien" and t2 == "drone_aerien": simulation.comms_aerien_aerien += 1
        else: simulation.comms_surface_aerien += 1
        return True
    
    def verifier_communications(self, autres, brouillages, simulation):
        for autre in autres:
            if autre.creature_id != self.creature_id and not autre.epuise and not self.epuise:
                dist = math.hypot(self.x - autre.x, self.y - autre.y)
                if dist <= (self.rayon_communication + autre.rayon_communication) / 2:
                    self.communiquer_avec(autre, brouillages, simulation)
    
    def deplacer(self, obstacles, homme_a_la_mer, autres, brouillages, simulation):
        if self.epuise: return
        self.temps_depuis_spawn += 1/FPS

        # --- NOUVEAU: Appel à la vérification de communication limité dans le temps ---
        current_time = time.time()
        if not self.en_repos and (current_time - self.last_comm_check_time > self.comm_check_interval):
            self.verifier_communications(autres, brouillages, simulation)
            self.last_comm_check_time = current_time
        
        if not self.en_repos and not self.retour_spawn and self.temps_depuis_spawn >= self.temps_avant_repos:
            self.retour_spawn = True
        
        if self.retour_spawn:
            dist_spawn = math.hypot(self.x - self.spawn_x, self.y - self.spawn_y)
            if self.temps_depuis_spawn > self.temps_avant_repos + 5 and dist_spawn > 10:
                self.epuise = True
                return
            if dist_spawn < 5:
                self.en_repos, self.retour_spawn = True, False
                self.temps_repos_debut = time.time()
                self.x, self.y = self.spawn_x, self.spawn_y
                if self.temps_debut_trajet:
                    self.temps_trajets.append(time.time() - self.temps_debut_trajet)
                    self.trajets_complets += 1
                return
            else:
                self.angle = math.atan2(self.spawn_y - self.y, self.spawn_x - self.x)
        
        elif self.en_repos:
            if time.time() - self.temps_repos_debut >= self.duree_repos:
                self.en_repos = False
                self.temps_depuis_spawn, self.temps_debut_trajet = 0, time.time()
            else:
                return
        
        else: # Exploration
            self.temps_changement_direction += 1
            if self.temps_changement_direction > 60:
                self.angle += random.uniform(-0.5, 0.5)
                self.temps_changement_direction = 0
            if self.type_creature == "drone_de_surface":
                for o in obstacles:
                    if o.x <= self.x < o.x + o.largeur and o.y <= self.y < o.y + o.hauteur:
                        self.angle = math.atan2(self.y - (o.y + o.hauteur/2), self.x - (o.x + o.largeur/2))
            if self.a_trouve_homme_mer:
                self.angle = math.atan2(homme_a_la_mer.y - self.y, homme_a_la_mer.x - self.x)
        
        nx, ny = self.x + math.cos(self.angle) * self.vitesse, self.y + math.sin(self.angle) * self.vitesse
        
        ok = 0 <= nx < LARGEUR_SIMULATION and 0 <= ny < HAUTEUR_SIMULATION
        if ok and self.type_creature == "drone_de_surface":
            if any(o.x <= nx < o.x + o.largeur and o.y <= ny < o.y + o.hauteur for o in obstacles):
                ok = False
        
        if ok:
            self.distance_parcourue += math.hypot(nx - self.x, ny - self.y)
            self.x, self.y = nx, ny
        else:
            self.angle += math.pi
        
        if not self.epuise and not self.en_repos:
            if not self.a_trouve_homme_mer and math.hypot(self.x - homme_a_la_mer.x, self.y - homme_a_la_mer.y) < self.zone_decouverte:
                self.a_trouve_homme_mer, self.temps_premiere_decouverte_homme_mer = True, time.time()
            
            r_exp = self.zone_decouverte // 10
            for dx in range(-r_exp, r_exp + 1):
                for dy in range(-r_exp, r_exp + 1):
                    if dx*dx + dy*dy <= r_exp*r_exp:
                        self.zone_exploree.add((int((self.x + dx*10)//10), int((self.y + dy*10)//10)))

class Obstacle:
    def __init__(self, x, y, largeur, hauteur): self.x, self.y, self.largeur, self.hauteur = x, y, largeur, hauteur
class Brouillage:
    def __init__(self, x, y, largeur, hauteur): self.x, self.y, self.largeur, self.hauteur = x, y, largeur, hauteur
class HommeALaMer:
    def __init__(self, x, y): self.x, self.y = x, y

class Simulation:
    def __init__(self, simulation_id, config, image_dir=None, stats_dir=None):
        self.simulation_id = simulation_id
        self.image_dir = image_dir
        self.stats_dir = stats_dir
        
        self.nb_drones_surface, self.nb_drones_aerien = config['nb_drones_surface'], config['nb_drones_aerien']
        self.spawn_x, self.spawn_y = config['spawn_x'], config['spawn_y']
        
        self.min_obstacle_percent, self.max_obstacle_percent = config['min_obstacle_percent'], config['max_obstacle_percent']
        self.min_brouillage_percent, self.max_brouillage_percent = config['min_brouillage_percent'], config['max_brouillage_percent']
        self.pourcentage_obstacle_reel, self.pourcentage_brouillage_reel = 0, 0

        self.logger = Logger(simulation_id)
        self.creatures, self.obstacles, self.brouillages = [], [], []
        self.homme_a_la_mer = None
        self.zones_explorees = set()
        self.homme_a_la_mer_decouvert = False
        self.temps_debut, self.temps_fin = time.time(), None
        self.simulation_reussie = False
        self.raison_echec = "N/A"
        self.premiere_decouverte_homme_mer, self.qui_a_trouve_homme_mer = None, None
        self.pause_automatique = False
        self.comms_surface_surface, self.comms_surface_aerien, self.comms_aerien_aerien = 0, 0, 0
        self.next_creature_id = 0
        
        self.generer_monde()
    
    def get_next_creature_id(self):
        cid = self.next_creature_id; self.next_creature_id += 1; return cid
    
    def generer_monde(self):
        for _ in range(self.nb_drones_surface): self.creatures.append(Drone(self.spawn_x, self.spawn_y, self.spawn_x, self.spawn_y, "drone_de_surface", self.logger, self.get_next_creature_id()))
        for _ in range(self.nb_drones_aerien): self.creatures.append(Drone(self.spawn_x, self.spawn_y, self.spawn_x, self.spawn_y, "drone_aerien", self.logger, self.get_next_creature_id()))
        
        surface_totale = LARGEUR_SIMULATION * HAUTEUR_SIMULATION
        
        obs_p = random.uniform(self.min_obstacle_percent, self.max_obstacle_percent)
        s_obs_cible = surface_totale * (obs_p / 100.0)
        s_obs_act = 0
        while s_obs_act < s_obs_cible:
            l, h = random.randint(20, 80), random.randint(20, 80)
            x, y = random.randint(0, LARGEUR_SIMULATION - l), random.randint(0, HAUTEUR_SIMULATION - h)
            self.obstacles.append(Obstacle(x, y, l, h)); s_obs_act += l * h
        self.pourcentage_obstacle_reel = (s_obs_act / surface_totale) * 100
        
        bro_p = random.uniform(self.min_brouillage_percent, self.max_brouillage_percent)
        s_bro_cible = surface_totale * (bro_p / 100.0)
        s_bro_act = 0
        while s_bro_act < s_bro_cible:
            l, h = random.randint(40, 120), random.randint(40, 120)
            x, y = random.randint(0, LARGEUR_SIMULATION - l), random.randint(0, HAUTEUR_SIMULATION - h)
            self.brouillages.append(Brouillage(x, y, l, h)); s_bro_act += l * h
        self.pourcentage_brouillage_reel = (s_bro_act / surface_totale) * 100
        
        zx, zy = random.randint(0, 2), random.randint(0, 2)
        zl, zh = LARGEUR_SIMULATION / 3, HAUTEUR_SIMULATION / 3
        while True:
            hx, hy = random.randint(int(zx*zl), int((zx+1)*zl)), random.randint(int(zy*zh), int((zy+1)*zh))
            if not any(o.x <= hx < o.x + o.largeur and o.y <= hy < o.y + o.hauteur for o in self.obstacles):
                self.homme_a_la_mer = HommeALaMer(hx, hy); break
        
        if self.image_dir: self.generer_image_zone()

    def generer_image_zone(self):
        try:
            img = Image.new('RGB', (LARGEUR_SIMULATION, HAUTEUR_SIMULATION), 'white')
            draw = ImageDraw.Draw(img)
            for o in self.obstacles: draw.rectangle([o.x, o.y, o.x + o.largeur, o.y + o.hauteur], fill=MARRON)
            for b in self.brouillages: draw.rectangle([b.x, b.y, b.x + b.largeur, b.y + b.hauteur], fill=VIOLET)
            r = 10; draw.ellipse([self.homme_a_la_mer.x-r, self.homme_a_la_mer.y-r, self.homme_a_la_mer.x+r, self.homme_a_la_mer.y+r], fill=JAUNE)
            r = 15; draw.ellipse([self.spawn_x-r, self.spawn_y-r, self.spawn_x+r, self.spawn_y+r], outline=VERT, width=3)
            img.save(os.path.join(self.image_dir, f"{self.simulation_id}_zone.png"))
        except Exception as e:
            print(f"[{self.simulation_id}] Erreur image: {e}")

    def mettre_a_jour(self):
        if self.pause_automatique: return
        
        if time.time() - self.temps_debut > TEMPS_MISSION_MAX_SECONDES:
            self.pause_automatique, self.simulation_reussie, self.raison_echec = True, False, "Temps écoulé"
            return
        if not self.homme_a_la_mer_decouvert and all(c.epuise for c in self.creatures):
            self.pause_automatique, self.simulation_reussie, self.raison_echec = True, False, "Épuisement des drones"
            return
            
        for c in self.creatures:
            c.deplacer(self.obstacles, self.homme_a_la_mer, self.creatures, self.brouillages, self)
            if c.a_trouve_homme_mer and not self.homme_a_la_mer_decouvert:
                self.homme_a_la_mer_decouvert = True
                self.simulation_reussie = True
                self.premiere_decouverte_homme_mer = c.temps_premiere_decouverte_homme_mer
                self.qui_a_trouve_homme_mer = f"{c.type_creature}_{c.creature_id}"
                self.pause_automatique = True
                break
        
        self.zones_explorees.update(*(c.zone_exploree for c in self.creatures))
    
    def sauvegarder_statistiques(self):
        self.temps_fin = time.time()
        duree = self.temps_fin - self.temps_debut
        
        stats_surface = self._calculer_stats_type("drone_de_surface")
        stats_aerien = self._calculer_stats_type("drone_aerien")

        comms_reussies = self.comms_surface_surface + self.comms_surface_aerien + self.comms_aerien_aerien
        tentatives_totales = sum(c.tentatives_communication for c in self.creatures)
        comms_echouees = sum(c.communications_echouees for c in self.creatures)
        drones_communicants = sum(1 for c in self.creatures if len(c.communications_reçues) > 0)
        creatures_epuisees = sum(1 for c in self.creatures if c.epuise)
        
        temps_decouverte = self.premiere_decouverte_homme_mer - self.temps_debut if self.premiere_decouverte_homme_mer else None
        
        statistiques = {
            "timestamp": datetime.now().isoformat(),
            "duree_simulation_secondes": round(duree, 2),
            "simulation_reussie": self.simulation_reussie,
            "temps_decouverte_homme_mer": round(temps_decouverte, 2) if temps_decouverte else None,
            "qui_a_trouve_homme_mer": self.qui_a_trouve_homme_mer,
            
            "configuration": {
                "nombre_drones_surface": self.nb_drones_surface, "nombre_drones_aerien": self.nb_drones_aerien,
                "spawn_position": [self.spawn_x, self.spawn_y],
                "homme_a_la_mer_position": [self.homme_a_la_mer.x, self.homme_a_la_mer.y],
                "nombre_obstacles": len(self.obstacles), "nombre_brouillages": len(self.brouillages),
                "pourcentage_brouillage_reel": round(self.pourcentage_brouillage_reel, 2),
            },
            
            "resultats_globaux": {
                "creatures_totales": len(self.creatures),
                "creatures_actives": len(self.creatures) - creatures_epuisees,
                "creatures_epuisees": creatures_epuisees,
                "taux_epuisement": round((creatures_epuisees / len(self.creatures)) * 100, 2) if self.creatures else 0,
                "zones_explorees": len(self.zones_explorees),
                "pourcentage_exploration": round((len(self.zones_explorees) / ((LARGEUR_SIMULATION//10)*(HAUTEUR_SIMULATION//10))) * 100, 2)
            },
            
            "statistiques_communication": {
                "tentatives_totales": tentatives_totales, "communications_reussies": comms_reussies,
                "communications_echouees": comms_echouees,
                "repartition_communications": {
                    "surface_avec_surface": self.comms_surface_surface, "surface_avec_aerien": self.comms_surface_aerien,
                    "aerien_avec_aerien": self.comms_aerien_aerien
                },
                "taux_reussite_communication": round((comms_reussies / tentatives_totales) * 100, 2) if tentatives_totales > 0 else 0,
                "communications_par_drone": round(comms_reussies / len(self.creatures), 2) if self.creatures else 0,
                "drones_communicants": drones_communicants,
                "taux_drones_communicants": round((drones_communicants / len(self.creatures)) * 100, 2) if self.creatures else 0
            },
            
            "statistiques_drones_surface": stats_surface,
            "statistiques_drones_aerien": stats_aerien,
            
            "comparaison": {
                "efficacite_drones_surface": round(stats_surface.get("zones_decouverte_par_creature", 0), 2),
                "efficacite_drones_aerien": round(stats_aerien.get("zones_decouverte_par_creature", 0), 2),
                "temps_decouverte_moyen_surface": stats_surface.get("temps_moyen_decouverte_homme_mer"),
                "temps_decouverte_moyen_aerien": stats_aerien.get("temps_moyen_decouverte_homme_mer"),
                "taux_reussite_com_surface": round(stats_surface.get("taux_reussite_communication", 0), 2),
                "taux_reussite_com_aerien": round(stats_aerien.get("taux_reussite_communication", 0), 2)
            }
        }
        
        filepath = os.path.join(self.stats_dir, f"sim_{self.simulation_id}_stats.json")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(statistiques, f, indent=2, ensure_ascii=False)
            print(f"[{self.simulation_id}] Statistiques sauvegardées: {filepath}")
            return filepath
        except Exception as e:
            print(f"[{self.simulation_id}] Erreur sauvegarde stats: {e}")
            return None

    def _calculer_stats_type(self, type_creature):
        creatures = [c for c in self.creatures if c.type_creature == type_creature]
        if not creatures: return {}
        
        epuisees = sum(1 for c in creatures if c.epuise)
        trajets_totaux = sum(c.trajets_complets for c in creatures)
        tous_temps = [t for c in creatures for t in c.temps_trajets]
        
        zones_decouvertes = sum(len(c.zone_exploree) for c in creatures)
        duree = self.temps_fin - self.temps_debut
        
        ont_trouve = sum(1 for c in creatures if c.a_trouve_homme_mer)
        temps_decouverte = [c.temps_premiere_decouverte_homme_mer - self.temps_debut for c in creatures if c.a_trouve_homme_mer]
        
        tentatives = sum(c.tentatives_communication for c in creatures)
        echouees = sum(c.communications_echouees for c in creatures)
        
        if type_creature == "drone_de_surface":
            reussies = (2 * self.comms_surface_surface) + self.comms_surface_aerien
        else:
            reussies = (2 * self.comms_aerien_aerien) + self.comms_surface_aerien
        
        return {
            "nombre": len(creatures), "epuisees": epuisees,
            "taux_epuisement": round((epuisees / len(creatures)) * 100, 2),
            "trajets_complets_total": trajets_totaux,
            "trajets_par_creature": round(trajets_totaux / len(creatures), 2),
            "temps_trajet_moyen": round(sum(tous_temps) / len(tous_temps), 2) if tous_temps else 0,
            "distance_moyenne": round(sum(c.distance_parcourue for c in creatures) / len(creatures), 2),
            "zones_decouvertes_total": zones_decouvertes,
            "zones_decouverte_par_creature": round(zones_decouvertes / len(creatures), 2),
            "vitesse_exploration": round(zones_decouvertes / duree, 2) if duree > 0 else 0,
            "ont_trouve_homme_mer": ont_trouve,
            "taux_reussite_homme_mer": round((ont_trouve / len(creatures)) * 100, 2),
            "temps_moyen_decouverte_homme_mer": round(sum(temps_decouverte)/len(temps_decouverte), 2) if temps_decouverte else None,
            "communications_reussies (liens)": reussies,
            "communications_par_creature": round(reussies / len(creatures), 2),
            "tentatives_totales": tentatives, "communications_echouees": echouees,
            "taux_reussite_communication": round((reussies / tentatives) * 100, 2) if tentatives > 0 else 0
        }

# =============================================================================
# SECTION 3: FONCTION D'EXÉCUTION
# =============================================================================

def run_single_simulation(simulation_id, image_dir=None, stats_dir=None):
    print(f"[Sim-{simulation_id}] Lancement...")
    start_time = time.time()
    
    config = {
        'nb_drones_surface': NB_DRONES_SURFACE_DEFAUT, 'nb_drones_aerien': NB_DRONES_AERIEN_DEFAUT,
        'spawn_x': SPAWN_X_DEFAUT, 'spawn_y': SPAWN_Y_DEFAUT,
        'min_obstacle_percent': MIN_OBSTACLE_PERCENT, 'max_obstacle_percent': MAX_OBSTACLE_PERCENT,
        'min_brouillage_percent': MIN_BROUILLAGE_PERCENT, 'max_brouillage_percent': MAX_BROUILLAGE_PERCENT,
    }
    
    sim = Simulation(f"Sim-{simulation_id}", config, image_dir, stats_dir)
    while not sim.pause_automatique:
        sim.mettre_a_jour()

    sim.logger.save_logs()
    stats_path = sim.sauvegarder_statistiques()
    
    end_time = time.time()
    result = f"Succès ({sim.temps_fin - sim.temps_debut:.2f}s)" if sim.simulation_reussie else f"Échec ({sim.raison_echec})"
    print(f"[Sim-{simulation_id}] Terminé en {end_time - start_time:.2f}s. Résultat: {result}.")
    
    return stats_path

# =============================================================================
# SECTION 4: LANCEUR PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    print(f"Lancement de {NOMBRE_SIMULATIONS_A_LANCER} simulations (max {PROCESSUS_PARALLELES_MAX} à la fois).")
    
    batch_folder_name = f"Session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    stats_main_dir = os.path.join("statistiques", batch_folder_name)
    os.makedirs(stats_main_dir, exist_ok=True)
    print(f"Les statistiques seront sauvegardées dans: {stats_main_dir}")

    image_main_dir = None
    if GENERER_IMAGES_ZONE:
        image_main_dir = os.path.join("imageZones", batch_folder_name)
        os.makedirs(image_main_dir, exist_ok=True)
        print(f"Les images des zones seront sauvegardées dans: {image_main_dir}")

    with concurrent.futures.ProcessPoolExecutor(max_workers=PROCESSUS_PARALLELES_MAX) as executor:
        tasks = [executor.submit(run_single_simulation, i, image_main_dir, stats_main_dir) for i in range(NOMBRE_SIMULATIONS_A_LANCER)]
        results = [future.result() for future in concurrent.futures.as_completed(tasks)]

    succes, echecs_temps, echecs_epuisement, total_temps = 0, 0, 0, 0
    for file in results:
        if file and os.path.exists(file):
            with open(file, 'r') as f:
                data = json.load(f)
                if data['simulation_reussie']:
                    succes += 1
                    total_temps += data['temps_decouverte_homme_mer']
                else:
                    if "Temps" in data.get("raison_echec", ""):
                        echecs_temps += 1
                    else:
                        echecs_epuisement += 1

    print("\n" + "="*40 + "\n       RÉSUMÉ GLOBAL\n" + "="*40)
    print(f"Simulations terminées : {len(results)}")
    print(f"  - Succès : {succes}")
    print(f"  - Échecs  : {echecs_temps + echecs_epuisement} (Temps: {echecs_temps}, Épuisement: {echecs_epuisement})")
    if succes > 0:
        print(f"  - Temps de découverte moyen : {total_temps / succes:.2f}s")
    print("="*40)
