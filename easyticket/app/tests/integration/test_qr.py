import json


def _post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload),
                       headers={"Content-Type": "application/json"})


def test_qr_validate(client, seed_minimal):
    ev = seed_minimal["event"]
    tk = seed_minimal["ticket"]

    # 1) Issue QR để lấy token đã ký
    r_issue = client.post(f"/api/qr/issue/{tk.id}")
    ji = r_issue.get_json()
    assert ji["ok"] is True
    token = ji["qr"]

    # 2) Validate & check-in
    r1 = client.post("/api/qr/validate", json={"qr": token, "event_id": ev.id})
    j1 = r1.get_json()
    assert j1["ok"] is True
    assert j1["message"] == "checked_in"

    # 3) Lần 2 phải báo already_checked_in (nếu muốn test)
    r2 = client.post("/api/qr/validate", json={"qr": token, "event_id": ev.id})
    j2 = r2.get_json()
    assert j2["ok"] is False
    assert j2["error"] == "already_checked_in"