#!/usr/bin/env python3
"""
Скрипт для тестирования системы okoCRM
"""

import requests
import json
import time

# URL для тестирования
BASE_URL = "http://localhost:5001"  # okoCRM работает на порту 5001

def test_oko_webhook():
    """Тестирование webhook'а okoCRM"""
    print("🧪 Тестирование okoCRM webhook...")
    
    # Тестовые данные webhook'а
    test_data = {
        "id": 1777448,
        "name": "4430",
        "pipeline_id": 19274,
        "stages_id": 89856,
        "user_id": 9867,
        "budget": "4050",
        "created_at": 1758193624,
        "updated_at": 1758196434,
        "cf_23294": "2024-10-19",
        "cf_23295": "13:00-14:00",
        "cf_23296": "Пять пять пять",
        "cf_23297": "Друг",
        "cf_23298": "+78888888888",
        "cf_23824": "https://111",
        "url": "https://mafia.okocrm.com/leads/19274#lead-1777448"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/webhook", json=test_data)
        print(f"✅ Webhook response: {response.status_code}")
        print(f"📄 Response body: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка при тестировании webhook: {e}")
        return False

def test_oko_status():
    """Тестирование статуса системы"""
    print("🧪 Тестирование статуса okoCRM...")
    
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ Status response: {response.status_code}")
        print(f"📄 Response body: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка при тестировании статуса: {e}")
        return False

def test_oko_callback():
    """Тестирование callback'а (симуляция)"""
    print("🧪 Тестирование okoCRM callback...")
    
    # Тестовые параметры callback'а
    callback_params = {
        "mdOrder": "test-order-123",
        "orderNumber": "OKO_1777448_A123",
        "operation": "deposited",
        "status": "1",
        "checksum": "test-checksum"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/payment_callback", params=callback_params)
        print(f"✅ Callback response: {response.status_code}")
        print(f"📄 Response body: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка при тестировании callback: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Начинаем тестирование системы okoCRM")
    print("=" * 50)
    
    # Тест 1: Статус системы
    status_ok = test_oko_status()
    print()
    
    # Тест 2: Webhook
    webhook_ok = test_oko_webhook()
    print()
    
    # Тест 3: Callback
    callback_ok = test_oko_callback()
    print()
    
    # Результаты
    print("=" * 50)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"✅ Статус системы: {'PASS' if status_ok else 'FAIL'}")
    print(f"✅ Webhook: {'PASS' if webhook_ok else 'FAIL'}")
    print(f"✅ Callback: {'PASS' if callback_ok else 'FAIL'}")
    
    if all([status_ok, webhook_ok, callback_ok]):
        print("🎉 Все тесты прошли успешно!")
    else:
        print("⚠️  Некоторые тесты не прошли. Проверьте логи.")

if __name__ == "__main__":
    main()

