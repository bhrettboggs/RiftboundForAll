# Accessible Blackjack System

A modular, voice-controlled blackjack game designed for blind and visually impaired users.

## Features
- Voice-controlled interface
- Computer vision card detection  
- Template-based card recognition
- Template training system
- Complete blackjack game logic

## Quick Start
1. Run: `python setup_modular_system.py`
2. Run: `python modular_blackjack_system.py`
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
