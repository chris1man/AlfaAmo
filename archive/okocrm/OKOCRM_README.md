# okoCRM Интеграция

Система интеграции okoCRM с Альфа-Банком для автоматизации оплаты сделок.

## 🏗️ Архитектура

### Файлы системы:
- `oko_config.py` - конфигурация okoCRM
- `oko_crm_client.py` - клиент для okoCRM API
- `oko_sbp_client.py` - клиент для второго эквайринга
- `oko_tasks.py` - Celery задачи
- `oko_webhook_handler.py` - webhook и callback обработчики
- `multi_system_handler.py` - главный обработчик всех систем
- `oko_payments.json` - файл с данными платежей

### Endpoints:
- `GET /` - статус системы
- `POST /webhook` - webhook от okoCRM
- `GET /payment_callback` - callback от Альфа-Банка

## ⚙️ Конфигурация

### okoCRM настройки:
- Pipeline ID: `19274`
- Trigger Stage ID: `89856` (создание ссылки)
- Paid Stage ID: `92475` (статус после оплаты)
- Custom Field ID: `23824` (поле для ссылки)
- Поле суммы: `budget` (в рублях)

### Эквайринг:
- Токен: <значение убрано, см. переменные окружения>
- Callback токен: <значение убрано, см. переменные окружения>
- Callback URL: `https://alfa-amocrm.ru/payment_callback_oko`

## 🚀 Запуск системы

### 1. Запуск okoCRM webhook handler:
```bash
python3 oko_webhook_handler.py
# Работает на порту 5001
```

### 2. Запуск Celery worker для okoCRM:
```bash
./start_oko_worker.sh
```

### 3. Запуск multi-system handler:
```bash
python3 multi_system_handler.py
# Работает на порту 5000
```

## 🧪 Тестирование

```bash
python3 test_oko_system.py
```

## 📊 Логирование

Все операции логируются в:
- `webapp.log` - основные операции
- `callback.log` - callback операции
- `celery.log` - Celery задачи

## 🔄 Процесс работы

1. **Webhook от okoCRM** → `/webhook`
2. **Проверка условий** → pipeline_id=19274, stages_id=89856
3. **Celery задача** → `process_oko_lead.delay()`
4. **Создание ссылки** → API Альфа-Банка
5. **Обновление сделки** → поле cf_23824
6. **Callback от банка** → `/payment_callback`
7. **Обработка оплаты** → тег "оплачено" + статус 92475

## ⚠️ Важно

- Система работает параллельно с amoCRM
- Не затрагивает существующую функциональность
- Использует отдельные файлы и порты
- Полная обратная совместимость

