# tts_module.py - CLEANED VERSION (TTS ONLY)

import threading
import queue
import time
import subprocess
import os

class AudioManager:
    """
    Handles all Text-to-Speech (TTS) functionality
    in a non-blocking background thread.
    
    (STT functionality has been removed.)
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
        # (All STT code has been removed)
        
        # Start speaker thread
        self.speaker_thread.start()
        
        print("[AudioManager] Ready.")

    # --- CALIBRATE_MIC REMOVED ---
    
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

    # --- _LISTEN_LOOP REMOVED ---

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

    # --- GET_COMMAND REMOVED ---
    # --- CLEAR_COMMANDS REMOVED ---

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
        
        # --- LISTENER_THREAD JOIN REMOVED ---
        
        print("[AudioManager] Stopped.")


# Test function (optional, can be removed)
if __name__ == "__main__":
    print("Testing AudioManager (TTS Only)...")
    audio = AudioManager()
    
    audio.speak("Testing text to speech.")
    audio.speak("This is a second test message.")
    
    print("Waiting for speech to finish...")
    audio.wait_for_speech()
    
    audio.stop()
    print("Test complete!")