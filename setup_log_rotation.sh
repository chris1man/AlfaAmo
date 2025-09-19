#!/bin/bash

# Скрипт для настройки автоматической ротации логов

echo "Настройка автоматической ротации логов..."

# Делаем скрипт очистки исполняемым
chmod +x /root/AlfaAmo/cleanup_logs.py

# Создаем cron-задачу для ежедневной очистки логов в 2:00
(crontab -l 2>/dev/null; echo "0 2 * * * /root/AlfaAmo/venv/bin/python /root/AlfaAmo/cleanup_logs.py >> /root/AlfaAmo/log_cleanup.log 2>&1") | crontab -

# Создаем cron-задачу для еженедельной очистки старых бэкапов в воскресенье в 3:00
(crontab -l 2>/dev/null; echo "0 3 * * 0 /root/AlfaAmo/venv/bin/python -c 'from logging_config import cleanup_old_logs; cleanup_old_logs()' >> /root/AlfaAmo/log_cleanup.log 2>&1") | crontab -

echo "Cron-задачи добавлены:"
echo "  - Ежедневная очистка логов в 2:00"
echo "  - Еженедельная очистка старых бэкапов в воскресенье в 3:00"

# Показываем текущие cron-задачи
echo ""
echo "Текущие cron-задачи:"
crontab -l

echo ""
echo "Настройка завершена!" 