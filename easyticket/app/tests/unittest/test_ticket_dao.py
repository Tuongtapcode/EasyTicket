import pytest
from types import SimpleNamespace
from datetime import datetime
from app.dao import ticket_dao


@pytest.fixture
def fake_session():
    actions = {"added": [], "committed": False}

    class FakeSession:
        def add(self, obj): actions["added"].append(obj)
        def commit(self): actions["committed"] = True
        def query(self, *args, **kwargs): return None

    ticket_dao.db.session = FakeSession()
    return actions


# --- get_ticket_type_by_event_id ---
def test_get_ticket_type_by_event_id(monkeypatch):
    fake_result = ["t1", "t2"]

    class FakeQuery:
        def filter_by(self, **kwargs):
            assert kwargs == {"event_id": 42}
            return self
        def all(self): return fake_result

    monkeypatch.setattr(ticket_dao, "TicketType", SimpleNamespace(query=FakeQuery()))
    result = ticket_dao.get_ticket_type_by_event_id(42)
    assert result == fake_result


# --- count_sold_by_ticket_type ---
def test_count_sold_by_ticket_type(monkeypatch, fake_session):
    called = {}

    def fake_query(*args):
        class FakeQuery:
            def filter(self, *filters):
                called["filters"] = filters
                return self
            def group_by(self, *args):
                called["group_by"] = True
                return self
            def all(self):
                return [(1, 10), (2, 5)]
        return FakeQuery()

    ticket_dao.db.session.query = fake_query
    result = ticket_dao.count_sold_by_ticket_type([1, 2])
    assert result == {1: 10, 2: 5}
    assert "group_by" in called


def test_count_sold_by_ticket_type_empty():
    assert ticket_dao.count_sold_by_ticket_type([]) == {}


# --- get_tickets_of_user ---
def test_get_tickets_of_user_basic(monkeypatch):
    qry_state = {"filters": [], "ordered": False, "paginated": False}

    class FakeCreatedAt:
        @staticmethod
        def desc():  # bắt chước SQLAlchemy column.desc()
            return "created_at_desc"

    class FakeQuery:
        def options(self, *args): return self
        def join(self, *args, **kwargs): return self
        def filter(self, cond):
            qry_state["filters"].append(cond)
            return self
        def order_by(self, *args):
            qry_state["ordered"] = True
            return self
        def paginate(self, page, per_page, error_out):
            qry_state["paginated"] = (page, per_page)
            return ["ticket1", "ticket2"]

    FakeTicket = SimpleNamespace(
        query=FakeQuery(),
        event="fake_event",
        ticket_type="fake_ticket_type",
        order_id="fake_order_id",
        created_at=FakeCreatedAt(),
        status="fake_status"
    )

    monkeypatch.setattr(ticket_dao, "Ticket", FakeTicket)
    monkeypatch.setattr(ticket_dao, "Order", SimpleNamespace(id="order_id", customer_id="customer_id"))
    monkeypatch.setattr(ticket_dao, "joinedload", lambda x: x)

    result = ticket_dao.get_tickets_of_user(user_id=123)
    assert result == ["ticket1", "ticket2"]
    assert qry_state["ordered"] is True
    assert qry_state["paginated"] == (1, 12)
    assert len(qry_state["filters"]) >= 1


def test_get_tickets_of_user_with_status_and_q(monkeypatch):
    qry_state = {"filters": []}

    class FakeCreatedAt:
        @staticmethod
        def desc():
            return "created_at_desc"

    class FakeQuery:
        def options(self, *args): return self
        def join(self, *args, **kwargs): return self
        def filter(self, cond):
            qry_state["filters"].append(cond)
            return self
        def order_by(self, *args): return self
        def paginate(self, page, per_page, error_out): return ["t"]

    FakeTicket = SimpleNamespace(
        query=FakeQuery(),
        event="fake_event",
        ticket_type="fake_ticket_type",
        order_id="fake_order_id",
        created_at=FakeCreatedAt(),
        status="fake_status"
    )

    monkeypatch.setattr(ticket_dao, "Ticket", FakeTicket)
    monkeypatch.setattr(ticket_dao, "Order", SimpleNamespace(id="order_id", customer_id="customer_id"))
    monkeypatch.setattr(ticket_dao, "joinedload", lambda x: x)

    # ✅ FIX: dùng __class_getitem__ để subscript được trên class
    class FakeTicketStatus:
        ACTIVE = "ACTIVE"

        @classmethod
        def __class_getitem__(cls, key):
            if key == "ACTIVE":
                return cls.ACTIVE
            raise KeyError

    monkeypatch.setattr(ticket_dao, "TicketStatus", FakeTicketStatus)

    result = ticket_dao.get_tickets_of_user(user_id=1, status="ACTIVE", q="music")
    assert result == ["t"]
    assert any("music" in str(f) for f in qry_state["filters"])


# --- get_ticket_by_id & get_ticket_by_qr ---
def test_get_ticket_by_id_and_qr(monkeypatch):
    monkeypatch.setattr(ticket_dao, "Ticket", SimpleNamespace(
        query=SimpleNamespace(
            get=lambda tid: "ticket_obj",
            filter_by=lambda qr_data=None: SimpleNamespace(first=lambda: "ticket_qr")
        )
    ))

    assert ticket_dao.get_ticket_by_id(1) == "ticket_obj"
    assert ticket_dao.get_ticket_by_qr("QRDATA") == "ticket_qr"


# --- save_ticket_qr ---
def test_save_ticket_qr(fake_session):
    ticket = SimpleNamespace(qr_data=None, issued_at=None)
    ticket_dao.save_ticket_qr(ticket, "QR123")

    assert ticket.qr_data == "QR123"
    assert isinstance(ticket.issued_at, datetime)
    assert ticket in fake_session["added"]
    assert fake_session["committed"]


# --- mark_checked_in ---
def test_mark_checked_in(fake_session):
    ticket = SimpleNamespace(status=None, use_at=None)

    ticket_dao.mark_checked_in(ticket)

    assert ticket.status.value == "USED"
    assert isinstance(ticket.use_at, datetime)
    assert ticket in fake_session["added"]
    assert fake_session["committed"]
