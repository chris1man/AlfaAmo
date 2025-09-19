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

## Управление логами

Система автоматически управляет логами с ограничениями:
- **Максимальный размер файла**: 10 MB
- **Время хранения**: 7 дней
- **Автоматическая очистка**: ежедневно в 2:00

Подробная документация: [docs/logs/](docs/logs/)

**📁 Структура документации:**
- [docs/logs/README.md](docs/logs/README.md) - Главная страница документации по логам
- [docs/logs/LOG_SUMMARY.md](docs/logs/LOG_SUMMARY.md) - Краткая сводка
- [docs/logs/LOG_FILES_DESCRIPTION.md](docs/logs/LOG_FILES_DESCRIPTION.md) - Подробное описание
- [docs/logs/LOG_MANAGEMENT.md](docs/logs/LOG_MANAGEMENT.md) - Управление логами
- [docs/logs/CLEANUP_INSTRUCTIONS.md](docs/logs/CLEANUP_INSTRUCTIONS.md) - Инструкции по очистке
- [docs/logs/TERMINAL_TROUBLESHOOTING.md](docs/logs/TERMINAL_TROUBLESHOOTING.md) - Решение проблем с терминалом

### Быстрые команды

```bash
# Просмотр размера логов
ls -lh *.log

# Ручная очистка логов
python3 cleanup_logs.py

# Настройка автоматической очистки
./setup_log_rotation.sh

# Тестирование ротации логов
python3 test_log_rotation.py
```
