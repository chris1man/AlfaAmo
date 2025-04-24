import requests
from config import Config
from uuid import uuid4

class SBPClient:
    def generate_payment_link(self, amount, order_number, description, return_url):
        """Генерирует ссылку на оплату через СБП Альфа-Банка."""
        base_url = "https://alfa.rbsuat.com/payment/rest" if Config.SBP_TEST_ENV else "https://alfa.rbs.com/payment/rest"
        register_url = f"{base_url}/register.do"
        
        payload = {
            "userName": Config.SBP_MERCHANT_LOGIN,
            "password": Config.SBP_MERCHANT_PASSWORD,
            "amount": amount,
            "orderNumber": order_number,
            "returnUrl": return_url,
            "description": description,
            "language": "ru",
            "currency": "643",
            "pageView": "DESKTOP"
        }
        
        try:
            response = requests.post(register_url, data=payload)
            response.raise_for_status()
            response_data = response.json()
            
            if "errorCode" in response_data and response_data["errorCode"] != "0":
                return {
                    "success": False,
                    "error": f"Ошибка {response_data['errorCode']}: {response_data.get('errorMessage', 'Неизвестная ошибка')}"
                }
            
            form_url = response_data.get("formUrl")
            order_id = response_data.get("orderId")
            
            if not form_url or not order_id:
                return {
                    "success": False,
                    "error": "Не удалось получить formUrl или orderId"
                }
            
            return {
                "success": True,
                "payment_link": form_url,
                "order_id": order_id
            }
        
        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"Ошибка HTTP-запроса: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Неизвестная ошибка: {str(e)}"
            }