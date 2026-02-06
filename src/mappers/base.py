from abc import ABC, abstractmethod
from typing import Dict

class MapperInterface(ABC):
    def __init__(self, config, db_service, translation_service):
        self.config = config
        self.db = db_service
        self.ts = translation_service

    @abstractmethod
    def transform(self, source_data: dict) -> dict:
        """Transform source dictionary to FHIR Questionnaire dictionary."""
        pass
    
    @abstractmethod
    def get_concept_translations(self, concept_uuid: str) -> Dict[str, str]:
        """Return locale keyed concept names/translations."""
        pass