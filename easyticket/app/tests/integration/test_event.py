def test_event_detail(client, seed_minimal):
    ev = seed_minimal["event"]
    r = client.get(f"/events/{ev.id}")
    assert r.status_code == 200
    assert ev.name.encode() in r.data
