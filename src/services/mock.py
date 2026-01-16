from typing import List, Dict
from .base import TranslationInterface

class MockTranslationService(TranslationInterface):
    def batch_translate(self, texts: List[str], target_locales: List[str]) -> Dict[str, Dict[str, str]]:
        result = {}
        for text in texts:
            result[text] = {}
            for loc in target_locales:
                result[text][loc] = f"[{loc}] {text}"
        return result