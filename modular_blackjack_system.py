import cv2
import pyttsx3
import speech_recognition as sr
import time
import random
from typing import List, Dict, Optional, Tuple
# --- NEW IMPORTS FOR THREADING AND QUEUES ---
import threading
from queue import Queue
# --- END NEW IMPORTS ---
from cnn_recognition_module import CNNRecognitionModule
from card_database import CardDatabase
from cv_detection_module import CardDetector, CardRegionExtractor
from blackjack_logic import BlackjackGameStateManager

class AudioManager:
    """Manages all text-to-speech and speech recognition functionality"""
    
    def __init__(self):
        self.tts_engine = pyttsx3.init()
        self.setup_tts()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.calibrate_microphone()
    
    def setup_tts(self):
        self.tts_engine.setProperty('rate', 150)
        self.tts_engine.setProperty('volume', 0.9)
    
    def speak(self, text: str):
        print(f"[SPEECH] {text}")
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()
    
    def calibrate_microphone(self):
        try:
            with self.microphone as source:
                print("Calibrating microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
        except Exception as e:
            print(f"Mic calibration failed: {e}")
    
    def listen_for_command(self, timeout: int = 5) -> Optional[str]:
        try:
            with self.microphone as source:
                print("[LISTENING]...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=4)
            command = self.recognizer.recognize_google(audio).lower().strip()
            print(f"[HEARD] {command}")
            return command
        except (sr.WaitTimeoutError, sr.UnknownValueError, sr.RequestError):
            # Suppress console logs for timeouts to keep it clean
            return None


class AccessibleBlackjackSystem:
    """Main system that coordinates all components"""
    
    def __init__(self):
        self.audio = AudioManager()
        self.card_db = CardDatabase()
        self.cnn_recognizer = CNNRecognitionModule()
        self.card_detector = CardDetector()
        self.card_extractor = CardRegionExtractor()
        self.blackjack = BlackjackGameStateManager(self.card_db)
        self.running = True
        self.current_mode = "menu"

        # --- NEW ATTRIBUTES FOR HIGH FPS ---
        self.command_queue = Queue() # Thread-safe queue for voice commands
        self.audio_thread = None     # Placeholder for our background thread
        # --- END NEW ATTRIBUTES ---

        self.audio.speak("System initialized successfully!")

    # --- NEW METHOD: RUNS IN THE BACKGROUND TO LISTEN FOR VOICE COMMANDS ---
    def _listen_in_background(self):
        """This function runs on a separate thread and continuously listens for commands."""
        while self.running:
            command = self.audio.listen_for_command(timeout=3)
            if command:
                self.command_queue.put(command) # Add heard command to the queue
            time.sleep(0.1) # Prevents the thread from using 100% CPU

    def main_menu(self):
        # Start the audio listening thread if it's not already running
        if self.audio_thread is None or not self.audio_thread.is_alive():
            self.audio_thread = threading.Thread(target=self._listen_in_background, daemon=True)
            self.audio_thread.start()

        while self.running and self.current_mode == "menu":
            self.audio.speak("Main Menu. Say 'play blackjack', 'test detection', or 'quit'.")
            # This now blocks only until a command is heard, then continues
            command = self.command_queue.get() 
            if command: self.handle_menu_command(command)

    def handle_menu_command(self, command: str):
        if "play" in command:
            self.current_mode = "playing"
            self.play_blackjack()
        elif "test" in command: 
            self.current_mode = "testing"
            self.test_detection_mode()
        elif "quit" in command:
            self.audio.speak("Goodbye!")
            self.running = False
    
    # --- FULLY REWRITTEN METHOD FOR HIGH FPS ---
    def play_blackjack(self):
        self.audio.speak("Starting Blackjack!")
        self.blackjack.reset_game()
        self.audio.speak("Place cards and say 'deal', or 'detect cards'.")

        frame_count = 0
        detection_interval = 5  # Run expensive detection only every 5 frames
        stable_cards, current_frame = [], None # Store the latest results

        while self.running and self.current_mode == "playing":
            current_frame = self.card_detector.capture_frame()
            if current_frame is None: continue

            # --- Selective Processing Logic ---
            # Only run the heavy card detection logic periodically
            if frame_count % detection_interval == 0:
                stable_cards, _ = self.card_detector.detect_cards_in_frame(current_frame)
            
            # --- Non-Blocking Command Check ---
            # Check the queue for a command without stopping the video loop
            command = None
            if not self.command_queue.empty():
                command = self.command_queue.get_nowait()

            if command: 
                # Pass the most recent frame and detections to the handler
                self.handle_blackjack_command(command, stable_cards, current_frame)

            # Annotation and display happens on every frame for smoothness
            annotated_frame = self.card_detector.annotate_frame(current_frame, stable_cards)
            cv2.imshow('Accessible Blackjack', annotated_frame)
            
            frame_count += 1
            if cv2.waitKey(1) & 0xFF == ord('q'): break
            
        cv2.destroyAllWindows()
        self.current_mode = "menu"
    
    def handle_blackjack_command(self, command: str, stable_cards: List[Dict], frame):
        if "menu" in command: self.current_mode = "menu"
        elif "detect" in command: self.announce_detected_cards(stable_cards, frame)
        elif "deal" in command and self.blackjack.game_phase == "waiting": self.deal_initial_cards(stable_cards, frame)
        elif "hit" in command and self.blackjack.game_phase == "player_turn": self.player_hit(stable_cards, frame)
        elif "stand" in command and self.blackjack.game_phase == "player_turn": self.player_stand()
        elif "new game" in command:
            self.blackjack.reset_game()
            self.audio.speak("New game started.")
    
    def announce_detected_cards(self, stable_cards: List[Dict], frame):
        if not stable_cards:
            self.audio.speak("No stable cards detected.")
            return
        self.audio.speak(f"I see {len(stable_cards)} stable cards.")
        for i, card_info in enumerate(stable_cards):
            card_image = self.card_extractor.extract_card_roi(frame, card_info)
            card_name, confidence = self.cnn_recognizer.predict_card(card_image)

            print(f"DEBUG: Card {i+1} -> Prediction: {card_name}, Confidence: {confidence:.2f}")

            if confidence > 0.5:
                self.audio.speak(f"Card {i+1}: {card_name.replace('_', ' ').title()} with {confidence:.0%} confidence")
            else:
                self.audio.speak(f"Card {i+1}: Cannot identify clearly.")

    def deal_initial_cards(self, stable_cards: List[Dict], frame):
        if len(stable_cards) < 3:
            self.audio.speak("Need at least 3 stable cards for the deal.")
            return
        stable_cards.sort(key=lambda c: c['bbox'][0])
        
        player_cards_info = stable_cards[:2]
        dealer_card_info = stable_cards[2]
        
        # This part has a slight bug: It adds a card to the logic but doesn't store the tuple
        # For now, we'll keep the logic but it could be improved
        player_hand_tuples = []
        dealer_hand_tuples = []

        for info in player_cards_info:
            img = self.card_extractor.extract_card_roi(frame, info)
            name, conf = self.cnn_recognizer.predict_card(img)
            if conf > 0.5:
                value, suit = name.split('_', 1) # Split only on the first underscore
                player_hand_tuples.append((value, suit))
        
        self.blackjack.player_cards = player_hand_tuples

        img = self.card_extractor.extract_card_roi(frame, dealer_card_info)
        name, conf = self.cnn_recognizer.predict_card(img)
        if conf > 0.5:
            value, suit = name.split('_', 1)
            dealer_hand_tuples.append((value, suit))
        
        self.blackjack.dealer_cards = dealer_hand_tuples

        self.audio.speak("Cards dealt!")
        self.audio.speak(f"Your hand: {self.blackjack.get_hand_description(self.blackjack.player_cards)}")
        self.audio.speak(f"Dealer shows: {self.blackjack.get_hand_description(self.blackjack.dealer_cards)}")
        
        if self.blackjack.is_blackjack(self.blackjack.player_cards):
            self.audio.speak("Blackjack!")
            self.end_game()
        else:
            self.blackjack.game_phase = "player_turn"
            self.audio.speak("Your turn. Say 'hit' or 'stand'.")

    def player_hit(self, stable_cards: List[Dict], frame):
        # This function needs access to the current cards to identify the new one
        # For simplicity, we assume the last card by position is the new one
        if len(stable_cards) <= len(self.blackjack.player_cards) + len(self.blackjack.dealer_cards):
            self.audio.speak("Place the new card and say 'hit' again.")
            return
        
        stable_cards.sort(key=lambda c: c['bbox'][0])
        new_card_info = stable_cards[-1]
        img = self.card_extractor.extract_card_roi(frame, new_card_info)
        name, conf = self.cnn_recognizer.predict_card(img)
        
        if conf > 0.5:
            value, suit = name.split('_', 1)
            new_card_tuple = (value, suit)
            self.blackjack.assign_new_card(stable_cards, self.blackjack.player_cards + self.blackjack.dealer_cards + [new_card_tuple])
            self.audio.speak(f"You drew {value} of {suit}. Your total is now {self.blackjack.calculate_hand_value(self.blackjack.player_cards)}.")
            if self.blackjack.is_bust(self.blackjack.player_cards):
                self.audio.speak("Bust!")
                self.end_game()
        else: self.audio.speak("Cannot identify the new card.")

    def player_stand(self):
        self.audio.speak(f"You stand with {self.blackjack.calculate_hand_value(self.blackjack.player_cards)}.")
        self.blackjack.game_phase = "dealer_turn"
        self.dealer_play()
        
    def dealer_play(self):
        self.audio.speak("Dealer's turn.")
        dealer_total = self.blackjack.calculate_hand_value(self.blackjack.dealer_cards)
        while dealer_total < 17:
            self.audio.speak("Dealer hits.")
            # Simulate a dealer hit for this version
            simulated_card_key = random.choice(list(self.card_db.card_data.keys()))
            value, suit = simulated_card_key.split('_', 1)
            self.blackjack.assign_dealer_hit((value, suit))
            dealer_total = self.blackjack.calculate_hand_value(self.blackjack.dealer_cards)
            self.audio.speak(f"Dealer's total is now {dealer_total}.")
        
        self.end_game()

    def end_game(self):
        self.blackjack.game_phase = "game_over"
        result = self.blackjack.determine_winner()
        self.audio.speak(f"Final hands. You have: {self.blackjack.get_hand_description(self.blackjack.player_cards)}. Dealer has: {self.blackjack.get_hand_description(self.blackjack.dealer_cards)}.")
        result_messages = {
            "player_wins_dealer_bust": "You win! Dealer busted.",
            "dealer_wins_player_bust": "Dealer wins. You busted.",
            "player_blackjack": "Blackjack! You win!",
            "dealer_blackjack": "Dealer has Blackjack. You lose.",
            "player_wins_higher": "You win with a higher score!",
            "dealer_wins_higher": "Dealer wins with a higher score.",
            "push": "It's a push. You tie."
        }
        self.audio.speak(result_messages.get(result, "Game over."))
        self.audio.speak("Say 'new game' or 'menu'.")
        
    def test_detection_mode(self):
        self.audio.speak("Detection test mode. Press 'q' to quit.")
        while self.running and self.current_mode == "testing":
            frame = self.card_detector.capture_frame()
            if frame is None: continue
            stable, _ = self.card_detector.detect_cards_in_frame(frame)
            annotated = self.card_detector.annotate_frame(frame, stable)
            
            for card_info in stable:
                x, y, w, h = card_info['bbox']
                card_image = self.card_extractor.extract_card_roi(frame, card_info)
                card_name, confidence = self.cnn_recognizer.predict_card(card_image)
                if confidence > 0.5:
                    label = f"{card_name.replace('_', ' ').title()} ({confidence:.0%})"
                    cv2.putText(annotated, label, (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            cv2.imshow('Detection Test', annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.current_mode = "menu"
                break
        cv2.destroyAllWindows()
        
    def cleanup(self):
        print("Cleaning up...")
        self.running = False # Signal the background thread to stop
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=1) # Wait briefly for the thread to exit
        self.card_detector.cleanup()
        cv2.destroyAllWindows()
    
    def run(self):
        try:
            self.audio.speak("Welcome to Accessible Blackjack!")
            # The main loop now only handles mode switching
            while self.running:
                if self.current_mode == "menu":
                    self.main_menu()
                # Other modes are handled within their respective methods
                time.sleep(0.5)

        except (KeyboardInterrupt, Exception) as e:
            print(f"System error or interrupt: {e}")
        finally:
            self.cleanup()

if __name__ == "__main__":
    system = AccessibleBlackjackSystem()
    system.run()