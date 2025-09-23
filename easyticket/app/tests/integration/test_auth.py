def test_login_organizer(client, seed_minimal):
    resp = client.post("/login", data={
        "username": "org1",
        "password": "123456"
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"organizer" in resp.data or b"Dashboard" in resp.data
