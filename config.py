from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    # amoCRM
    AMOCRM_CLIENT_ID = os.getenv("AMOCRM_CLIENT_ID")
    AMOCRM_CLIENT_SECRET = os.getenv("AMOCRM_CLIENT_SECRET")
    AMOCRM_REDIRECT_URI = os.getenv("AMOCRM_REDIRECT_URI")
    AMOCRM_ACCESS_TOKEN = os.getenv("AMOCRM_ACCESS_TOKEN")
    AMOCRM_DOMAIN = os.getenv("AMOCRM_DOMAIN")

    # Alfa-Bank SBP
    SBP_MERCHANT_LOGIN = os.getenv("SBP_MERCHANT_LOGIN")
    SBP_MERCHANT_PASSWORD = os.getenv("SBP_MERCHANT_PASSWORD")
    SBP_TEST_ENV = os.getenv("SBP_TEST_ENV", "true").lower() == "true"

    # Flask
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")