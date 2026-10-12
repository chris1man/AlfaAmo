import requests
import logging
from oko_config import OkoConfig

logger = logging.getLogger(__name__)

class OkoSBPClient:
    def __init__(self):
        self.base_url = "https://payment.alfabank.ru/payment/rest" if not OkoConfig.SBP2_TEST_ENV else "https://alfa.rbsuat.com/payment/rest"
        self.payment_token = OkoConfig.SBP2_PAYMENT_TOKEN

    def create_payment_link(self, amount, order_number):
        url = f"{self.base_url}/register.do"
        params = {
            "amount": amount,
            "orderNumber": order_number,
            "returnUrl": OkoConfig.SBP2_RETURN_URL,
            "description": "Payment",
            "language": "ru",
            "pageView": "DESKTOP",
            "callbackUrl": OkoConfig.SBP2_CALLBACK_URL,
            "sessionTimeoutSecs": 86400,  # 24 часа
            "token": self.payment_token
        }

        response = requests.post(url, data=params)
        logger.info(f"Create payment link response: {response.status_code}, {response.text}")
        response.raise_for_status()
        response_data = response.json()
        if "errorCode" in response_data:
            error_message = response_data.get("errorMessage", "Unknown error")
            raise Exception(f"Failed to create payment link: {response_data}")
        return response_data

