import pytest
from types import SimpleNamespace
from decimal import Decimal
from unittest.mock import patch

from app.services.vnpay_service import VNPayServiceImpl, AccessDeniedException
from app.models import PaymentStatus

# ---- Fixtures ----
@pytest.fixture
def order_mock():
    return SimpleNamespace(id=1, total_amount=100000, customer_id=1)

@pytest.fixture
def payment_mock():
    return SimpleNamespace(id=10, order_id=1, amount=100000, transaction_id=None)

# ---- Tests createVnpayPayment ----
def test_createVnpayPayment_success(order_mock, payment_mock):
    svc = VNPayServiceImpl()

    with patch("app.models.Order.query.get", return_value=order_mock), \
         patch("app.dao.payment_dao.create_payment", return_value=payment_mock), \
         patch("app.utils.vnpay_utils.hmac_sha512", lambda key, raw: "sig"):

        class FakeRequest:
            headers = {}
            remote_addr = "127.0.0.1"

        res = svc.createVnpayPayment(order_id=1, request=FakeRequest())
        assert "payUrl" in res
        assert res["paymentId"] == 10
        assert "sig" in res["payUrl"]

def test_createVnpayPayment_order_not_found():
    svc = VNPayServiceImpl()
    class FakeRequest:
        headers = {}
        remote_addr = "127.0.0.1"

    with patch("app.models.Order.query.get", return_value=None):
        with pytest.raises(AccessDeniedException):
            svc.createVnpayPayment(order_id=999, request=FakeRequest())

def test_createVnpayPayment_amount_mismatch(order_mock):
    svc = VNPayServiceImpl()
    class FakeRequest:
        headers = {}
        remote_addr = "127.0.0.1"

    with patch("app.models.Order.query.get", return_value=order_mock):
        with pytest.raises(AccessDeniedException):
            svc.createVnpayPayment(order_id=1, request=FakeRequest(), amount_override=123)

# ---- Tests processReturnUrl ----
def test_processReturnUrl_success(order_mock, payment_mock):
    svc = VNPayServiceImpl()
    params = {
        "vnp_SecureHash": "sig",
        "vnp_OrderInfo": "1-10",
        "vnp_TransactionStatus": "00",
        "vnp_ResponseCode": "00",
        "vnp_TransactionNo": "TX123",
        "vnp_Amount": "10000000"
    }

    with patch("app.models.Payment.query.get", return_value=payment_mock), \
         patch("app.models.Order.query.get", return_value=order_mock), \
         patch("app.dao.payment_dao.update_payment_status", lambda pid, status, txn: None), \
         patch("app.utils.vnpay_utils.hmac_sha512", lambda key, raw: "sig"):

        res = svc.processReturnUrl(params)
        assert res == params

def test_processReturnUrl_invalid_signature():
    svc = VNPayServiceImpl()
    params = {"vnp_SecureHash": "bad", "vnp_OrderInfo": "1-10"}
    # Patch secret để không còn None
    with patch("app.configs.vnpay_configs.VNP_HASHSECRET", "secret"):
        res = svc.processReturnUrl(params)
    assert res is None

def test_processReturnUrl_order_payment_mismatch(order_mock, payment_mock):
    svc = VNPayServiceImpl()
    params = {
        "vnp_SecureHash": "sig",
        "vnp_OrderInfo": "1-10",
        "vnp_TransactionStatus": "00",
        "vnp_ResponseCode": "00",
        "vnp_TransactionNo": "TX123",
        "vnp_Amount": "9990000"
    }

    payment_mock.amount = 100000
    with patch("app.models.Payment.query.get", return_value=payment_mock), \
         patch("app.models.Order.query.get", return_value=order_mock), \
         patch("app.utils.vnpay_utils.hmac_sha512", lambda key, raw: "sig"):

        res = svc.processReturnUrl(params)
        assert "error" in res
        assert res["error"] == "Amount mismatched"

# ---- Tests verifyReturn ----
def test_verifyReturn_success():
    svc = VNPayServiceImpl()
    params = {
        "vnp_SecureHash": "sig",
        "vnp_OrderInfo": "1-10",
        "vnp_ResponseCode": "00",
        "vnp_Amount": "10000000",
        "vnp_TransactionNo": "TX123"
    }

    with patch("app.configs.vnpay_configs.VNP_HASHSECRET", "secret"), \
         patch("app.utils.vnpay_utils.hmac_sha512", lambda key, raw: "sig"):
        res = svc.verifyReturn(params)
        assert res["ok"] is True
        assert res["orderId"] == "1"
        assert res["paymentId"] == "10"
        assert res["amount"] == 100000
        assert res["transId"] == "TX123"

def test_verifyReturn_invalid_signature():
    svc = VNPayServiceImpl()
    params = {"vnp_SecureHash": "bad", "vnp_OrderInfo": "1-10"}
    with patch("app.configs.vnpay_configs.VNP_HASHSECRET", "secret"), \
         patch("app.utils.vnpay_utils.hmac_sha512", lambda key, raw: "sig"):
        res = svc.verifyReturn(params)
        assert res["ok"] is False
        assert res["orderId"] == "1"
        assert res["paymentId"] == "10"
