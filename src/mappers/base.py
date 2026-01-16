from abc import ABC, abstractmethod

class MapperInterface(ABC):
    def __init__(self, config, db_service, translation_service):
        self.config = config
        self.db = db_service
        self.ts = translation_service

    @abstractmethod
    def transform(self, source_data: dict) -> dict:
        """Transform source dictionary to FHIR Questionnaire dictionary."""
        pass