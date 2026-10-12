# AlfaAmo

Проект для интеграции amoCRM и Альфа-Банка для автоматизации оплаты сделок.

## Описание

Этот проект позволяет:
- Обрабатывать вебхуки от amoCRM для создания ссылок на оплату через Альфа-Банк.
- Принимать callback-уведомления от Альфа-Банка о статусе платежей.
- Асинхронно обрабатывать задачи с помощью Celery и RabbitMQ.
- Автоматически управлять логами с ротацией и очисткой.

## Установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/yourusername/AlfaAmo.git
   cd AlfaAmo
   ```

## Настройка

Переменные окружения (файл `.env`, в git не попадает):

| Переменная | Назначение |
|---|---|
| `AMOCRM_*`, `AMO_PIPELINE_ID`, `AMO_ALLOWED_STATUS_IDS`, `AMO_CUSTOM_FIELD_ID` | доступ к amoCRM, воронка, этапы запуска и поле со ссылкой |
| `AMO_STATUS_PAID`, `AMO_STATUS_PAYMENT_FAILED` | этапы «оплачено» и «оплата не прошла» (по умолчанию 54415022 и 54415023) |
| `SBP_MERCHANT_LOGIN`, `SBP_MERCHANT_PASSWORD`, `SBP_PAYMENT_TOKEN`, `SBP_RETURN_URL` | реквизиты Альфа-Банка |
| `SBP_TEST_ENV` | обязательно `true` (тестовый стенд) или `false` (бой) |
| `CALLBACK_SECRET_KEY` | ключ проверки подписи колбэка банка |
| `CHECK_PAYMENTS_TOKEN` | секрет для `/check_payments` (заголовок `X-Check-Token`); без него эндпоинт доступен только с localhost |
| `PAYMENTS_FILE` | путь к `payments.json` (по умолчанию `/root/AlfaAmo/payments.json`) |

## Как это работает

1. amoCRM присылает вебхук `/webhook` при смене этапа, задача `process_lead` (Celery) создаёт заказ в банке и записывает ссылку в сделку.
2. Банк вызывает `/payment_callback` (подпись обязательна). При успехе сделка получает тег «оплачено» и переходит на этап оплаты, при отказе на этап «оплата не прошла».
3. Заказы сделки хранятся в `payments.json`; оплата по любой из выданных ссылок засчитывается. `/check_payments` опрашивает банк по тем же заказам.

Интеграция okoCRM больше не используется и лежит в `archive/okocrm/`.

## Тесты

```bash
pip install -r requirements.txt   # нужен Python 3.10+
python3 -m unittest discover -s tests -v
```

## Управление логами

Логи пишутся с ротацией (10 МБ, 7 копий). Ручная очистка и настройка автоочистки:

```bash
python3 cleanup_logs.py
./setup_log_rotation.sh
```
