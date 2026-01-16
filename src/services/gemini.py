import google.generativeai as genai
import json
import time
from typing import List, Dict
from .base import TranslationInterface

class GeminiTranslationService(TranslationInterface):
    def __init__(self, api_key):
        self.model = None
        if api_key and "YOUR_KEY" not in api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')

    def batch_translate(self, texts: List[str], target_locales: List[str]) -> Dict[str, Dict[str, str]]:
        if not self.model or not texts:
            return {}

        # Deduplicate and remove empties
        unique_texts = list(set([t for t in texts if t and t.strip()]))
        translation_map = {}
        
        # Chunking: Send 20-30 strings per prompt to avoid token limits/timeouts
        CHUNK_SIZE = 25 
        
        print(f"   [Gemini] Batching {len(unique_texts)} strings into {len(unique_texts)//CHUNK_SIZE + 1} requests...")

        for i in range(0, len(unique_texts), CHUNK_SIZE):
            chunk = unique_texts[i:i + CHUNK_SIZE]
            self._process_chunk(chunk, target_locales, translation_map)
            time.sleep(1)

        return translation_map

    def _process_chunk(self, chunk, locales, result_map):
        prompt = f"""
        You are a medical translator. Translate the following list of strings into these languages: {', '.join(locales)}.
        
        Input Strings:
        {json.dumps(chunk)}

        Requirements:
        1. Return ONLY valid JSON. No markdown, no code blocks, no text before/after.
        2. Structure: {{"Source String": {{"lang_code": "Translated String", ...}}, ...}}
        3. If a term is technical or untranslatable, keep it in English.
        """

        try:
            response = self.model.generate_content(prompt)
            clean_text = response.text.strip()
            
            # Clean up if Gemini adds markdown code blocks accidentally
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:-3]
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:-3]

            data = json.loads(clean_text)
            
            # Merge into main result
            result_map.update(data)
            
        except Exception as e:
            print(f"   [Gemini] Chunk failed: {str(e)}")
            # Fallback: Do nothing (result_map remains empty for these keys, code handles missing keys gracefully)