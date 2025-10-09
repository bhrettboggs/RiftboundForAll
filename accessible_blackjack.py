import cv2
import numpy as np
import pyttsx3
import speech_recognition as sr
import threading
import time
import sys
from typing import List, Tuple, Optional
from improved_card_detection import ImprovedCardDetector

class ImprovedAccessibleCardGame:
    def __init__(self):
        print("Starting initialization...")
        
        # Test TTS functionality first
        print("Testing TTS engine...")
        test_result = self.speak("TTS test")
        if not test_result:
            print("TTS test failed - continuing with print-only mode")
        
        # Initialize speech recognition
        print("Initializing speech recognition...")
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            print("Speech recognition initialized successfully")
        except Exception as e:
            print(f"Speech recognition initialization error: {e}")
        
        # Initialize camera
        print("Initializing camera...")
        self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
            print("Camera failed to open")
            self.speak("Error: Could not open camera")
            sys.exit(1)
        print("Camera initialized successfully")
            
        # Set camera properties for better detection
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        
        # Game state
        self.current_game = None
        self.running = True
        
        # Initialize improved card detector
        self.card_detector = ImprovedCardDetector()
        
        # Blackjack game state
        self.player_cards = []
        self.dealer_cards = []
        self.game_phase = "waiting"
        self.last_detected_count = 0
        self.detection_stable_frames = 0
        self.required_stable_frames = 10
        
        print("About to speak welcome message...")
        self.speak("Welcome to Accessible Card Games! Initializing camera and microphone...")
        
        # Calibrate microphone
        print("Calibrating microphone...")
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Microphone calibrated successfully")
        except Exception as e:
            print(f"Microphone calibration error: {e}")
        
        print("About to speak system ready message...")
        self.speak("System ready! Camera resolution set to high definition for better card detection.")
        

        print("About to speak help command...")
        self.speak("Say help for available commands.")

    def speak(self, text):
        """Convert text to speech using a fresh engine instance each time"""
        print(f"Speaking: {text}")
        
        try:
            # Create a completely fresh TTS engine for each message
            tts = pyttsx3.init()
            tts.setProperty('rate', 120)
            tts.setProperty('volume', 0.9)
            
            # Speak and wait
            tts.say(text)
            tts.runAndWait()
            
            # Clean up this instance
            del tts
            
            print(f"✓ Successfully spoke: {text}")
            return True
            
        except Exception as e:
            print(f"✗ TTS Error: {e}")
            print(f"Message was: {text}")
            time.sleep(2)  # Give time to read
            return False

    def listen_for_command(self, timeout=3):
        """Listen for voice commands"""
        try:
            print(f"Listening for command (timeout: {timeout} seconds)...")
            with self.microphone as source:
                # Don't announce listening every time - too verbose
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=4)
            
            command = self.recognizer.recognize_google(audio).lower()
            print(f"Command heard: {command}")
            self.speak(f"Command heard: {command}")
            return command
        except sr.WaitTimeoutError:
            print("Listening timeout - no command heard")
            return None
        except sr.UnknownValueError:
            print("Could not understand audio")
            self.speak("Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
            self.speak(f"Speech recognition error: {str(e)}")
            return None

    def preprocess_for_card_detection(self, frame):
        """Preprocess frame for better card detection"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Use Otsu's threshold (works best based on debug results)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Light morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return gray, thresh

    def detect_card_contours(self, thresh_frame):
        """Detect card-like contours in the frame"""
        # Find contours
        contours, _ = cv2.findContours(thresh_frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        card_contours = []
        
        for contour in contours:
            # Calculate area
            area = cv2.contourArea(contour)
            
            # Filter by area (using relaxed parameters)
            if self.min_card_area < area < self.max_card_area:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h
                
                # Check aspect ratio (more permissive)
                if self.card_aspect_ratio_min < aspect_ratio < self.card_aspect_ratio_max:
                    # Approximate contour to polygon
                    epsilon = 0.05 * cv2.arcLength(contour, True)  # More permissive
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    # Accept more shapes (not just 4-sided)
                    if len(approx) >= 3:  # Changed from 4 to 3
                        card_contours.append({
                            'contour': contour,
                            'approx': approx,
                            'bbox': (x, y, w, h),
                            'area': area,
                            'aspect_ratio': aspect_ratio
                        })
        
        # Sort by area (largest first)
        card_contours.sort(key=lambda x: x['area'], reverse=True)
        
        return card_contours

    def extract_corner_for_recognition(self, frame, card_info):
        """Extract the corner of the card where value/suit are located"""
        x, y, w, h = card_info['bbox']
        
        # Extract top-left corner (where card value typically is)
        corner_size_w = min(w // 3, 100)  # Larger corner extraction
        corner_size_h = min(h // 3, 140)
        
        # Ensure we don't go out of bounds
        corner_size_w = min(corner_size_w, frame.shape[1] - x)
        corner_size_h = min(corner_size_h, frame.shape[0] - y)
        
        if corner_size_w < 20 or corner_size_h < 20:
            return None
        
        corner = frame[y:y + corner_size_h, x:x + corner_size_w]
        
        return corner

    def analyze_card_corner(self, corner_roi):
        """Analyze the corner region to identify card features"""
        if corner_roi is None or corner_roi.size == 0:
            return None, None
        
        # Convert to grayscale if needed
        if len(corner_roi.shape) == 3:
            gray_corner = cv2.cvtColor(corner_roi, cv2.COLOR_BGR2GRAY)
        else:
            gray_corner = corner_roi
        
        # Apply different thresholds to isolate card markings
        _, thresh_high = cv2.threshold(gray_corner, 180, 255, cv2.THRESH_BINARY_INV)
        _, thresh_low = cv2.threshold(gray_corner, 120, 255, cv2.THRESH_BINARY_INV)
        
        # Find contours in the thresholded corner
        contours_high, _ = cv2.findContours(thresh_high, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours_low, _ = cv2.findContours(thresh_low, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Analyze contour characteristics
        return self.classify_card_from_contours(contours_high, contours_low, gray_corner)
    
    def classify_card_from_contours(self, contours_high, contours_low, gray_corner):
        """Classify card based on contour analysis"""
        
        # Count significant contours
        significant_contours = []
        for contour in contours_high:
            area = cv2.contourArea(contour)
            if area > 50:  # Filter small noise
                significant_contours.append(contour)
        
        contour_count = len(significant_contours)
        
        # Calculate total area of markings
        total_marking_area = sum(cv2.contourArea(c) for c in significant_contours)
        corner_area = gray_corner.size
        marking_ratio = total_marking_area / corner_area if corner_area > 0 else 0
        
        # Analyze the largest contour
        if significant_contours:
            largest_contour = max(significant_contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            aspect_ratio = w / h if h > 0 else 1
        else:
            aspect_ratio = 1
        
        # Card value classification based on characteristics
        value = self.classify_value(contour_count, marking_ratio, aspect_ratio)
        suit = self.classify_suit(significant_contours, gray_corner)
        
        return value, suit
    
    def classify_value(self, contour_count, marking_ratio, aspect_ratio):
        """Classify card value based on visual characteristics"""
        
        # Simple heuristic classification
        if marking_ratio < 0.05:
            # Very little marking - likely low number or Ace
            if contour_count <= 1:
                return 'A'
            else:
                return '2'
        elif marking_ratio < 0.15:
            # Moderate marking
            if contour_count <= 2:
                return ['3', '4'][contour_count % 2]
            else:
                return '5'
        elif marking_ratio < 0.25:
            # More marking
            if aspect_ratio > 1.5:  # Wide shape might be "10"
                return '10'
            else:
                return ['6', '7', '8'][contour_count % 3]
        else:
            # Heavy marking - likely face cards or 9/10
            if aspect_ratio > 1.2:
                return '10'
            elif contour_count > 3:
                return ['J', 'Q', 'K'][contour_count % 3]
            else:
                return '9'
    
    def classify_suit(self, contours, gray_corner):
        """Classify suit based on shape analysis"""
        
        if not contours:
            return ['Hearts', 'Diamonds', 'Clubs', 'Spades'][np.random.randint(0, 4)]
        
        # Analyze the suit symbol (if present in corner)
        h, w = gray_corner.shape
        
        # Look in the lower portion of the corner for suit symbol
        if h > 30:
            suit_region = gray_corner[h//2:, :]
            
            # Apply threshold to isolate suit symbol
            _, suit_thresh = cv2.threshold(suit_region, 150, 255, cv2.THRESH_BINARY_INV)
            
            # Find suit contours
            suit_contours, _ = cv2.findContours(suit_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if suit_contours:
                # Get the largest suit contour 
                largest_suit = max(suit_contours, key=cv2.contourArea)
                
                if cv2.contourArea(largest_suit) > 20:
                    # Analyze suit shape
                    x, y, w, h = cv2.boundingRect(largest_suit)
                    suit_aspect = w / h if h > 0 else 1
                    
                    # Simple suit classification
                    if suit_aspect > 1.2:
                        return 'Diamonds'  # Diamond tends to be wider
                    elif suit_aspect < 0.8:
                        return 'Spades'    # Spade tends to be taller
                    else:
                        # For circular-ish shapes, check solidity
                        hull = cv2.convexHull(largest_suit)
                        hull_area = cv2.contourArea(hull)
                        solidity = cv2.contourArea(largest_suit) / hull_area if hull_area > 0 else 0
                        
                        if solidity > 0.8:
                            return 'Hearts'    # Hearts are more solid
                        else:
                            return 'Clubs'     # Clubs have more concave areas
        
        # Fallback to random suit if analysis fails
        return ['Hearts', 'Diamonds', 'Clubs', 'Spades'][np.random.randint(0, 4)]

    def simple_card_recognition(self, corner_roi):
        """Main card recognition method"""
        return self.analyze_card_corner(corner_roi)

    def detect_and_identify_cards(self, frame):
        """Main card detection and identification method using improved detector"""
        # Use the improved card detector
        detected_cards_raw = self.card_detector.detect_and_identify_cards(frame)
        
        # Convert to the format expected by the rest of the code
        detected_cards = []
        for card in detected_cards_raw:
            # Only include cards with reasonable confidence
            if card['rank_confidence'] > 0.5 and card['suit_confidence'] > 0.5:
                detected_cards.append({
                    'value': card['rank'],
                    'suit': card['suit'],
                    'bbox': card['bbox'],
                    'area': card['bbox'][2] * card['bbox'][3],  # width * height
                    'confidence': min(card['rank_confidence'], card['suit_confidence'])
                })
        
        # Get annotated frame from the detector
        annotated_frame = self.card_detector.annotate_frame(frame, detected_cards_raw)
        
        # Add game phase to frame
        phase_text = f"Phase: {self.game_phase}"
        cv2.putText(annotated_frame, phase_text, (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        return detected_cards, annotated_frame

    def announce_detected_cards(self, detected_cards):
        """Announce all detected cards with manual correction option"""
        if not detected_cards:
            self.speak("No cards detected. Make sure cards are clearly visible on a contrasting background.")
            return
        
        count = len(detected_cards)
        self.speak(f"I can see {count} card{'s' if count != 1 else ''}")
        
        for i, card in enumerate(detected_cards):
            self.speak(f"Card {i + 1}: {card['value']} of {card['suit']}")
        
        # Offer manual correction
        self.speak("If any cards are wrong, say 'correct card 1' or 'correct card 2' etc. Say 'ok' if correct.")

    def card_value_for_blackjack(self, card_value):
        """Convert card value to blackjack numeric value"""
        if card_value in ['J', 'Q', 'K']:
            return 10
        elif card_value == 'A':
            return 11
        elif card_value == 'Unknown':
            return 0  # Handle unknown cards
        else:
            try:
                return int(card_value)
            except ValueError:
                return 0

    def calculate_blackjack_total(self, cards):
        """Calculate total value for blackjack, handling aces"""
        total = 0
        aces = 0
        
        for value, _ in cards:
            if value == 'A':
                aces += 1
                total += 11
            elif value in ['J', 'Q', 'K']:
                total += 10
            elif value != 'Unknown':
                try:
                    total += int(value)
                except ValueError:
                    pass  # Skip unknown values
        
        # Handle aces
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        
        return total

    def organize_cards_by_position(self, detected_cards):
        """Organize cards by position (top = dealer, bottom = player)"""
        if not detected_cards:
            return {'dealer': [], 'player': []}
        
        # Sort cards by y-coordinate
        sorted_cards = sorted(detected_cards, key=lambda card: card['bbox'][1])
        
        # Split into top and bottom halves
        mid_point = len(sorted_cards) // 2
        
        # In blackjack, typically player cards are in bottom, dealer in top
        if len(sorted_cards) >= 2:
            # Simple heuristic: if we have 3+ cards, assume first one is dealer
            dealer_cards = sorted_cards[:1] if len(sorted_cards) >= 3 else []
            player_cards = sorted_cards[1:] if len(sorted_cards) >= 3 else sorted_cards[-2:]
        else:
            dealer_cards = []
            player_cards = sorted_cards
        
        return {'dealer': dealer_cards, 'player': player_cards}

    def play_blackjack(self):
        """Main blackjack game loop with improved card detection"""
        self.speak("Starting Blackjack!")
        self.speak("Place cards clearly on a dark background. Cards should not overlap.")
        self.speak("Say 'detect' to check what cards I can see.")
        self.speak("Say 'deal' when you have the initial cards in position.")
        self.speak("Say 'help' for all commands.")
        
        self.game_phase = "waiting"
        self.player_cards = []
        self.dealer_cards = []
        
        detection_interval = 0
        
        while self.running and self.current_game == "blackjack":
            # Capture frame
            ret, frame = self.camera.read()
            if not ret:
                continue
            
            # Detect cards every few frames to reduce processing load
            detected_cards = []
            annotated_frame = frame
            
            if detection_interval % 5 == 0:  # Process every 5th frame
                detected_cards, annotated_frame = self.detect_and_identify_cards(frame)
            
            detection_interval += 1
            
            # Show frame
            cv2.imshow('Accessible Blackjack - Card Detection', annotated_frame)
            
            # Listen for commands (non-blocking)
            try:
                command = self.listen_for_command(timeout=0.5)
                if command:
                    self.handle_blackjack_command(command, detected_cards)
            except:
                pass
            
            # Check for quit
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.speak("Quitting game.")
                break
        
        cv2.destroyAllWindows()

    def handle_blackjack_command(self, command, detected_cards):
        """Handle voice commands during blackjack"""
        self.speak(f"Processing command: {command}")
        
        if "quit" in command or "exit" in command:
            self.speak("Exiting blackjack.")
            self.current_game = None
            return
        
        elif "detect" in command or "see" in command or "show" in command:
            self.announce_detected_cards(detected_cards)
        
        elif "correct card" in command:
            self.handle_card_correction(command, detected_cards)
        
        elif "deal" in command and self.game_phase == "waiting":
            self.deal_initial_cards(detected_cards)
        
        elif "hit" in command and self.game_phase == "player_turn":
            self.player_hit(detected_cards)
        
        elif "stand" in command and self.game_phase == "player_turn":
            self.player_stand(detected_cards)
        
        elif "new game" in command or "restart" in command:
            self.new_blackjack_game()
        
        elif "help" in command:
            self.blackjack_help()
        
        elif "status" in command:
            self.announce_game_status()
        
        else:
            self.speak("Command not recognized. Say 'help' for available commands.")

    def handle_card_correction(self, command, detected_cards):
        """Handle manual card correction"""
        try:
            # Extract card number
            words = command.split()
            card_num = None
            for word in words:
                if word.isdigit():
                    card_num = int(word) - 1  # Convert to 0-based index
                    break
            
            if card_num is None or card_num >= len(detected_cards):
                self.speak("Please specify a valid card number, like 'correct card 1'")
                return
            
            self.speak(f"What is the correct value for card {card_num + 1}? Say the value like 'ace' or 'king' or 'five'")
            
            # Listen for value
            value_command = self.listen_for_command(timeout=10)
            if not value_command:
                self.speak("Didn't hear the value. Please try again.")
                return
            
            # Parse value
            new_value = self.parse_card_value(value_command)
            if not new_value:
                self.speak("Didn't understand the value. Try again.")
                return
            
            self.speak("What suit? Say 'hearts', 'diamonds', 'clubs', or 'spades'")
            
            # Listen for suit
            suit_command = self.listen_for_command(timeout=10)
            if not suit_command:
                self.speak("Didn't hear the suit. Please try again.")
                return
            
            # Parse suit
            new_suit = self.parse_card_suit(suit_command)
            if not new_suit:
                self.speak("Didn't understand the suit. Try again.")
                return
            
            # Update the card
            detected_cards[card_num]['value'] = new_value
            detected_cards[card_num]['suit'] = new_suit
            
            self.speak(f"Updated card {card_num + 1} to {new_value} of {new_suit}")
            
        except Exception as e:
            self.speak("Error correcting card. Please try again.")

    def parse_card_value(self, command):
        """Parse spoken card value"""
        command = command.lower()
        
        value_map = {
            'ace': 'A', 'one': 'A',
            'two': '2', 'three': '3', 'four': '4', 'five': '5',
            'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
            'jack': 'J', 'queen': 'Q', 'king': 'K'
        }
        
        for word, value in value_map.items():
            if word in command:
                return value
        
        # Try direct number parsing
        for i in range(2, 11):
            if str(i) in command:
                return str(i)
        
        return None

    def parse_card_suit(self, command):
        """Parse spoken card suit"""
        command = command.lower()
        
        if 'heart' in command:
            return 'Hearts'
        elif 'diamond' in command:
            return 'Diamonds'
        elif 'club' in command:
            return 'Clubs'
        elif 'spade' in command:
            return 'Spades'
        
        return None

    def deal_initial_cards(self, detected_cards):
        """Deal initial cards for blackjack"""
        if len(detected_cards) < 3:
            self.speak("Please place at least 3 cards: 2 for you and 1 visible for the dealer.")
            return
        
        # Organize cards by position
        card_positions = self.organize_cards_by_position(detected_cards)
        
        if len(card_positions['player']) < 2:
            self.speak("I need to see at least 2 player cards. Place them in the bottom area of the camera view.")
            return
        
        if len(card_positions['dealer']) < 1:
            self.speak("I need to see at least 1 dealer card. Place it in the top area of the camera view.")
            return
        
        # Set cards
        self.player_cards = [(card['value'], card['suit']) for card in card_positions['player'][:2]]
        self.dealer_cards = [(card['value'], card['suit']) for card in card_positions['dealer'][:1]]
        
        # Announce cards
        self.speak("Cards dealt!")
        self.announce_cards(self.player_cards, "You have")
        self.announce_cards(self.dealer_cards, "Dealer shows")
        
        # Check for blackjack
        player_total = self.calculate_blackjack_total(self.player_cards)
        if player_total == 21:
            self.speak("Blackjack! You have 21!")
            self.game_phase = "game_over"
        else:
            self.game_phase = "player_turn"
            self.speak("Your turn. Say 'hit' to take another card or 'stand' to stay.")

    def announce_cards(self, cards, prefix=""):
        """Announce cards with total"""
        if not cards:
            return
        
        card_names = [f"{value} of {suit}" for value, suit in cards]
        total = self.calculate_blackjack_total(cards)
        
        if len(cards) == 1:
            message = f"{prefix} {card_names[0]}"
        else:
            message = f"{prefix} {', '.join(card_names[:-1])} and {card_names[-1]}"
        
        message += f". Total: {total}"
        self.speak(message)

    def player_hit(self, detected_cards):
        """Player takes another card"""
        expected_total = len(self.player_cards) + len(self.dealer_cards) + 1
        
        if len(detected_cards) < expected_total:
            self.speak(f"Please place your new card. I should see {expected_total} cards total.")
            return
        
        # Find the newest card (assume it's not in current cards)
        current_cards = set((card['value'], card['suit']) for card in detected_cards 
                          if (card['value'], card['suit']) in self.player_cards + self.dealer_cards)
        
        new_cards = [(card['value'], card['suit']) for card in detected_cards 
                    if (card['value'], card['suit']) not in current_cards]
        
        if not new_cards:
            self.speak("I cannot identify the new card. Make sure it's clearly visible.")
            return
        
        # Take the first new card
        new_card = new_cards[0]
        self.player_cards.append(new_card)
        
        self.speak(f"You drew {new_card[0]} of {new_card[1]}")
        
        player_total = self.calculate_blackjack_total(self.player_cards)
        self.speak(f"Your total is now {player_total}")
        
        if player_total > 21:
            self.speak("Bust! You went over 21. You lose.")
            self.game_phase = "game_over"
        elif player_total == 21:
            self.speak("21! Standing automatically.")
            self.player_stand(detected_cards)
        else:
            self.speak("Say 'hit' for another card or 'stand' to stay.")

    def player_stand(self, detected_cards):
        """Player stands, dealer plays"""
        self.speak("You stand with " + str(self.calculate_blackjack_total(self.player_cards)))
        self.speak("Dealer's turn. Please reveal the dealer's hole card.")
        
        # For this demo, we'll simulate dealer play
        # In a real game, you'd reveal the actual hole card
        time.sleep(2)
        
        # Add a simulated hole card
        hole_card = ("10", "Spades")  # Simulated
        self.dealer_cards.append(hole_card)
        
        self.announce_cards(self.dealer_cards, "Dealer has")
        
        # Dealer hits until 17+
        dealer_total = self.calculate_blackjack_total(self.dealer_cards)
        while dealer_total < 17:
            self.speak("Dealer must hit.")
            # Simulate dealer card
            new_card = ("6", "Hearts")  # Simulated
            self.dealer_cards.append(new_card)
            self.speak(f"Dealer draws {new_card[0]} of {new_card[1]}")
            dealer_total = self.calculate_blackjack_total(self.dealer_cards)
            self.speak(f"Dealer total: {dealer_total}")
        
        # Determine winner
        player_total = self.calculate_blackjack_total(self.player_cards)
        
        if dealer_total > 21:
            self.speak(f"Dealer busts! You win!")
        elif dealer_total > player_total:
            self.speak(f"Dealer wins {dealer_total} to {player_total}")
        elif player_total > dealer_total:
            self.speak(f"You win {player_total} to {dealer_total}!")
        else:
            self.speak(f"Push! Both have {player_total}")
        
        self.game_phase = "game_over"
        self.speak("Game over. Say 'new game' to play again.")

    def new_blackjack_game(self):
        """Start a new game"""
        self.player_cards = []
        self.dealer_cards = []
        self.game_phase = "waiting"
        self.speak("New game started. Place your cards and say 'deal' when ready.")

    def blackjack_help(self):
        """Provide help"""
        help_text = """Available commands: 
        'detect' - Tell me what cards I can see
        'correct card 1' - Fix a wrong card identification
        'deal' - Start the game with current cards
        'hit' - Take another card
        'stand' - Keep current total
        'new game' - Start over
        'help' - This message
        'quit' - Exit game"""
        self.speak(help_text)

    def announce_game_status(self):
        """Announce current status"""
        if self.player_cards:
            self.announce_cards(self.player_cards, "You have")
        if self.dealer_cards:
            self.announce_cards(self.dealer_cards, "Dealer has")
        
        self.speak(f"Game phase: {self.game_phase}")

    def game_selection_menu(self):
        """Voice-controlled game selection"""
        while self.running:
            self.speak("Game Selection. Say 'blackjack' to play, or 'quit' to exit.")
            print("Waiting for user command...")
            
            # Add a small delay to ensure TTS finishes
            time.sleep(1)
            
            command = self.listen_for_command(timeout=10)
            
            if command is None:
                print("No command received, continuing...")
                continue
            
            if "blackjack" in command:
                self.current_game = "blackjack"
                self.play_blackjack()
            
            elif "help" in command:
                self.speak("Say 'blackjack' to play blackjack, or 'quit' to exit.")
            
            elif "quit" in command or "exit" in command:
                self.speak("Goodbye!")
                self.running = False
                break
            
            else:
                self.speak("Available games: Blackjack. Say 'help' for commands.")

    def cleanup(self):
        """Clean up resources"""
        if self.camera:
            self.camera.release()
        cv2.destroyAllWindows()
        self.speak("Resources cleaned up successfully.")

    def run(self):
        """Main program loop"""
        try:
            self.game_selection_menu()
        except KeyboardInterrupt:
            self.speak("Program interrupted. Goodbye!")
        except Exception as e:
            self.speak(f"An error occurred: {str(e)}")
        finally:
            self.cleanup()


def main():
    """Main function"""
    # Speak the startup information instead of just printing
    game = ImprovedAccessibleCardGame()
    
    # Announce tips for better card detection
    game.speak("Starting Improved Accessible Card Games...")
    game.speak("Tips for better card detection:")
    game.speak("Use a dark or black table or background")
    game.speak("Ensure good, even lighting")
    game.speak("Keep cards flat and non-overlapping")
    game.speak("Use clean, uncreased cards")
    game.speak("Position camera 12 to 18 inches above cards")
    game.speak("Press Control plus C to exit at any time")
    
    game.run()


if __name__ == "__main__":
    main()