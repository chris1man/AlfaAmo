#!/usr/bin/env python3
"""
Скрипт для очистки старых лог-файлов
Запускается автоматически или вручную для удаления логов старше 7 дней
"""

import os
import sys
from datetime import datetime, timedelta
from logging_config import cleanup_old_logs

def main():
    """Основная функция очистки логов"""
    print("Начинаем очистку старых лог-файлов...")
    
    # Очищаем старые логи
    cleanup_old_logs()
    
    # Показываем текущий размер лог-файлов
    log_files = [
        '/root/AlfaAmo/webapp.log',
        '/root/AlfaAmo/callback.log', 
        '/root/AlfaAmo/celery.log',
        '/root/AlfaAmo/gunicorn.log'
    ]
    
    print("\nТекущий размер лог-файлов:")
    total_size = 0
    for log_file in log_files:
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            size_mb = size / (1024 * 1024)
            total_size += size
            print(f"  {os.path.basename(log_file)}: {size_mb:.2f} MB")
        else:
            print(f"  {os.path.basename(log_file)}: не существует")
    
    total_size_mb = total_size / (1024 * 1024)
    print(f"\nОбщий размер логов: {total_size_mb:.2f} MB")
    
    print("\nОчистка завершена!")

if __name__ == "__main__":
    main() 