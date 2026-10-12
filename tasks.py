from celery import Celery
from amocrm_client import AmoCRMClient
from sbp_client import SBPClient
from config import Config
import json
import time
import random
import string
import logging
import os
from logging_config import loggers
from payments_store import load_payments, save_payments, payments_lock

# Используем настроенный логгер для Celery
logger = loggers['celery']

app = Celery('tasks', broker='pyamqp://guest@localhost//')
app.conf.task_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.result_serializer = 'json'
app.conf.task_track_started = True

amocrm_client = AmoCRMClient()
sbp_client = SBPClient()

def generate_order_number(lead_id):
    logger.info(f"Generating order number for lead_id: {lead_id}")
    random_letter = random.choice(string.ascii_uppercase)
    random_digits = random.randint(100, 999)
    return f"{lead_id}_{random_letter}{random_digits}"

@app.task
def process_lead(lead_id, status_id, pipeline_id):
    logger.info(f"Starting async processing for lead_id: {lead_id}, status_id: {status_id}, pipeline_id: {pipeline_id}")

    if pipeline_id != Config.PIPELINE_ID or status_id not in Config.ALLOWED_STATUS_IDS:
        logger.info(f"Lead {lead_id} is not in pipeline 'Доставка цветов' or not in allowed status: {Config.ALLOWED_STATUS_IDS}")
        return

    try:
        logger.info(f"Fetching lead {lead_id} from amoCRM")
        lead = amocrm_client.get_lead_by_id(lead_id)
        logger.info(f"Lead {lead_id} found: {lead}")

        amount = lead.get("price", 0) * 100
        if amount <= 0:
            logger.warning(f"Lead {lead_id} has no price set")
            return

        payments = load_payments()

        if str(lead_id) in payments:
            existing_payment = payments[str(lead_id)]
            existing_amount = existing_payment.get("amount")
            logger.info(f"Lead {lead_id} already in payments.json, existing amount: {existing_amount}, new amount: {amount}")

            if existing_amount != amount:
                logger.info(f"Amounts differ, updating data for lead {lead_id}")
                order_number = generate_order_number(lead_id)
                logger.info(f"Creating payment link for amount: {amount}, order_number: {order_number}")
                payment_response = sbp_client.create_payment_link(amount, order_number)
                if isinstance(payment_response, str):
                    payment_response = json.loads(payment_response)
                payment_link = payment_response.get("formUrl")
                order_id = payment_response.get("orderId")
                logger.info(f"Created new payment link for lead {lead_id}: {payment_link}, orderId: {order_id}")

                field_value = f"{payment_link} (Order ID: {order_id})"
                logger.info(f"Updating lead {lead_id} in amoCRM with new payment link")
                amocrm_client.update_lead(lead_id, Config.CUSTOM_FIELD_ID, field_value)
                logger.info(f"Lead {lead_id} updated with new link and orderId")

                note_text = f"Создана новая ссылка на оплату (сумма изменена): {payment_link} (Order ID: {order_id})"
                logger.info(f"Adding note to lead {lead_id}: {note_text}")
                amocrm_client.add_note(lead_id, note_text)
                logger.info(f"Note added to lead {lead_id}")

                with payments_lock():
                    payments = load_payments()
                    payments[lead_id] = {
                        "order_number": order_number,
                        "amount": amount,
                        "form_url": payment_link,
                        "order_id": order_id,
                        "created_at": time.time()
                    }
                    save_payments(payments)
                logger.info(f"Lead {lead_id} updated in payments.json with new amount and link")
            else:
                logger.info(f"Amounts are the same, skipping processing for lead {lead_id}")
            return

        order_number = generate_order_number(lead_id)
        logger.info(f"Creating payment link for amount: {amount}, order_number: {order_number}")
        payment_response = sbp_client.create_payment_link(amount, order_number)
        if isinstance(payment_response, str):
            payment_response = json.loads(payment_response)
        payment_link = payment_response.get("formUrl")
        order_id = payment_response.get("orderId")
        logger.info(f"Created payment link for lead {lead_id}: {payment_link}, orderId: {order_id}")

        field_value = f"{payment_link} (Order ID: {order_id})"
        logger.info(f"Updating lead {lead_id} in amoCRM with payment link")
        amocrm_client.update_lead(lead_id, Config.CUSTOM_FIELD_ID, field_value)
        logger.info(f"Lead {lead_id} updated with link and orderId")

        note_text = f"Создана ссылка на оплату: {payment_link} (Order ID: {order_id})"
        logger.info(f"Adding note to lead {lead_id}: {note_text}")
        amocrm_client.add_note(lead_id, note_text)
        logger.info(f"Note added to lead {lead_id}")

        with payments_lock():
            payments = load_payments()
            payments[lead_id] = {
                "order_number": order_number,
                "amount": amount,
                "form_url": payment_link,
                "order_id": order_id,
                "created_at": time.time()
            }
            save_payments(payments)
        logger.info(f"Lead {lead_id} saved to payments.json")
    except Exception as e:
        logger.error(f"Error during async processing of lead {lead_id}: {str(e)}")
        raise