"""
AEGIS Text-To-Speech (TTS) Engine
Uses Windows Native PowerShell System.Speech Synthesis (with pyttsx3 fallback)
for crisp, zero-crash, thread-safe speech synthesis.
"""

import os
import sys
import subprocess
import threading
import queue
from typing import Optional

class TTSEngine:
    """Thread-safe Text-To-Speech engine."""

    def __init__(self, rate: int = 0, volume: float = 1.0):
        self.rate = rate
        self.volume = volume
        self.queue = queue.Queue()
        self._is_running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def _worker_loop(self):
        """Dedicated background thread managing speech synthesis."""
        while self._is_running:
            try:
                text = self.queue.get(timeout=1.0)
                if text is None:
                    break

                # Clean markdown, URLs, and symbols from speech text
                clean_text = (
                    text.replace("#", "")
                        .replace("*", "")
                        .replace("`", "")
                        .replace(">", "")
                        .replace("$$", "")
                )

                spoken = False

                # Priority 1: Piper TTS (Neural Voice)
                if os.name == "nt" and not spoken:
                    piper_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "piper")
                    piper_exe = os.path.join(piper_dir, "piper.exe")
                    # Find any .onnx model file
                    model_path = None
                    if os.path.isdir(piper_dir):
                        for f in os.listdir(piper_dir):
                            if f.endswith(".onnx"):
                                model_path = os.path.join(piper_dir, f)
                                break

                    if os.path.isfile(piper_exe) and model_path:
                        try:
                            wav_path = os.path.join(piper_dir, "tts_output.wav")
                            proc = subprocess.run(
                                [piper_exe, "--model", model_path, "--output_file", wav_path],
                                input=clean_text, capture_output=True, text=True, timeout=15
                            )
                            if proc.returncode == 0 and os.path.isfile(wav_path):
                                # Play the WAV file
                                import winsound
                                winsound.PlaySound(wav_path, winsound.SND_FILENAME)
                                spoken = True
                        except Exception as e:
                            print(f"[TTSEngine Piper Error]: {e}")

                # Priority 2: Windows PowerShell System.Speech (Fallback)
                if os.name == "nt" and not spoken:
                    safe_text = clean_text.replace("'", "''").replace('"', '`"')
                    command = f"""
Add-Type -AssemblyName System.Speech
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speak.Rate = {self.rate}
$speak.Speak('{safe_text}')
$speak.Dispose()
"""
                    subprocess.run(
                        ["powershell", "-NoProfile", "-Command", command],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                else:
                    # Fallback to pyttsx3
                    try:
                        import pyttsx3
                        engine = pyttsx3.init()
                        engine.say(clean_text)
                        engine.runAndWait()
                    except Exception as err:
                        print(f"[TTSEngine Fallback Error]: {err}")

                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[TTSEngine Worker Error]: {e}")

    def speak(self, text: str) -> None:
        """Enqueues text for asynchronous vocalization."""
        if text and text.strip():
            self.queue.put(text)

    def stop(self) -> None:
        """Stops the TTS background thread."""
        self._is_running = False
        self.queue.put(None)
