# app/tests/conftest.py
import pytest
from werkzeug.security import generate_password_hash
from datetime import datetime

def _load_app():
    """
    Ưu tiên app factory nếu bạn có create_app(config);
    nếu không thì import app.module-level.
    """
    try:
        # nếu bạn có create_app
        from app import create_app, db
        app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "WTF_CSRF_ENABLED": False,   # tắt CSRF cho POST form trong test
            "SERVER_NAME": "localhost",
        })
        return app, db
    except Exception:
        # fallback: app kiểu module-level trong app/index.py
        from app.index import app
        from app import db
        app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite://",
            WTF_CSRF_ENABLED=False,
            SERVER_NAME="localhost",
        )
        return app, db

@pytest.fixture(scope="session")
def app_and_db():
    app, db = _load_app()
    with app.app_context():
        db.create_all()
        yield app, db
        db.drop_all()

@pytest.fixture
def app(app_and_db):
    return app_and_db[0]

@pytest.fixture
def db(app_and_db):
    return app_and_db[1]

@pytest.fixture
def client(app):
    return app.test_client()

# tiện: factory tạo user đúng định dạng hash để check_password_hash hoạt động
@pytest.fixture
def make_user(db):
    def _make(
        username="demo",
        password="123456",
        role_value="USER",
        **overrides,            # cho phép override thêm field nếu cần
    ):
        from app.models import User

        u = User(
            # các cột NOT NULL -> đặt default hợp lý
            first_name=overrides.get("first_name", "Demo"),
            last_name =overrides.get("last_name",  "User"),
            email     =overrides.get("email",      f"{username}@example.com"),
            phone     =overrides.get("phone",      "0900000000"),
            avatar    =overrides.get("avatar",     "https://cdn.pixabay.com/photo/2023/02/18/11/00/icon-7797704_640.png"),
            active    =overrides.get("active",     True),

            # các cột nghiệp vụ
            username  =username,
            password  =generate_password_hash(password),

            # enum/role
            user_role =overrides.get("user_role", role_value),

            # nếu model không có default ở DB, bạn gán luôn
            created_at=overrides.get("created_at", datetime.now()),
            updated_at=overrides.get("updated_at", datetime.now()),
            last_login_at=overrides.get("last_login_at", datetime.now()),
        )

        db.session.add(u)
        db.session.commit()
        return u
    return _make
