from celery import Celery
from oko_crm_client import OkoCRMClient
from oko_sbp_client import OkoSBPClient
from oko_config import OkoConfig
import json
import time
import random
import string
import logging
import os
from logging_config import loggers

# Используем настроенный логгер для Celery
logger = loggers['celery']

app = Celery('oko_tasks', broker='pyamqp://guest@localhost//')
app.conf.task_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.result_serializer = 'json'
app.conf.task_track_started = True

oko_crm_client = OkoCRMClient()
oko_sbp_client = OkoSBPClient()

OKO_PAYMENTS_FILE = "/root/AlfaAmo/oko_payments.json"

logger.info("OkoCRM Celery worker started, logging configured")

def load_oko_payments():
    logger.info(f"Loading oko payments from {OKO_PAYMENTS_FILE}")
    if not os.path.exists(OKO_PAYMENTS_FILE):
        logger.info("Oko payments file does not exist, creating new one")
        save_oko_payments({})
        return {}
    try:
        with open(OKO_PAYMENTS_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                logger.info("Oko payments file is empty, initializing with {}")
                return {}
            return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in oko payments file: {str(e)}")
        save_oko_payments({})
        return {}
    except Exception as e:
        logger.error(f"Failed to load oko payments: {str(e)}")
        return {}

def save_oko_payments(payments):
    logger.info(f"Saving oko payments to {OKO_PAYMENTS_FILE}")
    try:
        with open(OKO_PAYMENTS_FILE, "w") as f:
            json.dump(payments, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save oko payments: {str(e)}")

def generate_order_number(lead_id):
    logger.info(f"Generating order number for oko lead_id: {lead_id}")
    random_letter = random.choice(string.ascii_uppercase)
    random_digits = random.randint(100, 999)
    return f"OKO_{lead_id}_{random_letter}{random_digits}"

@app.task(routing_key='celery')
def process_oko_lead(lead_id, stage_id, pipeline_id):
    logger.info(f"Starting async processing for oko lead_id: {lead_id}, stage_id: {stage_id}, pipeline_id: {pipeline_id}")

    if pipeline_id != OkoConfig.OKOCRM_PIPELINE_ID or stage_id != OkoConfig.OKOCRM_TRIGGER_STAGE_ID:
        logger.info(f"Oko lead {lead_id} is not in correct pipeline or stage")
        return

    try:
        logger.info(f"Fetching oko lead {lead_id} from okoCRM")
        lead = oko_crm_client.get_lead_by_id(lead_id)
        logger.info(f"Oko lead {lead_id} found: {lead}")

        # В okoCRM API данные находятся в поле 'data'
        lead_data = lead.get("data", lead)
        amount = int(lead_data.get("budget", 0)) * 100  # Конвертируем в копейки
        if amount <= 0:
            logger.warning(f"Oko lead {lead_id} has no budget set")
            return

        payments = load_oko_payments()

        if str(lead_id) in payments:
            existing_payment = payments[str(lead_id)]
            existing_amount = existing_payment.get("amount")
            logger.info(f"Oko lead {lead_id} already in payments.json, existing amount: {existing_amount}, new amount: {amount}")

            if existing_amount != amount:
                logger.info(f"Amounts differ, updating data for oko lead {lead_id}")
                order_number = generate_order_number(lead_id)
                logger.info(f"Creating payment link for amount: {amount}, order_number: {order_number}")
                payment_response = oko_sbp_client.create_payment_link(amount, order_number)
                if isinstance(payment_response, str):
                    payment_response = json.loads(payment_response)
                payment_link = payment_response.get("formUrl")
                order_id = payment_response.get("orderId")
                logger.info(f"Created new payment link for oko lead {lead_id}: {payment_link}, orderId: {order_id}")

                # Записываем только URL в поле типа "ссылка"
                field_value = payment_link
                logger.info(f"Updating oko lead {lead_id} in okoCRM with new payment link")
                oko_crm_client.update_lead(lead_id, OkoConfig.OKOCRM_CUSTOM_FIELD_ID, field_value)
                logger.info(f"Oko lead {lead_id} updated with new payment link")

                note_text = f"Создана новая ссылка на оплату (сумма изменена): {payment_link} (Order ID: {order_id})"
                logger.info(f"Adding note to oko lead {lead_id}: {note_text}")
                oko_crm_client.add_note(lead_id, note_text)
                logger.info(f"Note added to oko lead {lead_id}")

                payments[lead_id] = {
                    "order_number": order_number,
                    "amount": amount,
                    "form_url": payment_link,
                    "order_id": order_id,
                    "created_at": time.time()
                }
                save_oko_payments(payments)
                logger.info(f"Oko lead {lead_id} updated in payments.json with new amount and link")
            else:
                logger.info(f"Amounts are the same, skipping processing for oko lead {lead_id}")
            return

        order_number = generate_order_number(lead_id)
        logger.info(f"Creating payment link for amount: {amount}, order_number: {order_number}")
        payment_response = oko_sbp_client.create_payment_link(amount, order_number)
        if isinstance(payment_response, str):
            payment_response = json.loads(payment_response)
        payment_link = payment_response.get("formUrl")
        order_id = payment_response.get("orderId")
        logger.info(f"Created payment link for oko lead {lead_id}: {payment_link}, orderId: {order_id}")

        # Записываем только URL в поле типа "ссылка"
        field_value = payment_link
        logger.info(f"Updating oko lead {lead_id} in okoCRM with payment link")
        oko_crm_client.update_lead(lead_id, OkoConfig.OKOCRM_CUSTOM_FIELD_ID, field_value)
        logger.info(f"Oko lead {lead_id} updated with payment link")

        note_text = f"Создана ссылка на оплату: {payment_link} (Order ID: {order_id})"
        logger.info(f"Adding note to oko lead {lead_id}: {note_text}")
        oko_crm_client.add_note(lead_id, note_text)
        logger.info(f"Note added to oko lead {lead_id}")

        payments[lead_id] = {
            "order_number": order_number,
            "amount": amount,
            "form_url": payment_link,
            "order_id": order_id,
            "created_at": time.time()
        }
        save_oko_payments(payments)
        logger.info(f"Oko lead {lead_id} saved to payments.json")
    except Exception as e:
        logger.error(f"Error during async processing of oko lead {lead_id}: {str(e)}")
        raise
