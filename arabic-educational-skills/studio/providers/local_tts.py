"""
Local TTS Provider for Arabic Educational Skills Studio.
Uses pyttsx3 for offline, free, and local text-to-speech synthesis.
"""

import os
from typing import Optional, Dict, Any

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

class LocalTTSProvider:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.rate = self.config.get("rate", 150)
        self.volume = self.config.get("volume", 1.0)
        self.voice_id = self.config.get("voice_id", None)
        self.engine = None
        
        if pyttsx3:
            try:
                self.engine = pyttsx3.init()
                self._configure_engine()
            except Exception as e:
                print(f"Warning: Could not initialize pyttsx3 engine: {e}")

    def _configure_engine(self):
        if not self.engine:
            return
        
        self.engine.setProperty('rate', self.rate)
        self.engine.setProperty('volume', self.volume)
        
        try:
            voices = self.engine.getProperty('voices')
            if self.voice_id:
                self.engine.setProperty('voice', self.voice_id)
            elif voices:
                for voice in voices:
                    v_id = getattr(voice, 'id', '').lower()
                    v_name = getattr(voice, 'name', '').lower()
                    v_lang = str(getattr(voice, 'languages', [])).lower()
                    if 'ar' in v_id or 'arabic' in v_name or 'ar' in v_lang:
                        self.engine.setProperty('voice', voice.id)
                        break
        except Exception as e:
            print(f"Warning: Voice configuration issue: {e}")

    def synthesize(self, text: str, output_path: str) -> str:
        """
        Synthesizes text to audio file locally.
        """
        if not self.engine:
            raise RuntimeError("Local TTS Engine (pyttsx3) is not available or initialized.")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        self.engine.save_to_file(text, output_path)
        self.engine.runAndWait()
        return output_path

    def get_info(self) -> Dict[str, Any]:
        return {
            "provider": "local_tts",
            "engine": "pyttsx3",
            "offline": True,
            "free": True,
            "rate": self.rate
        }
