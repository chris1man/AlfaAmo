import fcntl
import json
import logging
import os
import tempfile
from contextlib import contextmanager

logger = logging.getLogger(__name__)

PAYMENTS_FILE = "/root/AlfaAmo/payments.json"
LOCK_FILE = PAYMENTS_FILE + ".lock"


@contextmanager
def payments_lock():
    """Межпроцессная блокировка для цикла load -> изменить -> save.

    Не вкладывать: повторный flock из того же процесса на другом дескрипторе заблокируется.
    """
    with open(LOCK_FILE, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def load_payments():
    """Читает payments.json. Нет файла или он пуст -> {}.

    Битый JSON не затираем: пробрасываем ошибку, чтобы не потерять активные заказы.
    """
    if not os.path.exists(PAYMENTS_FILE):
        return {}
    with open(PAYMENTS_FILE, "r") as f:
        content = f.read().strip()
    if not content:
        return {}
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in {PAYMENTS_FILE}, файл не изменён")
        raise


def save_payments(payments):
    """Атомарная запись: во временный файл рядом и os.replace."""
    directory = os.path.dirname(PAYMENTS_FILE) or "."
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".payments.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payments, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, PAYMENTS_FILE)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
