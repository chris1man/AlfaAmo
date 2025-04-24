Интеграция amoCRM с СБП Альфа-Банка
Описание
Проект интегрирует amoCRM с СБП Альфа-Банка для автоматической генерации ссылок на оплату. При обновлении сделки в определённой стадии воронки создаётся ссылка на оплату, которая сохраняется в пользовательском поле и добавляется как примечание.
Установка

Клонируйте репозиторий:git clone <your-repo-url>
cd sbp_amocrm_integration


Установите зависимости:pip install -r requirements.txt


Создайте файл .env на основе .env.example и заполните его:
AMOCRM_*: Данные интеграции amoCRM (получите в настройках).
SBP_*: Логин и пароль мерчанта Альфа-Банка.
FLASK_SECRET_KEY: Случайная строка для Flask.


Настройте вебхук в amoCRM:
URL: https://<your-domain>/webhook
Событие: Обновление сделки.



Запуск локально
python webhook_handler.py

Деплой на Render

Создайте аккаунт на Render.
Создайте новый Web Service, выбрав ваш репозиторий.
Настройки:
Environment: Python
Build Command: pip install -r requirements.txt
Start Command: gunicorn webhook_handler:app


Добавьте переменные окружения в настройках сервиса (из .env).
Разверните приложение и получите URL для вебхука.

Деплой на Heroku

Создайте аккаунт на Heroku.
Установите Heroku CLI и выполните:heroku create
git push heroku main


Добавьте переменные окружения:heroku config:set AMOCRM_CLIENT_ID=your_value


Настройте вебхук в amoCRM.

Настройки amoCRM

PIPELINE_ID: ID воронки (см. API или интерфейс).
STATUS_ID: ID стадии (см. API или интерфейс).
CUSTOM_FIELD_ID: ID пользовательского поля для ссылки (создайте в amoCRM).

Замечания

Используйте тестовую среду СБП (SBP_TEST_ENV=true) для отладки.
В тестовой среде СБП результат оплаты зависит от суммы: < 500 руб. — успешно, > 500 руб. — неуспешно.
Храните .env в безопасном месте и не добавляйте в Git.

