from datetime import datetime, timedelta
import io

def test_user_cannot_create_event(client, make_user, login):
    u = make_user(username="u1", password="123456", role_value="USER")
    login(u.username, "123456")
    r = client.get("/events/create", follow_redirects=False)
    # vì user thường sẽ bị redirect về main.index
    assert r.status_code in (302, 303)
    assert "/main.index" in r.headers["Location"] or "/" in r.headers["Location"]


def test_organizer_can_open_create_event_form(client, make_user, login):
    organizer = make_user(username="org1", password="123456", role_value="ORGANIZER")

    # login organizer
    login(organizer.username, "123456")

    # truy cập trang create event, lần này nên 200
    r = client.get("/events/create", follow_redirects=True)

    assert r.status_code == 200
    assert b"<form" in r.data
    assert b"name" in r.data.lower()