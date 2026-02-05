# Translation Demo Questionnaires

## Purpose
These files are **example** FHIR R4 Questionnaire resources that can be used to test run this project.

## Location & Usage
- Directory: `questionnaires/`
- Files:
  - `CRIES-8.json`
  - `PHQ-9.json`

## How to Run / Load Locally
1. Follow the main setup instructions in `README.md` (virtualenv, dependencies).
2. (Optional for translation) Update `src/config.py` if you want to include `es` in `Config.locales`.
3. Run the converter:
   ```bash
   python -m src.main
   ```
4. If you want to load these questionnaires, copy them into the location your local tooling expects (for example, a test loader or any local FHIR import step you already use).

## Prerequisites / Flags
- For translation ensure the desired locale (e.g., `es`) is present in `Config.locales` in `src/config.py`.
- No additional flags are required for these dummy files; they are static examples.
