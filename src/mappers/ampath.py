import uuid
import datetime
import re
from .base import MapperInterface

class AmpathMapper(MapperInterface):
    def __init__(self, config, db_service, translation_service):
        super().__init__(config, db_service, translation_service)
        self.variables = []
        self.translation_cache = {}

    def transform(self, source_json):
        """
        Main entry point for transformation.
        1. Harvest all text.
        2. Batch translate.
        3. Map to FHIR using cache.
        """
        self.variables = []
        self.translation_cache = {}

        # --- STEP 1: HARVEST STRINGS ---
        print("   [Mapper] Harvesting strings for translation...")
        all_strings = self._harvest_strings(source_json)
        
        # --- STEP 2: BATCH TRANSLATE ---
        if all_strings:
            self.translation_cache = self.ts.batch_translate(all_strings, self.config.locales)

        # --- STEP 3: TRANSFORM (Standard Logic) ---
        print("   [Mapper] Generating FHIR resources...")
        
        enc_string = source_json.get("encounter", "")
        # Try DB lookup, fallback to generated UUIDs if DB not connected
        try:
            form_uuid, et_uuid = self.db.get_form_metadata(enc_string)
        except:
            form_uuid, et_uuid = str(uuid.uuid4()), str(uuid.uuid4())
            
        if not form_uuid: form_uuid = str(uuid.uuid4())
        if not et_uuid: et_uuid = str(uuid.uuid4())

        display_name = source_json.get("display", enc_string.replace("encounter.", "").upper())

        questionnaire = {
            "resourceType": "Questionnaire",
            "id": source_json.get("uuid", str(uuid.uuid4())),
            "title": display_name,
            "status": "active",
            "date": datetime.datetime.now().isoformat(),
            "subjectType": ["Encounter", "Patient", "Practitioner"],
            "code": [
                {
                    "system": "http://fhir.openmrs.org/code-system/encounter-type",
                    "code": et_uuid,
                    "display": display_name
                },
                {
                    "system": "http://fhir.openmrs.org/core/StructureDefinition/omrs-form",
                    "code": form_uuid,
                    "display": display_name
                }
            ],
            "item": []
        }

        # Add Title Translations (Fast Lookup)
        self._inject_translation(questionnaire, display_name, is_root=True)

        # Process Pages
        if "pages" in source_json:
            for page in source_json["pages"]:
                q_item = self._process_group(page, is_page=True)
                questionnaire["item"].append(q_item)

        # Inject Variables (Scoring) at Root
        if self.variables:
            if "extension" not in questionnaire: questionnaire["extension"] = []
            for var in self.variables:
                questionnaire["extension"].append({
                    "url": "http://hl7.org/fhir/StructureDefinition/variable",
                    "valueExpression": {
                        "name": var['name'],
                        "language": "text/fhirpath",
                        "expression": var['expression']
                    }
                })
        
        return questionnaire

    def _harvest_strings(self, node) -> list:
        """Recursive function to find all translatable text in the raw JSON."""
        strings = []
        
        if isinstance(node, dict):
            # Check common label keys
            if "label" in node: strings.append(node["label"])
            # 'text' key is rare in Ampath source but check anyway
            if "text" in node: strings.append(node["text"])
            
            # Check HTML/Display
            if "questionOptions" in node:
                opts = node["questionOptions"]
                if "html" in opts: 
                    clean = re.sub('<[^<]+?>', '', opts["html"])
                    strings.append(clean)
                if "answers" in opts:
                    for ans in opts["answers"]:
                        if "label" in ans: strings.append(ans["label"])

            # Recurse
            for key, value in node.items():
                strings.extend(self._harvest_strings(value))
                
        elif isinstance(node, list):
            for item in node:
                strings.extend(self._harvest_strings(item))
                
        return strings

    def _process_group(self, group_json, is_page=False):
        """Handles Pages and Sections recursively."""
        label = group_json.get("label", "Group")
        # Sanitize label for linkId
        safe_label = re.sub(r'[^a-zA-Z0-9]', '-', label.lower())
        link_id = f"page-{safe_label}" if is_page else f"section-{safe_label}"
        
        item = {
            "linkId": link_id,
            "type": "group",
            "text": label,
            "item": []
        }

        # Page Extension
        if is_page:
            item["extension"] = [{
                "url": "http://hl7.org/fhir/StructureDefinition/questionnaire-itemControl",
                "valueCodeableConcept": {
                    "coding": [{"system": "http://hl7.org/fhir/questionnaire-item-control", "code": "page", "display": "Page"}]
                }
            }]
            
        self._inject_translation(item, label)

        # Process Sub-sections
        if "sections" in group_json:
            for section in group_json["sections"]:
                item["item"].append(self._process_group(section, is_page=False))
        
        # Process Questions
        if "questions" in group_json:
            for question in group_json["questions"]:
                
                # 1. Handle Display/HTML Instructions
                if self._is_display_element(question):
                    item["item"].append(self._create_display_item(question))
                    continue

                # 2. Skip Ignored
                if question.get("id") in self.config.ignored_questions:
                    continue

                # 3. Handle SDC Extraction Pattern (Obs)
                # Matches if type is 'obs' OR has a concept mapped
                opts = question.get("questionOptions", {})
                if question.get("type") == "obs" or "concept" in opts:
                    item["item"].append(self._create_extraction_group(question))
                
                # 4. Handle Simple Inputs (e.g. Encounter Date)
                elif question.get("type") in ["encounterDatetime", "encounterProvider"]:
                    # Simplify for now, treat as date/string
                    fhir_type = "date" if "Date" in question.get("type") else "string"
                    item["item"].append(self._create_simple_input(question, fhir_type))

        return item

    def _create_extraction_group(self, q_json):
        """
        Creates the 3-level structure for SDC Extraction:
        Group (Context=Obs) -> [Inner Group -> [Input Item, Hidden Code Item]]
        """
        q_id = q_json.get("id", str(uuid.uuid4()))
        opts = q_json.get("questionOptions", {})
        concept_uuid = opts.get("concept", "UNKNOWN-CONCEPT")
        question_text = self._resolve_question_text(q_json)
        
        # A. The Wrapper Group (Extraction Context)
        wrapper = {
            "linkId": f"{q_id}-group",
            "type": "group",
            "extension": [{
                "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-itemExtractionContext",
                "valueExpression": {
                    "language": "application/x-fhir-query",
                    "expression": "Observation",
                    "name": q_id
                }
            }],
            "item": []
        }

        # B. The Inner Container
        inner_group = {
            "linkId": f"{q_id}-inner-group",
            "type": "group",
            "item": []
        }
        
        # Definition is often required on the inner group for validation in some parsers
        if self._determine_fhir_type(q_json) == "choice":
             inner_group["definition"] = "http://hl7.org/fhir/StructureDefinition/Observation#Observation.valueCodeableConcept"

        # C. The Visible Input Item
        input_type = self._determine_fhir_type(q_json)
        input_item = {
            "linkId": q_id,
            "type": input_type,
            "text": question_text,
            "required": q_json.get("required") == "true"
        }
        
        if "prefix" in q_json:
            input_item["prefix"] = q_json["prefix"]

        self._inject_translation(input_item, question_text)
        self._add_item_control(input_item, q_json)

        # Handle Answers (Choices)
        if "answers" in opts:
            input_item["answerOption"] = []
            for ans in opts["answers"]:
                opt = {
                    "valueCoding": {
                        "code": ans.get("concept"),
                        "display": ans.get("label", "Option"),
                    }
                }
                # Translate Answer Options
                if "label" in ans:
                     self._inject_translation(opt["valueCoding"], ans["label"], is_root=False, is_display=True)
                
                input_item["answerOption"].append(opt)
            
            # SCORING: Generate variable if score map exists
            if "score" in q_json:
                self._generate_score_variable(q_id, q_json["score"])

        # CALCULATIONS
        if "calculate" in opts:
            calc_expr = opts["calculate"].get("calculateExpression", "")
            fhir_expr = self._transform_calculation(calc_expr)
            input_item["readOnly"] = True
            if "extension" not in input_item: input_item["extension"] = []
            
            input_item["extension"].append({
                "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-calculatedExpression",
                "valueExpression": {"language": "text/fhirpath", "expression": fhir_expr}
            })

        # D. The Hidden Code Item
        hidden_item = {
            "linkId": f"{q_id}-obs",
            "type": "choice",
            "definition": "http://hl7.org/fhir/StructureDefinition/Observation#Observation.code",
            "extension": [{"url": "http://hl7.org/fhir/StructureDefinition/questionnaire-hidden", "valueBoolean": True}],
            "initial": [{"valueCoding": {"code": concept_uuid, "display": question_text}}]
        }
        
        # Add Translations to hidden item display just in case
        self._inject_translation(hidden_item["initial"][0]["valueCoding"], question_text, is_display=True)

        inner_group["item"].append(input_item)
        inner_group["item"].append(hidden_item)
        wrapper["item"].append(inner_group)

        return wrapper

    def _create_display_item(self, q_json):
        """Map HTML/Instructions to Display items."""
        raw_html = q_json.get("questionOptions", {}).get("html", "")
        clean_text = re.sub('<[^<]+?>', '', raw_html) # Remove tags
        
        item = {
            "linkId": str(uuid.uuid4()),
            "type": "display",
            "text": clean_text
        }
        self._inject_translation(item, clean_text)
        return item

    def _create_simple_input(self, q_json, fhir_type):
        """For non-Obs fields like Encounter Date."""
        question_text  = self._resolve_question_text(q_json)
        item = {
            "linkId": q_json.get("id"),
            "type": fhir_type,
            "text": question_text,
            "required": q_json.get("required") == "true"
        }
        self._inject_translation(item, question_text)
        return item
        
    def _resolve_question_text(self, q_json):
        """Determines question text with consistent precedence and blank handling."""
        opts = q_json.get("questionOptions", {})

        display = opts.get("display")
        if isinstance(display, str) and display.strip():
            return display.strip()

        label = q_json.get("label")
        if isinstance(label, str) and label.strip():
            return label.strip()

        concept_uuid = opts.get("concept")
        if isinstance(concept_uuid, str) and concept_uuid.strip():
            try:
                concept_name = self.db.get_concept_name(concept_uuid.strip())
                if isinstance(concept_name, str) and concept_name.strip():
                    return concept_name.strip()
            except Exception:
                pass

        return "Question"

    def _determine_fhir_type(self, q_json):
        """Determines FHIR type checking 'rendering' option."""
        opts = q_json.get("questionOptions", {})
        rendering = opts.get("rendering", "")
        
        if rendering in ["text", "textarea"]: return "string"
        if rendering in ["radio", "select", "ui-select-extended"]: return "choice"
        if rendering == "number": return "integer"
        if "answers" in opts: return "choice"
        return "string"

    def _add_item_control(self, item, q_json):
        """Adds UI hints (Radio, Text Box)."""
        opts = q_json.get("questionOptions", {})
        rendering = opts.get("rendering", "")
        
        code = None
        if rendering == "radio": code = "radio-button"
        elif rendering in ["textarea", "text"]: code = "text-box"
        
        if code:
            if "extension" not in item: item["extension"] = []
            item["extension"].append({
                "url": "http://hl7.org/fhir/StructureDefinition/questionnaire-itemControl",
                "valueCodeableConcept": {
                    "coding": [{"system": "http://hl7.org/fhir/questionnaire-item-control", "code": code}]
                }
            })

    def _generate_score_variable(self, q_id, score_map):
        """Generates FHIRPath variable for scoring logic."""
        var_name = f"{q_id}Score"
        
        # Path to the answer's coding code.
        item_path = f"%resource.item.descendants().where(linkId='{q_id}').answer.value.coding.code"
        
        # Build nested iif structure: iif(path='A', 1, iif(path='B', 2, 0))
        expr_str = "0"
        for ans_code, score in score_map.items():
            expr_str = f"iif({item_path}='{ans_code}', {score}, {expr_str})"
            
        self.variables.append({"name": var_name, "expression": expr_str})

    def _transform_calculation(self, ampath_calc):
        """
        Transforms Ampath JS calc -> FHIRPath.
        Ex: (FORM.q1.score[q1] || 0) -> (%q1Score)
        """
        clean = ampath_calc.replace("FORM.", "")
        
        # Replace .score[x] with %xScore
        clean = re.sub(r"(\w+)\.score\[\1\]", r"%\1Score", clean)
        
        # Remove JS fallbacks
        clean = clean.replace(" || 0", "")
        
        return clean.strip()

    def _is_display_element(self, q_json):
        opts = q_json.get("questionOptions", {})
        return opts.get("customControl") is True or "html" in opts

    def _inject_translation(self, item, text, is_root=False, is_display=False):
        """
        Looks up the text in self.translation_cache and injects the extension.
        No API calls happen here.
        """
        if not text or text not in self.translation_cache:
            return

        translations = self.translation_cache[text] # {"fr": "...", "es": "..."}
        
        exts = []
        for lang_code, translated_text in translations.items():
            exts.append({
                "url": "http://hl7.org/fhir/StructureDefinition/translation",
                "extension": [
                    {"url": "lang", "valueCode": lang_code},
                    {"url": "content", "valueString": translated_text}
                ]
            })

        if exts:
            key = "_title" if is_root else ("_display" if is_display else "_text")
            if key not in item: item[key] = {}
            item[key]["extension"] = exts