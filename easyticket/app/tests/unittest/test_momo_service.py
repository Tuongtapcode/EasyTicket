import pytest
from types import SimpleNamespace
from decimal import Decimal
from unittest.mock import patch

from app.services.momo_service import MoMoService, AccessDeniedException
from app.models import PaymentStatus

# ---- Fixtures ----
@pytest.fixture
def order_mock():
    return SimpleNamespace(id=1, total_amount=100000)

@pytest.fixture
def payment_mock():
    return SimpleNamespace(id=10, order_id=1, amount=100000)

# ---- Tests createMomoPayment ----
def test_createMomoPayment_success(order_mock, payment_mock):
    svc = MoMoService()

    with patch("app.models.Order.query.get", return_value=order_mock), \
         patch("app.dao.payment_dao.create_payment", return_value=payment_mock), \
         patch("requests.post", return_value=SimpleNamespace(json=lambda: {"payUrl": "http://fakeurl"})), \
         patch("app.services.momo_service.hmac_sha256_hex", lambda raw, key: "sig"):

        res = svc.createMomoPayment(order_id=1)
        assert res["payUrl"] == "http://fakeurl"
        assert res["paymentId"] == 10

def test_createMomoPayment_order_not_found():
    svc = MoMoService()
    with patch("app.models.Order.query.get", return_value=None):
        with pytest.raises(AccessDeniedException):
            svc.createMomoPayment(order_id=999)

def test_createMomoPayment_amount_mismatch(order_mock):
    svc = MoMoService()
    with patch("app.models.Order.query.get", return_value=order_mock):
        with pytest.raises(AccessDeniedException):
            svc.createMomoPayment(order_id=1, amount_override=123)

def test_createMomoPayment_momo_error(order_mock, payment_mock):
    svc = MoMoService()

    def raise_exc(*args, **kwargs):
        raise Exception("Network fail")

    with patch("app.models.Order.query.get", return_value=order_mock), \
         patch("app.dao.payment_dao.create_payment", return_value=payment_mock), \
         patch("requests.post", raise_exc), \
         patch("app.services.momo_service.hmac_sha256_hex", lambda raw, key: "sig"):

        res = svc.createMomoPayment(order_id=1)
        assert "error" in res
        assert res["paymentId"] == 10

# ---- Tests processIPN ----
def test_processIPN_invalid_signature(order_mock, payment_mock):
    svc = MoMoService()
    ipn = {"signature": "wrong", "orderId": "1-10", "amount": "100000", "resultCode": "0"}

    with patch("app.models.Order.query.get", return_value=order_mock), \
         patch("app.models.Payment.query.get", return_value=payment_mock), \
         patch("app.services.momo_service.hmac_sha256_hex", lambda raw, key: "sig"):

        res = svc.processIPN(ipn)
        assert res["resultCode"] == 97

def test_processIPN_success(order_mock, payment_mock):
    svc = MoMoService()
    ipn = {"signature": "sig", "orderId": "1-10", "amount": "100000", "resultCode": "0"}

    with patch("app.models.Order.query.get", return_value=order_mock), \
         patch("app.models.Payment.query.get", return_value=payment_mock), \
         patch("app.dao.payment_dao.update_payment_status", lambda pid, status, txn: None), \
         patch("app.services.momo_service.hmac_sha256_hex", lambda raw, key: "sig"):

        res = svc.processIPN(ipn)
        assert res["resultCode"] == 0
        assert res["message"] == "Success"

# ---- Tests verifyReturn ----
def test_verifyReturn():
    svc = MoMoService()
    params = {"signature": "sig", "orderId": "1-10", "amount": "100000", "resultCode": "0", "message": "OK"}

    with patch("app.services.momo_service.hmac_sha256_hex", lambda raw, key: "sig"):
        res = svc.verifyReturn(params)
        assert res["ok"] is True
        assert res["orderId"] == "1"
        assert res["paymentId"] == "10"
