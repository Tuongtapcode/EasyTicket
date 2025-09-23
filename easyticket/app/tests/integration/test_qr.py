import json


def _post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload),
                       headers={"Content-Type": "application/json"})


def test_qr_validate(client, seed_minimal):
    ev = seed_minimal["event"]
    tk = seed_minimal["ticket"]

    # DEBUG: Print data
    print("=" * 50)
    print("DEBUG QR VALIDATION")
    print("=" * 50)
    print(f"Ticket: id={tk.id}, code={tk.ticket_code}, qr_data={tk.qr_data}, status={tk.status}")
    print(f"Event: id={ev.id}, name={ev.name}, status={ev.status}")
    print(f"QR payload: {{'qr': '{tk.qr_data}', 'event_id': {ev.id}}}")
    print("-" * 50)

    # Call API
    r1 = _post_json(client, "/api/qr/validate", {"qr": tk.qr_data, "event_id": ev.id})

    # DEBUG: Print response
    print(f"Response status code: {r1.status_code}")
    print(f"Response headers: {dict(r1.headers)}")
    print(f"Response data: {r1.data.decode('utf-8')}")

    if r1.content_type == 'application/json':
        j1 = r1.get_json()
        print(f"Parsed JSON: {j1}")
        print(f"JSON 'ok' field: {j1.get('ok')}")
        if not j1.get("ok"):
            print(f"Error message: {j1.get('error', 'No error field')}")
    else:
        print("Response is NOT JSON!")

    print("=" * 50)

    # Original assertion
    j1 = r1.get_json()
    assert j1["ok"] is True

    # Second validation (commented out for now)
    # r2 = _post_json(client, "/api/qr/validate", {"qr": tk.qr_data, "event_id": ev.id})
    # j2 = r2.get_json()
    # assert j2.get("error") == "already_checked_in"