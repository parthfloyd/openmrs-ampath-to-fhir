import unittest

from src.mappers.ampath import AmpathMapper


class DummyConfig:
    ignored_questions = []
    locales = []


class DummyTranslationService:
    def batch_translate(self, strings, locales):
        return {}


class TrackingDBService:
    def __init__(self, concept_name=None):
        self.concept_name = concept_name
        self.calls = []

    def get_concept_name(self, concept_uuid):
        self.calls.append(concept_uuid)
        return self.concept_name


class AmpathMapperQuestionTextTests(unittest.TestCase):
    def _build_mapper(self, concept_name=None):
        return AmpathMapper(DummyConfig(), TrackingDBService(concept_name=concept_name), DummyTranslationService())

    def test_resolve_question_text_prefers_display_over_label_and_concept(self):
        mapper = self._build_mapper(concept_name="DB Concept Name")
        question = {
            "id": "q1",
            "label": "Label Text",
            "questionOptions": {
                "display": "Display Text",
                "concept": "concept-uuid"
            }
        }

        extraction_group = mapper._create_extraction_group(question)
        input_item = extraction_group["item"][0]["item"][0]
        hidden_item = extraction_group["item"][0]["item"][1]

        self.assertEqual(input_item["text"], "Display Text")
        self.assertEqual(hidden_item["initial"][0]["valueCoding"]["display"], "Display Text")
        self.assertEqual(mapper.db.calls, [])

    def test_resolve_question_text_uses_label_when_display_missing(self):
        mapper = self._build_mapper(concept_name="DB Concept Name")
        question = {
            "id": "q2",
            "label": "Label Text",
            "questionOptions": {
                "display": "   ",
                "concept": "concept-uuid"
            }
        }

        extraction_group = mapper._create_extraction_group(question)
        input_item = extraction_group["item"][0]["item"][0]

        self.assertEqual(input_item["text"], "Label Text")
        self.assertEqual(mapper.db.calls, [])

    def test_resolve_question_text_uses_concept_name_when_display_and_label_missing(self):
        mapper = self._build_mapper(concept_name="DB Concept Name")
        question = {
            "id": "q3",
            "label": "   ",
            "questionOptions": {
                "display": "   ",
                "concept": "concept-uuid"
            }
        }

        extraction_group = mapper._create_extraction_group(question)
        input_item = extraction_group["item"][0]["item"][0]

        self.assertEqual(input_item["text"], "DB Concept Name")
        self.assertEqual(mapper.db.calls, ["concept-uuid"])

    def test_resolve_question_text_falls_back_to_question_when_all_missing(self):
        mapper = self._build_mapper(concept_name="   ")
        question = {
            "id": "q4",
            "label": "   ",
            "questionOptions": {
                "display": "   ",
                "concept": "   "
            }
        }

        extraction_group = mapper._create_extraction_group(question)
        input_item = extraction_group["item"][0]["item"][0]
        hidden_item = extraction_group["item"][0]["item"][1]

        self.assertEqual(input_item["text"], "Question")
        self.assertEqual(hidden_item["initial"][0]["valueCoding"]["display"], "Question")
        self.assertEqual(mapper.db.calls, [])


if __name__ == "__main__":
    unittest.main()
