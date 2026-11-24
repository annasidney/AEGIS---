"""
AEGIS Speech-To-Text (STT) Engine
Captures desktop microphone input and converts speech into text using SpeechRecognition.
"""

from typing import Tuple, Optional

class STTEngine:
    """Desktop microphone speech recognizer."""

    def __init__(self):
        self.recognizer = None
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
        except Exception as e:
            print(f"[STTEngine Init Warning]: {e}")

    def listen_and_transcribe(self, timeout: int = 5) -> Tuple[bool, str]:
        """
        Listens to the default audio input and transcribes speech.
        Returns: (success, transcribed_text_or_error)
        """
        if not self.recognizer:
            return False, "Speech recognition library not initialized."

        try:
            import speech_recognition as sr
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
                text = self.recognizer.recognize_google(audio)
                return True, text
        except sr.WaitTimeoutError:
            return False, "Listening timed out. No speech detected."
        except sr.UnknownValueError:
            return False, "Could not understand audio clearly."
        except sr.RequestError as e:
            return False, f"Speech recognition service error: {e}"
        except Exception as e:
            return False, f"Microphone error: {str(e)}"
