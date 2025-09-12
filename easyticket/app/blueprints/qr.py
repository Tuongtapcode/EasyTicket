# app/blueprints/qr.py
from flask import Blueprint, jsonify, request
from app.dao.ticket_dao import (
    get_ticket_by_id, get_ticket_by_qr, save_ticket_qr, mark_checked_in
)
from app.utils.qr_utils import sign_payload, verify_token
from app.models import TicketStatus

qr_bp = Blueprint("qr", __name__, url_prefix="/api/qr")

@qr_bp.post("/issue/<int:ticket_id>")
def issue_qr(ticket_id: int):
    """
    Phát hành QR cho 1 ticket (gọi sau khi thanh toán thành công).
    Nếu vé đã có qr_data, trả lại luôn.
    """
    t = get_ticket_by_id(ticket_id)
    if not t:
        return jsonify(ok=False, error="Ticket not found"), 404
    if t.qr_data:
        return jsonify(ok=True, ticket_id=t.id, qr=t.qr_data)

    payload = {"tid": t.id, "oid": t.order_id, "eid": t.event_id}
    token = sign_payload(payload)
    save_ticket_qr(t, token)
    return jsonify(ok=True, ticket_id=t.id, qr=token)

@qr_bp.post("/validate")
def validate_and_checkin():
    """
    Organizer gửi: {"qr": "...", "event_id": <id>}
    """
    data = request.get_json(silent=True) or {}
    token = data.get("qr")
    event_id = data.get("event_id")
    if not token or not event_id:
        return jsonify(ok=False, error="Missing qr or event_id"), 400

    ok, payload, msg = verify_token(token)
    if not ok:
        return jsonify(ok=False, error=msg), 400

    t = get_ticket_by_qr(token)
    if not t:
        return jsonify(ok=False, error="Ticket not found"), 404
    if t.event_id != int(event_id):
        return jsonify(ok=False, error="Wrong event"), 400
    if t.status != TicketStatus.ACTIVE:
        return jsonify(ok=False, error=f"Invalid state: {t.status.value}"), 400

    mark_checked_in(t)
    return jsonify(ok=True, message="Checked-in", ticket_id=t.id, status=t.status.value)
