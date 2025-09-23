def test_login_success(client, db, make_user):
    # Given
    make_user(username="demo", password="123456", role_value="USER")

    # When
    resp = client.post("/login", data={
        "username": "demo",
        "password": "123456"
    }, follow_redirects=True)

    # Then
    assert resp.status_code == 200
    assert b"login successful" in resp.data.lower()