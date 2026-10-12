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
    import tasks  # noqa: E402
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


class ProcessLeadTests(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.amo = mock.patch.object(tasks, "amocrm_client").start()
        self.bank = mock.patch.object(tasks, "sbp_client").start()
        self.lead = {"pipeline_id": tasks.Config.PIPELINE_ID, "status_id": tasks.Config.ALLOWED_STATUS_IDS[0], "price": 100}
        self.amo.get_lead_by_id.side_effect = lambda _id: dict(self.lead)
        self.n = 0

        def register(amount, order_number):
            self.n += 1
            return {"formUrl": f"https://pay/{self.n}", "orderId": f"md-{self.n}"}
        self.bank.create_payment_link.side_effect = register
        self.addCleanup(mock.patch.stopall)

    def run_task(self):
        tasks.process_lead("42", tasks.Config.ALLOWED_STATUS_IDS[0], tasks.Config.PIPELINE_ID)

    def test_creates_order_and_posts_link_once(self):
        self.run_task()
        self.run_task()  # дубль вебхука
        self.assertEqual(self.bank.create_payment_link.call_count, 1)
        self.amo.update_lead.assert_called_once()
        entry = payments_store.load_payments()["42"]
        self.assertTrue(entry["link_posted"])
        self.assertEqual(len(payments_store.get_orders(entry)), 1)

    def test_retry_after_amocrm_failure_reuses_order(self):
        import requests
        self.amo.update_lead.side_effect = [requests.ConnectionError("boom"), None]
        with self.assertRaises(requests.ConnectionError):
            self.run_task()
        self.assertFalse(payments_store.load_payments()["42"]["link_posted"])
        self.run_task()
        self.assertEqual(self.bank.create_payment_link.call_count, 1)
        self.assertTrue(payments_store.load_payments()["42"]["link_posted"])

    def test_amount_change_keeps_old_order_payable(self):
        self.run_task()
        self.lead["price"] = 200
        self.run_task()
        payments = payments_store.load_payments()
        self.assertEqual(len(payments_store.get_orders(payments["42"])), 2)
        old = payments_store.get_orders(payments["42"])[0]
        self.assertEqual(payments_store.find_lead_by_order(payments, old["order_id"], old["order_number"]), "42")

    def test_wrong_pipeline_in_amocrm_is_ignored(self):
        self.lead["pipeline_id"] = 999999
        self.run_task()
        self.bank.create_payment_link.assert_not_called()

    def test_legacy_entry_format_is_supported(self):
        payments_store.save_payments({"42": {"order_number": "42_A1", "order_id": "md-old", "amount": 10000,
                                              "form_url": "u", "created_at": 1}})
        self.run_task()  # сумма та же, ссылка считается записанной
        self.bank.create_payment_link.assert_not_called()


class WebhookAccountTests(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.client = webhook_handler.app.test_client()
        self.delay = mock.patch.object(webhook_handler.process_lead, "delay").start()
        self.addCleanup(mock.patch.stopall)

    def post(self, account_id):
        form = {"leads[status][0][id]": "42", "leads[status][0][status_id]": "1",
                "leads[status][0][pipeline_id]": "1", "account[id]": account_id}
        return self.client.post("/webhook", data=form)

    def test_own_account_is_processed(self):
        self.assertEqual(self.post("1").status_code, 200)
        self.delay.assert_called_once()

    def test_foreign_account_is_ignored(self):
        self.post("777")
        self.delay.assert_not_called()

    def test_missing_account_is_ignored(self):
        self.client.post("/webhook", data={"leads[status][0][id]": "42", "leads[status][0][status_id]": "1",
                                           "leads[status][0][pipeline_id]": "1"})
        self.delay.assert_not_called()


if __name__ == "__main__":
    unittest.main()
