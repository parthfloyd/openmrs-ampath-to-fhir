import os

class Config:
    def __init__(self):
        # Application Settings 
        self.locales = ["fr", "es", "ru", "ar"] # "en" is implicit source
        
        # Database Settings
        self.db_config = {
            "host": "localhost",
            "port": 3306,
            "user": "user",
            "password": "password",
            "database": "openmrs"
        }
        
        # Paths
        self.input_dir = os.path.join(os.getcwd(), "input")
        self.output_dir = os.path.join(os.getcwd(), "output")
        
        # API Keys
        self.gemini_api_key = "YOUR_KEY"
        
        # Domain Specifics
        self.ignored_questions = ["provider", "encDate"]

        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)