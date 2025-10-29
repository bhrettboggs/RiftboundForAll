import cv2
import pyttsx3
import speech_recognition as sr
import time
import random
from typing import List, Dict, Optional, Tuple, Any
import threading
from queue import Queue, Empty # Import Empty
from roboflow import Roboflow
from card_database import CardDatabase
from blackjack_logic import BlackjackGameStateManager
import os

print(f"DEBUG: Environment ROBOFLOW_API_KEY = {os.environ.get('ROBOFLOW_API_KEY')}")

class AudioManager:
    """Manages all text-to-speech and speech recognition functionality (Improved)"""
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        # --- Speech Rec Improvement: Adjust energy threshold manually ---
        self.recognizer.energy_threshold = 4000 # Default is 300, higher means less sensitive to background noise. Adjust as needed.
        self.recognizer.dynamic_energy_threshold = False # Use the fixed threshold
        # --- End Improvement ---
        self.calibrate_microphone() # Calibrate after setting threshold

    # --- START OF TTS FIX V2 (Copied from previous response) ---
    def speak(self, text: str):
        """Convert text to speech using a fresh engine instance each time with error handling."""
        print(f"[SPEECH] {text}")
        try:
            engine = pyttsx3.init() # Try default first
            engine.setProperty('rate', 150); engine.setProperty('volume', 1.0)
            engine.say(text); engine.runAndWait(); engine.stop()
            del engine; print(f"DEBUG: TTS completed successfully (using default driver).")
            return True
        except Exception as e:
            print(f"!!!!!!!! TTS Error (default driver): {e} !!!!!!!!!!")
            try: # Fallback
                print("DEBUG: Trying TTS with nsss driver...")
                engine = pyttsx3.init(driverName='nsss')
                engine.setProperty('rate', 150); engine.setProperty('volume', 1.0)
                engine.say(text); engine.runAndWait(); engine.stop()
                del engine; print(f"DEBUG: TTS completed successfully (using nsss driver).")
                return True
            except Exception as e2:
                 print(f"!!!!!!!! TTS Error (nsss driver fallback): {e2} !!!!!!!!!!")
                 print(f"!!!!!!!! Text was: {text} !!!!!!!!!!"); return False
    # --- END OF TTS FIX V2 ---

    def calibrate_microphone(self):
        try:
            with self.microphone as source:
                print("Calibrating microphone...")
                # --- Speech Rec Improvement: Longer calibration ---
                self.recognizer.adjust_for_ambient_noise(source, duration=2) # Increased to 2 seconds
                # --- End Improvement ---
                print(f"Adjusted energy threshold to: {self.recognizer.energy_threshold}") # See calibrated value if dynamic was True
        except Exception as e:
            print(f"Mic calibration failed: {e}")
            self.speak("Microphone calibration failed.") # Audio feedback

    def listen_for_command(self, timeout: int = 5) -> Optional[str]:
        command = None
        # Use the microphone instance stored in self
        with self.microphone as source:
            # print("[LISTENING]...") # Keep console cleaner
            try:
                 # --- Speech Rec Improvement: Slightly longer phrase limit ---
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=5) # Increased to 5 seconds
                # --- End Improvement ---
                print("Processing audio...") # Feedback that audio was captured
                command = self.recognizer.recognize_google(audio).lower().strip()
                print(f"[HEARD] {command}")
            except sr.WaitTimeoutError:
                pass # It's okay if they don't speak
            except sr.UnknownValueError:
                print("[ERROR] Speech Recognition Error: Could not understand audio.")
                # --- Speech Rec Improvement: Audio Feedback ---
                self.speak("Sorry, I didn't catch that. Please try again.")
                # --- End Improvement ---
            except sr.RequestError as e:
                print(f"[ERROR] Speech Recognition Error: Could not reach Google services; {e}")
                # --- Speech Rec Improvement: Audio Feedback ---
                self.speak("Sorry, I'm having trouble connecting. Please check your internet connection.")
                # --- End Improvement ---
            except Exception as e:
                 print(f"[ERROR] Unexpected error in listen_for_command: {e}")
                 self.speak("An unexpected listening error occurred.")

        return command

class AccessibleBlackjackSystem:
    """Main system using Roboflow YOLO for detection"""

    def __init__(self):
        self.audio = AudioManager()
        self.card_db = CardDatabase()
        print(f"[DB] Loaded {len(self.card_db.card_data)} card entries.")
        self.blackjack = BlackjackGameStateManager(self.card_db)
        self.running = True
        self.current_mode = "menu"
        self.command_queue = Queue()
        self.audio_thread = None
        self.yolo_model = None
        self.yolo_class_names = {}

        # --- Camera Setup ---
        self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
             print("FATAL ERROR: Could not open camera.")
             self.audio.speak("Error: Could not open camera.")
             self.running = False
             return
        desired_width = 640
        desired_height = 480
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, desired_width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, desired_height)
        print(f"Attempting to set camera resolution to {desired_width}x{desired_height}")

        # --- Roboflow Setup ---
        try:
            # --- IMPORTANT: PASTE YOUR NEWEST VALID API KEY HERE ---
            api_key = "DiIME5kv2PXA6GJQWMI1"
            # --- END IMPORTANT ---

            print(f"DEBUG: Using api_key variable: '{api_key}'")
            if not api_key or "YOUR" in api_key:
                 raise ValueError("API Key not set correctly in the script. Please replace the placeholder.")

            print("Attempting to authenticate with Roboflow...")
            rf = Roboflow(api_key=api_key)
            print("Authentication successful!")

            print("Attempting to load project...")
            workspace_id = "augmented-startups"
            project_id = "playing-cards-ow27d"
            version_number = 4
            project = rf.workspace(workspace_id).project(project_id)
            self.yolo_class_names = project.classes
            version = project.version(version_number)

            print("Attempting to load model...")
            self.yolo_model = version.model
            print("Roboflow model loaded successfully!")
            print("Class names dictionary:", self.yolo_class_names)

        except Exception as e:
            print(f"FATAL ERROR during Roboflow setup: {e}")
            self.audio.speak("Error connecting to Roboflow or loading the model. Please check the API key and project details.")
            self.running = False
            return

        # Start background listener thread here after successful init
        self.audio_thread = threading.Thread(target=self._listen_in_background, daemon=True)
        self.audio_thread.start()

        self.audio.speak("System initialized successfully!")

    # --- Helper: Parse Roboflow Class Name (Unchanged) ---
    def _parse_card_name(self, class_name: str) -> Optional[Tuple[str, str]]:
        if not class_name or len(class_name) < 2: return None
        value_str = class_name[:-1]; suit_char = class_name[-1]
        value_map = {'A': 'Ace', 'K': 'King', 'Q': 'Queen', 'J': 'Jack', '10': '10', '9': '9', '8': '8', '7': '7', '6': '6', '5': '5', '4': '4', '3': '3', '2': '2'}
        value = value_map.get(value_str)
        suit_map = {'C': 'Clubs', 'D': 'Diamonds', 'H': 'Hearts', 'S': 'Spades'}
        suit = suit_map.get(suit_char)
        if value and suit: return value, suit
        else: print(f"Warning: Could not parse card name '{class_name}'"); return None

    # --- Background Listening Thread (Unchanged) ---
    def _listen_in_background(self):
        while self.running:
            command = self.audio.listen_for_command(timeout=3)
            if command: self.command_queue.put(command)
            time.sleep(0.1)

    # --- Main Menu (Unchanged) ---
    def main_menu(self):
        # Ensure thread is running (might have stopped if returning from game)
        if self.audio_thread is None or not self.audio_thread.is_alive():
             print("WARN: Restarting audio listener thread.")
             self.audio_thread = threading.Thread(target=self._listen_in_background, daemon=True)
             self.audio_thread.start()

        print("INFO: Entering Main Menu.")
        self.audio.speak("Main Menu. Say 'play blackjack', 'test detection', or 'quit'.")
        while self.running and self.current_mode == "menu":
            try:
                command = self.command_queue.get(timeout=1)
                if command: self.handle_menu_command(command)
            except Empty: pass
            time.sleep(0.1)

    # --- Menu Command Handler (Unchanged) ---
    def handle_menu_command(self, command: str):
        print(f"DEBUG: Handling menu command: {command}")
        if "play" in command or "blackjack" in command: self.current_mode = "playing"
        elif "test" in command: self.current_mode = "testing"
        elif "quit" in command: self.audio.speak("Goodbye!"); self.running = False
        else: self.audio.speak("Command not recognized. Please say 'play blackjack', 'test detection', or 'quit'.")

    # --- Play Blackjack Loop (Removed duplicate debug print) ---
    def play_blackjack(self):
        self.audio.speak("Starting Blackjack!")
        self.blackjack.reset_game()
        self.audio.speak("Place cards and say 'deal', or 'detect cards'.")

        frame_counter = 0; process_every_n_frames = 3
        latest_detected_cards_tuples: List[Tuple[str, str]] = []
        latest_raw_results: Dict[str, Any] = {'predictions': []}
        prev_frame_time = time.time()

        while self.running and self.current_mode == "playing":
            ret, frame = self.camera.read()
            if not ret: print("Error reading frame in play_blackjack"); time.sleep(0.1); continue

            frame_counter += 1; new_frame_time = time.time(); processed_this_frame = False

            if frame_counter % process_every_n_frames == 0:
                processed_this_frame = True
                try:
                    results = self.yolo_model.predict(frame, confidence=40, overlap=50).json()
                    latest_raw_results = results

                    detected_cards_with_pos = []
                    for prediction in results.get('predictions', []):
                        class_name = prediction.get('class')
                        parsed_card = self._parse_card_name(class_name)
                        if parsed_card:
                             x_center = prediction.get('x', 0)
                             detected_cards_with_pos.append({'card': parsed_card, 'x': x_center})

                    detected_cards_with_pos.sort(key=lambda item: item['x'])
                    raw_sorted_tuples = [item['card'] for item in detected_cards_with_pos]

                    unique_cards = []; seen_cards = set()
                    for card_tuple in raw_sorted_tuples:
                        if card_tuple not in seen_cards:
                            unique_cards.append(card_tuple)
                            seen_cards.add(card_tuple)
                    latest_detected_cards_tuples = unique_cards
                    # --- Removed Debug Print ---
                    # if len(raw_sorted_tuples) > len(latest_detected_cards_tuples):
                    #      print(f"DEBUG: Removed duplicate detections...")

                except Exception as e:
                    print(f"Error during prediction: {e}")
                    results = latest_raw_results

            command = None
            try: command = self.command_queue.get_nowait()
            except Empty: pass

            if command: self.handle_blackjack_command(command, latest_detected_cards_tuples)

            annotated_frame = frame.copy()
            for bounding_box in latest_raw_results.get('predictions', []):
                try:
                    x1=int(bounding_box['x']-bounding_box['width']/2); y1=int(bounding_box['y']-bounding_box['height']/2)
                    x2=int(bounding_box['x']+bounding_box['width']/2); y2=int(bounding_box['y']+bounding_box['height']/2)
                    label=bounding_box['class']; confidence=bounding_box['confidence']
                    cv2.rectangle(annotated_frame,(x1,y1),(x2,y2),(0,255,0),2)
                    cv2.putText(annotated_frame,f"{label} ({confidence:.2f})",(x1, y1-10),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)
                except Exception as e: print(f"Error drawing box: {e}")

            fps=1/(new_frame_time-prev_frame_time) if (new_frame_time-prev_frame_time)>0 else 0
            prev_frame_time=new_frame_time
            cv2.putText(annotated_frame, f"FPS: {int(fps)}", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)
            if processed_this_frame: cv2.putText(annotated_frame, "Processing", (10,70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

            cv2.imshow('Accessible Blackjack (YOLO)', annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'): self.current_mode = "menu"; break

        if cv2.getWindowProperty('Accessible Blackjack (YOLO)', cv2.WND_PROP_VISIBLE) >= 1: cv2.destroyWindow('Accessible Blackjack (YOLO)')
        print("INFO: Exiting Blackjack Game.")

    # --- Game Command Handler (Unchanged) ---
    def handle_blackjack_command(self, command: str, detected_cards: List[Tuple[str, str]]):
        if "menu" in command: self.current_mode = "menu"; self.audio.speak("Returning to main menu.")
        elif "detect" in command: self.announce_detected_cards(detected_cards)
        elif ("deal" in command or "dale" in command) and self.blackjack.game_phase == "waiting": self.deal_initial_cards(detected_cards)
        elif "hit" in command and self.blackjack.game_phase == "player_turn": self.player_hit(detected_cards)
        elif "stand" in command and self.blackjack.game_phase == "player_turn": self.player_stand()
        elif "new game" in command: self.blackjack.reset_game(); self.audio.speak("New game started. Place cards and say 'deal'.")
        else: self.audio.speak("Command not recognized in game. Say 'hit', 'stand', 'detect cards', 'new game', or 'menu'.")

    # --- Announce Cards (Unchanged) ---
    def announce_detected_cards(self, detected_cards: List[Tuple[str, str]]):
        if not detected_cards: self.audio.speak("No cards detected clearly."); return
        count = len(detected_cards)
        self.audio.speak(f"I see {count} card{'s' if count > 1 else ''}.")
        for i, (value, suit) in enumerate(detected_cards):
            speak_value = value; self.audio.speak(f"Card {i+1}: {speak_value} of {suit}")

    # --- Deal Initial Cards (Unchanged) ---
    def deal_initial_cards(self, detected_cards: List[Tuple[str, str]]):
        if len(detected_cards) < 3: self.audio.speak("Need at least 3 cards detected for the deal (2 player, 1 dealer)."); return
        player_hand_tuples = detected_cards[:2]; dealer_hand_tuples = detected_cards[2:3]
        if len(player_hand_tuples) < 2 or len(dealer_hand_tuples) < 1: self.audio.speak("Couldn't assign cards correctly. Please ensure 3 cards are clearly visible."); return
        self.blackjack.player_cards = player_hand_tuples; self.blackjack.dealer_cards = dealer_hand_tuples
        self.audio.speak("Cards dealt!")
        self.audio.speak(f"Your hand: {self.blackjack.get_hand_description(self.blackjack.player_cards)}")
        self.audio.speak(f"Dealer shows: {self.blackjack.get_hand_description(self.blackjack.dealer_cards)}")
        if self.blackjack.is_blackjack(self.blackjack.player_cards): self.audio.speak("Blackjack!"); self.end_game()
        else: self.blackjack.game_phase = "player_turn"; self.audio.speak("Your turn. Say 'hit' or 'stand'.")

    # --- Player Hit (Unchanged) ---
    def player_hit(self, detected_cards: List[Tuple[str, str]]):
        expected_cards = len(self.blackjack.player_cards) + len(self.blackjack.dealer_cards) + 1
        if len(detected_cards) < expected_cards: self.audio.speak(f"Place the new card. I should see {expected_cards} cards total."); return
        assigned_cards = set(self.blackjack.player_cards) | set(self.blackjack.dealer_cards)
        new_cards = [card for card in detected_cards if card not in assigned_cards]
        if not new_cards: self.audio.speak("Cannot identify the new card clearly among the detected cards."); return
        if len(new_cards) > 1: print(f"Warning: Detected multiple new cards: {new_cards}. Using the first one.")
        new_card_tuple = new_cards[0]; self.blackjack.player_cards.append(new_card_tuple)
        value, suit = new_card_tuple; self.audio.speak(f"You drew {value} of {suit}.")
        player_total = self.blackjack.calculate_hand_value(self.blackjack.player_cards)
        self.audio.speak(f"Your total is now {player_total}.")
        if self.blackjack.is_bust(self.blackjack.player_cards): self.audio.speak("Bust!"); self.end_game()
        elif player_total == 21: self.audio.speak("Twenty-one!"); self.player_stand()
        else: self.audio.speak("Say 'hit' or 'stand'.")

    # --- Player Stand (Unchanged) ---
    def player_stand(self):
        if self.blackjack.game_phase != "player_turn": self.audio.speak("It's not your turn to stand."); return
        player_total = self.blackjack.calculate_hand_value(self.blackjack.player_cards)
        self.audio.speak(f"You stand with {player_total}."); self.blackjack.game_phase = "dealer_turn"
        self.simulate_dealer_play()

    # --- Simulate Dealer Play (Unchanged) ---
    def simulate_dealer_play(self):
        self.audio.speak("Dealer's turn.")
        possible_hole_cards=[('Ace','Spades'),('King','Hearts'),('10','Clubs'),('9','Diamonds'),('7','Spades')]
        if len(self.blackjack.dealer_cards)==1: hole_card=random.choice(possible_hole_cards); self.blackjack.dealer_cards.append(hole_card); self.audio.speak(f"Dealer reveals {hole_card[0]} of {hole_card[1]}.")
        self.audio.speak(f"Dealer has: {self.blackjack.get_hand_description(self.blackjack.dealer_cards)}")
        dealer_total = self.blackjack.calculate_hand_value(self.blackjack.dealer_cards)
        while dealer_total < 17:
            self.audio.speak("Dealer hits.")
            simulated_card_key=random.choice(list(self.card_db.card_data.keys())); value,suit=simulated_card_key.split('_',1)
            roboflow_val = {'Ace':'A','King':'K','Queen':'Q','Jack':'J'}.get(value,value); roboflow_suit = suit[0].upper(); roboflow_name = roboflow_val + roboflow_suit
            parsed_card = self._parse_card_name(roboflow_name)
            if parsed_card: self.blackjack.dealer_cards.append(parsed_card); self.audio.speak(f"Dealer draws {parsed_card[0]} of {parsed_card[1]}.")
            else: self.audio.speak("Dealer draws an unknown card (simulation error).")
            dealer_total = self.blackjack.calculate_hand_value(self.blackjack.dealer_cards)
            self.audio.speak(f"Dealer's total is now {dealer_total}."); time.sleep(1)
        if dealer_total > 21: self.audio.speak("Dealer busts!")
        else: self.audio.speak(f"Dealer stands with {dealer_total}.")
        self.end_game()

    # --- End Game (Unchanged) ---
    def end_game(self):
        if self.blackjack.game_phase == "dealer_turn": pass
        self.blackjack.game_phase = "game_over"; result = self.blackjack.determine_winner()
        self.audio.speak("--- Game Over ---")
        self.audio.speak(f"Final hands. You have: {self.blackjack.get_hand_description(self.blackjack.player_cards)} (Total: {self.blackjack.calculate_hand_value(self.blackjack.player_cards)}).")
        self.audio.speak(f"Dealer has: {self.blackjack.get_hand_description(self.blackjack.dealer_cards)} (Total: {self.blackjack.calculate_hand_value(self.blackjack.dealer_cards)}).")
        result_messages = {"player_wins_dealer_bust":"You win! Dealer busted.","dealer_wins_player_bust":"Dealer wins. You busted.","player_blackjack":"Blackjack! You win!","dealer_blackjack":"Dealer has Blackjack. You lose.","player_wins_higher":"You win with a higher score!","dealer_wins_higher":"Dealer wins with a higher score.","push":"It's a push. You tie."}
        self.audio.speak(result_messages.get(result, "Game complete.")); self.audio.speak("Say 'new game' or 'menu'.")

    # --- Test Detection Mode (Uses updated overlap and Queue Empty) ---
    def test_detection_mode(self):
        self.audio.speak("Starting detection test mode. Press 'q' to return to menu.")
        prev_frame_time = time.time()
        while self.running and self.current_mode == "testing":
            ret, frame = self.camera.read();
            if not ret: print("Error reading frame in test_detection_mode"); time.sleep(0.1); continue
            new_frame_time = time.time()
            try: results = self.yolo_model.predict(frame, confidence=40, overlap=50).json()
            except Exception as e: print(f"Prediction error in test mode: {e}"); results = {'predictions': []}
            annotated_frame = frame.copy()
            for bounding_box in results.get('predictions',[]):
                 try:
                    x1=int(bounding_box['x']-bounding_box['width']/2); y1=int(bounding_box['y']-bounding_box['height']/2)
                    x2=int(bounding_box['x']+bounding_box['width']/2); y2=int(bounding_box['y']+bounding_box['height']/2)
                    label=bounding_box['class']; confidence=bounding_box['confidence']
                    cv2.rectangle(annotated_frame,(x1,y1),(x2,y2),(0,255,0),2)
                    cv2.putText(annotated_frame,f"{label} ({confidence:.2f})",(x1,y1-10),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)
                 except Exception as e: print(f"Error drawing box in test mode: {e}")
            fps=1/(new_frame_time-prev_frame_time) if (new_frame_time-prev_frame_time)>0 else 0
            prev_frame_time=new_frame_time
            cv2.putText(annotated_frame,f"FPS: {int(fps)}",(10,30),cv2.FONT_HERSHEY_SIMPLEX,1,(255,0,0),2)
            cv2.putText(annotated_frame,f"Detected: {len(results.get('predictions',[]))}",(10,70),cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,0),2)
            cv2.imshow('YOLO Detection Test', annotated_frame)
            try:
                 command = self.command_queue.get_nowait()
                 if command and "menu" in command: self.current_mode = "menu"; break
            except Empty: pass # Use imported Empty
            if cv2.waitKey(1) & 0xFF == ord('q'): self.current_mode = "menu"; break
        if cv2.getWindowProperty('YOLO Detection Test',cv2.WND_PROP_VISIBLE)>=1: cv2.destroyWindow('YOLO Detection Test')
        self.audio.speak("Exiting test mode."); print("INFO: Exiting Test Detection Mode.")

    # --- Cleanup (Unchanged) ---
    def cleanup(self):
        print("Cleaning up...")
        self.running = False
        if self.audio_thread and self.audio_thread.is_alive():
            try: self.audio_thread.join(timeout=1)
            except Exception as e: print(f"Error joining audio thread: {e}")
        if hasattr(self, 'camera') and self.camera and self.camera.isOpened(): self.camera.release()
        cv2.destroyAllWindows()
        print("Cleanup finished.")

    def run(self):
        """ Main application loop """
        if not self.running:
             print("System failed to initialize. Exiting.")
             return # Exit if initialization failed
        try:
            # Welcome message moved to __init__ upon successful loading
            # self.audio.speak("Welcome to Accessible Blackjack!")
            while self.running:
                if self.current_mode == "menu":
                    self.main_menu()
                elif self.current_mode == "playing":
                    self.play_blackjack()
                    # THIS 'if' block is indented UNDER the 'elif' above
                    if self.running:
                        self.current_mode = "menu"
                elif self.current_mode == "testing":
                    self.test_detection_mode()
                    # THIS 'if' block is indented UNDER the 'elif' above
                    if self.running:
                        self.current_mode = "menu"

                # THIS 'time.sleep' is at the same level as the 'if/elif' blocks
                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\nCtrl+C detected. Shutting down...")
            self.audio.speak("Shutting down.")
        except Exception as e:
            print(f"System error: {e}")
            try:
                 self.audio.speak("An unexpected error occurred. Shutting down.")
            except:
                 pass
        finally:
            self.cleanup()

if __name__ == "__main__":
    from profile_integration import ProfileIntegratedBlackjackSystem
    system = ProfileIntegratedBlackjackSystem()
    system.run()