from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
import cv2
import base64
import time
import threading
from typing import Optional
import numpy as np

# Import the existing modules
from blackjack_logic import BlackjackGame
from card_detection import CardDetector

app = Flask(__name__)
app.config['SECRET_KEY'] = 'blackjack_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

class WebBlackjackGame:
    """
    Web-based version of the blackjack game that integrates with the existing logic.
    """
    
    def __init__(self):
        print("[WebGame] Initializing web-based blackjack...")
        self.detector = CardDetector()
        self.running = False
        self.game_thread = None
        
        # Game state tracking
        self.card_values = {
            'A': 11, 'K': 10, 'Q': 10, 'J': 10, '10': 10, 
            '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2
        }
        
        self.player_hand = []
        self.dealer_hand = []
        self.player_total = 0
        self.dealer_total = 0
        self.last_dealer_total = 0
        self.last_player_total = 0
        
        self.last_seen_player_hand = ()
        self.last_seen_dealer_hand = ()
        self.current_stability_count = 0
        self.REQUIRED_STABILITY = 30
        
        self.game_phase = "WAITING_FOR_CLEAR"
        self.game_end_announced = False
        self.last_message = "Welcome to Accessible Blackjack! Please clear all cards from the table."

    def calculate_hand_value(self, hand):
        """Calculate the total value of a hand."""
        total = 0
        aces = 0
        for card_id in hand:
            value_str = card_id[:-1] 
            value = self.card_values.get(value_str, 0)
            if value == 11: 
                aces += 1
            total += value
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        return total

    def determine_winner(self, player_total, dealer_total):
        """Compare final totals and return result."""
        if player_total > 21:
            return f"You busted with {player_total}. You lose."
        if dealer_total > 21:
            return f"Dealer busted with {dealer_total}. You win!"
        if player_total > dealer_total:
            return f"You win with {player_total} to {dealer_total}!"
        if dealer_total > player_total:
            return f"Dealer wins with {dealer_total} to {player_total}."
        return f"It's a push. You both have {player_total}."

    def reset_game(self):
        """Reset the game to initial state."""
        print("[WebGame] Resetting game...")
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
        self.game_end_announced = False
        
        return "New game. Please clear all cards from the table."

    def update_game_state(self, command: Optional[str] = None):
        """Update game state based on card detection or voice command."""
        message_to_speak = None

        if command:
            command = command.lower().strip()
        
        # Global commands
        if command:
            if command in ["new game", "play again", "restart", "deal again", "again"]:
                message_to_speak = self.reset_game()
                self.emit_game_state(message_to_speak)
                return message_to_speak
            elif command in ["i quit", "quit", "exit", "stop"]:
                self.running = False
                return None

        # Recalculate totals
        self.player_total = self.calculate_hand_value(self.player_hand)
        self.dealer_total = self.calculate_hand_value(self.dealer_hand)

        # State machine
        if self.game_phase == "WAITING_FOR_CLEAR":
            if len(self.player_hand) == 0 and len(self.dealer_hand) == 0:
                self.game_phase = "STARTING"
                message_to_speak = "Table is clear. Please place 2 cards for yourself and 1 for the dealer."

        elif self.game_phase == "STARTING":
            if len(self.player_hand) == 2 and len(self.dealer_hand) == 1:
                self.game_phase = "PLAYER_TURN"
                message_to_speak = (f"Cards dealt. You have {self.player_total}. "
                                    f"Dealer shows {self.dealer_hand[0]}. "
                                    "Say 'hit' or 'stand'.")
                self.last_dealer_total = self.dealer_total
                self.last_player_total = self.player_total

        elif self.game_phase == "PLAYER_TURN":
            if self.player_total > 21:
                message_to_speak = f"You busted with {self.player_total}. You lose. Say 'new game' to play again."
                self.game_phase = "GAME_OVER"
                self.last_player_total = self.player_total
            
            elif self.player_total == 21:
                message_to_speak = "You have 21. Standing automatically."
                self.game_phase = "DEALER_TURN"
                self.last_player_total = self.player_total

            elif not command and self.player_total != self.last_player_total:
                message_to_speak = f"Your total is now {self.player_total}. Say 'hit' or 'stand'."
                self.last_player_total = self.player_total

            elif command:
                if command in ["i hit", "hit", "hit me", "deal me", "card"]:
                    message_to_speak = "Hit. Please add your new card."
                    self.last_player_total = self.player_total
                elif command in ["stand", "stay", "i stand", "i'm good", "hold"]:
                    message_to_speak = (f"You stand with {self.player_total}. "
                                        "Dealer's turn. Please reveal the dealer's hole card.")
                    self.game_phase = "DEALER_TURN"
                    self.last_player_total = self.player_total
                    self.game_end_announced = False

        elif self.game_phase == "DEALER_TURN":
            if self.dealer_total != self.last_dealer_total and self.dealer_total < 17:
                message_to_speak = f"Dealer total is now {self.dealer_total}."
                self.last_dealer_total = self.dealer_total
            
            if self.dealer_total >= 17 and not self.game_end_announced:
                self.game_end_announced = True
                
                if self.dealer_total > 21:
                    dealer_end = f"Dealer busts with {self.dealer_total}."
                else:
                    dealer_end = f"Dealer stands with {self.dealer_total}."
                
                result = self.determine_winner(self.player_total, self.dealer_total)
                message_to_speak = f"{dealer_end} {result} Say 'new game' to play again."
                self.game_phase = "GAME_OVER"
                self.last_dealer_total = self.dealer_total

        if message_to_speak:
            self.last_message = message_to_speak
            self.emit_game_state(message_to_speak)
        
        return message_to_speak

    def emit_game_state(self, message=None):
        """Emit current game state to all connected clients."""
        socketio.emit('game_update', {
            'player_hand': self.player_hand,
            'dealer_hand': self.dealer_hand,
            'player_total': self.player_total,
            'dealer_total': self.dealer_total,
            'game_phase': self.game_phase,
            'message': message or self.last_message,
            'stability': self.current_stability_count
        })

    def game_loop(self):
        """Main game loop running in background thread."""
        print("[WebGame] Starting game loop...")
        
        while self.running:
            # Get detected cards and frame
            card_data, frame = self.detector.get_detected_cards()
            
            if frame is None:
                print("[WebGame] No frame from camera")
                time.sleep(0.1)
                continue
            
            # Stability logic
            current_player_hand = tuple(sorted([c['id'] for c in card_data if c['owner'] == 'Player']))
            current_dealer_hand = tuple(sorted([c['id'] for c in card_data if c['owner'] == 'Dealer']))
            
            has_vision_changed = (current_player_hand != self.last_seen_player_hand) or \
                                 (current_dealer_hand != self.last_seen_dealer_hand)
            
            if has_vision_changed:
                self.current_stability_count = 0
                self.last_seen_player_hand = current_player_hand
                self.last_seen_dealer_hand = current_dealer_hand
            else:
                self.current_stability_count += 1

            # Update game state when stable
            is_now_stable = self.current_stability_count == self.REQUIRED_STABILITY
            if is_now_stable:
                self.player_hand = list(self.last_seen_player_hand)
                self.dealer_hand = list(self.last_seen_dealer_hand)
                self.update_game_state(None)
            
            # Emit state periodically
            self.emit_game_state()
            
            time.sleep(0.03)

        print("[WebGame] Game loop stopped")

    def start(self):
        """Start the game in a background thread."""
        if not self.running:
            self.running = True
            self.game_thread = threading.Thread(target=self.game_loop, daemon=True)
            self.game_thread.start()
            print("[WebGame] Game started")

    def stop(self):
        """Stop the game."""
        self.running = False
        if self.game_thread:
            self.game_thread.join(timeout=2)
        self.detector.cleanup()
        print("[WebGame] Game stopped")

    def get_frame(self):
        """Get the current camera frame as JPEG."""
        _, frame = self.detector.get_detected_cards()
        if frame is not None:
            _, buffer = cv2.imencode('.jpg', frame)
            return buffer.tobytes()
        return None


# Global game instance
web_game = WebBlackjackGame()


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('blackjack.html')


def generate_frames():
    """Generator function for video streaming."""
    while True:
        frame = web_game.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.033)  # ~30 FPS


@app.route('/video_feed')
def video_feed():
    """Video streaming route."""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print('[WebGame] Client connected')
    web_game.emit_game_state()


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print('[WebGame] Client disconnected')


@socketio.on('voice_command')
def handle_voice_command(data):
    """Handle voice command from client."""
    command = data.get('command', '')
    print(f'[WebGame] Received command: {command}')
    web_game.update_game_state(command)


@socketio.on('start_game')
def handle_start_game():
    """Start the game."""
    print('[WebGame] Starting game...')
    web_game.start()
    emit('game_started', {'status': 'Game started'})


@socketio.on('stop_game')
def handle_stop_game():
    """Stop the game."""
    print('[WebGame] Stopping game...')
    web_game.stop()
    emit('game_stopped', {'status': 'Game stopped'})


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎰 Accessible Blackjack - Web Interface")
    print("="*60)
    print("\nStarting server...")
    print("Open your browser and go to: http://localhost:5000")
    print("\nPress Ctrl+C to quit\n")
    
    try:
        web_game.start()
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n[WebGame] Shutting down...")
    finally:
        web_game.stop()