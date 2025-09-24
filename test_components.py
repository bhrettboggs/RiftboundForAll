#!/usr/bin/env python3
"""
Test script for Accessible Blackjack components
"""

import cv2
import pyttsx3
import speech_recognition as sr
import numpy as np

def test_all_components():
    print("Testing Accessible Blackjack Components\n")
    
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
    print("\n2. Testing Text-to-Speech...")
    try:
        engine = pyttsx3.init()
        engine.say("Speech test successful")
        engine.runAndWait()
        print("   [SUCCESS] TTS OK")
    except Exception as e:
        print(f"   [ERROR] TTS Error: {e}")
    
    # Test microphone
    print("\n3. Testing Microphone...")
    print("   Say something in the next 5 seconds...")
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            audio = r.listen(source, timeout=5, phrase_time_limit=3)
        text = r.recognize_google(audio)
        print(f"   [SUCCESS] Microphone OK - You said: '{text}'")
    except Exception as e:
        print(f"   [ERROR] Microphone Error: {e}")
    
    print("\nComponent testing complete!")

if __name__ == "__main__":
    test_all_components()
