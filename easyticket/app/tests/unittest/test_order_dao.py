import pytest
from types import SimpleNamespace
from app.dao import order_dao  # giả sử bạn lưu hàm trong order_dao.py


# ---- Helper: biến dict thành object giả ----
def make_order(obj: dict):
    return SimpleNamespace(**obj)


@pytest.fixture
def sample_orders():
    return [
        {"id": 1, "order_code": "ORD001", "total_amount": 100.0},
        {"id": 2, "order_code": "ORD002", "total_amount": 200.0},
    ]


def test_get_order_by_id(monkeypatch, sample_orders):
    # giả lập Order objects
    o1 = make_order(sample_orders[0])
    o2 = make_order(sample_orders[1])

    # patch Order trong order_dao
    monkeypatch.setattr(
        order_dao,
        "Order",
        SimpleNamespace(query=SimpleNamespace(get=lambda _id: o1 if _id == 1 else (o2 if _id == 2 else None)))
    )

    # test order có id = 1
    result = order_dao.get_order_by_id(1)
    assert result.id == 1
    assert result.order_code == "ORD001"

    # test order có id = 2
    result = order_dao.get_order_by_id(2)
    assert result.id == 2
    assert result.order_code == "ORD002"

    # test order không tồn tại
    result = order_dao.get_order_by_id(99)
    assert result is None
