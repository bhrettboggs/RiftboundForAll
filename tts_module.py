# tts_module.py - IMPROVED VERSION

import speech_recognition as sr
import threading
import queue
import time
import subprocess
import os

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
        self.current_speech_process = None
        self.speech_lock = threading.Lock()
        self.speaker_thread = threading.Thread(target=self._speak_loop, daemon=True)

        # --- STT (Listener) Setup ---
        self.command_queue = queue.Queue()
        self.recognizer = sr.Recognizer()
        
        # IMPROVED: Better recognition settings
        self.recognizer.energy_threshold = 4000
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 0.8  # How long to wait for pause
        
        try:
            self.microphone = sr.Microphone()
            self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.calibrate_mic()
        except Exception as e:
            print(f"[STT] Warning: Microphone initialization failed: {e}")
            self.microphone = None
            self.listener_thread = None
        
        # Start threads
        self.speaker_thread.start()
        if self.listener_thread:
            self.listener_thread.start()
        
        print("[AudioManager] Ready.")

    def calibrate_mic(self):
        """Calibrate microphone for ambient noise."""
        if not self.microphone:
            return
            
        try:
            with self.microphone as source:
                print("[STT] Calibrating microphone (stay quiet for 2 seconds)...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                print(f"[STT] Microphone calibrated. Energy threshold: {self.recognizer.energy_threshold}")
        except Exception as e:
            print(f"[STT] Mic calibration error: {e}")

    def _speak_loop(self):
        """
        Background thread for TTS.
        Uses subprocess for better control and non-blocking operation.
        """
        while self.running:
            try:
                text = self.speak_queue.get(timeout=0.5)
                if text is None:  # Shutdown signal
                    continue

                print(f"[TTS] Speaking: {text}")
                
                with self.speech_lock:
                    # Kill any ongoing speech
                    if self.current_speech_process:
                        try:
                            self.current_speech_process.kill()
                        except:
                            pass
                    
                    # Start new speech (non-blocking with Popen)
                    try:
                        # Escape text properly for shell
                        safe_text = text.replace('"', '\\"')
                        
                        # Use subprocess.Popen for non-blocking
                        self.current_speech_process = subprocess.Popen(
                            ['say', safe_text],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        
                        # Wait for completion
                        self.current_speech_process.wait()
                        
                    except Exception as e:
                        print(f"[TTS] Error during speech: {e}")
                    finally:
                        self.current_speech_process = None
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[TTS] Speak loop error: {e}")

    def _listen_loop(self):
        """Background thread for speech recognition."""
        if not self.microphone:
            print("[STT] No microphone available, listening disabled")
            return
            
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.running:
            try:
                with self.microphone as source:
                    # Listen with timeout
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                
                # Recognize speech
                command = self.recognizer.recognize_google(audio).lower().strip()
                print(f"[STT] Heard: '{command}'")
                
                # Put in queue
                self.command_queue.put(command)
                
                # Reset error counter on success
                consecutive_errors = 0

            except sr.WaitTimeoutError:
                # Normal timeout - not an error
                consecutive_errors = 0
                pass
                
            except sr.UnknownValueError:
                # Couldn't understand - not critical
                consecutive_errors = 0
                pass
                
            except sr.RequestError as e:
                # API error - more serious
                consecutive_errors += 1
                print(f"[STT] Google API Error: {e}")
                if consecutive_errors >= max_consecutive_errors:
                    print("[STT] Too many API errors, pausing recognition...")
                    time.sleep(10)
                    consecutive_errors = 0
                    
            except Exception as e:
                consecutive_errors += 1
                print(f"[STT] Listener Error: {e}")
                if consecutive_errors >= max_consecutive_errors:
                    print("[STT] Too many errors, restarting listener...")
                    time.sleep(5)
                    consecutive_errors = 0
            
            time.sleep(0.1)

    # --- Public Methods ---

    def speak(self, text: str):
        """
        Queue text to be spoken.
        Non-blocking - returns immediately.
        """
        if text and text.strip():
            self.speak_queue.put(text.strip())

    def speak_immediate(self, text: str):
        """
        Interrupt current speech and speak this immediately.
        Useful for urgent messages.
        """
        if not text or not text.strip():
            return
            
        # Clear the queue
        while not self.speak_queue.empty():
            try:
                self.speak_queue.get_nowait()
            except queue.Empty:
                break
        
        # Add this message
        self.speak_queue.put(text.strip())

    def get_command(self) -> str:
        """
        Get the next voice command (non-blocking).
        Returns None if no command available.
        """
        try:
            command = self.command_queue.get_nowait()
            return command
        except queue.Empty:
            return None

    def clear_commands(self):
        """Clear all pending voice commands."""
        while not self.command_queue.empty():
            try:
                self.command_queue.get_nowait()
            except queue.Empty:
                break

    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        with self.speech_lock:
            return self.current_speech_process is not None

    def wait_for_speech(self, timeout: float = 10.0):
        """
        Wait for current speech to finish.
        Useful when you need to ensure a message is heard before continuing.
        """
        start_time = time.time()
        while self.is_speaking():
            if time.time() - start_time > timeout:
                break
            time.sleep(0.1)

    def stop(self):
        """Stop all audio threads."""
        print("[AudioManager] Stopping threads...")
        self.running = False
        
        # Stop any ongoing speech
        with self.speech_lock:
            if self.current_speech_process:
                try:
                    self.current_speech_process.kill()
                except:
                    pass
        
        # Clear queues
        self.speak_queue.put(None)
        
        # Wait for threads
        if self.speaker_thread.is_alive():
            self.speaker_thread.join(timeout=2)
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=2)
        
        print("[AudioManager] Stopped.")


# Test function
if __name__ == "__main__":
    print("Testing AudioManager...")
    audio = AudioManager()
    
    audio.speak("Testing text to speech. This is a test message.")
    time.sleep(3)
    
    audio.speak("Say something now...")
    time.sleep(5)
    
    cmd = audio.get_command()
    if cmd:
        print(f"You said: {cmd}")
        audio.speak(f"I heard you say: {cmd}")
    else:
        audio.speak("I didn't hear anything")
    
    time.sleep(3)
    audio.stop()
    print("Test complete!")