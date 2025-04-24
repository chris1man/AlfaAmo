from flask import Flask, request, jsonify
from amocrm_client import AmoCRMClient
from sbp_client import SBPClient
from config import Config
import logging

app = Flask(__name__)
app.config["SECRET_KEY"] = Config.FLASK_SECRET_KEY

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация клиентов
amocrm_client = AmoCRMClient()
sbp_client = SBPClient()

# Настройки amoCRM (замените на ваши значения)
PIPELINE_ID = 123456  # ID воронки
STATUS_ID = 789012    # ID стадии
CUSTOM_FIELD_ID = 345678  # ID пользовательского поля для ссылки
RETURN_URL = "https://example.com/success"

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    """Обработка вебхука от amoCRM."""
    try:
        data = request.json
        logger.info(f"Получен вебхук: {data}")
        
        # Проверка, что это событие обновления сделки
        if not data.get("leads"):
            return jsonify({"status": "ignored"}), 200
        
        lead_id = data["leads"]["update"][0]["id"]
        leads = amocrm_client.get_leads_by_pipeline_status(PIPELINE_ID, STATUS_ID)
        
        for lead in leads:
            if lead["id"] != lead_id:
                continue
                
            # Получение бюджета сделки
            amount = lead.get("price", 0) * 100  # Конвертация в копейки
            if amount <= 0:
                logger.warning(f"Бюджет сделки {lead_id} не указан")
                continue
                
            order_number = str(lead["id"])
            description = lead.get("name", "Оплата заказа")
            
            # Генерация ссылки на оплату
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
            
            # Обновление сделки
            amocrm_client.update_lead(lead_id, CUSTOM_FIELD_ID, payment_link)
            amocrm_client.add_note(lead_id, f"Создана ссылка на оплату: {payment_link}")
            logger.info(f"Сделка {lead_id} обновлена с ссылкой: {payment_link}")
        
        return jsonify({"status": "success"}), 200
    
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)