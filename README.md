## Overview
openmrs-ampath-to-fhir is a lightweight converter that transforms AMPATH OpenMRS form JSON into FHIR R4 Questionnaire resources, optionally enriching them with translations and OpenMRS metadata.

## Prerequisites
- Python 3.9+ (recommended)
- A virtual environment tool such as `venv` or `virtualenv`
- Access to a MySQL-compatible OpenMRS database (optional, for metadata lookups)
- A Gemini API key (optional, for live translations)

## Setup & Run
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure the app:
   - Edit `src/config.py` to set your database connection info, locales, and Gemini API key.
4. Add input files:
   - Place AMPATH OpenMRS form JSON files into the `input/` directory (created automatically on first run).
5. Run the converter:
   ```bash
   python -m src.main
   ```
6. Review results:
   - Generated FHIR Questionnaire JSON files are written to `output/` as `fhir_<original>.json`.

## Contributing & Issues
- Found a bug or have a feature request? Please open an issue with details and reproducible steps.
- Contributions are welcome! Fork the repository, create a branch, and submit a pull request describing your changes.