# app/blueprints/qr.py
from flask import Blueprint, jsonify, request
from app.dao.ticket_dao import (
   get_ticket_by_id, get_ticket_by_qr, save_ticket_qr, mark_checked_in
)
from app.utils.qr_utils import *

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
   Organizer gửi: {"qr": ".", "event_id": <id>}
   Trả về JSON chi tiết:
   - khi lần đầu checkin: { ok: True, message: "Checked-in", ticket: {...}, buyer: {...}, checkin_at: "<iso>" }
   - khi đã checkin trước đó: { ok: False, error: "already_checked_in", ticket: {...}, buyer: {...}, checked_at: "<iso>"}
   - lỗi khác: ok: False, error: "message"
   """
   data = request.get_json(silent=True) or {}
   token = data.get("qr")
   event_id = data.get("event_id")
   if not token or not event_id:
       return jsonify(ok=False, error="missing_qr_or_event"), 400


   # verify token signature + payload
   ok, payload, msg = verify_token(token)
   if not ok:
       return jsonify(ok=False, error="invalid_qr", detail=msg), 400


   # lookup ticket by exact qr_data
   t = get_ticket_by_qr(token)
   if not t:
       return jsonify(ok=False, error="ticket_not_found"), 404


   # ensure ticket belongs to event being scanned
   if t.event_id != int(event_id):
       return jsonify(ok=False, error="wrong_event"), 400


   # build buyer info (if available)
   buyer = None
   try:
       if getattr(t, "order", None) and getattr(t.order, "customer", None):
           c = t.order.customer
           buyer = {
               "id": c.id,
               "username": c.username,
               "first_name": getattr(c, "first_name", None),
               "last_name": getattr(c, "last_name", None),
               "email": getattr(c, "email", None),
               "phone": getattr(c, "phone", None)
           }
   except Exception:
       buyer = None


   # If already used (checked-in) -> return specific payload (don't re-mark)
   from app.models import TicketStatus
   if t.status == TicketStatus.USED:
       # format checked time if exists
       checked_at = t.use_at.isoformat() if getattr(t, "use_at", None) else None
       return jsonify(
           ok=False,
           error="already_checked_in",
           message="Ticket already checked-in",
           ticket={
               "id": t.id,
               "ticket_code": t.ticket_code,
               "ticket_type": getattr(t.ticket_type, "name", None),
               "issued_at": t.issued_at.isoformat() if getattr(t, "issued_at", None) else None,
           },
           buyer=buyer,
           checked_at=checked_at
       ), 200


   # Only ACTIVE allowed to be checked in
   if t.status != TicketStatus.ACTIVE:
       return jsonify(ok=False, error="invalid_state", message=f"Invalid state: {t.status.value}"), 400


   # perform check-in
   # (mark_checked_in will set status=USED and use_at to now)
   prev_use_at = getattr(t, "use_at", None)
   mark_checked_in(t)  # commits


   # reload or use t.use_at (mark_checked_in already saved)
   checked_at = t.use_at.isoformat() if getattr(t, "use_at", None) else None


   return jsonify(
       ok=True,
       message="checked_in",
       ticket={
           "id": t.id,
           "ticket_code": t.ticket_code,
           "ticket_type": getattr(t.ticket_type, "name", None),
           "issued_at": t.issued_at.isoformat() if getattr(t, "issued_at", None) else None,
       },
       buyer=buyer,
       checkin_at=checked_at
   ), 200

