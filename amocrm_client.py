import requests
import logging
from config import Config

logger = logging.getLogger(__name__)

class AmoCRMClient:
    def __init__(self):
        self.base_url = f"https://{Config.AMOCRM_DOMAIN}/api/v4"
        self.headers = {
            "Authorization": f"Bearer {Config.AMOCRM_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

    def get_lead_by_id(self, lead_id):
        url = f"{self.base_url}/leads/{lead_id}"
        try:
            logger.info(f"Sending request to {url}")
            response = requests.get(url, headers=self.headers)
            logger.info(f"Response status: {response.status_code}, content: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch lead {lead_id}: {str(e)}")
            raise

    def get_leads_by_pipeline_status(self, pipeline_id, status_id):
        url = f"{self.base_url}/leads"
        params = {
            "filter[pipeline_id]": pipeline_id,
            "filter[statuses][0][status_id]": status_id
        }
        try:
            logger.info(f"Sending request to {url} with params {params}")
            response = requests.get(url, headers=self.headers, params=params)
            logger.info(f"Response status: {response.status_code}, content: {response.text}")
            response.raise_for_status()
            data = response.json()
            leads = data.get("_embedded", {}).get("leads", [])
            logger.info(f"Found {len(leads)} leads in pipeline {pipeline_id}, status {status_id}")
            return leads
        except requests.RequestException as e:
            logger.error(f"Failed to fetch leads: {str(e)}")
            raise

    def update_lead(self, lead_id, custom_field_id, payment_link):
        url = f"{self.base_url}/leads/{lead_id}"
        data = {
            "custom_fields_values": [
                {
                    "field_id": custom_field_id,
                    "values": [{"value": payment_link}]
                }
            ]
        }
        try:
            response = requests.patch(url, headers=self.headers, json=data)
            logger.info(f"Update lead {lead_id} response: {response.status_code}, {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to update lead {lead_id}: {str(e)}")
            raise

    def add_note(self, lead_id, note_text):
        url = f"{self.base_url}/leads/{lead_id}/notes"
        data = {
            "note_type": "common",
            "params": {"text": note_text}
        }
        try:
            response = requests.post(url, headers=self.headers, json=[data])
            logger.info(f"Add note to lead {lead_id} response: {response.status_code}, {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to add note to lead {lead_id}: {str(e)}")
            raise

    def add_tag(self, lead_id, tag_name):
        # Получаем текущие данные сделки
        lead = self.get_lead_by_id(lead_id)
        
        # Извлекаем существующие теги
        existing_tags = lead.get("_embedded", {}).get("tags", [])
        existing_tag_names = [tag["name"] for tag in existing_tags]

        # Проверяем, есть ли уже такой тег
        if tag_name in existing_tag_names:
            logger.info(f"Tag '{tag_name}' already exists on lead {lead_id}, skipping")
            return lead

        # Добавляем новый тег к списку
        existing_tag_names.append(tag_name)
        new_tags = [{"name": name} for name in existing_tag_names]

        # Обновляем сделку с новым списком тегов
        url = f"https://{self.domain}/api/v4/leads/{lead_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "_embedded": {
                "tags": new_tags
            }
        }
        response = requests.patch(url, headers=headers, json=data)
        logger.info(f"Add tag to lead {lead_id} response: {response.status_code}, {response.text}")
        response.raise_for_status()
        return response.json()

    def change_status(self, lead_id, status_id):
        url = f"{self.base_url}/leads/{lead_id}"
        data = {
            "status_id": status_id
        }
        try:
            response = requests.patch(url, headers=self.headers, json=data)
            logger.info(f"Change status of lead {lead_id} response: {response.status_code}, {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to change status of lead {lead_id}: {str(e)}")
            raise