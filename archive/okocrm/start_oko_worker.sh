#!/bin/bash
# Скрипт для запуска Celery worker для okoCRM

echo "Запуск Celery worker для okoCRM..."

# Активируем виртуальное окружение если есть
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Виртуальное окружение активировано"
fi

# Запускаем Celery worker для okoCRM задач
celery -A oko_tasks worker --loglevel=info --concurrency=2

echo "Celery worker для okoCRM запущен"

