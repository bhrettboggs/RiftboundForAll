from typing import List, Dict, Tuple, Optional
from card_database import CardDatabase # Assuming CardDatabase has correct value lookup

# Type alias for clarity
CardTuple = Tuple[str, str] # (Value, Suit)
DetectedCardInfo = Dict # Dict of card data from CardDetector

class BlackjackGameStateManager:
    """
    Manages the mapping of recognized cards to the game state (player/dealer hands).
    Also handles core blackjack calculations.
    """
    
    def __init__(self, card_database: CardDatabase):
        self.db = card_database
        self.reset_game()
        
    def reset_game(self):
        """Reset all game state variables."""
        self.player_cards: List[CardTuple] = []
        self.dealer_cards: List[CardTuple] = []
        self.game_phase: str = "waiting" # waiting, dealing, player_turn, dealer_turn, game_over
        self.game_result: Optional[str] = None
        
        # Tracking the physical cards (simplified based on the number seen)
        self.cards_in_play_count: int = 0

    # --- Core Blackjack Logic ---

    def calculate_hand_value(self, cards: List[CardTuple]) -> int:
        """Calculate blackjack value of a hand, handling Aces."""
        total = 0
        aces = 0
        
        for value, _ in cards:
            blackjack_values = self.db.get_blackjack_value(value)
            
            if not blackjack_values:
                # Handle unrecognized card value (e.g., set to 0 or 1)
                continue

            if len(blackjack_values) > 1:  # Ace (1/11)
                aces += 1
                total += 11
            else:
                total += blackjack_values[0]
        
        # Handle Aces (convert 11 to 1 if needed to avoid bust)
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        
        return total

    def is_blackjack(self, cards: List[CardTuple]) -> bool:
        """Check if hand is blackjack (21 with exactly 2 cards)."""
        return len(cards) == 2 and self.calculate_hand_value(cards) == 21
    
    def is_bust(self, cards: List[CardTuple]) -> bool:
        """Check if hand is bust (over 21)."""
        return self.calculate_hand_value(cards) > 21

    # --- Card Assignment Logic (Crucial for CV integration) ---

    def assign_initial_cards(self, identified_cards: List[CardTuple]):
        """
        Assigns the first 3 or 4 identified cards to player and dealer hands.
        Assumes first 2 cards are player's, next 1 is dealer's upcard.
        """
        if len(identified_cards) < 3:
            return False, "Not enough cards detected for initial deal (need at least 3)."
        
        self.player_cards = identified_cards[:2]
        self.dealer_cards = identified_cards[2:3] # Dealer shows 1 card
        self.cards_in_play_count = len(self.player_cards) + len(self.dealer_cards)
        self.game_phase = "player_turn"
        
        return True, "Initial deal successful."

    def assign_new_card(self, stable_cards_detected: List[DetectedCardInfo], identified_cards: List[CardTuple]) -> Optional[CardTuple]:
        """
        Assigns the next card during a 'Hit' by comparing the newly identified card count
        with the current cards in play count.
        
        Returns: The new CardTuple if successful, otherwise None.
        """
        new_card_count = len(identified_cards)
        
        if new_card_count <= self.cards_in_play_count:
            return None, f"Expected {self.cards_in_play_count + 1} cards, only saw {new_card_count}."
        
        # The new card is the last identified card in the list
        new_card = identified_cards[-1]
        
        # Add to player hand
        self.player_cards.append(new_card)
        self.cards_in_play_count += 1
        
        return new_card, "Player successfully hit."

    def assign_dealer_hit(self, new_card: CardTuple):
        """Adds a card to the dealer's hand and updates the count."""
        self.dealer_cards.append(new_card)
        self.cards_in_play_count += 1

    def determine_winner(self) -> str:
        """Determine game winner based on final hands."""
        player_total = self.calculate_hand_value(self.player_cards)
        dealer_total = self.calculate_hand_value(self.dealer_cards)
        
        if self.is_bust(self.player_cards):
            return "dealer_wins_player_bust"
        
        if self.is_bust(self.dealer_cards):
            return "player_wins_dealer_bust"
        
        if self.is_blackjack(self.player_cards) and self.is_blackjack(self.dealer_cards):
            return "push_both_blackjack"
        elif self.is_blackjack(self.player_cards):
            return "player_blackjack"
        elif self.is_blackjack(self.dealer_cards):
            return "dealer_blackjack"
        
        if player_total > dealer_total:
            return "player_wins_higher"
        elif dealer_total > player_total:
            return "dealer_wins_higher"
        else:
            return "push"
        
    def get_hand_description(self, cards: List[CardTuple], show_total: bool = True) -> str:
        """Get spoken description of a hand."""
        if not cards:
            return "no cards"
        
        descriptions = []
        for value, suit in cards:
            card_info = self.db.get_card_info(value, suit)
            descriptions.append(card_info['name'] if card_info else f"{value} of {suit}")
        
        description = f"{', '.join(descriptions[:-1])} and {descriptions[-1]}" if len(descriptions) > 1 else descriptions[0]
        
        if show_total:
            total = self.calculate_hand_value(cards)
            description += f", total {total}"
        
        return description
