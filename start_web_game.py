#!/usr/bin/env python3
"""
Quick Start Script for Accessible Blackjack Web Interface
Run this script to start the game!
"""

import sys
import os

def check_dependencies():
    """Check if required modules are available."""
    required_modules = [
        ('flask', 'Flask'),
        ('flask_socketio', 'flask-socketio'),
        ('cv2', 'opencv-python'),
        ('roboflow', 'roboflow'),
        ('speech_recognition', 'SpeechRecognition')
    ]
    
    missing = []
    for module_name, package_name in required_modules:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(package_name)
    
    if missing:
        print("❌ Missing dependencies:")
        for package in missing:
            print(f"   - {package}")
        print("\n💡 Install them with:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    return True

def check_files():
    """Check if required game files exist."""
    required_files = [
        'blackjack_logic.py',
        'card_detection.py',
        'tts_module.py',
        'web_app.py',
        'templates/blackjack.html'
    ]
    
    missing = []
    for file in required_files:
        if not os.path.exists(file):
            missing.append(file)
    
    if missing:
        print("❌ Missing required files:")
        for file in missing:
            print(f"   - {file}")
        return False
    
    return True

def main():
    """Main startup function."""
    print("="*60)
    print("🎰 Accessible Blackjack - Web Interface Launcher")
    print("="*60)
    print()
    
    # Check dependencies
    print("🔍 Checking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    print("✅ All dependencies found!")
    print()
    
    # Check files
    print("🔍 Checking required files...")
    if not check_files():
        sys.exit(1)
    print("✅ All files found!")
    print()
    
    # Start the server
    print("🚀 Starting web server...")
    print()
    print("="*60)
    print("🎮 Game will be available at: http://localhost:5000")
    print("="*60)
    print()
    print("📝 Quick Tips:")
    print("   - Place cards in camera view")
    print("   - Player cards go in bottom half")
    print("   - Dealer cards go in top half")
    print("   - Use buttons or voice commands to play")
    print()
    print("🛑 Press Ctrl+C to quit")
    print("="*60)
    print()
    
    # Import and run
    try:
        from web_app import socketio, app, web_game
        web_game.start()
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n\n👋 Thanks for playing! Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()