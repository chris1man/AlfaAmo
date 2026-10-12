#!/usr/bin/env python3
"""
Скрипт для отправки тестовых webhook'ов в okoCRM систему
"""

import requests
import json
import time

# Конфигурация
WEBHOOK_URL = "http://localhost:5001/webhook"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "okoCRM-Webhook-Test/1.0"
}

def send_test_webhook():
    """Отправляет тестовый webhook"""
    
    # Тестовые данные webhook'а
    test_data = {
        "id": 1777448,
        "name": "Тестовая сделка",
        "pipeline_id": 19274,
        "stages_id": 89856,
        "user_id": 9867,
        "budget": "1000",
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
        "cf_23294": "2024-10-19",
        "cf_23295": "13:00-14:00",
        "cf_23296": "Тестовый адрес",
        "cf_23297": "Тестовый получатель",
        "cf_23298": "+79999999999",
        "cf_23824": "https://test-link.com",
        "url": "https://mafia.okocrm.com/leads/19274#lead-1777448"
    }
    
    print("🚀 Отправка тестового webhook'а...")
    print(f"📡 URL: {WEBHOOK_URL}")
    print(f"📄 Данные: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
    print("-" * 50)
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            headers=HEADERS,
            json=test_data,
            timeout=10
        )
        
        print(f"✅ Ответ сервера: {response.status_code}")
        print(f"📄 Тело ответа: {response.text}")
        
        if response.status_code == 200:
            print("🎉 Webhook успешно отправлен!")
        else:
            print("⚠️  Webhook отправлен, но с ошибкой")
            
    except requests.exceptions.ConnectionError:
        print("❌ Ошибка подключения. Проверьте, что сервер запущен на порту 5001")
    except requests.exceptions.Timeout:
        print("❌ Таймаут запроса")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def send_wrong_pipeline_webhook():
    """Отправляет webhook с неправильным pipeline (для тестирования фильтрации)"""
    
    test_data = {
        "id": 999999,
        "name": "Тестовая сделка (неправильный pipeline)",
        "pipeline_id": 99999,  # Неправильный pipeline
        "stages_id": 89856,
        "user_id": 9867,
        "budget": "500",
        "created_at": int(time.time()),
        "updated_at": int(time.time())
    }
    
    print("🚀 Отправка webhook'а с неправильным pipeline...")
    print(f"📡 URL: {WEBHOOK_URL}")
    print(f"📄 Данные: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
    print("-" * 50)
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            headers=HEADERS,
            json=test_data,
            timeout=10
        )
        
        print(f"✅ Ответ сервера: {response.status_code}")
        print(f"📄 Тело ответа: {response.text}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def main():
    """Главная функция"""
    print("🧪 ТЕСТИРОВАНИЕ WEBHOOK'ОВ OKOCRM")
    print("=" * 50)
    
    while True:
        print("\nВыберите действие:")
        print("1. Отправить правильный webhook")
        print("2. Отправить webhook с неправильным pipeline")
        print("3. Выход")
        
        choice = input("\nВведите номер (1-3): ").strip()
        
        if choice == "1":
            send_test_webhook()
        elif choice == "2":
            send_wrong_pipeline_webhook()
        elif choice == "3":
            print("👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор. Попробуйте снова.")

if __name__ == "__main__":
    main()

