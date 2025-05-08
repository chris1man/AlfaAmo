from flask import Flask, request, jsonify
import logging
import json
import os
import time
import random
import string
import hmac
import hashlib
import urllib.parse
from config import Config
import requests
from urllib.parse import parse_qs
from amocrm_client import AmoCRMClient
from sbp_client import SBPClient
from tasks import process_lead

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/AlfaAmo/webapp.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

callback_logger = logging.getLogger('callback_handler')
callback_handler = logging.FileHandler('/root/AlfaAmo/callback.log')
callback_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
callback_logger.setLevel(logging.INFO)
callback_logger.addHandler(callback_handler)

amocrm_client = AmoCRMClient()
sbp_client = SBPClient()
PAYMENTS_FILE = "/root/AlfaAmo/payments.json"

CALLBACK_SECRET_KEY = Config.CALLBACK_SECRET_KEY

def load_payments():
    if not os.path.exists(PAYMENTS_FILE):
        logger.info("Payments file does not exist, creating new one")
        save_payments({})
        return {}
    try:
        with open(PAYMENTS_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                logger.info("Payments file is empty, initializing with {}")
                return {}
            return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in payments file: {str(e)}")
        save_payments({})
        return {}
    except Exception as e:
        logger.error(f"Failed to load payments: {str(e)}")
        return {}

def save_payments(payments):
    try:
        with open(PAYMENTS_FILE, "w") as f:
            json.dump(payments, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save payments: {str(e)}")

def clean_old_payments(payments, max_age_seconds=7*24*3600):
    current_time = time.time()
    return {k: v for k, v in payments.items() if current_time - v["created_at"] < max_age_seconds}

def parse_form_data(form_data):
    result = {}
    for key, value in form_data.items():
        parts = key.replace(']', '').split('[')
        current = result
        for part in parts[:-1]:
            if part.isdigit():
                part = int(part)
                if part not in current:
                    current[part] = {}
                current = current[part]
            else:
                if part not in current:
                    current[part] = {}
                current = current[part]
        current[parts[-1]] = value[0] if isinstance(value, list) else value
    return result

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok"}), 200

@app.route("/webhook_test", methods=["POST"])
def webhook_test():
    data = request.get_json(silent=True) or request.form
    logger.info(f"Тестовый вебхук: {json.dumps(data, indent=2)}")
    logger.info(f"Заголовки: {dict(request.headers)}")
    return jsonify({"status": "received"}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    start_time = time.time()
    try:
        content_type = request.headers.get("Content-Type", "")
        logger.info(f"Получен вебхук с Content-Type: {content_type}")
        logger.info(f"Заголовки запроса: {dict(request.headers)}")

        if "application/x-www-form-urlencoded" in content_type:
            form_data = request.form
            logger.info(f"Данные формы: {dict(form_data)}")
            data = parse_form_data(form_data)
            logger.info(f"Декодированные данные: {json.dumps(data, indent=2)}")
        elif "application/json" in content_type:
            data = request.get_json(silent=True)
            if data is None:
                logger.warning("Получен невалидный JSON")
                return jsonify({"status": "invalid_json"}), 200
            logger.info(f"Тело вебхука: {json.dumps(data, indent=2)}")
        else:
            logger.warning(f"Неподдерживаемый Content-Type: {content_type}")
            return jsonify({"status": "ignored_non_json"}), 200

        if not data or "leads" not in data or "status" not in data["leads"]:
            logger.info("Нет обновленных сделок")
            return jsonify({"status": "ignored"})

        if len(data["leads"]["status"]) == 0 or not any(data["leads"]["status"].values()):
            logger.info("Тестовый вебхук, возвращаем быстрый ответ")
            return jsonify({"status": "test_received"}), 200

        status_dict = data["leads"]["status"]
        status_list = list(status_dict.values()) if isinstance(status_dict, dict) else status_dict
        if not isinstance(status_list, list):
            status_list = [status_list]

        for lead_status in status_list:
            lead_id = str(lead_status.get("id"))
            status_id = int(lead_status.get("status_id")) if lead_status.get("status_id") else None
            pipeline_id = int(lead_status.get("pipeline_id")) if lead_status.get("pipeline_id") else None
            logger.info(f"Добавление задачи для сделки с ID: {lead_id}, status_id: {status_id}, pipeline_id: {pipeline_id}")

            # Асинхронно добавляем задачу в очередь
            process_lead.delay(lead_id, status_id, pipeline_id)

        elapsed_time = time.time() - start_time
        logger.info(f"Вебхук обработан за {elapsed_time:.2f} секунд")
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Критическая ошибка в вебхуке: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 200

@app.route("/check_payments", methods=["GET"])
def check_payments():
    payments = clean_old_payments(load_payments())
    updated_payments = payments.copy()

    for lead_id, payment in payments.items():
        order_number = payment["order_number"]
        try:
            status_url = "https://alfa.rbsuat.com/payment/rest/getOrderStatus.do"
            status_params = {
                "userName": Config.SBP_MERCHANT_LOGIN,
                "password": Config.SBP_MERCHANT_PASSWORD,
                "orderNumber": order_number,
                "language": "ru"
            }
            response = requests.get(status_url, params=status_params)
            logger.info(f"Check payment status for {lead_id}: {response.status_code}, {response.text}")
            response.raise_for_status()
            status_data = response.json()

            if status_data.get("orderStatus") == 2:
                logger.info(f"Оплата для сделки {lead_id} успешна")
                amocrm_client.add_tag(lead_id, "оплачено")
                amocrm_client.change_status(lead_id, 54415022)
                del updated_payments[lead_id]
                save_payments(updated_payments)
                logger.info(f"Сделка {lead_id} удалена из payments.json")
        except Exception as e:
            logger.error(f"Ошибка проверки оплаты для сделки {lead_id}: {str(e)}")
            continue

    return jsonify({"status": "checked", "remaining_payments": len(updated_payments)})

@app.route("/payment_callback", methods=["GET"])
def payment_callback():
    callback_logger.info(f"Payment callback received: {request.query_string}")

    params = request.args
    md_order = params.get("mdOrder")
    order_number = params.get("orderNumber")
    operation = params.get("operation")
    status = params.get("status")
    checksum = params.get("checksum")
    sign_alias = params.get("sign_alias")

    callback_logger.info(f"Callback parameters: mdOrder={md_order}, orderNumber={order_number}, operation={operation}, status={status}, checksum={checksum}, sign_alias={sign_alias}")

    if not all([md_order, order_number, status]):
        callback_logger.error("Некорректные данные в callback: отсутствуют обязательные параметры")
        return jsonify({"status": "error", "message": "Missing required parameters"}), 400

    if checksum:
        params_copy = dict(params)
        params_copy.pop("checksum", None)
        params_copy.pop("sign_alias", None)
        sorted_params = sorted(params_copy.items(), key=lambda x: x[0])
        sign_string = ""
        for key, value in sorted_params:
            if "%" in value:
                value = urllib.parse.unquote(value)
            sign_string += f"{key};{value};"
        callback_logger.info(f"Sign string for checksum: {sign_string}")

        computed_checksum = hmac.new(
            CALLBACK_SECRET_KEY.encode('utf-8'),
            sign_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()

        if computed_checksum != checksum:
            callback_logger.error(f"Неверная контрольная сумма: ожидаемая {computed_checksum}, полученная {checksum}")
            return jsonify({"status": "error", "message": "Invalid checksum"}), 400
        callback_logger.info("Контрольная сумма успешно проверена")

    lead_id = None
    payments = load_payments()
    callback_logger.info(f"Current payments: {json.dumps(payments, indent=2)}")

    for lid, payment in payments.items():
        callback_logger.info(f"Checking payment: lead_id={lid}, payment={payment}")
        if payment.get("order_id") == md_order and payment.get("order_number") == order_number:
            lead_id = lid
            break

    if not lead_id:
        callback_logger.warning(f"Не найдена сделка с mdOrder: {md_order} и orderNumber: {order_number}")
        return jsonify({"status": "received"}), 200

    note_text = f"Callback: операция {operation}, статус {status}"
    amocrm_client.add_note(lead_id, note_text)
    callback_logger.info(f"Добавлено примечание к сделке {lead_id}: {note_text}")

    if operation == "deposited" and int(status) == 1:
        lead = amocrm_client.get_lead_by_id(lead_id)
        if lead.get("status_id") == 54415022:
            callback_logger.info(f"Сделка {lead_id} уже обработана ранее (статус 54415022), пропускаем")
            return jsonify({"status": "received"}), 200

        amocrm_client.add_tag(lead_id, "оплачено")
        amocrm_client.change_status(lead_id, 54415022)
        del payments[lead_id]
        save_payments(payments)
        callback_logger.info(f"Сделка {lead_id} обработана по callback: успешная оплата, операция: {operation}")
    elif operation == "declined_timeout":
        amocrm_client.change_status(lead_id, 54415023)
        callback_logger.info(f"Сделка {lead_id} перемещена в колонку 'Оплата не прошла' из-за отклонения по таймауту")
    else:
        callback_logger.info(f"Событие обработано: операция {operation}, статус {status}, примечание добавлено")

    return jsonify({"status": "received"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)