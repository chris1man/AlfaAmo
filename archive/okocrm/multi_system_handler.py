from flask import Flask, request, jsonify
from webhook_handler import app as amocrm_app
from oko_webhook_handler import app as okocrm_app
import logging

# Создаем главное приложение
app = Flask(__name__)

# Регистрируем существующие маршруты amoCRM
app.register_blueprint(amocrm_app, url_prefix='/amocrm')

# Регистрируем новые маршруты okoCRM  
app.register_blueprint(okocrm_app, url_prefix='/okocrm')

# Главная страница
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "ok",
        "systems": {
            "amocrm": "active",
            "okocrm": "active"
        },
        "endpoints": {
            "amocrm_webhook": "/amocrm/webhook",
            "amocrm_callback": "/amocrm/payment_callback",
            "okocrm_webhook": "/okocrm/webhook", 
            "okocrm_callback": "/okocrm/payment_callback"
        }
    }), 200

# Маршруты для обратной совместимости amoCRM
@app.route("/webhook", methods=["POST"])
def webhook_amocrm_legacy():
    """Обратная совместимость для существующих webhook'ов amoCRM"""
    return amocrm_app.handle_request()

@app.route("/payment_callback", methods=["GET"])
def payment_callback_amocrm_legacy():
    """Обратная совместимость для существующих callback'ов amoCRM"""
    return amocrm_app.handle_request()

# Новые маршруты для okoCRM
@app.route("/webhook_okocrm", methods=["POST"])
def webhook_okocrm():
    """Webhook для okoCRM"""
    return okocrm_app.handle_request()

@app.route("/payment_callback_oko", methods=["GET"])
def payment_callback_oko():
    """Callback для okoCRM"""
    return okocrm_app.handle_request()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

