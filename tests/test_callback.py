"""Тесты колбэка Альфа-Банка и хранилища payments.json (без сети и без /root/AlfaAmo)."""
import hashlib
import hmac
import json
import logging
import logging.handlers
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SECRET = "test-secret"
os.environ.update({
    "FLASK_SECRET_KEY": "x", "AMOCRM_CLIENT_ID": "x", "AMOCRM_CLIENT_SECRET": "x",
    "AMOCRM_REDIRECT_URI": "x", "AMOCRM_ACCESS_TOKEN": "x", "AMOCRM_DOMAIN": "example.amocrm.ru",
    "AMOCRM_ACCOUNT_ID": "1", "AMO_PIPELINE_ID": "1", "AMO_STATUS_ID": "1",
    "AMO_ALLOWED_STATUS_IDS": "1", "AMO_CUSTOM_FIELD_ID": "1", "SBP_MERCHANT_LOGIN": "x",
    "SBP_MERCHANT_PASSWORD": "x", "SBP_RETURN_URL": "x", "CALLBACK_SECRET_KEY": SECRET,
    "SBP_TEST_ENV": "true",
})

# logging_config при импорте создаёт файлы в /root/AlfaAmo: подставляем заглушки
with mock.patch.object(logging.handlers, "RotatingFileHandler", lambda *a, **k: logging.NullHandler()), \
        mock.patch("os.makedirs"):
    import webhook_handler  # noqa: E402
import payments_store  # noqa: E402


def signed(params):
    sign = "".join(f"{k};{v};" for k, v in sorted(params.items()))
    checksum = hmac.new(SECRET.encode(), sign.encode(), hashlib.sha256).hexdigest().upper()
    return {**params, "checksum": checksum}


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        path = os.path.join(self.dir, "payments.json")
        self.patches = [
            mock.patch.object(payments_store, "PAYMENTS_FILE", path),
            mock.patch.object(payments_store, "LOCK_FILE", path + ".lock"),
        ]
        for p in self.patches:
            p.start()
        self.path = path

    def tearDown(self):
        for p in self.patches:
            p.stop()


class PaymentsStoreTests(StoreTestCase):
    def test_roundtrip_and_missing_file(self):
        self.assertEqual(payments_store.load_payments(), {})
        payments_store.save_payments({"1": {"amount": 100}})
        self.assertEqual(payments_store.load_payments(), {"1": {"amount": 100}})

    def test_broken_json_is_not_wiped(self):
        with open(self.path, "w") as f:
            f.write("{broken")
        with self.assertRaises(json.JSONDecodeError):
            payments_store.load_payments()
        with open(self.path) as f:
            self.assertEqual(f.read(), "{broken")


class CallbackTests(StoreTestCase):
    def setUp(self):
        super().setUp()
        payments_store.save_payments({"42": {"order_number": "42_A111", "order_id": "md-1", "amount": 100}})
        self.client = webhook_handler.app.test_client()
        self.amo = mock.patch.object(webhook_handler, "amocrm_client").start()
        self.amo.get_lead_by_id.return_value = {"status_id": 1}
        self.addCleanup(mock.patch.stopall)

    def callback(self, **extra):
        params = {"mdOrder": "md-1", "orderNumber": "42_A111", "operation": "deposited", "status": "1"}
        params.update(extra)
        return self.client.get("/payment_callback", query_string=signed(params))

    def test_without_checksum_is_rejected(self):
        resp = self.client.get("/payment_callback", query_string={
            "mdOrder": "md-1", "orderNumber": "42_A111", "operation": "deposited", "status": "1"})
        self.assertEqual(resp.status_code, 400)
        self.amo.change_status.assert_not_called()

    def test_wrong_checksum_is_rejected(self):
        resp = self.client.get("/payment_callback", query_string={
            "mdOrder": "md-1", "orderNumber": "42_A111", "operation": "deposited", "status": "1",
            "checksum": "DEADBEEF"})
        self.assertEqual(resp.status_code, 400)
        self.amo.change_status.assert_not_called()

    def test_deposited_marks_paid_and_removes_payment(self):
        resp = self.callback()
        self.assertEqual(resp.status_code, 200)
        self.amo.add_tag.assert_called_once_with("42", "оплачено")
        self.amo.change_status.assert_called_once_with("42", webhook_handler.STATUS_PAID)
        self.assertNotIn("42", payments_store.load_payments())

    def test_declined_moves_to_failed_and_keeps_payment(self):
        for operation in ("declined", "declined_timeout"):
            self.amo.change_status.reset_mock()
            resp = self.callback(operation=operation, status="0")
            self.assertEqual(resp.status_code, 200)
            self.amo.change_status.assert_called_once_with("42", webhook_handler.STATUS_PAYMENT_FAILED)
        self.assertIn("42", payments_store.load_payments())


class CheckPaymentsAccessTests(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.client = webhook_handler.app.test_client()

    def test_forbidden_from_outside_without_token(self):
        resp = self.client.get("/check_payments", environ_overrides={"REMOTE_ADDR": "203.0.113.5"})
        self.assertEqual(resp.status_code, 403)

    def test_token_grants_access(self):
        with mock.patch.dict(os.environ, {"CHECK_PAYMENTS_TOKEN": "secret"}):
            bad = self.client.get("/check_payments", headers={"X-Check-Token": "nope"},
                                  environ_overrides={"REMOTE_ADDR": "203.0.113.5"})
            ok = self.client.get("/check_payments", headers={"X-Check-Token": "secret"},
                                 environ_overrides={"REMOTE_ADDR": "203.0.113.5"})
        self.assertEqual(bad.status_code, 403)
        self.assertEqual(ok.status_code, 200)


if __name__ == "__main__":
    unittest.main()
