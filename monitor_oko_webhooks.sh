#!/bin/bash
# Скрипт для мониторинга webhook'ов okoCRM в реальном времени

echo "🔍 Мониторинг webhook'ов okoCRM..."
echo "📁 Лог файл: /root/AlfaAmo/oko_webhook.log"
echo "⏹️  Для остановки нажмите Ctrl+C"
echo "=" * 50

# Проверяем, существует ли файл лога
if [ ! -f "/root/AlfaAmo/oko_webhook.log" ]; then
    echo "⚠️  Файл лога не найден. Создаем пустой файл..."
    touch /root/AlfaAmo/oko_webhook.log
fi

# Показываем последние 20 строк и затем следим за изменениями
echo "📋 Последние записи:"
tail -20 /root/AlfaAmo/oko_webhook.log
echo ""
echo "👀 Ожидание новых webhook'ов..."
echo ""

# Следим за изменениями файла в реальном времени
tail -f /root/AlfaAmo/oko_webhook.log

