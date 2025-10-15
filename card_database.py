import os
import json
import numpy as np
from typing import List, Tuple, Dict, Optional
import cv2

# --- File Paths ---
DB_FILE = os.path.join("card_database", "card_data.json")
TEMPLATES_PATH = os.path.join("card_database", "templates")

class CardDatabase:
    """Database system for storing and retrieving card templates and information."""
    
    def __init__(self):
        self.card_data: Dict = {}
        self.load_card_data()
        self.template_cache: Dict = {} # Cache for loaded CV templates

    def load_card_data(self):
        """Loads card metadata from the JSON file."""
        if not os.path.exists(DB_FILE):
            print(f"[ERROR] Database file not found at: {DB_FILE}")
            # Use data from the 5 pilot cards as a robust fallback
            self.card_data = self._create_default_data()
            return

        try:
            with open(DB_FILE, 'r') as f:
                # Assuming the JSON file structure has a top-level 'cards' key
                self.card_data = json.load(f)['cards']
            print(f"[DB] Loaded {len(self.card_data)} card entries.")
        except Exception as e:
            print(f"[ERROR] Failed to load card data: {e}")
            self.card_data = self._create_default_data()

    def _create_default_data(self) -> Dict:
        """Creates minimal default data if the JSON file fails to load."""
        print("[DB] Using minimal placeholder card data for 5 pilot cards.")
        # We must include the 5 cards you collected data for to avoid errors.
        return {
            "2_hearts": {"value": "2", "suit": "Hearts", "name": "Two of Hearts"},
            "5_diamonds": {"value": "5", "suit": "Diamonds", "name": "Five of Diamonds"},
            "7_clubs": {"value": "7", "suit": "Clubs", "name": "Seven of Clubs"},
            "8_spades": {"value": "8", "suit": "Spades", "name": "Eight of Spades"},
            "A_clubs": {"value": "A", "suit": "Clubs", "name": "Ace of Clubs"},
        }

    def get_card_info(self, value: str, suit: str) -> Optional[Dict]:
        """Gets complete information for a specific card."""
        key = f"{value}_{suit}".lower()
        return self.card_data.get(key)
    
    def get_blackjack_value(self, value: str) -> List[int]:
        """Gets the blackjack value(s) (e.g., [1, 11] for Ace)."""
        # This is a robust placeholder for blackjack scoring
        value_map = {'A': [1, 11], 'K': [10], 'Q': [10], 'J': [10]}
        if value.isdigit():
            return [int(value)]
        return value_map.get(value, [0])

    def list_available_templates(self) -> List[str]:
        """Lists all card keys present in the database (used for checking completeness)."""
        return list(self.card_data.keys())


# --- Legacy/Template Classes (Required only for satisfying modular_blackjack_system imports) ---

class TemplateCardRecognition:
    """Placeholder for the old template matching logic."""
    def __init__(self, db):
        self.db = db
    
    def identify_card_from_corner(self, corner_image) -> Tuple[str, str, float]:
        """Placeholder identity - will always be overwritten by CNN logic later."""
        return "Unknown", "Unknown", 0.0 # Return low confidence 0.0

class TemplateTrainer:
    """Placeholder for the legacy template training mode."""
    def __init__(self, db):
        self.db = db
    
    def start_template_collection(self):
        """Simulates the start of the template collection mode."""
        print("[TRAINER] Legacy Template Trainer running (not used by CNN mode).")
        # In the real code, this would open the camera and collect templates.
