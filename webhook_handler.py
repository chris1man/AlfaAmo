from flask import Flask, request, jsonify
from amocrm_client import AmoCRMClient
from sbp_client import SBPClient
from config import Config
import logging
import time
from functools import wraps

app = Flask(__name__)
app.config["SECRET_KEY"] = Config.FLASK_SECRET_KEY

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация клиентов
amocrm_client = AmoCRMClient()
sbp_client = SBPClient()

# Конфигурация
PIPELINE_ID = Config.PIPELINE_ID
STATUS_ID = Config.STATUS_ID
CUSTOM_FIELD_ID = Config.CUSTOM_FIELD_ID
RETURN_URL = Config.SBP_RETURN_URL

def retry_on_failure(max_attempts=3, base_delay=1):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Попытка {attempt + 1} не удалась: {str(e)}")
                    if attempt < max_attempts - 1:
                        time.sleep(base_delay * 2 ** attempt)  # Экспоненциальная задержка
            raise last_exception
        return wrapper
    return decorator

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    """Обработка вебхука от amoCRM."""
    start_time = time.time()
    try:
        data = request.json
        logger.info(f"Получен вебхук: {data}")
        
        # Валидация данных
        if not data or not isinstance(data, dict):
            raise ValueError("Неверный формат данных")
            
        leads_update = data.get("leads", {}).get("update", [])
        if not leads_update:
            logger.info("Нет обновленных сделок")
            return jsonify({"status": "ignored"}), 200
            
        lead_id = leads_update[0]["id"]
        
        @retry_on_failure()
        def process_lead():
            leads = amocrm_client.get_leads_by_pipeline_status(PIPELINE_ID, STATUS_ID)
            
            for lead in leads:
                if lead["id"] != lead_id:
                    continue
                    
                amount = lead.get("price", 0) * 100  # Конвертация в копейки
                if amount <= 0:
                    logger.warning(f"Бюджет сделки {lead_id} не указан")
                    continue
                    
                order_number = str(lead["id"])
                description = lead.get("name", "Оплата заказа")
                
                result = sbp_client.generate_payment_link(
                    amount=amount,
                    order_number=order_number,
                    description=description,
                    return_url=RETURN_URL
                )
                
                if not result["success"]:
                    logger.error(f"Ошибка генерации ссылки для сделки {lead_id}: {result['error']}")
                    continue
                    
                payment_link = result["payment_link"]
                
                amocrm_client.update_lead(lead_id, CUSTOM_FIELD_ID, payment_link)
                amocrm_client.add_note(lead_id, f"Создана ссылка на оплату: {payment_link}")
                logger.info(f"Сделка {lead_id} обновлена с ссылкой: {payment_link}")
                
        process_lead()
        
        execution_time = time.time() - start_time
        logger.info(f"Вебхук обработан за {execution_time:.2f} секунд")
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)