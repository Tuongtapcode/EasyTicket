import pytest
from types import SimpleNamespace
from app.dao import ticket_type_dao
from app import db


@pytest.fixture
def fake_session(monkeypatch):
    actions = {"deleted": None, "committed": False, "rollback_called": False}

    class FakeSession:
        def query(self, *args, **kwargs):
            actions["query_called"] = True
            return self

        def filter(self, *args):
            actions["filters"] = args
            return self

        def order_by(self, *args):
            actions["ordered"] = True
            return self

        def all(self):
            return ["t1", "t2"]

        def delete(self, obj):
            actions["deleted"] = obj

        def commit(self):
            actions["committed"] = True

        def rollback(self):
            actions["rollback_called"] = True

    monkeypatch.setattr(ticket_type_dao, "db", SimpleNamespace(session=FakeSession()))
    return actions


# --- get_ticket_type_by_id ---
def test_get_ticket_type_by_id(monkeypatch):
    called = {}

    class FakeQuery:
        def get_or_404(self, tid):
            called["id"] = tid
            return "ticket_type_obj"

    monkeypatch.setattr(ticket_type_dao, "TicketType", SimpleNamespace(query=FakeQuery()))
    result = ticket_type_dao.get_ticket_type_by_id(10)

    assert result == "ticket_type_obj"
    assert called["id"] == 10


# --- get_ticket_types_by_event ---
def test_get_ticket_types_by_event(fake_session, monkeypatch):
    class FakeTicketType:
        class _Field:
            def __init__(self, name):
                self.name = name

            def __eq__(self, other):
                return f"{self.name}=={other}"

        event_id = _Field("event_id")
        active = _Field("active")
        price = SimpleNamespace(asc=lambda: "price_asc")

    monkeypatch.setattr(ticket_type_dao, "TicketType", FakeTicketType)
    result = ticket_type_dao.get_ticket_types_by_event(123)

    assert result == ["t1", "t2"]
    # kiểm tra đã filter đúng điều kiện event_id và active
    assert any("event_id" in str(f) for f in fake_session["filters"])
    assert any("active" in str(f) for f in fake_session["filters"])
    assert fake_session["ordered"] is True


# --- delete_ticket_type_by_id ---
def test_delete_ticket_type_success(fake_session, monkeypatch):
    fake_ticket_type = SimpleNamespace(id=1)

    class FakeQuery:
        def get(self, tid):
            assert tid == 1
            return fake_ticket_type

    monkeypatch.setattr(ticket_type_dao, "TicketType", SimpleNamespace(query=FakeQuery()))
    result = ticket_type_dao.delete_ticket_type_by_id(1)

    assert result is True
    assert fake_session["deleted"] == fake_ticket_type
    assert fake_session["committed"] is True


def test_delete_ticket_type_not_found(fake_session, monkeypatch):
    class FakeQuery:
        def get(self, tid):
            return None  # không tìm thấy

    monkeypatch.setattr(ticket_type_dao, "TicketType", SimpleNamespace(query=FakeQuery()))
    result = ticket_type_dao.delete_ticket_type_by_id(99)

    assert result is False
    assert fake_session["deleted"] is None
    assert fake_session["committed"] is False


def test_delete_ticket_type_exception(fake_session, monkeypatch):
    fake_ticket_type = SimpleNamespace(id=1)

    class FakeQuery:
        def get(self, tid):
            return fake_ticket_type

    class FakeSessionWithError:
        def delete(self, obj):
            raise Exception("DB Error")

        def commit(self):
            pass

        def rollback(self):
            fake_session["rollback_called"] = True

    monkeypatch.setattr(ticket_type_dao, "TicketType", SimpleNamespace(query=FakeQuery()))
    monkeypatch.setattr(ticket_type_dao, "db", SimpleNamespace(session=FakeSessionWithError()))

    result = ticket_type_dao.delete_ticket_type_by_id(1)
    assert result is False
    assert fake_session["rollback_called"] is True
