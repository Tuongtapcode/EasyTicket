import pytest
from decimal import Decimal
from types import SimpleNamespace

from app.dao import payment_dao


# ---- Helper: tạo Payment giả ----
def make_payment(**kwargs):
    return SimpleNamespace(**kwargs)


# ---- Test create_payment ----
def test_create_payment(monkeypatch):
    added = {"obj": None, "flushed": False, "committed": False}

    # Fake session
    class FakeSession:
        def add(self, obj): added["obj"] = obj
        def flush(self): added["flushed"] = True
        def commit(self): added["committed"] = True

    # Patch db.session
    payment_dao.db.session = FakeSession()

    # Patch Payment để tạo object SimpleNamespace thay vì model thật
    def fake_payment(**kwargs):
        return make_payment(**kwargs)

    monkeypatch.setattr(payment_dao, "Payment", fake_payment)

    result = payment_dao.create_payment(order_id=42, amount=150, method=payment_dao.PaymentMethod.CREDIT_CARD)

    # Kiểm tra object được tạo đúng
    assert added["obj"] is result
    assert added["flushed"] is True
    assert added["committed"] is True

    # Kiểm tra dữ liệu trong Payment
    assert result.order_id == 42
    assert isinstance(result.amount, Decimal)
    assert result.amount == Decimal(150)
    assert result.payment_method == payment_dao.PaymentMethod.CREDIT_CARD
    assert result.status == payment_dao.PaymentStatus.PENDING
    assert result.transaction_id == "init"


# ---- Test update_payment_status ----
def test_update_payment_status(monkeypatch):
    # Tạo Payment giả với giá trị ban đầu
    pay = make_payment(
        id=1,
        status=payment_dao.PaymentStatus.PENDING,
        transaction_id="init"
    )

    class FakeQuery:
        def get(self, pid):
            return pay if pid == 1 else None

    class FakeSession:
        def commit(self): self.committed = True

    payment_dao.db.session = FakeSession()

    monkeypatch.setattr(
        payment_dao,
        "Payment",
        SimpleNamespace(query=FakeQuery())
    )

    # Cập nhật có transaction_id
    payment_dao.update_payment_status(
        payment_id=1,
        status=payment_dao.PaymentStatus.SUCCESS,
        transaction_id="abc123"
    )

    assert pay.status == payment_dao.PaymentStatus.SUCCESS
    assert pay.transaction_id == "abc123"

    # Cập nhật với payment_id không tồn tại
    result = payment_dao.update_payment_status(
        payment_id=999,
        status=payment_dao.PaymentStatus.FAILED
    )
    assert result is None  # không crash, chỉ trả về None
