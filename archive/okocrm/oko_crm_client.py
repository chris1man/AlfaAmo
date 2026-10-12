import requests
import logging
from oko_config import OkoConfig

logger = logging.getLogger(__name__)

class OkoCRMClient:
    def __init__(self):
        self.base_url = "https://api.okocrm.com/v2"
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {OkoConfig.OKOCRM_ACCESS_TOKEN}"
        }

    def get_lead_by_id(self, lead_id):
        url = f"{self.base_url}/leads/{lead_id}/"
        try:
            logger.info(f"Sending request to {url}")
            response = requests.get(url, headers=self.headers)
            logger.info(f"Response status: {response.status_code}, content: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch lead {lead_id}: {str(e)}")
            raise

    def update_lead(self, lead_id, custom_field_id, payment_link):
        url = f"{self.base_url}/leads/{lead_id}/"
        data = {
            f"cf_{custom_field_id}": payment_link
        }
        try:
            response = requests.put(url, headers=self.headers, json=data)
            logger.info(f"Update lead {lead_id} response: {response.status_code}, {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to update lead {lead_id}: {str(e)}")
            raise

    def add_note(self, lead_id, note_text):
        url = f"{self.base_url}/notes/note"
        data = {
            "lead_id": str(lead_id),
            "text": note_text
        }
        try:
            response = requests.post(url, headers=self.headers, data=data)
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
        existing_tags = lead.get("tags", [])
        
        # Проверяем, есть ли уже такой тег
        if tag_name in existing_tags:
            logger.info(f"Tag '{tag_name}' already exists on lead {lead_id}, skipping")
            return lead

        # Добавляем новый тег к списку
        existing_tags.append(tag_name)

        # Обновляем сделку с новым списком тегов
        url = f"{self.base_url}/leads/{lead_id}/"
        data = {
            "tags": existing_tags
        }
        try:
            response = requests.put(url, headers=self.headers, json=data)
            logger.info(f"Add tag to lead {lead_id} response: {response.status_code}, {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to add tag to lead {lead_id}: {str(e)}")
            raise

    def change_status(self, lead_id, stage_id):
        url = f"{self.base_url}/leads/{lead_id}/"
        data = {
            "stages_id": stage_id
        }
        try:
            response = requests.put(url, headers=self.headers, json=data)
            logger.info(f"Change status of lead {lead_id} response: {response.status_code}, {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to change status of lead {lead_id}: {str(e)}")
            raise

