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


@contextmanager
def lead_lock(lead_id):
    """Блокировка на одну сделку: дубли вебхука не создают второй заказ параллельно.

    Берётся до payments_lock (обратный порядок запрещён), на время сетевых вызовов.
    """
    with open(f"{PAYMENTS_FILE}.lead-{lead_id}.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


ORDER_FIELDS = ("order_number", "order_id", "amount", "form_url", "created_at")


def get_orders(entry):
    """Все заказы сделки. Старый формат (поля заказа прямо в записи) тоже поддерживается."""
    orders = list(entry.get("orders") or [])
    if entry.get("order_number") and not any(o.get("order_number") == entry["order_number"] for o in orders):
        orders.append({k: entry.get(k) for k in ORDER_FIELDS})
    return orders


def find_lead_by_order(payments, md_order, order_number):
    """Находит сделку по любому из её заказов, не только по последнему."""
    for lead_id, entry in payments.items():
        for order in get_orders(entry):
            if order.get("order_id") == md_order and order.get("order_number") == order_number:
                return lead_id
    return None


def add_order(payments, lead_id, order, link_posted):
    """Добавляет заказ в запись сделки; поля верхнего уровня описывают последний заказ."""
    entry = payments.get(lead_id, {})
    orders = get_orders(entry) + [order]
    payments[lead_id] = {**order, "orders": orders, "link_posted": link_posted}
    return payments[lead_id]
