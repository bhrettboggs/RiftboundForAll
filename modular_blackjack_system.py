import cv2
import pyttsx3
import speech_recognition as sr
import time
from typing import List, Dict, Optional, Tuple
from card_database import CardDatabase, TemplateCardRecognition, TemplateTrainer
from cv_detection_module import CardDetector, CardRegionExtractor

class AudioManager:
    """Manages all text-to-speech and speech recognition functionality"""
    
    def __init__(self):
        # Initialize TTS engine
        self.tts_engine = pyttsx3.init()
        self.setup_tts()
        
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.calibrate_microphone()
    
    def setup_tts(self):
        """Configure text-to-speech settings"""
        # Get available voices
        voices = self.tts_engine.getProperty('voices')
        
        # Set speech rate and volume
        self.tts_engine.setProperty('rate', 150)
        self.tts_engine.setProperty('volume', 0.9)
        
        # Try to use a clear voice (prefer female voices for better clarity)
        for voice in voices:
            if 'zira' in voice.name.lower() or 'female' in voice.name.lower():
                self.tts_engine.setProperty('voice', voice.id)
                break
    
    def speak(self, text: str, interrupt: bool = False):
        """Convert text to speech with optional interrupt"""
        if interrupt:
            self.tts_engine.stop()
        
        print(f"[SPEECH] {text}")
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()
    
    def calibrate_microphone(self):
        """Calibrate microphone for ambient noise"""
        try:
            with self.microphone as source:
                print("Calibrating microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            print("Microphone calibrated successfully")
        except Exception as e:
            print(f"Microphone calibration failed: {e}")
    
    def listen_for_command(self, timeout: int = 5, phrase_limit: int = 4) -> Optional[str]:
        """Listen for voice commands with timeout"""
        try:
            with self.microphone as source:
                print("[LISTENING] Waiting for command...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            
            command = self.recognizer.recognize_google(audio).lower().strip()
            print(f"[HEARD] {command}")
            return command
            
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            print("[AUDIO] Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"[AUDIO] Speech recognition error: {e}")
            return None


class BlackjackGame:
    """Core blackjack game logic"""
    
    def __init__(self, card_database: CardDatabase):
        self.db = card_database
        self.reset_game()
    
    def reset_game(self):
        """Reset game state"""
        self.player_cards = []
        self.dealer_cards = []
        self.game_phase = "waiting"  # waiting, dealing, player_turn, dealer_turn, game_over
        self.game_result = None
    
    def add_card_to_player(self, value: str, suit: str):
        """Add card to player's hand"""
        self.player_cards.append((value, suit))
    
    def add_card_to_dealer(self, value: str, suit: str):
        """Add card to dealer's hand"""
        self.dealer_cards.append((value, suit))
    
    def calculate_hand_value(self, cards: List[Tuple[str, str]]) -> int:
        """Calculate blackjack value of a hand"""
        total = 0
        aces = 0
        
        for value, _ in cards:
            blackjack_values = self.db.get_blackjack_value(value)
            
            if len(blackjack_values) > 1:  # Ace
                aces += 1
                total += 11
            else:
                total += blackjack_values[0]
        
        # Handle aces
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        
        return total
    
    def get_player_total(self) -> int:
        """Get player's hand total"""
        return self.calculate_hand_value(self.player_cards)
    
    def get_dealer_total(self) -> int:
        """Get dealer's hand total"""
        return self.calculate_hand_value(self.dealer_cards)
    
    def is_blackjack(self, cards: List[Tuple[str, str]]) -> bool:
        """Check if hand is blackjack (21 with 2 cards)"""
        return len(cards) == 2 and self.calculate_hand_value(cards) == 21
    
    def is_bust(self, cards: List[Tuple[str, str]]) -> bool:
        """Check if hand is bust (over 21)"""
        return self.calculate_hand_value(cards) > 21
    
    def should_dealer_hit(self) -> bool:
        """Determine if dealer should hit based on standard rules"""
        return self.get_dealer_total() < 17
    
    def determine_winner(self) -> str:
        """Determine game winner"""
        player_total = self.get_player_total()
        dealer_total = self.get_dealer_total()
        
        # Check for busts
        if self.is_bust(self.player_cards):
            return "dealer_wins_player_bust"
        
        if self.is_bust(self.dealer_cards):
            return "player_wins_dealer_bust"
        
        # Check for blackjacks
        player_bj = self.is_blackjack(self.player_cards)
        dealer_bj = self.is_blackjack(self.dealer_cards)
        
        if player_bj and dealer_bj:
            return "push_both_blackjack"
        elif player_bj:
            return "player_blackjack"
        elif dealer_bj:
            return "dealer_blackjack"
        
        # Compare totals
        if player_total > dealer_total:
            return "player_wins_higher"
        elif dealer_total > player_total:
            return "dealer_wins_higher"
        else:
            return "push"
    
    def get_hand_description(self, cards: List[Tuple[str, str]]) -> str:
        """Get spoken description of a hand"""
        if not cards:
            return "no cards"
        
        descriptions = []
        for value, suit in cards:
            card_info = self.db.get_card_info(value, suit)
            if card_info:
                descriptions.append(card_info['name'])
            else:
                descriptions.append(f"{value} of {suit}")
        
        total = self.calculate_hand_value(cards)
        
        if len(descriptions) == 1:
            return f"{descriptions[0]}, total {total}"
        else:
            return f"{', '.join(descriptions[:-1])} and {descriptions[-1]}, total {total}"


class AccessibleBlackjackSystem:
    """Main system that coordinates all components"""
    
    def __init__(self):
        # Initialize all modules
        print("Initializing Accessible Blackjack System...")
        
        self.audio = AudioManager()
        self.card_db = CardDatabase()
        self.card_recognizer = TemplateCardRecognition(self.card_db)
        self.card_detector = CardDetector()
        self.card_extractor = CardRegionExtractor()
        self.blackjack = BlackjackGame(self.card_db)
        
        # System state
        self.running = True
        self.current_mode = "menu"  # menu, training, playing
        
        self.audio.speak("System initialized successfully!")
        
        # Check if we have templates
        available_templates = self.card_db.list_available_templates()
        if not available_templates:
            self.audio.speak("No card templates found. You may want to train some templates first for better recognition.")
        else:
            self.audio.speak(f"Loaded {len(available_templates)} card templates.")
    
    def main_menu(self):
        """Main menu system"""
        while self.running and self.current_mode == "menu":
            self.audio.speak("""Main Menu. Say:
            'play blackjack' to start a game,
            'train templates' to add card templates,
            'test detection' to test card detection,
            'help' for more options,
            or 'quit' to exit.""")
            
            command = self.audio.listen_for_command(timeout=15)
            
            if not command:
                continue
            
            self.handle_menu_command(command)
    
    def handle_menu_command(self, command: str):
        """Handle main menu commands"""
        if "play" in command and "blackjack" in command:
            self.current_mode = "playing"
            self.play_blackjack()
        
        elif "train" in command and "template" in command:
            self.current_mode = "training"
            self.train_templates()
        
        elif "test" in command and "detection" in command:
            self.test_detection_mode()
        
        elif "help" in command:
            self.show_help()
        
        elif "quit" in command or "exit" in command:
            self.audio.speak("Goodbye!")
            self.running = False
        
        else:
            self.audio.speak("Command not recognized. Say 'help' for available options.")
    
    def play_blackjack(self):
        """Main blackjack game loop"""
        self.audio.speak("Starting Blackjack! Setting up camera...")
        
        # Reset game
        self.blackjack.reset_game()
        
        self.audio.speak("""Place cards on a dark surface with good lighting.
        Say 'detect cards' to see what I can identify,
        'deal' when ready to start the game,
        or 'menu' to return to main menu.""")
        
        while self.running and self.current_mode == "playing":
            # Capture and process frame
            frame = self.card_detector.capture_frame()
            if frame is None:
                continue
            
            # Detect cards
            detected_cards, _ = self.card_detector.detect_cards_in_frame(frame)
            
            # Show annotated frame
            annotated_frame = self.card_detector.annotate_frame(frame, detected_cards)
            cv2.imshow('Accessible Blackjack', annotated_frame)
            
            # Listen for commands
            command = self.audio.listen_for_command(timeout=1)
            if command:
                self.handle_blackjack_command(command, detected_cards, frame)
            
            # Check for window close
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cv2.destroyAllWindows()
        self.current_mode = "menu"
    
    def handle_blackjack_command(self, command: str, detected_cards: List[Dict], frame):
        """Handle commands during blackjack game"""
        
        if "menu" in command or "quit" in command:
            self.current_mode = "menu"
            return
        
        elif "detect" in command:
            self.announce_detected_cards(detected_cards, frame)
        
        elif "deal" in command and self.blackjack.game_phase == "waiting":
            self.deal_initial_cards(detected_cards, frame)
        
        elif "hit" in command and self.blackjack.game_phase == "player_turn":
            self.player_hit(detected_cards, frame)
        
        elif "stand" in command and self.blackjack.game_phase == "player_turn":
            self.player_stand()
        
        elif "new game" in command or "restart" in command:
            self.blackjack.reset_game()
            self.audio.speak("New game started. Place your cards and say 'deal' when ready.")
        
        elif "help" in command:
            self.show_blackjack_help()
    
    def announce_detected_cards(self, detected_cards: List[Dict], frame):
        """Announce what cards are detected with recognition"""
        stable_cards = [card for card in detected_cards 
                       if card.get('stable_frames', 0) >= 3]
        
        if not stable_cards:
            self.audio.speak("No stable cards detected. Make sure cards are flat and well-lit.")
            return
        
        self.audio.speak(f"I can see {len(stable_cards)} stable cards.")
        
        # Try to identify each card
        for i, card_info in enumerate(stable_cards):
            card_image = self.card_extractor.extract_and_normalize_card(frame, card_info)
            corner_image = self.card_extractor.get_primary_corner(card_image)
            
            # Use template recognition
            value, suit, confidence = self.card_recognizer.identify_card_from_corner(corner_image)
            
            if value and suit and confidence > 0.5:
                self.audio.speak(f"Card {i + 1}: {value} of {suit} with {confidence:.1%} confidence")
            else:
                self.audio.speak(f"Card {i + 1}: Cannot identify clearly. Confidence too low.")
    
    def deal_initial_cards(self, detected_cards: List[Dict], frame):
        """Deal initial blackjack cards"""
        stable_cards = [card for card in detected_cards 
                       if card.get('stable_frames', 0) >= 5]
        
        if len(stable_cards) < 3:
            self.audio.speak("I need to see at least 3 stable cards: 2 for you and 1 for the dealer.")
            return
        
        # Identify cards
        identified_cards = []
        for card_info in stable_cards[:4]:  # Max 4 cards for initial deal
            card_image = self.card_extractor.extract_and_normalize_card(frame, card_info)
            corner_image = self.card_extractor.get_primary_corner(card_image)
            
            value, suit, confidence = self.card_recognizer.identify_card_from_corner(corner_image)
            
            if value and suit and confidence > 0.4:
                identified_cards.append((value, suit, confidence))
            else:
                self.audio.speak("Some cards cannot be identified clearly. Please adjust lighting or card position.")
                return
        
        # Assign cards (assume bottom cards are player's, top card is dealer's)
        # This is simplified - in a real system you'd use position analysis
        if len(identified_cards) >= 3:
            # Player gets first 2 cards
            for i in range(2):
                value, suit, _ = identified_cards[i]
                self.blackjack.add_card_to_player(value, suit)
            
            # Dealer gets 1 card
            value, suit, _ = identified_cards[2]
            self.blackjack.add_card_to_dealer(value, suit)
            
            # Announce deal
            self.audio.speak("Cards dealt!")
            self.audio.speak(f"Your hand: {self.blackjack.get_hand_description(self.blackjack.player_cards)}")
            self.audio.speak(f"Dealer shows: {self.blackjack.get_hand_description(self.blackjack.dealer_cards)}")
            
            # Check for blackjack
            if self.blackjack.is_blackjack(self.blackjack.player_cards):
                self.audio.speak("Blackjack! You have 21!")
                self.blackjack.game_phase = "game_over"
                self.end_game()
            else:
                self.blackjack.game_phase = "player_turn"
                self.audio.speak("Your turn. Say 'hit' for another card or 'stand' to stay.")
    
    def player_hit(self, detected_cards: List[Dict], frame):
        """Handle player hit"""
        expected_total_cards = len(self.blackjack.player_cards) + len(self.blackjack.dealer_cards) + 1
        
        stable_cards = [card for card in detected_cards 
                       if card.get('stable_frames', 0) >= 3]
        
        if len(stable_cards) < expected_total_cards:
            self.audio.speak(f"Please place your new card. I should see {expected_total_cards} total cards.")
            return
        
        # Find the new card (this is simplified logic)
        # In a real system, you'd track which specific card was added
        new_card_info = stable_cards[expected_total_cards - 1]
        card_image = self.card_extractor.extract_and_normalize_card(frame, new_card_info)
        corner_image = self.card_extractor.get_primary_corner(card_image)
        
        value, suit, confidence = self.card_recognizer.identify_card_from_corner(corner_image)
        
        if value and suit and confidence > 0.4:
            self.blackjack.add_card_to_player(value, suit)
            self.audio.speak(f"You drew {value} of {suit}")
            
            player_total = self.blackjack.get_player_total()
            self.audio.speak(f"Your total is now {player_total}")
            
            if self.blackjack.is_bust(self.blackjack.player_cards):
                self.audio.speak("Bust! You went over 21.")
                self.blackjack.game_phase = "game_over"
                self.end_game()
            elif player_total == 21:
                self.audio.speak("21! Standing automatically.")
                self.player_stand()
        else:
            self.audio.speak("Cannot identify the new card clearly. Please adjust position.")
    
    def player_stand(self):
        """Handle player stand - dealer plays"""
        self.audio.speak(f"You stand with {self.blackjack.get_player_total()}")
        self.blackjack.game_phase = "dealer_turn"
        
        # Simulate dealer's play (in real game, you'd reveal hole card and deal more)
        self.audio.speak("Dealer reveals hole card and plays...")
        
        # Add simulated dealer cards
        while self.blackjack.should_dealer_hit():
            # In a real implementation, you'd wait for actual cards to be placed
            self.audio.speak("Dealer hits...")
            time.sleep(1)
            # Simulate dealer card (this would be actual card recognition)
            import random
            values = ['2', '3', '4', '5', '6', '7', '8', '9', '10']
            suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
            sim_value = random.choice(values)
            sim_suit = random.choice(suits)
            self.blackjack.add_card_to_dealer(sim_value, sim_suit)
            
            dealer_total = self.blackjack.get_dealer_total()
            self.audio.speak(f"Dealer draws {sim_value} of {sim_suit}. Dealer total: {dealer_total}")
        
        self.blackjack.game_phase = "game_over"
        self.end_game()
    
    def end_game(self):
        """End the current game and announce results"""
        result = self.blackjack.determine_winner()
        
        # Announce final hands
        self.audio.speak(f"Final results:")
        self.audio.speak(f"Your hand: {self.blackjack.get_hand_description(self.blackjack.player_cards)}")
        self.audio.speak(f"Dealer's hand: {self.blackjack.get_hand_description(self.blackjack.dealer_cards)}")
        
        # Announce winner
        result_messages = {
            "player_wins_dealer_bust": "You win! Dealer busted.",
            "dealer_wins_player_bust": "Dealer wins. You busted.",
            "player_blackjack": "You win with Blackjack!",
            "dealer_blackjack": "Dealer wins with Blackjack.",
            "push_both_blackjack": "Push! Both have Blackjack.",
            "player_wins_higher": "You win with the higher total!",
            "dealer_wins_higher": "Dealer wins with the higher total.",
            "push": "Push! It's a tie."
        }
        
        self.audio.speak(result_messages.get(result, "Game complete."))
        self.audio.speak("Say 'new game' to play again or 'menu' to return to main menu.")
    
    def train_templates(self):
        """Template training mode"""
        self.audio.speak("Template training mode. This will help improve card recognition.")
        
        trainer = TemplateTrainer(self.card_db)
        
        self.audio.speak("Starting camera for template collection. Press C in the camera window to capture, Q to quit.")
        
        trainer.start_template_collection()
        
        # Reload templates
        self.card_recognizer.update_templates()
        
        self.audio.speak("Template training complete. Recognition system updated.")
        self.current_mode = "menu"
    
    def test_detection_mode(self):
        """Test detection without playing"""
        self.audio.speak("Detection test mode. Place cards and say 'detect' to test recognition.")
        
        while self.current_mode == "menu":  # Stay in this mode
            frame = self.card_detector.capture_frame()
            if frame is None:
                continue
            
            detected_cards, debug_info = self.card_detector.detect_cards_in_frame(frame, return_debug_info=True)
            annotated_frame = self.card_detector.annotate_frame(frame, detected_cards)
            
            cv2.imshow('Detection Test', annotated_frame)
            
            command = self.audio.listen_for_command(timeout=1)
            
            if command:
                if "detect" in command:
                    self.announce_detected_cards(detected_cards, frame)
                elif "menu" in command or "quit" in command:
                    break
                elif "help" in command:
                    self.audio.speak("Say 'detect' to test recognition, 'menu' to return to main menu.")
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cv2.destroyAllWindows()
    
    def show_help(self):
        """Show help information"""
        help_text = """Available commands:
        
        Main Menu:
        - 'play blackjack' - Start a blackjack game
        - 'train templates' - Add card templates for better recognition
        - 'test detection' - Test card detection without playing
        - 'quit' - Exit the program
        
        During Blackjack:
        - 'detect cards' - See what cards I can identify
        - 'deal' - Start the game with current cards
        - 'hit' - Take another card
        - 'stand' - Keep current total, dealer plays
        - 'new game' - Start a new round
        - 'menu' - Return to main menu
        
        Tips for better detection:
        - Use a dark, solid background
        - Ensure bright, even lighting
        - Keep cards flat and separate
        - Position camera 12-18 inches above cards
        """
        
        self.audio.speak(help_text)
    
    def show_blackjack_help(self):
        """Show blackjack-specific help"""
        help_text = """Blackjack commands:
        'detect cards' - See current card recognition
        'deal' - Start game (need 3+ cards visible)
        'hit' - Take another card
        'stand' - Stop taking cards
        'new game' - Reset and start over
        'menu' - Return to main menu
        """
        
        self.audio.speak(help_text)
    
    def cleanup(self):
        """Cleanup all system resources"""
        print("Cleaning up system resources...")
        if hasattr(self, 'card_detector'):
            self.card_detector.cleanup()
        cv2.destroyAllWindows()
    
    def run(self):
        """Main system loop"""
        try:
            self.audio.speak("Welcome to the Accessible Blackjack System!")
            
            # Check system status
            templates_count = len(self.card_db.list_available_templates())
            if templates_count == 0:
                self.audio.speak("""No card templates found. For best results, 
                you should train some templates first. Say 'train templates' from the main menu.""")
            
            # Start main menu
            self.main_menu()
            
        except KeyboardInterrupt:
            self.audio.speak("System interrupted. Goodbye!")
        
        except Exception as e:
            print(f"System error: {e}")
            self.audio.speak("System error occurred. Please restart the program.")
        
        finally:
            self.cleanup()


def main():
    """Main entry point"""
    print("=" * 60)
    print("ACCESSIBLE BLACKJACK SYSTEM")
    print("=" * 60)
    print()
    print("This modular system includes:")
    print("• Voice-controlled interface")
    print("• Advanced computer vision card detection")
    print("• Template-based card recognition")
    print("• Training system for custom card templates")
    print("• Complete blackjack game logic")
    print()
    print("Requirements:")
    print("• Working camera (for card detection)")
    print("• Working microphone (for voice commands)")
    print("• Good lighting and dark background for cards")
    print()
    print("Press Ctrl+C to exit at any time")
    print("=" * 60)
    
    # Initialize and run the system
    system = AccessibleBlackjackSystem()
    system.run()


if __name__ == "__main__":
    main()