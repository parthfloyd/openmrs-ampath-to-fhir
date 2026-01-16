# src/services/base.py
from abc import ABC, abstractmethod
from typing import List, Dict

class TranslationInterface(ABC):
    @abstractmethod
    def batch_translate(self, texts: List[str], target_locales: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Input: ["Hello", "Goodbye"], ["fr", "es"]
        Output: {
            "Hello": {"fr": "Bonjour", "es": "Hola"},
            "Goodbye": {"fr": "Au revoir", "es": "Adiós"}
        }
        """
        pass