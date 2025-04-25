from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    # Flask
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
    
    # amoCRM
    AMOCRM_CLIENT_ID = os.getenv("AMOCRM_CLIENT_ID")
    AMOCRM_CLIENT_SECRET = os.getenv("AMOCRM_CLIENT_SECRET")
    AMOCRM_REDIRECT_URI = os.getenv("AMOCRM_REDIRECT_URI")
    AMOCRM_ACCESS_TOKEN = os.getenv("AMOCRM_ACCESS_TOKEN")
    AMOCRM_DOMAIN = os.getenv("AMOCRM_DOMAIN")
    AMOCRM_ACCOUNT_ID = os.getenv("AMOCRM_ACCOUNT_ID")
    PIPELINE_ID = int(os.getenv("AMO_PIPELINE_ID"))
    STATUS_ID = int(os.getenv("AMO_STATUS_ID"))
    CUSTOM_FIELD_ID = int(os.getenv("AMO_CUSTOM_FIELD_ID"))
    
    # Alfa-Bank SBP
    SBP_MERCHANT_LOGIN = os.getenv("SBP_MERCHANT_LOGIN")
    SBP_MERCHANT_PASSWORD = os.getenv("SBP_MERCHANT_PASSWORD")
    SBP_TEST_ENV = os.getenv("SBP_TEST_ENV", "true").lower() == "true"
    SBP_RETURN_URL = os.getenv("SBP_RETURN_URL")

    @staticmethod
    def validate():
        """Проверка наличия обязательных переменных окружения."""
        required_vars = [
            "FLASK_SECRET_KEY", "AMOCRM_CLIENT_ID", "AMOCRM_CLIENT_SECRET",
            "AMOCRM_REDIRECT_URI", "AMOCRM_ACCESS_TOKEN", "AMOCRM_DOMAIN",
            "AMOCRM_ACCOUNT_ID", "AMO_PIPELINE_ID", "AMO_STATUS_ID",
            "AMO_CUSTOM_FIELD_ID", "SBP_MERCHANT_LOGIN", "SBP_MERCHANT_PASSWORD",
            "SBP_RETURN_URL"
        ]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Отсутствуют обязательные переменные окружения: {', '.join(missing)}")

# Проверка конфигурации при загрузке модуля
Config.validate()