# app/tests/conftest.py
import pytest
from werkzeug.security import generate_password_hash
from datetime import datetime

def _load_app():
    try:
        # nếu có create_app
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

#factory tạo user đúng định dạng hash để check_password_hash hoạt động
#Tạo user tùy chỉnh thay vì dùng user trong db thật
@pytest.fixture
def make_user(db):
    def _make(
        username="demo",
        password="123456",
        role_value="USER",
        **overrides,            #verride field nếu cần
    ):
        from app.models import User

        u = User(

            first_name=overrides.get("first_name", "Demo"),
            last_name =overrides.get("last_name",  "User"),
            email     =overrides.get("email",      f"{username}@example.com"),
            phone     =overrides.get("phone",      f"090{abs(hash(username)) % 10000000:07d}"),
            avatar    =overrides.get("avatar",     "https://cdn.pixabay.com/photo/2023/02/18/11/00/icon-7797704_640.png"),
            active    =overrides.get("active",     True),
            username  =username,
            password  =generate_password_hash(password),
            user_role =overrides.get("user_role", role_value),
            created_at=overrides.get("created_at", datetime.now()),
            updated_at=overrides.get("updated_at", datetime.now()),
            last_login_at=overrides.get("last_login_at", datetime.now()),
        )

        db.session.add(u)
        db.session.commit()
        return u
    return _make

#Tao ham de login
@pytest.fixture
def login(client):
    def _login(username, password, remember=False):
        return client.post(
            "/login",
            data={"username": username, "password": password, "remember": "y" if remember else ""},
            follow_redirects=True,
        )
    return _login

@pytest.fixture
def organizer_user(make_user):
    from app.models import UserRole
    role = UserRole.query.filter_by(name="ORGANIZER").first()
    if not role:
        role = UserRole(name="ORGANIZER")
        db.session.add(role)
        db.session.commit()
    return make_user(username="org1", password="123456", role_value=role.name)

@pytest.fixture
def logged_in_organizer(client, organizer_user, login):
    login(organizer_user.username, "123456")
    return organizer_user