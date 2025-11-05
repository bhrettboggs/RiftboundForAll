# tts_module.py

import speech_recognition as sr
import threading
import queue
import time
import os  # <-- ADD THIS IMPORT

class AudioManager:
    """
    Handles all Text-to-Speech (TTS) and Speech-to-Text (STT)
    functionality in non-blocking background threads.
    """

    def __init__(self):
        print("[AudioManager] Initializing...")
        
        self.running = True
        
        # --- TTS (Speaker) Setup ---
        self.speak_queue = queue.Queue()
        self.speaker_thread = threading.Thread(target=self._speak_loop, daemon=True)
        # We no longer need to initialize pyttsx3 here

        # --- STT (Listener) Setup ---
        self.command_queue = queue.Queue()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        
        self.calibrate_mic()
        
        self.speaker_thread.start()
        self.listener_thread.start()
        
        print("[AudioManager] Ready.")

    def calibrate_mic(self):
        # ... (this function is unchanged) ...
        try:
            with self.microphone as source:
                print("[STT] Calibrating microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("[STT] Microphone calibrated.")
        except Exception as e:
            print(f"[STT] Mic calibration error: {e}")

    # --- NEW, SIMPLIFIED SPEAK LOOP ---
    def _speak_loop(self):
        """
        Internal function running in a thread.
        Waits for text in speak_queue and speaks it using the
        macOS 'say' command, which is much more reliable.
        """
        while self.running:
            try:
                text = self.speak_queue.get()
                if text is None: # Shutdown signal
                    continue

                print(f"[TTS] Speaking: {text}")
                
                # This is the new, more reliable code.
                # It "escapes" the text to handle apostrophes
                safe_text = text.replace("'", "'\\''")
                os.system(f'say "{safe_text}"')
                
            except Exception as e:
                print(f"[TTS] Error: {e}")
    # --- END OF NEW LOOP ---

    def _listen_loop(self):
        # ... (this function is unchanged) ...
        while self.running:
            try:
                with self.microphone as source:
                    print("[STT] Listening...")
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=4)
                
                print("[STT] Recognizing...")
                command = self.recognizer.recognize_google(audio).lower()
                print(f"[STT] Heard: {command}")
                
                self.command_queue.put(command)

            except sr.WaitTimeoutError:
                pass
            except sr.UnknownValueError:
                print("[STT] Could not understand audio.")
            except sr.RequestError as e:
                print(f"[STT] Google API Error: {e}")
            except Exception as e:
                print(f"[STT] Listener Error: {e}")
            
            time.sleep(0.1) # Brief pause

    # --- Public Methods (unchanged) ---

    def speak(self, text: str):
        self.speak_queue.put(text)

    def get_command(self,):
        try:
            command = self.command_queue.get_nowait()
            return command
        except queue.Empty:
            return None

    def stop(self):
        print("[AudioManager] Stopping threads...")
        self.running = False
        self.speak_queue.put(None)