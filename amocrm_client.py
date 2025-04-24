import requests
from config import Config

class AmoCRMClient:
    def __init__(self):
        self.base_url = f"https://{Config.AMOCRM_DOMAIN}/api/v4"
        self.headers = {
            "Authorization": f"Bearer {Config.AMOCRM_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

    def get_leads_by_pipeline_status(self, pipeline_id, status_id):
        """Получить сделки из определённой стадии воронки."""
        url = f"{self.base_url}/leads"
        params = {
            "filter[pipeline_id]": pipeline_id,
            "filter[statuses][0][status_id]": status_id
        }
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()["_embedded"]["leads"]

    def update_lead(self, lead_id, custom_field_id, payment_link):
        """Обновить поле сделки с ссылкой на оплату."""
        url = f"{self.base_url}/leads/{lead_id}"
        data = {
            "custom_fields_values": [
                {
                    "field_id": custom_field_id,
                    "values": [{"value": payment_link}]
                }
            ]
        }
        response = requests.patch(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def add_note(self, lead_id, note_text):
        """Добавить примечание к сделке."""
        url = f"{self.base_url}/leads/{lead_id}/notes"
        data = {
            "note_type": "common",
            "params": {"text": note_text}
        }
        response = requests.post(url, headers=self.headers, json=[data])
        response.raise_for_status()
        return response.json()