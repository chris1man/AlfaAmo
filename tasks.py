from celery import Celery
from amocrm_client import AmoCRMClient
from sbp_client import SBPClient
from config import Config
import json
import requests
import time
import random
import string
import logging
import os
from logging_config import loggers
from payments_store import load_payments, save_payments, payments_lock, lead_lock, get_orders, add_order

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

@app.task(bind=True, autoretry_for=(requests.RequestException,), retry_backoff=True,
          retry_backoff_max=300, retry_jitter=True, max_retries=5)
def process_lead(self, lead_id, status_id, pipeline_id):
    lead_id = str(lead_id)
    logger.info(f"Starting async processing for lead_id: {lead_id}, status_id: {status_id}, pipeline_id: {pipeline_id}")

    if pipeline_id != Config.PIPELINE_ID or status_id not in Config.ALLOWED_STATUS_IDS:
        logger.info(f"Lead {lead_id} is not in pipeline 'Доставка цветов' or not in allowed status: {Config.ALLOWED_STATUS_IDS}")
        return

    # Одна сделка обрабатывается одним воркером за раз: дубли вебхука ждут и видят уже созданный заказ
    with lead_lock(lead_id):
        _process_lead_locked(lead_id)


def _process_lead_locked(lead_id):
    try:
        lead = amocrm_client.get_lead_by_id(lead_id)
        logger.info(f"Lead {lead_id} found: {lead}")

        # Вебхук не проверяемый, поэтому воронку и этап берём из ответа amoCRM, а не из тела вебхука
        if lead.get("pipeline_id") != Config.PIPELINE_ID or lead.get("status_id") not in Config.ALLOWED_STATUS_IDS:
            logger.warning(f"Lead {lead_id}: по данным amoCRM воронка/этап не подходят "
                           f"(pipeline_id={lead.get('pipeline_id')}, status_id={lead.get('status_id')}), пропускаем")
            return

        amount = lead.get("price", 0) * 100
        if amount <= 0:
            logger.warning(f"Lead {lead_id} has no price set")
            return

        entry = load_payments().get(lead_id)
        pending_order = None  # заказ в банке уже есть, но ссылка в сделку ещё не записана

        if entry:
            last = get_orders(entry)[-1]
            if last.get("amount") == amount:
                if entry.get("link_posted", True):
                    logger.info(f"Amounts are the same, skipping processing for lead {lead_id}")
                    return
                pending_order = last
                logger.info(f"Lead {lead_id}: заказ {last['order_number']} создан, но ссылка не записана, дописываем")
            else:
                logger.info(f"Lead {lead_id}: сумма изменилась ({last.get('amount')} -> {amount}), создаём новый заказ. "
                            "Оплата по прежним ссылкам тоже будет засчитана")

        changed = bool(entry) and pending_order is None

        if pending_order is None:
            order_number = generate_order_number(lead_id)
            logger.info(f"Creating payment link for amount: {amount}, order_number: {order_number}")
            payment_response = sbp_client.create_payment_link(amount, order_number)
            if isinstance(payment_response, str):
                payment_response = json.loads(payment_response)
            pending_order = {
                "order_number": order_number,
                "amount": amount,
                "form_url": payment_response.get("formUrl"),
                "order_id": payment_response.get("orderId"),
                "created_at": time.time(),
            }
            # Сохраняем сразу, до записи в amoCRM: если она упадёт, повтор не создаст второй заказ,
            # а оплата по этой ссылке уже отслеживается.
            with payments_lock():
                payments = load_payments()
                add_order(payments, lead_id, pending_order, link_posted=False)
                save_payments(payments)
            logger.info(f"Lead {lead_id}: заказ {order_number} сохранён в payments.json")

        payment_link = pending_order["form_url"]
        order_id = pending_order["order_id"]
        logger.info(f"Updating lead {lead_id} in amoCRM with payment link")
        amocrm_client.update_lead(lead_id, Config.CUSTOM_FIELD_ID, f"{payment_link} (Order ID: {order_id})")

        prefix = "Создана новая ссылка на оплату (сумма изменена)" if changed else "Создана ссылка на оплату"
        amocrm_client.add_note(lead_id, f"{prefix}: {payment_link} (Order ID: {order_id})")

        with payments_lock():
            payments = load_payments()
            if lead_id in payments:
                payments[lead_id]["link_posted"] = True
                save_payments(payments)
        logger.info(f"Lead {lead_id}: ссылка записана в сделку")
    except Exception as e:
        logger.error(f"Error during async processing of lead {lead_id}: {str(e)}")
        raise
