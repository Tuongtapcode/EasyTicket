import pytest
from types import SimpleNamespace
from app.dao import user_dao


@pytest.fixture
def fake_session(monkeypatch):
    actions = {"added": None, "committed": False}

    class FakeSession:
        def add(self, obj): actions["added"] = obj
        def commit(self): actions["committed"] = True

    monkeypatch.setattr(user_dao, "db", SimpleNamespace(session=FakeSession()))
    return actions


# --- add_user ---
def test_add_user(monkeypatch, fake_session):
    # Patch generate_password_hash để kiểm tra có được gọi
    monkeypatch.setattr(user_dao, "generate_password_hash", lambda pw: f"hashed-{pw}")

    # Patch User model để tạo object giả
    created_users = {}
    def fake_user(**kwargs):
        created_users.update(kwargs)
        return SimpleNamespace(**kwargs)
    monkeypatch.setattr(user_dao, "User", fake_user)

    # Patch UserRole.USER
    monkeypatch.setattr(user_dao, "UserRole", SimpleNamespace(USER="USER_ROLE"))

    result = user_dao.add_user(
        first_name="John",
        last_name="Doe",
        username="johndoe",
        email="john@example.com",
        phone="12345",
        password="secret"
    )

    # Kiểm tra giá trị được truyền vào User
    assert created_users["first_name"] == "John"
    assert created_users["password"] == "hashed-secret"
    assert created_users["user_role"] == "USER_ROLE"

    # Kiểm tra đã add và commit vào session
    assert fake_session["added"] == result
    assert fake_session["committed"] is True


# --- get_user_by_username ---
def test_get_user_by_username(monkeypatch):
    captured_username = {}

    class FakeQuery:
        def filter_by(self, **kwargs):
            captured_username.update(kwargs)
            return self
        def first(self): return "user_obj"

    monkeypatch.setattr(user_dao, "User", SimpleNamespace(query=FakeQuery()))

    result = user_dao.get_user_by_username("johndoe")
    assert result == "user_obj"
    assert captured_username["username"] == "johndoe"
