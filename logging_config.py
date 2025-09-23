import logging
import logging.handlers
import os
from datetime import datetime, timedelta

def setup_logging():
    """Настройка логирования с ротацией файлов"""
    
    # Создаем директорию для логов если её нет
    log_dir = "/root/AlfaAmo/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Форматтер для логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Настройка основного логгера
    main_logger = logging.getLogger()
    main_logger.setLevel(logging.INFO)
    
    # Очищаем существующие обработчики
    for handler in main_logger.handlers[:]:
        main_logger.removeHandler(handler)
    
    # Ротация по размеру (10MB) и времени (7 дней)
    webapp_handler = logging.handlers.RotatingFileHandler(
        '/root/AlfaAmo/webapp.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=7,  # Хранить 7 файлов бэкапа
        encoding='utf-8'
    )
    webapp_handler.setFormatter(formatter)
    webapp_handler.setLevel(logging.INFO)
    
    # Ротация callback логов
    callback_handler = logging.handlers.RotatingFileHandler(
        '/root/AlfaAmo/callback.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=7,  # Хранить 7 файлов бэкапа
        encoding='utf-8'
    )
    callback_handler.setFormatter(formatter)
    callback_handler.setLevel(logging.INFO)
    
    # Ротация celery логов
    celery_handler = logging.handlers.RotatingFileHandler(
        '/root/AlfaAmo/celery.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=7,  # Хранить 7 файлов бэкапа
        encoding='utf-8'
    )
    celery_handler.setFormatter(formatter)
    celery_handler.setLevel(logging.INFO)
    
    # Ротация gunicorn логов
    gunicorn_handler = logging.handlers.RotatingFileHandler(
        '/root/AlfaAmo/gunicorn.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=7,  # Хранить 7 файлов бэкапа
        encoding='utf-8'
    )
    gunicorn_handler.setFormatter(formatter)
    gunicorn_handler.setLevel(logging.INFO)
    
    # Ротация okoCRM webhook логов
    oko_webhook_handler = logging.handlers.RotatingFileHandler(
        '/root/AlfaAmo/oko_webhook.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=7,  # Хранить 7 файлов бэкапа
        encoding='utf-8'
    )
    oko_webhook_handler.setFormatter(formatter)
    oko_webhook_handler.setLevel(logging.INFO)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Добавляем обработчики к основному логгеру
    main_logger.addHandler(console_handler)
    
    # Создаем специальные логгеры для разных компонентов
    webapp_logger = logging.getLogger('webapp')
    webapp_logger.addHandler(webapp_handler)
    webapp_logger.setLevel(logging.INFO)
    webapp_logger.propagate = False
    
    callback_logger = logging.getLogger('callback_handler')
    callback_logger.addHandler(callback_handler)
    callback_logger.setLevel(logging.INFO)
    callback_logger.propagate = False
    
    celery_logger = logging.getLogger('celery')
    celery_logger.addHandler(celery_handler)
    celery_logger.setLevel(logging.INFO)
    celery_logger.propagate = False
    
    gunicorn_logger = logging.getLogger('gunicorn')
    gunicorn_logger.addHandler(gunicorn_handler)
    gunicorn_logger.setLevel(logging.INFO)
    gunicorn_logger.propagate = False
    
    oko_webhook_logger = logging.getLogger('oko_webhook')
    oko_webhook_logger.addHandler(oko_webhook_handler)
    oko_webhook_logger.setLevel(logging.INFO)
    oko_webhook_logger.propagate = False
    
    return {
        'webapp': webapp_logger,
        'callback': callback_logger,
        'celery': celery_logger,
        'gunicorn': gunicorn_logger,
        'oko_webhook': oko_webhook_logger
    }

def cleanup_old_logs():
    """Очистка старых лог-файлов старше 7 дней"""
    log_files = [
        '/root/AlfaAmo/webapp.log',
        '/root/AlfaAmo/callback.log', 
        '/root/AlfaAmo/celery.log',
        '/root/AlfaAmo/gunicorn.log'
    ]
    
    cutoff_date = datetime.now() - timedelta(days=7)
    
    for log_file in log_files:
        if os.path.exists(log_file):
            file_time = datetime.fromtimestamp(os.path.getmtime(log_file))
            if file_time < cutoff_date:
                try:
                    os.remove(log_file)
                    print(f"Удален старый лог-файл: {log_file}")
                except Exception as e:
                    print(f"Ошибка при удалении {log_file}: {e}")
    
    # Удаляем старые бэкап файлы
    for log_file in log_files:
        base_name = log_file.replace('.log', '')
        for i in range(1, 10):  # Проверяем файлы .log.1 до .log.9
            backup_file = f"{base_name}.log.{i}"
            if os.path.exists(backup_file):
                file_time = datetime.fromtimestamp(os.path.getmtime(backup_file))
                if file_time < cutoff_date:
                    try:
                        os.remove(backup_file)
                        print(f"Удален старый бэкап: {backup_file}")
                    except Exception as e:
                        print(f"Ошибка при удалении {backup_file}: {e}")

# Инициализация логирования при импорте модуля
loggers = setup_logging() 