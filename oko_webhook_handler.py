from flask import Flask, request, jsonify
import logging
import json
import time
import hmac
import hashlib
import urllib.parse
from oko_config import OkoConfig
from oko_crm_client import OkoCRMClient
from oko_sbp_client import OkoSBPClient
from oko_tasks import process_oko_lead
from logging_config import loggers

app = Flask(__name__)

# Используем настроенные логгеры
logger = loggers['webapp']
callback_logger = loggers['callback']
webhook_logger = loggers['oko_webhook']

oko_crm_client = OkoCRMClient()
oko_sbp_client = OkoSBPClient()
OKO_PAYMENTS_FILE = "/root/AlfaAmo/oko_payments.json"

CALLBACK_SECRET_KEY = OkoConfig.SBP2_CALLBACK_TOKEN

def load_oko_payments():
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
    try:
        with open(OKO_PAYMENTS_FILE, "w") as f:
            json.dump(payments, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save oko payments: {str(e)}")

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "system": "okoCRM"}), 200

@app.route("/webhook", methods=["POST"])
def oko_webhook():
    start_time = time.time()
    
    # Логируем входящий запрос
    webhook_logger.info("=" * 50)
    webhook_logger.info("NEW OKOCRM WEBHOOK RECEIVED")
    webhook_logger.info(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    webhook_logger.info(f"Method: {request.method}")
    webhook_logger.info(f"Headers: {dict(request.headers)}")
    webhook_logger.info(f"Remote IP: {request.remote_addr}")
    webhook_logger.info(f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
    
    try:
        data = request.get_json(silent=True)
        if data is None:
            webhook_logger.warning("Получен невалидный JSON от okoCRM")
            webhook_logger.warning(f"Raw data: {request.get_data()}")
            return jsonify({"status": "invalid_json"}), 200

        webhook_logger.info(f"OkoCRM webhook data: {json.dumps(data, indent=2, ensure_ascii=False)}")

        # Проверяем, что это обновление сделки
        if not data or "id" not in data:
            webhook_logger.info("Нет данных о сделке в webhook")
            return jsonify({"status": "ignored"})

        lead_id = str(data.get("id"))
        stage_id = data.get("stages_id")
        pipeline_id = data.get("pipeline_id")

        webhook_logger.info(f"Parsed data - Lead ID: {lead_id}, Stage ID: {stage_id}, Pipeline ID: {pipeline_id}")

        # Проверяем, нужно ли создавать ссылку на оплату
        if pipeline_id == OkoConfig.OKOCRM_PIPELINE_ID and stage_id == OkoConfig.OKOCRM_TRIGGER_STAGE_ID:
            webhook_logger.info(f"✅ CONDITIONS MET - Adding task for oko lead: {lead_id}")
            webhook_logger.info(f"Expected pipeline: {OkoConfig.OKOCRM_PIPELINE_ID}, got: {pipeline_id}")
            webhook_logger.info(f"Expected stage: {OkoConfig.OKOCRM_TRIGGER_STAGE_ID}, got: {stage_id}")
            
            try:
                result = process_oko_lead.delay(lead_id, stage_id, pipeline_id)
                webhook_logger.info(f"✅ Task submitted successfully: {result.id}")
            except Exception as task_error:
                webhook_logger.error(f"❌ Error submitting task: {str(task_error)}")
        else:
            webhook_logger.info(f"❌ CONDITIONS NOT MET - Oko lead {lead_id} is not in correct pipeline/stage")
            webhook_logger.info(f"Expected pipeline: {OkoConfig.OKOCRM_PIPELINE_ID}, got: {pipeline_id}")
            webhook_logger.info(f"Expected stage: {OkoConfig.OKOCRM_TRIGGER_STAGE_ID}, got: {stage_id}")

        elapsed_time = time.time() - start_time
        webhook_logger.info(f"OkoCRM webhook processed in {elapsed_time:.2f} seconds")
        webhook_logger.info("=" * 50)
        return jsonify({"status": "success"})
    except Exception as e:
        webhook_logger.error(f"❌ CRITICAL ERROR in okoCRM webhook: {str(e)}")
        webhook_logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        webhook_logger.error(f"Traceback: {traceback.format_exc()}")
        webhook_logger.info("=" * 50)
        return jsonify({"status": "error", "message": str(e)}), 200

@app.route("/payment_callback", methods=["GET"])
def oko_payment_callback():
    callback_logger.info(f"OkoCRM payment callback received: {request.query_string}")

    params = request.args
    md_order = params.get("mdOrder")
    order_number = params.get("orderNumber")
    operation = params.get("operation")
    status = params.get("status")
    checksum = params.get("checksum")

    callback_logger.info(f"OkoCRM callback parameters: mdOrder={md_order}, orderNumber={order_number}, operation={operation}, status={status}, checksum={checksum}")

    if not all([md_order, order_number, status]):
        callback_logger.error("Некорректные данные в okoCRM callback: отсутствуют обязательные параметры")
        return jsonify({"status": "error", "message": "Missing required parameters"}), 400

    # Проверка контрольной суммы
    if checksum:
        params_copy = dict(params)
        params_copy.pop("checksum", None)
        sorted_params = sorted(params_copy.items(), key=lambda x: x[0])
        sign_string = ""
        for key, value in sorted_params:
            if "%" in value:
                value = urllib.parse.unquote(value)
            sign_string += f"{key};{value};"
        callback_logger.info(f"Sign string for okoCRM checksum: {sign_string}")

        computed_checksum = hmac.new(
            CALLBACK_SECRET_KEY.encode('utf-8'),
            sign_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()

        if computed_checksum != checksum:
            callback_logger.error(f"Неверная контрольная сумма в okoCRM callback: ожидаемая {computed_checksum}, полученная {checksum}")
            return jsonify({"status": "error", "message": "Invalid checksum"}), 400
        callback_logger.info("Контрольная сумма okoCRM успешно проверена")

    # Поиск сделки по order_id
    lead_id = None
    payments = load_oko_payments()
    callback_logger.info(f"Current oko payments: {json.dumps(payments, indent=2)}")

    for lid, payment in payments.items():
        callback_logger.info(f"Checking oko payment: lead_id={lid}, payment={payment}")
        if payment.get("order_id") == md_order and payment.get("order_number") == order_number:
            lead_id = lid
            break

    if not lead_id:
        callback_logger.warning(f"Не найдена okoCRM сделка с mdOrder: {md_order} и orderNumber: {order_number}")
        return jsonify({"status": "received"}), 200

    note_text = f"Callback: операция {operation}, статус {status}"
    oko_crm_client.add_note(lead_id, note_text)
    callback_logger.info(f"Добавлено примечание к okoCRM сделке {lead_id}: {note_text}")

    if operation == "deposited" and int(status) == 1:
        # Проверяем, не обработана ли уже сделка
        lead = oko_crm_client.get_lead_by_id(lead_id)
        if lead.get("stages_id") == OkoConfig.OKOCRM_PAID_STAGE_ID:
            callback_logger.info(f"OkoCRM сделка {lead_id} уже обработана ранее, пропускаем")
            return jsonify({"status": "received"}), 200

        oko_crm_client.add_tag(lead_id, "оплачено")
        oko_crm_client.change_status(lead_id, OkoConfig.OKOCRM_PAID_STAGE_ID)
        del payments[lead_id]
        save_oko_payments(payments)
        callback_logger.info(f"OkoCRM сделка {lead_id} обработана по callback: успешная оплата")
    else:
        callback_logger.info(f"OkoCRM событие обработано: операция {operation}, статус {status}")

    return jsonify({"status": "received"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
