# Architecture & Flow

## Purpose
This project converts AMPATH OpenMRS form JSON into FHIR R4 Questionnaire resources, optionally enriching the output with translations and OpenMRS metadata.

## High-Level Flow
1. **Startup & configuration**
   - `src/main.py` loads `Config` from `src/config.py`.
   - Configuration defines locales, database connection settings, input/output paths, and the Gemini API key.
2. **Service wiring**
   - `OpenMRSDatabase` is initialized for optional metadata lookups (form UUIDs, encounter type UUIDs).
   - A translation service is selected (Gemini or mock).
   - `AmpathMapper` receives config + services.
3. **Input discovery**
   - `src/main.py` scans the `input/` directory for `*.json` files.
4. **Translation preparation**
   - The mapper recursively harvests all translatable strings from the form JSON (labels, HTML instructions, answer labels).
   - Strings are deduplicated and checked against concept dictionary translations first.
   - Concept dictionary language translations are authoritative and are prioritized over Gemini translations; Gemini is fallback for missing entries/locales.
5. **Transformation to FHIR**
   - The mapper builds a FHIR `Questionnaire`:
     - Root metadata includes `resourceType`, `id`, `title`, `status`, `subjectType`, and `code` entries.
     - Each page becomes a FHIR `group` with a page extension.
     - Sections become nested `group` items.
     - Questions map to different structures depending on type (simple, display, or observation extraction group).
6. **Enhancements & extensions**
   - Translations are injected into `_title`, `_text`, or `_display` extensions.
   - Optional scoring variables and calculated expressions are added using FHIRPath.
7. **Output**
   - Each transformed form is written to `output/fhir_<original>.json`.

## Key Modules
- **`src/main.py`**
  - Entry point: wires dependencies, reads inputs, writes outputs.
- **`src/config.py`**
  - Defines locales, paths, DB config, ignored questions, and API keys.
- **`src/mappers/ampath.py`**
  - Core mapping logic from AMPATH JSON → FHIR Questionnaire.
- **`src/services/gemini.py`**
  - Translation via Gemini API with batching.
- **`src/services/mock.py`**
  - Local mock translation service for testing.
- **`src/database/openmrs_sql.py`**
  - OpenMRS lookup helpers (currently contains a placeholder for metadata lookup).

## Data Shapes (Inputs/Outputs)
- **Input:** AMPATH OpenMRS JSON forms (pages → sections → questions).
- **Output:** FHIR R4 `Questionnaire` JSON resources written to `output/`.