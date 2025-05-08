import requests
import logging

from config import Config

logger = logging.getLogger(__name__)

class SBPClient:
    def __init__(self):
        self.base_url = "https://payment.alfabank.ru/payment/rest" if not Config.SBP_TEST_ENV else "https://alfa.rbsuat.com/payment/rest"
        self.merchant_login = Config.SBP_MERCHANT_LOGIN
        self.merchant_password = Config.SBP_MERCHANT_PASSWORD
        self.payment_token = Config.SBP_PAYMENT_TOKEN

    def create_payment_link(self, amount, order_number):
        url = f"{self.base_url}/register.do"
        params = {
            "amount": amount,
            "orderNumber": order_number,
            "returnUrl": Config.SBP_RETURN_URL,
            "description": "Payment",
            "language": "ru",
            "pageView": "DESKTOP",
            "callbackUrl": "https://alfa-amocrm.ru/payment_callback"
        }

        if Config.SBP_TEST_ENV:
            # Тестовая среда: используем userName и password
            params["userName"] = self.merchant_login
            params["password"] = self.merchant_password
        else:
            # Продуктивная среда: используем токен
            params["token"] = self.payment_token

        response = requests.post(url, data=params)
        logger.info(f"Create payment link response: {response.status_code}, {response.text}")
        response.raise_for_status()
        response_data = response.json()
        if "errorCode" in response_data:
            error_message = response_data.get("errorMessage", "Unknown error")
            raise Exception(f"Failed to create payment link: {response_data}")
        return response_data