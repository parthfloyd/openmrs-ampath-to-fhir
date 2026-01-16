from abc import ABC, abstractmethod

class DatabaseInterface(ABC):
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def get_concept_name(self, concept_uuid: str) -> str:
        """Return the fully specified name for a concept."""
        pass

    @abstractmethod
    def get_form_metadata(self, encounter_string: str):
        """Return tuple (form_uuid, encounter_type_uuid)."""
        pass