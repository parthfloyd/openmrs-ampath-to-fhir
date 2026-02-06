import mysql.connector
from .base import DatabaseInterface

class OpenMRSDatabase(DatabaseInterface):
    def __init__(self, config):
        self.config = config
        self.conn = None

    def connect(self):
        try:
            self.conn = mysql.connector.connect(**self.config.db_config)
        except Exception as e:
            print(f"DB Connection failed: {e}")

    def close(self):
        if self.conn and self.conn.is_connected():
            self.conn.close()

    def get_concept_name(self, concept_uuid: str) -> str:
        if not self.conn:
            return "Unknown Concept"
        query = """
            SELECT name FROM concept_name cn
            JOIN concept c ON cn.concept_id = c.concept_id
            WHERE c.uuid = %s AND cn.locale = 'en' AND cn.concept_name_type = 'FULLY_SPECIFIED'
            LIMIT 1;
        """
        cursor = self.conn.cursor()
        cursor.execute(query, (concept_uuid,))
        res = cursor.fetchone()
        cursor.close()
        return res[0] if res else "Unknown Concept"

    def get_form_metadata(self, encounter_string: str):
        if not self.conn:
            return None, None
        return "mock-form-uuid", "mock-enc-uuid"  # Placeholder for brevity

    def get_concept_translations(self, concept_uuid: str):
        if not self.conn:
            return {}

        query = """
            SELECT cn.locale, cn.name
            FROM concept_name cn
            JOIN concept c ON cn.concept_id = c.concept_id
            WHERE c.uuid = %s
              AND cn.voided = 0
              AND cn.name IS NOT NULL
              AND TRIM(cn.name) <> ''
            ORDER BY
                cn.locale,
                CASE cn.concept_name_type
                    WHEN 'FULLY_SPECIFIED' THEN 0
                    WHEN 'SHORT' THEN 1
                    WHEN 'INDEX_TERM' THEN 2
                    ELSE 3
                END,
                cn.locale_preferred DESC,
                cn.concept_name_id ASC;
        """

        cursor = self.conn.cursor()
        cursor.execute(query, (concept_uuid,))
        rows = cursor.fetchall()
        cursor.close()

        translations = {}
        for locale, name in rows:
            if locale not in translations:
                translations[locale] = name

        return translations