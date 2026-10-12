from dotenv import load_dotenv
import os

load_dotenv()

class OkoConfig:
    # okoCRM настройки
    OKOCRM_ACCESS_TOKEN = os.getenv("OKOCRM_ACCESS_TOKEN")
    OKOCRM_PIPELINE_ID = 19274
    OKOCRM_TRIGGER_STAGE_ID = 89856
    OKOCRM_PAID_STAGE_ID = 92475
    OKOCRM_CUSTOM_FIELD_ID = 23824
    
    # Второй эквайринг для okoCRM
    SBP2_PAYMENT_TOKEN = os.getenv("SBP2_PAYMENT_TOKEN")
    SBP2_CALLBACK_TOKEN = os.getenv("SBP2_CALLBACK_TOKEN")
    SBP2_RETURN_URL = os.getenv("SBP2_RETURN_URL")
    SBP2_CALLBACK_URL = os.getenv("SBP2_CALLBACK_URL")
    SBP2_TEST_ENV = False  # Измените на False для продакшена
    
    @staticmethod
    def validate():
        """Проверка наличия обязательных переменных"""
        required_vars = [
            "OKOCRM_ACCESS_TOKEN", "OKOCRM_PIPELINE_ID", 
            "OKOCRM_TRIGGER_STAGE_ID", "OKOCRM_PAID_STAGE_ID",
            "OKOCRM_CUSTOM_FIELD_ID", "SBP2_PAYMENT_TOKEN",
            "SBP2_CALLBACK_TOKEN"
        ]
        missing = [var for var in required_vars if not getattr(OkoConfig, var)]
        if missing:
            raise ValueError(f"Отсутствуют обязательные переменные: {', '.join(missing)}")

# Проверка конфигурации при загрузке модуля
OkoConfig.validate()

