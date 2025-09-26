# Accessible Blackjack System

A modular, voice-controlled blackjack game designed for blind and visually impaired users.

#User Interface for Blackjack System
- Start the Python program (it will open the camera and start TTS)
- Open your browser and go to: http://localhost:5001
- You'll see the modern UI with real-time connection to your Python backend

## Features
- Voice-controlled interface
- Computer vision card detection  
- Template-based card recognition
- Template training system
- Complete blackjack game logic

## Quick Start
1. Run: `install_script.py`
2. Run: `accessible_blackjack.py`
3. Say "train templates" to add card recognition templates
4. Say "play blackjack" to start playing

## File Structure
- `accessible_blackjack.py` - Main system coordinator
- `simple_card_detector.py` - Card database and template recognition  
- `install_script.py` - Downloading necesarry libraries and testing
- `card_database/` - Directory for card templates and data
- `test_components.py` - Testing all components


## Voice Commands

### Main Menu
- "blackjack" - Start game
- "help" - Show commands
- "quit" - Exit

### During Game  
- "detect cards" - Check card recognition
- "deal" - Start with current cards
- "hit" - Take another card
- "stand" - Stop taking cards
- "new game" - Reset game

## Setup Tips
- Use dark background for cards
- Ensure bright, even lighting
- Keep cards flat and separate
- Position camera 12-18 inches above cards
