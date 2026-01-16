import json
import os
import glob
from config import Config

from database.openmrs_sql import OpenMRSDatabase
from services.gemini import GeminiTranslationService
from services.mock import MockTranslationService
from mappers.ampath import AmpathMapper

def main():
    cfg = Config()

    db_service = OpenMRSDatabase(cfg) 
    
    #trans_service = MockTranslationService()
    trans_service = GeminiTranslationService(cfg.gemini_api_key)
    
    # 3. Mapper
    mapper = AmpathMapper(cfg, db_service, trans_service)

    db_service.connect()
    
    files = glob.glob(os.path.join(cfg.input_dir, "*.json"))
    print(f"Found {len(files)} files.")

    for file_path in files:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        try:
            fhir_result = mapper.transform(data)
            
            out_name = "fhir_" + os.path.basename(file_path)
            with open(os.path.join(cfg.output_dir, out_name), 'w') as f_out:
                json.dump(fhir_result, f_out, indent=2)
            print(f"Mapped: {out_name}")
            
        except Exception as e:
            print(f"Failed {file_path}: {e}")

    db_service.close()

if __name__ == "__main__":
    main()