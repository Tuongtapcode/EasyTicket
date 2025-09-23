import pytest
from app import create_app, db
from app.models import User, Category, EventType, Event, TicketType, Ticket
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta, timezone  # ← Thêm timezone

@pytest.fixture(scope="function")  # ← THAY ĐỔI TỪ "session" THÀNH "function"
def app():
    """Create a new Flask app for each test"""
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": "test-secret",
    })
    with app.app_context():
        db.create_all()  # ← Tạo tables mới cho mỗi test
    yield app
    with app.app_context():
        db.drop_all()  # ← Xóa tables sau mỗi test

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def db_session(app):
    with app.app_context():
        # Sử dụng db.session thay vì tạo scoped session phức tạp
        db.session.rollback()  # Clean up previous data
        yield db.session
        db.session.rollback()  # Rollback after test
        db.session.remove()

@pytest.fixture(scope="function")  # ← THÊM scope="function"
def seed_minimal(db_session):
    """Create test data for each test"""
    organizer = User(
        first_name="Organizer",
        last_name="Test",
        username="org1",
        email="org1@example.com",
        phone="0900000001",
        password=generate_password_hash("123456"),
        user_role="ORGANIZER",
        active=True
    )
    buyer = User(
        first_name="Buyer",
        last_name="Test",
        username="buyer1",
        email="buyer1@example.com",
        phone="0911111112",
        password=generate_password_hash("123456"),
        user_role="USER",
        active=True
    )
    db_session.add_all([organizer, buyer])

    cat = Category(name="Music", description="Âm nhạc", active=True)
    et = EventType(name="CONCERT", active=True)
    db_session.add_all([cat, et])
    db_session.flush()

    ev = Event(
        organizer_id=organizer.id,
        name="Private Show Vũ.",
        description="Show thử nghiệm",
        status="PUBLISHED",
        event_type_id=et.id,
        category_id=cat.id,
        start_datetime=datetime.now(timezone.utc)+timedelta(days=1),  # ← Fix warning
        end_datetime=datetime.now(timezone.utc)+timedelta(days=1,hours=3),  # ← Fix warning
        address="1900 Le Théâtre",
        created_at=datetime.now(timezone.utc),  # ← Fix warning
        updated_at=datetime.now(timezone.utc),  # ← Fix warning
        published_at=datetime.now(timezone.utc)  # ← Fix warning
    )
    db_session.add(ev)
    db_session.flush()

    tt = TicketType(
        event_id=ev.id,
        name="Standard",
        description="Vé thường",
        quantity=100,
        price=300000,
        active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(tt)
    db_session.flush()

    # Tạo ticket trước, không có qr_data
    tk = Ticket(
        event_id=ev.id,
        ticket_type_id=tt.id,
        ticket_code="TKT-TEST-001",
        status="ACTIVE",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        issued_at=datetime.now(timezone.utc),
        use_at=None,
    )
    db_session.add(tk)
    db_session.flush()  # Flush để có tk.id

    # Tạo qr_data với format 3 phần: ticket_id:event_id:timestamp
    tk.qr_data = f"{tk.id}:{ev.id}:{int(datetime.now(timezone.utc).timestamp())}"
    db_session.commit()

    yield {"organizer": organizer, "buyer": buyer, "event": ev, "ticket": tk}