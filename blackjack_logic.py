import cv2
import time
import random
from typing import List, Dict, Optional, Tuple

# Import the other team members' modules
from card_detection import CardDetector  # Ash's Module
import tts_module                             # Bhrett's NEW Module

class BlackjackGame:
    """
    This is Evan's module.
    It acts as the central hub, connecting detection (Ash) and 
    audio (Bhrett) to manage the full game.
    """
    
    def __init__(self):
        print("[GameState] Initializing systems...")
        self.detector = CardDetector()
        self.tts = tts_module.AudioManager()  # Use the real audio module
        self.running = True
        
        self.card_values = {
            'A': 11, 'K': 10, 'Q': 10, 'J': 10, '10': 10, 
            '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2
        }
        
        # --- Stability and State Tracking ---
        self.player_hand: List[str] = []
        self.dealer_hand: List[str] = []
        self.player_total: int = 0
        self.dealer_total: int = 0
        self.last_dealer_total: int = 0
        self.last_player_total: int = 0  # <-- ADDED THIS
        
        self.last_seen_player_hand: Tuple[str, ...] = ()
        self.last_seen_dealer_hand: Tuple[str, ...] = ()
        self.current_stability_count: int = 0
        
        # --- UPDATED: More Stability ---
        self.REQUIRED_STABILITY: int = 30 
        
        # --- Game Phases ---
        self.game_phase: str = "WAITING_FOR_CLEAR"

    def speak_and_wait(self, text: str, wait_time: float = 1.0):
        """
        Speak text and wait for it to finish before continuing.
        Useful for important messages.
        """
        self.tts.speak(text)
        self.tts.wait_for_speech(timeout=5.0)
        time.sleep(wait_time)  # Extra pause for comprehension
        
    def reset_game(self) -> str:
        """Resets the game to its initial state."""
        print("[GameState] Resetting game...")
        self.player_hand = []
        self.dealer_hand = []
        self.player_total = 0
        self.dealer_total = 0
        self.last_dealer_total = 0
        self.last_player_total = 0  # <-- ADDED THIS
        
        self.last_seen_player_hand = ()
        self.last_seen_dealer_hand = ()
        self.current_stability_count = 0
        
        self.game_phase = "WAITING_FOR_CLEAR" 
        
        return "New game. Please clear all cards from the table."

    def calculate_hand_value(self, hand: List[str]) -> int:
        """Calculates the total value of a hand of cards."""
        total = 0
        aces = 0
        for card_id in hand:
            value_str = card_id[:-1] 
            value = self.card_values.get(value_str, 0)
            if value == 11: aces += 1
            total += value
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        return total

    def determine_winner(self, player_total: int, dealer_total: int) -> str:
        """Compares final totals and returns a result message."""
        if player_total > 21:
            return f"You busted with {player_total}. You lose."
        if dealer_total > 21:
            return f"Dealer busted with {dealer_total}. You win!"
        if player_total > dealer_total:
            return f"You win with {player_total} to {dealer_total}!"
        if dealer_total > player_total:
            return f"Dealer wins with {dealer_total} to {player_total}."
        return f"It's a push. You both have {player_total}."

    def update_game_state(self, command: Optional[str]):
        """
        This logic function is now only called when a STABLE vision change
        or a VOICE command occurs.
        """
        message_to_speak = None

        if command:
            command = command.lower().strip()
        
        # --- NEW: Global Commands (The Escape Hatch) ---
        if command:
            if command in ["new game", "play again", "restart", "deal again", "again"]: # <-- MODIFIED
                message_to_speak = self.reset_game()
                return message_to_speak 
            elif command in ["i quit", "quit", "exit", "stop"]: # <-- MODIFIED
                self.running = False
                return None 
        # --- END NEW ---

        # 1. Recalculate totals based on the STABLE hands
        self.player_total = self.calculate_hand_value(self.player_hand)
        self.dealer_total = self.calculate_hand_value(self.dealer_hand)

        # 2. Run the State Machine
        
        # --- STATE: WAITING_FOR_CLEAR ---
        if self.game_phase == "WAITING_FOR_CLEAR":
            if len(self.player_hand) == 0 and len(self.dealer_hand) == 0:
                self.game_phase = "STARTING"
                message_to_speak = "Table is clear. Please place 2 cards for yourself and 1 for the dealer."

        # --- STATE: STARTING ---
        elif self.game_phase == "STARTING":
            if len(self.player_hand) == 2 and len(self.dealer_hand) == 1:
                self.game_phase = "PLAYER_TURN"
                player_total_str = str(self.player_total)
                dealer_card_str = self.dealer_hand[0]
                message_to_speak = (f"Cards dealt. You have {player_total_str}. "
                                    f"Dealer shows {dealer_card_str}. "
                                    "Say 'hit' or 'stand'.") # <-- MODIFIED
                self.last_dealer_total = self.dealer_total
                self.last_player_total = self.player_total  # <-- ADDED THIS
        
        # --- STATE: PLAYER_TURN (REPLACED BLOCK) ---
        elif self.game_phase == "PLAYER_TURN":
            # 1. Check for Bust (Vision)
            if self.player_total > 21:
            # Speak bust message once and wait
                bust_message = f"You busted with {self.player_total}. You lose."
                self.speak_and_wait(bust_message, 2.0)
                
                # Now set the game over prompt
                message_to_speak = "Say 'new game' to play again, or 'i quit' to exit."
                            # --- END MODIFIED BLOCK ---
                
                self.game_phase = "GAME_OVER"
                self.last_player_total = self.player_total # Lock in the total
                
            
            # 2. Check for 21 (Vision)
            elif self.player_total == 21:
                message_to_speak = "You have 21. Standing automatically."
                self.game_phase = "DEALER_TURN"
                self.last_player_total = self.player_total # Lock in the total

            # 3. NEW: Check for Vision Change (if no command)
            # This is the fix. It runs if no voice command was given
            # AND the player's total has changed since we last spoke.
            elif not command and self.player_total != self.last_player_total:
                message_to_speak = f"Your total is now {self.player_total}. Say 'hit' or 'stand'."
                self.last_player_total = self.player_total # Update the last total

            # 4. Check for Voice Commands
            elif command:
                if command in ["i hit", "hit", "hit me", "deal me", "card"]:# <-- MODIFIED
                    message_to_speak = "Hit. Please add your new card."
                    # We update last_player_total so the *next*
                    # vision update will trigger the block above.
                    self.last_player_total = self.player_total 
                elif command in ["stand", "stay", "i stand", "i'm good", "hold"]:
                    message_to_speak = (f"You stand with {self.player_total}. "
                                        "Dealer's turn. Please reveal the dealer's hole card. "
                                        "Keep adding cards until the dealer's total is 17 or more.")
                    self.game_phase = "DEALER_TURN"
                    self.last_player_total = self.player_total # Lock in the total
        
        # --- STATE: DEALER_TURN (Vision-based) ---
        elif self.game_phase == "DEALER_TURN":
            if self.dealer_total != self.last_dealer_total:
                message_to_speak = f"Dealer total is now {self.dealer_total}."
                self.last_dealer_total = self.dealer_total
            
            if self.dealer_total >= 17:
                if self.dealer_total > 21:
                    dealer_end_message = f"Dealer busts with {self.dealer_total}."
                else:
                    dealer_end_message = f"Dealer stands with {self.dealer_total}."
                
                self.tts.speak(dealer_end_message)
                time.sleep(1) 
                
                result_message = self.determine_winner(self.player_total, self.dealer_total)
                self.tts.speak(result_message)
                time.sleep(1)
                
                message_to_speak = "Game over. Say 'new game' to play again, or 'i quit' to exit." # <-- MODIFIED
                self.game_phase = "GAME_OVER"
        
        # --- STATE: GAME_OVER ---
        elif self.game_phase == "GAME_OVER":
            pass
                
        return message_to_speak

    def run(self):
        """The main application loop."""
        
        self.reset_game() 
        self.tts.speak("Welcome to Accessible Blackjack. "
                       "Press 'q' on the keyboard to quit at any time. "
                       "Please clear all cards from the table to begin.")
        
        while self.running:
            # 1. Get Data from Ash's Module
            card_data, frame_to_show = self.detector.get_detected_cards()
            
            if frame_to_show is None:
                print("Error: No frame from camera. Exiting.")
                break
            
            # 2. Get Input from Bhrett's Module (non-blocking)
            voice_command = self.tts.get_command()
            
            # 3. Check for keyboard 'q' to quit
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.running = False
                break
            
            # --- 4. STABILITY LOGIC ---
            current_player_hand_tuple = tuple(sorted([c['id'] for c in card_data if c['owner'] == 'Player']))
            current_dealer_hand_tuple = tuple(sorted([c['id'] for c in card_data if c['owner'] == 'Dealer']))
            
            game_message = None
            
            has_vision_changed = (current_player_hand_tuple != self.last_seen_player_hand) or \
                                 (current_dealer_hand_tuple != self.last_seen_dealer_hand)
            
            if has_vision_changed:
                self.current_stability_count = 0
                self.last_seen_player_hand = current_player_hand_tuple
                self.last_seen_dealer_hand = current_dealer_hand_tuple
            else:
                self.current_stability_count += 1

            # --- 5. RUN GAME LOGIC (EVENT-DRIVEN) ---
            
            is_now_stable = self.current_stability_count == self.REQUIRED_STABILITY

            if voice_command:
                print(f"[Game Update] Voice Command: '{voice_command}'")
                game_message = self.update_game_state(voice_command)
            
            elif is_now_stable:
                self.player_hand = list(self.last_seen_player_hand)
                self.dealer_hand = list(self.last_seen_dealer_hand)
                
                print(f"[Game Update] Stable State: Phase: {self.game_phase} | "
                      f"Player: {len(self.player_hand)} ({self.calculate_hand_value(self.player_hand)}) | "
                      f"Dealer: {len(self.dealer_hand)} ({self.calculate_hand_value(self.dealer_hand)})")
                
                game_message = self.update_game_state(None) # Vision trigger
            
            # 6. Send to Bhrett's Module
            if game_message:
                self.tts.speak(game_message)

            # 7. Show the visual feed
            cv2.imshow("Accessible Blackjack - Game State", frame_to_show)
            
            time.sleep(0.01)

    def cleanup(self):
        """Cleans up resources."""
        print("\n[GameState] Cleaning up and shutting down...")
        self.detector.cleanup()
        self.tts.stop() # Tell the audio threads to stop
        cv2.destroyAllWindows()


if __name__ == "__main__":
    game = BlackjackGame()
    try:
        game.run()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        game.cleanup()