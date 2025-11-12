import cv2
import time
import random
from typing import List, Dict, Optional, Tuple
#evan testing
from firebase import firebase

firebaseConfig = {
  'apiKey': "AIzaSyDuUkLD09Xwhon__e-0RoYI0K_-5QBDvyg",
  'authDomain': "blackjack-49d5a.firebaseapp.com",
  'databaseURL': "https://blackjack-49d5a-default-rtdb.firebaseio.com",
  'projectId': "blackjack-49d5a",
  'storageBucket': "blackjack-49d5a.firebasestorage.app",
  'messagingSenderId': "27773902305",
  'appId': "1:27773902305:web:d5c161bbfcdba6e13c46a0",
  'measurementId': "G-7QTF96C5CT"
};

firebase_app = firebase.FirebaseApplication(firebaseConfig['databaseURL'], None)

#evans testing

# Import the other team members' modules
from card_detection import CardDetector  # Ash's Module
import tts_module                             # Bhrett's NEW Module (only TTS is used)

class BlackjackGame:
    """
    This is Evan's module.
    It acts as the central hub, connecting detection (Ash) and 
    audio (Bhrett) to manage the full game.
    
    VERSION: 100% Vision-Driven (No STT)
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
        self.last_player_total: int = 0
       
        self.last_seen_player_hand: Tuple[str, ...] = ()
        self.last_seen_dealer_hand: Tuple[str, ...] = ()
        self.current_stability_count: int = 0
       
        self.REQUIRED_STABILITY: int = 30
       
        # --- Game Phases ---
        self.game_phase: str = "WAITING_FOR_CLEAR"
        self.game_end_announced: bool = False

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
        self.last_player_total = 0
       
        self.last_seen_player_hand = ()
        self.last_seen_dealer_hand = ()
        self.current_stability_count = 0

       
        self.game_phase = "WAITING_FOR_CLEAR"
        self.game_end_announced = False  # Reset the flag
       
        # This is now just an internal reset, the "Welcome"
        # message is handled by the WAITING_FOR_CLEAR state.
        return "" 

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
        #evan testing
        wincount = 0
        #evan testing
        """Compares final totals and returns a result message."""
        if player_total > 21:
            return f"You busted with {player_total}. You lose."
        if dealer_total > 21:
            wincount += 1
            firebase_app.put('game', 'User', 'test', wincount)
            return f"Dealer busted with {dealer_total}. You win!"
        if player_total > dealer_total:
            wincount += 1
            firebase_app.put('game', 'User', 'test', wincount)
            return f"You win with {player_total} to {dealer_total}!"
        if dealer_total > player_total:
            return f"Dealer wins with {dealer_total} to {player_total}."
        return f"It's a push. You both have {player_total}."

    def update_game_state(self):
        """
        This logic function is now only called when a STABLE vision change
        occurs. It is 100% vision-driven.
        
        NEW: It now loops internally to allow for "chained" state updates
        in a single event (e.g., GAME_OVER -> WAITING_FOR_CLEAR -> STARTING).
        """
        
        # This will store the *last* message we want to speak
        # after all chained state updates are done.
        final_message_to_speak = None
        
        # This loop allows the state machine to run multiple times
        # in one call, resolving chained states instantly.
        while True:
            message_to_speak = None
            state_changed = False # Flag to see if we need to loop again

            # 1. Recalculate totals based on the STABLE hands
            self.player_total = self.calculate_hand_value(self.player_hand)
            self.dealer_total = self.calculate_hand_value(self.dealer_hand)

            # 2. Run the State Machine
       
            # --- STATE: WAITING_FOR_CLEAR ---
            if self.game_phase == "WAITING_FOR_CLEAR":
                if len(self.player_hand) == 0 and len(self.dealer_hand) == 0:
                    self.game_phase = "STARTING"
                    message_to_speak = "Table is clear. Please place 2 cards for yourself and 1 for the dealer."
                    state_changed = True # Loop again to check STARTING state

            # --- STATE: STARTING ---
            elif self.game_phase == "STARTING":
                if len(self.player_hand) == 2 and len(self.dealer_hand) == 1:
                    self.game_phase = "PLAYER_TURN"
                    player_total_str = str(self.player_total)
                    dealer_card_str = self.dealer_hand[0]
                    message_to_speak = (f"Cards dealt. You have {player_total_str}. "
                                        f"Dealer shows {dealer_card_str}.")
                    self.last_dealer_total = self.dealer_total
                    self.last_player_total = self.player_total
                    state_changed = True # Loop again to check PLAYER_TURN state
           
            # --- STATE: PLAYER_TURN ---
            elif self.game_phase == "PLAYER_TURN":
                player_hand_changed = self.player_total != self.last_player_total
                dealer_hand_changed = len(self.dealer_hand) > 1 
                
                # 1. Check for Bust (Vision)
                if self.player_total > 21:
                    bust_message = f"You busted with {self.player_total}. You lose."
                    self.speak_and_wait(bust_message, 2.0)
                    message_to_speak = "Game over. Please clear the table to play again."
                    self.game_phase = "GAME_OVER"
                    self.last_player_total = self.player_total
                    state_changed = True
                
                # 2. Check for 21 (Vision)
                elif self.player_total == 21:
                    message_to_speak = "You have 21. Standing automatically."
                    self.game_phase = "DEALER_TURN"

                    self.last_player_total = self.player_total
                    state_changed = True

                # 3. Check for a "Hit" (A new player card appeared)
                elif player_hand_changed:
                    message_to_speak = f"Your total is now {self.player_total}."
                    self.last_player_total = self.player_total
                    # We DON'T set state_changed=True here, because we
                    # want to wait for the next physical action.
                
                # 4. Check for a "Stand" (Dealer's hand changed)
                elif not player_hand_changed and dealer_hand_changed:
                    # --- THIS IS THE FIX FOR "STAND" ---
                    # Speak the "stand" message *immediately*
                    stand_message = f"You stand with {self.player_total}. Dealer's turn."
                    self.speak_and_wait(stand_message, 0.5) # Speak and pause briefly
                    
                    # Now, set the state and allow the loop to continue
                    # *without* setting a new message_to_speak.
                    message_to_speak = None 
                    # --- END FIX ---
                    
                    self.game_phase = "DEALER_TURN"
                    self.last_player_total = self.player_total
                    self.game_end_announced = False
                    state_changed = True # Allow the loop to continue to DEALER_TURN

            # --- STATE: DEALER_TURN ---
            elif self.game_phase == "DEALER_TURN":
                if self.dealer_total >= 17 and not self.game_end_announced:
                    # GAME ENDS
                    self.game_end_announced = True
                    self.last_dealer_total = self.dealer_total
                    
                    if self.dealer_total > 21:
                        dealer_end_message = f"Dealer busts with {self.dealer_total}."
                    else:
                        dealer_end_message = f"Dealer stands with {self.dealer_total}."
                   
                    self.speak_and_wait(dealer_end_message, 1.5)
                    result_message = self.determine_winner(self.player_total, self.dealer_total)
                    self.speak_and_wait(result_message, 2.0)
                   
                    message_to_speak = "Game over. Please clear the table to play again."
                    self.game_phase = "GAME_OVER"
                    state_changed = True
                
                elif self.dealer_total != self.last_dealer_total and self.dealer_total < 17:
                    # Dealer hit, but game continues
                    message_to_speak = f"Dealer total is now {self.dealer_total}."
                    self.last_dealer_total = self.dealer_total
                    # No state change, wait for next card
           
            # --- STATE: GAME_OVER ---
            elif self.game_phase == "GAME_OVER":
                if len(self.player_hand) == 0 and len(self.dealer_hand) == 0:
                    # This is the "new game" signal
                    self.game_phase = "WAITING_FOR_CLEAR"
                    self.reset_game() # Call reset here
                    state_changed = True # Loop again to enter WAITING_FOR_CLEAR
            
            
            # --- Loop Control ---
            
            # If we generated a message, store it.
            # This ensures we only speak the *last* message in a chain.
            if message_to_speak:
                final_message_to_speak = message_to_speak
            
            if state_changed:
                continue # A state changed, so re-run the loop immediately
            else:
                break # No state changed, so we're done for this event

        return final_message_to_speak

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
           
            # --- REMOVED: Get Input from Bhrett's Module (STT) ---
            # voice_command = self.tts.get_command()
           
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

            # --- MODIFIED: Logic only runs on stable vision ---
            if is_now_stable:
                self.player_hand = list(self.last_seen_player_hand)
                self.dealer_hand = list(self.last_seen_dealer_hand)
               
                print(f"[Game Update] Stable State: Phase: {self.game_phase} | "
                      f"Player: {len(self.player_hand)} ({self.calculate_hand_value(self.player_hand)}) | "
                      f"Dealer: {len(self.dealer_hand)} ({self.calculate_hand_value(self.dealer_hand)})")
               
                game_message = self.update_game_state() # --- MODIFIED: No command passed
           
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
