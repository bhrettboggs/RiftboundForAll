import cv2
import numpy as np
import pyttsx3
import speech_recognition as sr
import threading
import time
import sys
from typing import List, Tuple, Optional
from flask import Flask, render_template_string, jsonify
from flask_socketio import SocketIO, emit
import json
import os

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

class ImprovedAccessibleCardGame:
    def __init__(self):
        print("Starting initialization...")
        
        # Add SocketIO reference
        self.socketio = socketio
        
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
        
        # Card detection parameters
        self.min_card_area = 3000
        self.max_card_area = 80000
        self.card_aspect_ratio_min = 0.4
        self.card_aspect_ratio_max = 1.0
        
        # Blackjack game state
        self.player_cards = []
        self.dealer_cards = []
        self.game_phase = "waiting"
        self.last_detected_count = 0
        self.detection_stable_frames = 0
        self.required_stable_frames = 10
        self.detected_cards = []  # For web UI
        
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
        self.speak("Web interface available at http://localhost:5000")
        self.speak("Say help for available commands.")

    def broadcast_game_state(self):
        """Send current game state to web UI"""
        try:
            state = {
                'phase': self.game_phase,
                'player_cards': self.player_cards,
                'dealer_cards': self.dealer_cards,
                'detected_cards': [
                    {'value': card['value'], 'suit': card['suit']} 
                    for card in self.detected_cards
                ],
                'player_total': self.calculate_blackjack_total(self.player_cards),
                'dealer_total': self.calculate_blackjack_total(self.dealer_cards)
            }
            self.socketio.emit('game_update', state)
            print(f"Broadcasted game state: {state['phase']}")
        except Exception as e:
            print(f"Error broadcasting game state: {e}")

    def broadcast_log_message(self, message, msg_type="system"):
        """Send log message to web UI"""
        try:
            self.socketio.emit('log_message', {
                'message': message,
                'type': msg_type,
                'timestamp': time.time()
            })
        except Exception as e:
            print(f"Error broadcasting log: {e}")

    def speak(self, text):
        """Convert text to speech using a fresh engine instance each time"""
        print(f"Speaking: {text}")
        
        # Also send to web UI
        self.broadcast_log_message(f"TTS: {text}", "system")
        
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
            # Broadcast listening status
            self.socketio.emit('voice_status', {'status': 'Listening...', 'listening': True})
            
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=4)
            
            command = self.recognizer.recognize_google(audio).lower()
            print(f"Command heard: {command}")
            self.speak(f"Command heard: {command}")
            self.broadcast_log_message(f"Voice command: {command}", "command")
            
            # Reset voice status
            self.socketio.emit('voice_status', {'status': 'Ready', 'listening': False})
            return command
        except sr.WaitTimeoutError:
            print("Listening timeout - no command heard")
            self.socketio.emit('voice_status', {'status': 'Ready', 'listening': False})
            return None
        except sr.UnknownValueError:
            print("Could not understand audio")
            self.speak("Could not understand audio")
            self.broadcast_log_message("Could not understand audio", "error")
            self.socketio.emit('voice_status', {'status': 'Ready', 'listening': False})
            return None
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
            self.speak(f"Speech recognition error: {str(e)}")
            self.broadcast_log_message(f"Speech recognition error: {str(e)}", "error")
            self.socketio.emit('voice_status', {'status': 'Ready', 'listening': False})
            return None

    def preprocess_for_card_detection(self, frame):
        """Preprocess frame for better card detection"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        return gray, thresh

    def detect_card_contours(self, thresh_frame):
        """Detect card-like contours in the frame"""
        contours, _ = cv2.findContours(thresh_frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        card_contours = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_card_area < area < self.max_card_area:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h
                if self.card_aspect_ratio_min < aspect_ratio < self.card_aspect_ratio_max:
                    epsilon = 0.05 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    if len(approx) >= 3:
                        card_contours.append({
                            'contour': contour,
                            'approx': approx,
                            'bbox': (x, y, w, h),
                            'area': area,
                            'aspect_ratio': aspect_ratio
                        })
        
        card_contours.sort(key=lambda x: x['area'], reverse=True)
        return card_contours

    def extract_corner_for_recognition(self, frame, card_info):
        """Extract the corner of the card where value/suit are located"""
        x, y, w, h = card_info['bbox']
        corner_size_w = min(w // 3, 100)
        corner_size_h = min(h // 3, 140)
        corner_size_w = min(corner_size_w, frame.shape[1] - x)
        corner_size_h = min(corner_size_h, frame.shape[0] - y)
        
        if corner_size_w < 20 or corner_size_h < 20:
            return None
        
        corner = frame[y:y + corner_size_h, x:x + corner_size_w]
        return corner

    def simple_card_recognition(self, corner_roi):
        """Main card recognition method - simplified for demo"""
        if corner_roi is None or corner_roi.size == 0:
            return 'Unknown', 'Unknown'
        
        # Simplified recognition - returns random values for demo
        values = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        
        value = np.random.choice(values)
        suit = np.random.choice(suits)
        
        return value, suit

    def detect_and_identify_cards(self, frame):
        """Main card detection and identification method"""
        gray, thresh = self.preprocess_for_card_detection(frame)
        card_contours = self.detect_card_contours(thresh)
        
        detected_cards = []
        annotated_frame = frame.copy()
        
        for i, card_info in enumerate(card_contours[:6]):
            corner = self.extract_corner_for_recognition(gray, card_info)
            
            if corner is not None and corner.size > 100:
                value, suit = self.simple_card_recognition(corner)
                
                detected_cards.append({
                    'value': value,
                    'suit': suit,
                    'bbox': card_info['bbox'],
                    'area': card_info['area']
                })
                
                x, y, w, h = card_info['bbox']
                cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
                label = f"#{i+1}: {value} of {suit}"
                cv2.putText(annotated_frame, label, (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        info_text = f"Cards detected: {len(detected_cards)}"
        cv2.putText(annotated_frame, info_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        phase_text = f"Phase: {self.game_phase}"
        cv2.putText(annotated_frame, phase_text, (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        self.detected_cards = detected_cards
        return detected_cards, annotated_frame

    def announce_detected_cards(self, detected_cards):
        """Announce all detected cards"""
        if not detected_cards:
            self.speak("No cards detected. Make sure cards are clearly visible on a contrasting background.")
            return
        
        count = len(detected_cards)
        self.speak(f"I can see {count} card{'s' if count != 1 else ''}")
        
        for i, card in enumerate(detected_cards):
            self.speak(f"Card {i + 1}: {card['value']} of {card['suit']}")

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
                    pass
        
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        
        return total

    def organize_cards_by_position(self, detected_cards):
        """Organize cards by position (top = dealer, bottom = player)"""
        if not detected_cards:
            return {'dealer': [], 'player': []}
        
        sorted_cards = sorted(detected_cards, key=lambda card: card['bbox'][1])
        
        if len(sorted_cards) >= 2:
            dealer_cards = sorted_cards[:1] if len(sorted_cards) >= 3 else []
            player_cards = sorted_cards[1:] if len(sorted_cards) >= 3 else sorted_cards[-2:]
        else:
            dealer_cards = []
            player_cards = sorted_cards
        
        return {'dealer': dealer_cards, 'player': player_cards}

    def play_blackjack(self):
        """Main blackjack game loop"""
        self.speak("Starting Blackjack!")
        self.speak("Place cards clearly on a dark background. Cards should not overlap.")
        self.speak("Say 'detect' to check what cards I can see.")
        self.speak("Say 'deal' when you have the initial cards in position.")
        
        self.game_phase = "waiting"
        self.player_cards = []
        self.dealer_cards = []
        self.broadcast_game_state()
        
        detection_interval = 0
        
        while self.running and self.current_game == "blackjack":
            ret, frame = self.camera.read()
            if not ret:
                continue
            
            detected_cards = []
            annotated_frame = frame
            
            if detection_interval % 5 == 0:
                detected_cards, annotated_frame = self.detect_and_identify_cards(frame)
                if detected_cards != self.detected_cards:
                    self.broadcast_game_state()
            
            detection_interval += 1
            
            cv2.imshow('Accessible Blackjack - Card Detection', annotated_frame)
            
            try:
                command = self.listen_for_command(timeout=0.5)
                if command:
                    self.handle_blackjack_command(command, detected_cards)
            except:
                pass
            
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
            self.broadcast_log_message("Exiting blackjack", "system")
            return
        
        elif "detect" in command or "see" in command or "show" in command:
            self.announce_detected_cards(detected_cards)
        
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
            self.broadcast_log_message(f"Unrecognized command: {command}", "error")

    def deal_initial_cards(self, detected_cards):
        """Deal initial cards for blackjack"""
        if len(detected_cards) < 3:
            self.speak("Please place at least 3 cards: 2 for you and 1 visible for the dealer.")
            return
        
        card_positions = self.organize_cards_by_position(detected_cards)
        
        if len(card_positions['player']) < 2:
            self.speak("I need to see at least 2 player cards. Place them in the bottom area of the camera view.")
            return
        
        if len(card_positions['dealer']) < 1:
            self.speak("I need to see at least 1 dealer card. Place it in the top area of the camera view.")
            return
        
        self.player_cards = [(card['value'], card['suit']) for card in card_positions['player'][:2]]
        self.dealer_cards = [(card['value'], card['suit']) for card in card_positions['dealer'][:1]]
        
        self.speak("Cards dealt!")
        self.announce_cards(self.player_cards, "You have")
        self.announce_cards(self.dealer_cards, "Dealer shows")
        
        player_total = self.calculate_blackjack_total(self.player_cards)
        if player_total == 21:
            self.speak("Blackjack! You have 21!")
            self.game_phase = "game_over"
        else:
            self.game_phase = "player_turn"
            self.speak("Your turn. Say 'hit' to take another card or 'stand' to stay.")
        
        self.broadcast_game_state()

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
        # Simulate hitting for demo
        new_card = ("5", "Clubs")
        self.player_cards.append(new_card)
        
        self.speak(f"You drew {new_card[0]} of {new_card[1]}")
        self.broadcast_log_message(f"Player drew {new_card[0]} of {new_card[1]}", "system")
        
        player_total = self.calculate_blackjack_total(self.player_cards)
        self.speak(f"Your total is now {player_total}")
        
        if player_total > 21:
            self.speak("Bust! You went over 21. You lose.")
            self.game_phase = "game_over"
            self.broadcast_log_message("Player busts!", "system")
        elif player_total == 21:
            self.speak("21! Standing automatically.")
            self.player_stand(detected_cards)
        else:
            self.speak("Say 'hit' for another card or 'stand' to stay.")
        
        self.broadcast_game_state()

    def player_stand(self, detected_cards):
        """Player stands, dealer plays"""
        player_total = self.calculate_blackjack_total(self.player_cards)
        self.speak(f"You stand with {player_total}")
        self.broadcast_log_message(f"Player stands with {player_total}", "system")
        self.game_phase = "dealer_turn"
        self.broadcast_game_state()
        
        self.speak("Dealer's turn. Please reveal the dealer's hole card.")
        time.sleep(2)
        
        hole_card = ("10", "Spades")
        self.dealer_cards.append(hole_card)
        self.announce_cards(self.dealer_cards, "Dealer has")
        
        dealer_total = self.calculate_blackjack_total(self.dealer_cards)
        while dealer_total < 17:
            self.speak("Dealer must hit.")
            new_card = ("6", "Hearts")
            self.dealer_cards.append(new_card)
            self.speak(f"Dealer draws {new_card[0]} of {new_card[1]}")
            dealer_total = self.calculate_blackjack_total(self.dealer_cards)
            self.speak(f"Dealer total: {dealer_total}")
            self.broadcast_game_state()
            time.sleep(1)
        
        if dealer_total > 21:
            self.speak(f"Dealer busts! You win!")
            self.broadcast_log_message("Dealer busts! Player wins!", "system")
        elif dealer_total > player_total:
            self.speak(f"Dealer wins {dealer_total} to {player_total}")
            self.broadcast_log_message(f"Dealer wins {dealer_total} to {player_total}", "system")
        elif player_total > dealer_total:
            self.speak(f"You win {player_total} to {dealer_total}!")
            self.broadcast_log_message(f"Player wins {player_total} to {dealer_total}!", "system")
        else:
            self.speak(f"Push! Both have {player_total}")
            self.broadcast_log_message(f"Push! Both have {player_total}", "system")
        
        self.game_phase = "game_over"
        self.speak("Game over. Say 'new game' to play again.")
        self.broadcast_game_state()

    def new_blackjack_game(self):
        """Start a new game"""
        self.player_cards = []
        self.dealer_cards = []
        self.game_phase = "waiting"
        self.detected_cards = []
        self.speak("New game started. Place your cards and say 'deal' when ready.")
        self.broadcast_game_state()

    def blackjack_help(self):
        """Provide help"""
        help_text = """Available commands: 
        'detect' - Tell me what cards I can see
        'deal' - Start the game with current cards
        'hit' - Take another card
        'stand' - Keep current total
        'new game' - Start over
        'help' - This message
        'quit' - Exit game"""
        self.speak(help_text)
        self.broadcast_log_message("Help requested", "system")

    def announce_game_status(self):
        """Announce current status"""
        if self.player_cards:
            self.announce_cards(self.player_cards, "You have")
        if self.dealer_cards:
            self.announce_cards(self.dealer_cards, "Dealer has")
        
        self.speak(f"Game phase: {self.game_phase}")
        self.broadcast_log_message("Status requested", "command")

    def game_selection_menu(self):
        """Voice-controlled game selection"""
        while self.running:
            self.speak("Game Selection. Say 'blackjack' to play, or 'quit' to exit.")
            self.broadcast_log_message("Game selection menu", "system")
            print("Waiting for user command...")
            
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

    def run(self):
        """Main program loop"""
        try:
            self.game_selection_menu()
        except KeyboardInterrupt:
            self.speak("Program interrupted. Goodbye!")
        except Exception as e:
            self.speak(f"An error occurred: {str(e)}")
            self.broadcast_log_message(f"Error: {str(e)}", "error")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        if self.camera:
            self.camera.release()
        cv2.destroyAllWindows()
        self.speak("Resources cleaned up successfully.")

# Global game instance
game_instance = None

# HTML Template - Properly formatted as Python string
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Accessible Blackjack</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh; color: white; overflow-x: hidden;
        }
        .container {
            max-width: 1400px; margin: 0 auto; padding: 20px;
            display: grid; grid-template-columns: 1fr 400px; gap: 20px; min-height: 100vh;
        }
        .game-area { display: flex; flex-direction: column; gap: 20px; }
        .header {
            text-align: center; padding: 20px;
            background: rgba(255, 255, 255, 0.1); border-radius: 20px;
            backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3); }
        .status-bar {
            display: flex; justify-content: space-between; align-items: center;
            padding: 15px 20px; background: rgba(0, 0, 0, 0.3); border-radius: 15px;
            font-size: 1.1em; font-weight: 600;
        }
        .game-phase { color: #4CAF50; }
        .cards-detected { color: #FFC107; }
        .card-areas { display: grid; grid-template-rows: 1fr auto 1fr; gap: 30px; min-height: 400px; }
        .dealer-section, .player-section {
            background: rgba(255, 255, 255, 0.1); border-radius: 20px; padding: 25px;
            backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .section-title { font-size: 1.4em; font-weight: 700; margin-bottom: 15px; text-align: center; }
        .dealer-section .section-title { color: #FF6B6B; }
        .player-section .section-title { color: #4ECDC4; }
        .cards-container {
            display: flex; justify-content: center; gap: 15px; min-height: 120px;
            align-items: center; flex-wrap: wrap;
        }
        .card {
            width: 80px; height: 110px; background: linear-gradient(145deg, #ffffff, #f0f0f0);
            border-radius: 12px; display: flex; flex-direction: column; justify-content: space-between;
            padding: 8px; color: #333; font-weight: bold; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
            border: 2px solid #ddd; position: relative; transition: transform 0.3s ease;
        }
        .card:hover { transform: translateY(-5px); }
        .card.hearts, .card.diamonds { color: #d32f2f; }
        .card.clubs, .card.spades { color: #333; }
        .card-value { font-size: 16px; font-weight: 900; }
        .card-suit { font-size: 20px; text-align: center; margin: 5px 0; }
        .empty-card {
            background: rgba(255, 255, 255, 0.1); border: 2px dashed rgba(255, 255, 255, 0.3);
            color: rgba(255, 255, 255, 0.5); display: flex; align-items: center; justify-content: center; font-size: 12px;
        }
        .total-display {
            text-align: center; font-size: 1.3em; font-weight: 700; margin-top: 15px;
            padding: 10px; background: rgba(0, 0, 0, 0.2); border-radius: 10px;
        }
        .middle-info {
            text-align: center; padding: 20px; background: rgba(0, 0, 0, 0.3);
            border-radius: 15px; font-size: 1.1em;
        }
        .control-panel {
            background: rgba(255, 255, 255, 0.1); border-radius: 20px; padding: 25px;
            backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.2);
            display: flex; flex-direction: column; gap: 20px;
        }
        .control-section { background: rgba(0, 0, 0, 0.2); border-radius: 15px; padding: 20px; }
        .control-section h3 { margin-bottom: 15px; color: #FFC107; font-size: 1.2em; }
        .button-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; }
        .btn {
            padding: 12px 20px; border: none; border-radius: 10px; font-size: 1em; font-weight: 600;
            cursor: pointer; transition: all 0.3s ease; background: linear-gradient(145deg, #667eea 0%, #764ba2 100%);
            color: white; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3); }
        .btn:active { transform: translateY(0); }
        .btn.primary { background: linear-gradient(145deg, #4CAF50, #45a049); }
        .btn.danger { background: linear-gradient(145deg, #f44336, #da190b); }
        .btn.warning { background: linear-gradient(145deg, #ff9800, #f57c00); }
        .voice-status {
            display: flex; align-items: center; gap: 10px; padding: 15px;
            background: rgba(0, 0, 0, 0.3); border-radius: 10px; margin-bottom: 20px;
        }
        .voice-indicator {
            width: 12px; height: 12px; border-radius: 50%; background: #4CAF50; animation: pulse 2s infinite;
        }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
        .voice-indicator.listening { background: #FF5722; animation: pulse 0.5s infinite; }
        .detection-area { background: rgba(0, 0, 0, 0.2); border-radius: 15px; padding: 20px; }
        .detected-cards { max-height: 200px; overflow-y: auto; }
        .detected-card {
            display: flex; justify-content: space-between; align-items: center; padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        .detected-card:last-child { border-bottom: none; }
        .log-area { background: rgba(0, 0, 0, 0.2); border-radius: 15px; padding: 20px; max-height: 200px; overflow-y: auto; }
        .log-entry {
            margin-bottom: 10px; padding: 8px; background: rgba(255, 255, 255, 0.05);
            border-radius: 5px; font-size: 0.9em;
        }
        .log-entry.command { border-left: 3px solid #4CAF50; }
        .log-entry.system { border-left: 3px solid #2196F3; }
        .log-entry.error { border-left: 3px solid #f44336; }
        .tips-section { font-size: 0.9em; line-height: 1.6; }
        .tips-section ul { list-style: none; padding: 0; }
        .tips-section li { padding: 5px 0; padding-left: 15px; position: relative; }
        .tips-section li:before { content: "💡"; position: absolute; left: 0; }
        @media (max-width: 1200px) { .container { grid-template-columns: 1fr; gap: 15px; } }
        @media (max-width: 768px) {
            .button-grid { grid-template-columns: 1fr; }
            .cards-container { gap: 10px; }
            .card { width: 60px; height: 85px; padding: 6px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="game-area">
            <div class="header">
                <h1>🎴 Accessible Blackjack</h1>
                <p>Computer Vision + Voice Control Card Game</p>
                <p><small>Connected to Python Backend</small></p>
            </div>

            <div class="status-bar">
                <div class="game-phase">Phase: <span id="game-phase">Waiting</span></div>
                <div class="cards-detected">Cards Detected: <span id="cards-count">0</span></div>
            </div>

            <div class="card-areas">
                <div class="dealer-section">
                    <div class="section-title">🎩 Dealer</div>
                    <div class="cards-container" id="dealer-cards">
                        <div class="card empty-card">Card 1</div>
                    </div>
                    <div class="total-display">Total: <span id="dealer-total">0</span></div>
                </div>

                <div class="middle-info">
                    <div id="game-message">Connecting to Python backend...</div>
                </div>

                <div class="player-section">
                    <div class="section-title">🎯 You</div>
                    <div class="cards-container" id="player-cards">
                        <div class="card empty-card">Card 1</div>
                        <div class="card empty-card">Card 2</div>
                    </div>
                    <div class="total-display">Total: <span id="player-total">0</span></div>
                </div>
            </div>
        </div>

        <div class="control-panel">
            <div class="voice-status">
                <div class="voice-indicator" id="voice-indicator"></div>
                <span>Voice Control: <span id="voice-status">Connecting...</span></span>
            </div>

            <div class="control-section">
                <h3>🎮 Game Controls</h3>
                <div class="button-grid">
                    <button class="btn primary" onclick="sendCommand('detect')">🔍 Detect Cards</button>
                    <button class="btn primary" onclick="sendCommand('deal')">🎴 Deal</button>
                    <button class="btn warning" onclick="sendCommand('hit')">📈 Hit</button>
                    <button class="btn danger" onclick="sendCommand('stand')">✋ Stand</button>
                </div>
                <button class="btn" onclick="sendCommand('new game')" style="width: 100%;">🔄 New Game</button>
            </div>

            <div class="control-section">
                <h3>🎯 Detected Cards</h3>
                <div class="detection-area">
                    <div class="detected-cards" id="detected-cards">
                        <div style="text-align: center; color: rgba(255,255,255,0.5);">
                            Waiting for Python backend...
                        </div>
                    </div>
                </div>
            </div>

            <div class="control-section">
                <h3>📝 Activity Log</h3>
                <div class="log-area" id="activity-log">
                    <div class="log-entry system">Initializing web interface...</div>
                </div>
            </div>

            <div class="control-section tips-section">
                <h3>💡 Detection Tips</h3>
                <ul>
                    <li>Use dark background</li>
                    <li>Good lighting is essential</li>
                    <li>Keep cards flat, no overlap</li>
                    <li>Camera 12-18" above cards</li>
                    <li>Clean, uncreased cards work best</li>
                </ul>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        
        let gameState = {
            phase: 'waiting', playerCards: [], dealerCards: [], detectedCards: [],
            playerTotal: 0, dealerTotal: 0, isListening: false
        };

        socket.on('connect', function() {
            console.log('Connected to Python backend');
            addLogEntry('Connected to Python backend', 'system');
            setVoiceStatus('Ready', false);
            document.getElementById('game-message').textContent = 'Connected! Ready to play blackjack.';
        });

        socket.on('disconnect', function() {
            console.log('Disconnected from Python backend');
            addLogEntry('Disconnected from backend', 'error');
            setVoiceStatus('Disconnected', false);
            document.getElementById('game-message').textContent = 'Connection lost. Please restart Python backend.';
        });

        socket.on('game_update', function(data) {
            console.log('Game update received:', data);
            updateGameState(data);
        });

        socket.on('log_message', function(data) {
            console.log('Log message received:', data);
            addLogEntry(data.message, data.type);
        });

        socket.on('voice_status', function(data) {
            console.log('Voice status update:', data);
            setVoiceStatus(data.status, data.listening);
        });

        function updateGameState(data) {
            if (data.phase) updateGamePhase(data.phase);
            if (data.player_cards) updatePlayerCards(data.player_cards);
            if (data.dealer_cards) updateDealerCards(data.dealer_cards);
            if (data.detected_cards) updateDetectedCards(data.detected_cards);
        }

        function updateGamePhase(phase) {
            gameState.phase = phase;
            document.getElementById('game-phase').textContent = phase;
            
            const messageEl = document.getElementById('game-message');
            switch(phase) {
                case 'waiting': messageEl.textContent = 'Place your cards and say "deal" when ready'; break;
                case 'player_turn': messageEl.textContent = 'Your turn! Say "hit" or "stand"'; break;
                case 'dealer_turn': messageEl.textContent = 'Dealer is playing...'; break;
                case 'game_over': messageEl.textContent = 'Game finished! Say "new game" to play again'; break;
            }
        }

        function updateDetectedCards(cards) {
            gameState.detectedCards = cards;
            document.getElementById('cards-count').textContent = cards.length;
            
            const container = document.getElementById('detected-cards');
            if (cards.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: rgba(255,255,255,0.5);">No cards detected</div>';
                return;
            }
            
            container.innerHTML = cards.map((card, index) => 
                `<div class="detected-card"><span>Card ${index + 1}: ${card.value} of ${card.suit}</span></div>`
            ).join('');
        }

        function createCardElement(value, suit) {
            const suitSymbols = { 'Hearts': '♥', 'Diamonds': '♦', 'Clubs': '♣', 'Spades': '♠' };
            const suitClass = suit.toLowerCase();
            const symbol = suitSymbols[suit] || '?';
            
            return `<div class="card ${suitClass}">
                        <div class="card-value">${value}</div>
                        <div class="card-suit">${symbol}</div>
                        <div class="card-value" style="transform: rotate(180deg); font-size: 12px;">${value}</div>
                    </div>`;
        }

        function updatePlayerCards(cards) {
            gameState.playerCards = cards;
            const container = document.getElementById('player-cards');
            
            let html = '';
            for (let i = 0; i < Math.max(2, cards.length); i++) {
                if (i < cards.length) {
                    const [value, suit] = cards[i];
                    html += createCardElement(value, suit);
                } else {
                    html += '<div class="card empty-card">Card ' + (i + 1) + '</div>';
                }
            }
            container.innerHTML = html;
            
            const total = calculateTotal(cards);
            gameState.playerTotal = total;
            document.getElementById('player-total').textContent = total;
        }

        function updateDealerCards(cards) {
            gameState.dealerCards = cards;
            const container = document.getElementById('dealer-cards');
            
            let html = '';
            for (let i = 0; i < Math.max(1, cards.length); i++) {
                if (i < cards.length) {
                    const [value, suit] = cards[i];
                    html += createCardElement(value, suit);
                } else {
                    html += '<div class="card empty-card">Card ' + (i + 1) + '</div>';
                }
            }
            container.innerHTML = html;
            
            const total = calculateTotal(cards);
            gameState.dealerTotal = total;
            document.getElementById('dealer-total').textContent = total;
        }

        function calculateTotal(cards) {
            let total = 0, aces = 0;
            
            for (const [value] of cards) {
                if (value === 'A') { aces++; total += 11; }
                else if (['J', 'Q', 'K'].includes(value)) total += 10;
                else if (!isNaN(value)) total += parseInt(value);
            }
            
            while (total > 21 && aces > 0) { total -= 10; aces--; }
            return total;
        }

        function addLogEntry(message, type = 'system') {
            const log = document.getElementById('activity-log');
            const entry = document.createElement('div');
            entry.className = `log-entry ${type}`;
            entry.textContent = new Date().toLocaleTimeString() + ': ' + message;
            
            log.insertBefore(entry, log.firstChild);
            while (log.children.length > 20) log.removeChild(log.lastChild);
        }

        function setVoiceStatus(status, listening = false) {
            document.getElementById('voice-status').textContent = status;
            const indicator = document.getElementById('voice-indicator');
            
            if (listening) { indicator.classList.add('listening'); gameState.isListening = true; }
            else { indicator.classList.remove('listening'); gameState.isListening = false; }
        }

        function sendCommand(command) {
            addLogEntry(`Button: ${command}`, 'command');
            socket.emit('web_command', {command: command});
        }

        addLogEntry('Web interface loaded');
        
        setTimeout(() => {
            if (!socket.connected) {
                addLogEntry('Waiting for Python backend connection...', 'error');
                document.getElementById('game-message').textContent = 'Start the Python backend to begin playing.';
            }
        }, 2000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main game interface"""
    return render_template_string(HTML_TEMPLATE)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Web client connected')
    emit('log_message', {'message': 'Web interface connected', 'type': 'system'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Web client disconnected')

@socketio.on('web_command')
def handle_web_command(data):
    """Handle commands from web interface"""
    global game_instance
    if game_instance and 'command' in data:
        command = data['command']
        print(f"Web command received: {command}")
        
        if game_instance.current_game == "blackjack":
            game_instance.handle_blackjack_command(command, game_instance.detected_cards)
        else:
            if command == 'blackjack':
                game_instance.current_game = "blackjack"
                threading.Thread(target=game_instance.play_blackjack, daemon=True).start()

def run_flask_app():
    """Run the Flask app in a separate thread"""
    socketio.run(app, host='0.0.0.0', port=5001, debug=False, use_reloader=False)

def main():
    """Main function with web integration"""
    global game_instance
    
    print("Starting Accessible Card Games with Web Interface...")
    
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    
    time.sleep(2)
    
    game_instance = ImprovedAccessibleCardGame()
    
    game_instance.speak("Web interface started at http://localhost:5000")
    game_instance.speak("You can use voice commands or the web interface buttons")
    
    try:
        game_instance.run()
    except KeyboardInterrupt:
        game_instance.speak("Program interrupted. Goodbye!")
    except Exception as e:
        game_instance.speak(f"An error occurred: {str(e)}")
    finally:
        game_instance.cleanup()

if __name__ == "__main__":
    main()