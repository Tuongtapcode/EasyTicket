import pytest
from types import SimpleNamespace
from app.dao import event_dao
from app.models import EventStatus


# ---- Helper ----
def make_event(obj: dict):
    return SimpleNamespace(**obj)


def make_event_type(obj: dict):
    return SimpleNamespace(**obj)


@pytest.fixture
def sample_event_types():
    return [
        {"id": 1, "name": "Concert"},
        {"id": 2, "name": "Workshop"}
    ]


@pytest.fixture
def sample_events():
    return [
        {
            "id": 1,
            "name": "Music Night",
            "description": "Live concert",
            "address": "Hanoi",
            "status": "PUBLISHED",
            "event_type_id": 1,
            "organizer_id": 10,
            "created_at": "2025-09-01T12:00:00",
            "start_datetime": "2025-09-10T19:00:00"
        },
        {
            "id": 2,
            "name": "Python 101",
            "description": "Basic Python workshop",
            "address": "Saigon",
            "status": "DRAFT",
            "event_type_id": 2,
            "organizer_id": 20,
            "created_at": "2025-09-02T09:00:00",
            "start_datetime": "2025-09-12T09:00:00"
        }
    ]


# ---- Test get_all_events ----
def test_get_all_events(monkeypatch, sample_events):
    events = [make_event(e) for e in sample_events]

    mock_created_at = SimpleNamespace(desc=lambda: "created_at_desc")

    mock_query = SimpleNamespace(
        order_by=lambda *args, **kwargs: mock_query,
        paginate=lambda **kwargs: SimpleNamespace(items=events)
    )

    monkeypatch.setattr(
        event_dao,
        "Event",
        SimpleNamespace(query=mock_query, created_at=mock_created_at)
    )

    result = event_dao.get_all_events()

    assert len(result.items) == 2
    assert result.items[0].name == "Music Night"
    assert result.items[1].name == "Python 101"


# ---- Test get_event_by_id ----
def test_get_event_by_id(monkeypatch, sample_events):
    e1 = make_event(sample_events[0])
    e2 = make_event(sample_events[1])

    monkeypatch.setattr(
        event_dao,
        "Event",
        SimpleNamespace(query=SimpleNamespace(
            get=lambda _id: e1 if _id == 1 else (e2 if _id == 2 else None)
        ))
    )

    result = event_dao.get_event_by_id(1)
    assert result.name == "Music Night"
    assert result.status == "PUBLISHED"

    result = event_dao.get_event_by_id(99)
    assert result is None


# ---- Test get_all_event_types ----
def test_get_all_event_types(monkeypatch, sample_event_types):
    types = [make_event_type(t) for t in sample_event_types]

    monkeypatch.setattr(
        event_dao,
        "EventType",
        SimpleNamespace(query=SimpleNamespace(all=lambda: types))
    )

    result = event_dao.get_all_event_types()

    assert len(result) == 2
    assert result[0].name == "Concert"
    assert result[1].name == "Workshop"


# ---- Test search_events ----
def test_search_events(monkeypatch, sample_events):
    published_events = [make_event(e) for e in sample_events if e["status"] == "PUBLISHED"]
    mock_paginate = SimpleNamespace(items=published_events, page=1, per_page=12, total=len(published_events))

    mock_created_at = SimpleNamespace(desc=lambda: "created_at_desc", asc=lambda: "created_at_asc")
    mock_start_datetime = SimpleNamespace(asc=lambda: "start_datetime_asc")

    mock_query = SimpleNamespace(
        filter=lambda *args, **kwargs: mock_query,
        order_by=lambda *args, **kwargs: mock_query,
        paginate=lambda **kwargs: mock_paginate
    )

    monkeypatch.setattr(
        event_dao,
        "Event",
        SimpleNamespace(
            query=SimpleNamespace(filter=lambda x: mock_query),
            status=SimpleNamespace(),
            name=SimpleNamespace(ilike=lambda x: True),
            description=SimpleNamespace(ilike=lambda x: True),
            address=SimpleNamespace(ilike=lambda x: True),
            created_at=mock_created_at,
            start_datetime=mock_start_datetime
        )
    )

    result = event_dao.search_events(q="Music")
    assert result.items[0].name == "Music Night"

    result = event_dao.search_events(q=None)
    assert len(result.items) == 1


# ---- Test get_events_by_organizer ----
def test_get_events_by_organizer(monkeypatch, sample_events):
    organizer_events = [make_event(e) for e in sample_events if e["organizer_id"] == 10]
    mock_paginate = SimpleNamespace(items=organizer_events, page=1, per_page=10, total=len(organizer_events))

    mock_start_datetime = SimpleNamespace(desc=lambda: "start_datetime_desc")

    mock_query = SimpleNamespace(
        filter_by=lambda **kwargs: mock_query,
        filter=lambda x: mock_query,
        order_by=lambda x: mock_query,
        paginate=lambda **kwargs: mock_paginate
    )

    monkeypatch.setattr(
        event_dao,
        "Event",
        SimpleNamespace(
            query=mock_query,
            start_datetime=mock_start_datetime,
            status="PUBLISHED"   # FIX lỗi thiếu thuộc tính status
        )
    )

    result = event_dao.get_events_by_organizer(organizer_id=10)
    assert len(result.items) == 1
    assert result.items[0].name == "Music Night"

    result = event_dao.get_events_by_organizer(
        organizer_id=10,
        status=EventStatus.PUBLISHED
    )
    assert len(result.items) == 1


# ---- Test delete_event_by_id ----
def test_delete_event_by_id(monkeypatch, sample_events):
    e1 = make_event(sample_events[0])

    monkeypatch.setattr(
        event_dao,
        "get_event_by_id",
        lambda _id: e1 if _id == 1 else None
    )

    class FakeSession:
        def __init__(self):
            self.deleted = None
            self.committed = False
            self.rolled_back = False

        def delete(self, obj):
            self.deleted = obj

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True

    fake_session = FakeSession()
    monkeypatch.setattr(event_dao.db, "session", fake_session)

    result = event_dao.delete_event_by_id(1)
    assert result is True
    assert fake_session.deleted == e1
    assert fake_session.committed is True

    result = event_dao.delete_event_by_id(99)
    assert result is False


def test_delete_event_by_id_exception(monkeypatch, sample_events):
    e1 = make_event(sample_events[0])

    monkeypatch.setattr(
        event_dao,
        "get_event_by_id",
        lambda _id: e1 if _id == 1 else None
    )

    class FakeSessionWithError:
        def __init__(self):
            self.rolled_back = False

        def delete(self, obj):
            raise Exception("Database error")

        def rollback(self):
            self.rolled_back = True

    fake_session = FakeSessionWithError()
    monkeypatch.setattr(event_dao.db, "session", fake_session)

    result = event_dao.delete_event_by_id(1)
    assert result is False
    assert fake_session.rolled_back is True
