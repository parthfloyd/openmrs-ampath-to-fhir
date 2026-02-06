from src.mappers.ampath import AmpathMapper


class StubConfig:
    locales = ["fr", "es"]
    ignored_questions = []


class StubDB:
    def __init__(self, concept_translations=None):
        self.concept_translations = concept_translations or {}

    def get_form_metadata(self, encounter_string):
        return "form-uuid", "enc-uuid"

    def get_concept_translations(self, concept_uuid):
        return self.concept_translations.get(concept_uuid, {})


class StubTranslationService:
    def __init__(self, translations):
        self.translations = translations
        self.calls = []

    def batch_translate(self, texts, target_locales):
        self.calls.append((list(texts), list(target_locales)))
        result = {}
        for text in texts:
            result[text] = {}
            for loc in target_locales:
                result[text][loc] = self.translations.get(text, {}).get(loc, f"[{loc}] {text}")
        return result


def _sample_source(question_label="Question text", answer_label="Yes"):
    return {
        "uuid": "q-1",
        "encounter": "encounter.test",
        "display": "Display",
        "pages": [
            {
                "label": "Page 1",
                "sections": [
                    {
                        "label": "Section 1",
                        "questions": [
                            {
                                "id": "q1",
                                "type": "obs",
                                "label": question_label,
                                "questionOptions": {
                                    "concept": "concept-question",
                                    "rendering": "radio",
                                    "answers": [
                                        {"label": answer_label, "concept": "concept-answer-yes"}
                                    ],
                                },
                            }
                        ],
                    }
                ],
            }
        ],
    }


def _get_display_translation(questionnaire):
    option = questionnaire["item"][0]["item"][0]["item"][0]["item"][0]["item"][0]["answerOption"][0]["valueCoding"]
    exts = option["_display"]["extension"]
    return {e["extension"][0]["valueCode"]: e["extension"][1]["valueString"] for e in exts}


def test_dictionary_translation_precedence_over_gemini():
    db = StubDB(
        concept_translations={
            "concept-question": {"fr": "Question dictionnaire fr", "es": "Question dictionnaire es"},
            "concept-answer-yes": {"fr": "Oui dictionnaire", "es": "Si diccionario"},
        }
    )
    ts = StubTranslationService(
        translations={
            "Question text": {"fr": "Question gemini fr", "es": "Question gemini es"},
            "Yes": {"fr": "Oui gemini", "es": "Si gemini"},
        }
    )
    mapper = AmpathMapper(StubConfig(), db, ts)

    questionnaire = mapper.transform(_sample_source())

    # Gemini still used for uncovered strings, but not for fully covered concept strings
    sent_texts = set(ts.calls[0][0])
    assert "Question text" not in sent_texts
    assert "Yes" not in sent_texts

    answer_translations = _get_display_translation(questionnaire)
    assert answer_translations["fr"] == "Oui dictionnaire"
    assert answer_translations["es"] == "Si diccionario"


def test_dictionary_missing_locale_falls_back_to_gemini():
    db = StubDB(
        concept_translations={
            "concept-answer-yes": {"fr": "Oui dictionnaire"},
        }
    )
    ts = StubTranslationService(translations={"Yes": {"fr": "Oui gemini", "es": "Si gemini"}})
    mapper = AmpathMapper(StubConfig(), db, ts)

    questionnaire = mapper.transform(_sample_source())

    answer_translations = _get_display_translation(questionnaire)
    assert answer_translations["fr"] == "Oui dictionnaire"
    assert answer_translations["es"] == "Si gemini"


def test_no_concept_mapping_uses_gemini_only():
    db = StubDB()
    ts = StubTranslationService(translations={"No concept text": {"fr": "Sans concept", "es": "Sin concepto"}})
    mapper = AmpathMapper(StubConfig(), db, ts)

    source = _sample_source(question_label="No concept text")
    source["pages"][0]["sections"][0]["questions"][0]["questionOptions"].pop("concept")

    questionnaire = mapper.transform(source)
    input_item = questionnaire["item"][0]["item"][0]["item"][0]["item"][0]["item"][0]
    translations = {e["extension"][0]["valueCode"]: e["extension"][1]["valueString"] for e in input_item["_text"]["extension"]}

    assert "No concept text" in ts.calls[0][0]
    assert translations["fr"] == "Sans concept"
    assert translations["es"] == "Sin concepto"


def test_blank_dictionary_value_does_not_block_gemini_fallback():
    db = StubDB(
        concept_translations={
            "concept-answer-yes": {"fr": "   ", "es": "Si diccionario"},
        }
    )
    ts = StubTranslationService(translations={"Yes": {"fr": "Oui gemini", "es": "Si gemini"}})
    mapper = AmpathMapper(StubConfig(), db, ts)

    questionnaire = mapper.transform(_sample_source())

    answer_translations = _get_display_translation(questionnaire)
    assert answer_translations["fr"] == "Oui gemini"
    assert answer_translations["es"] == "Si diccionario"
