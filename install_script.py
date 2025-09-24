#!/usr/bin/env python3
"""
Installation script for Accessible Blackjack Game
This script will install all required dependencies and test your system
"""

import subprocess
import sys
import platform
import os

def run_command(command, description):
    """Run a system command and handle errors"""
    print(f"\n[*] {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"[SUCCESS] {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Error during {description}:")
        print(f"   Command: {command}")
        print(f"   Error: {e.stderr}")
        return False

def install_pip_packages():
    """Install required Python packages"""
    packages = [
        'opencv-python',
        'pyttsx3', 
        'SpeechRecognition',
        'numpy'
    ]
    
    print("\n[*] Installing Python packages...")
    for package in packages:
        print(f"   Installing {package}...")
        success = run_command(f'pip install {package}', f"Installing {package}")
        if not success:
            print(f"[ERROR] Failed to install {package}")
            return False
    
    # Try to install pyaudio (can be tricky on some systems)
    print("\n[*] Installing pyaudio (microphone support)...")
    success = run_command('pip install pyaudio', "Installing pyaudio")
    if not success:
        print("[WARNING] pyaudio installation failed. Trying alternative methods...")
        
        system = platform.system().lower()
        if system == "windows":
            print("   For Windows, try installing Microsoft Visual C++ Build Tools")
            print("   Or download pyaudio wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio")
        elif system == "darwin":  # macOS
            print("   For macOS, try: brew install portaudio")
            run_command('brew install portaudio', "Installing portaudio via Homebrew")
            run_command('pip install pyaudio', "Retrying pyaudio installation")
        elif system == "linux":
            print("   For Linux, installing system dependencies...")
            run_command('sudo apt-get update', "Updating package list")
            run_command('sudo apt-get install -y python3-dev portaudio19-dev', 
                       "Installing system dependencies")
            run_command('pip install pyaudio', "Retrying pyaudio installation")
    
    return True

def test_camera():
    """Test camera functionality"""
    print("\n[*] Testing camera...")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[ERROR] Camera test failed - could not open camera")
            return False
        
        ret, frame = cap.read()
        if ret:
            print("[SUCCESS] Camera working correctly")
            height, width = frame.shape[:2]
            print(f"   Resolution: {width}x{height}")
        else:
            print("[ERROR] Camera test failed - could not read frame")
            cap.release()
            return False
        
        cap.release()
        return True
        
    except ImportError:
        print("[ERROR] OpenCV not properly installed")
        return False
    except Exception as e:
        print(f"[ERROR] Camera test failed: {e}")
        return False

def test_microphone():
    """Test microphone functionality"""
    print("\n[*] Testing microphone...")
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        
        # List available microphones
        mic_list = sr.Microphone.list_microphone_names()
        print(f"   Found {len(mic_list)} microphones:")
        for i, name in enumerate(mic_list[:3]):  # Show first 3
            print(f"     {i}: {name}")
        
        # Test default microphone
        with sr.Microphone() as source:
            print("   Adjusting for ambient noise... (stay quiet for 2 seconds)")
            r.adjust_for_ambient_noise(source, duration=2)
            print("[SUCCESS] Microphone working correctly")
            return True
            
    except ImportError:
        print("[ERROR] SpeechRecognition not properly installed")
        return False
    except Exception as e:
        print(f"[ERROR] Microphone test failed: {e}")
        print("   Make sure you have a working microphone connected")
        return False

def test_text_to_speech():
    """Test text-to-speech functionality"""
    print("\n[*] Testing text-to-speech...")
    try:
        import pyttsx3
        engine = pyttsx3.init()
        
        # Get available voices
        voices = engine.getProperty('voices')
        print(f"   Found {len(voices)} voices:")
        for i, voice in enumerate(voices[:3]):  # Show first 3
            print(f"     {i}: {voice.name} ({voice.languages})")
        
        print("   Testing speech output...")
        engine.say("Text to speech is working correctly!")
        engine.runAndWait()
        print("[SUCCESS] Text-to-speech working correctly")
        return True
        
    except ImportError:
        print("[ERROR] pyttsx3 not properly installed")
        return False
    except Exception as e:
        print(f"[ERROR] Text-to-speech test failed: {e}")
        return False

def create_test_script():
    """Create a simple test script for the user"""
    test_code = '''#!/usr/bin/env python3
"""
Test script for Accessible Blackjack components
"""

import cv2
import pyttsx3
import speech_recognition as sr
import numpy as np

def test_all_components():
    print("Testing Accessible Blackjack Components\\n")
    
    # Test camera
    print("1. Testing Camera...")
    try:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        if ret:
            print("   [SUCCESS] Camera OK")
            cv2.imshow('Camera Test', frame)
            print("   Press any key to close camera window...")
            cv2.waitKey(3000)
            cv2.destroyAllWindows()
        cap.release()
    except Exception as e:
        print(f"   [ERROR] Camera Error: {e}")
    
    # Test TTS
    print("\\n2. Testing Text-to-Speech...")
    try:
        engine = pyttsx3.init()
        engine.say("Speech test successful")
        engine.runAndWait()
        print("   [SUCCESS] TTS OK")
    except Exception as e:
        print(f"   [ERROR] TTS Error: {e}")
    
    # Test microphone
    print("\\n3. Testing Microphone...")
    print("   Say something in the next 5 seconds...")
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            audio = r.listen(source, timeout=5, phrase_time_limit=3)
        text = r.recognize_google(audio)
        print(f"   [SUCCESS] Microphone OK - You said: '{text}'")
    except Exception as e:
        print(f"   [ERROR] Microphone Error: {e}")
    
    print("\\nComponent testing complete!")

if __name__ == "__main__":
    test_all_components()
'''
    
    with open('test_components.py', 'w') as f:
        f.write(test_code)
    print("\n[*] Created test_components.py script")

def main():
    """Main installation function"""
    print("Accessible Blackjack Game Installation")
    print("=" * 50)
    
    print(f"Python version: {sys.version}")
    print(f"Operating system: {platform.system()} {platform.release()}")
    
    # Install packages
    if not install_pip_packages():
        print("\n[ERROR] Package installation failed. Please check the errors above.")
        return False
    
    print("\n[*] Testing installed components...")
    
    # Test components
    camera_ok = test_camera()
    mic_ok = test_microphone()
    tts_ok = test_text_to_speech()
    
    # Create test script
    create_test_script()
    
    # Summary
    print("\n" + "=" * 50)
    print("INSTALLATION SUMMARY")
    print("=" * 50)
    print(f"Camera:         {'[SUCCESS] Working' if camera_ok else '[ERROR] Failed'}")
    print(f"Microphone:     {'[SUCCESS] Working' if mic_ok else '[ERROR] Failed'}")
    print(f"Text-to-Speech: {'[SUCCESS] Working' if tts_ok else '[ERROR] Failed'}")
    
    if camera_ok and mic_ok and tts_ok:
        print("\n[SUCCESS] Installation completed successfully!")
        print("\nNext steps:")
        print("1. Run 'python accessible_blackjack.py' to start the game")
        print("2. Make sure you have a deck of cards ready")
        print("3. Ensure good lighting for card detection")
        print("4. Have fun playing accessible blackjack!")
    else:
        print("\n[WARNING] Some components failed testing.")
        print("Please check the error messages above and:")
        print("1. Install missing system dependencies")
        print("2. Check hardware connections (camera/microphone)")
        print("3. Run 'python test_components.py' to test again")
    
    return camera_ok and mic_ok and tts_ok

if __name__ == "__main__":
    try:
        success = main()
        if success:
            input("\nPress Enter to exit...")
        else:
            input("\nInstallation had issues. Press Enter to exit...")
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error during installation: {e}")
        input("Press Enter to exit...")