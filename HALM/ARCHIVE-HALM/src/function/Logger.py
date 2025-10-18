import time
import json
import os
from datetime import datetime
from utils import constant

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
                "fps": constant.FPS,
                "screen_size": [constant.LARGEUR_SIMULATION, constant.HAUTEUR_SIMULATION],
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