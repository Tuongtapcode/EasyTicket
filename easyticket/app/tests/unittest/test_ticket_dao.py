from app.models import Ticket, TicketType, TicketStatus, Order, Event
from app import db
from sqlalchemy import or_, func
from sqlalchemy.orm import joinedload
from datetime import datetime

def get_ticket_type_by_event_id(event_id):
    return TicketType.query.filter_by(event_id=event_id).all()

def count_sold_by_ticket_type(ticket_type_ids: list[int]) -> dict[int, int]:
    if not ticket_type_ids:
        return {}
    rows = (
        db.session.query(Ticket.ticket_type_id, func.count(Ticket.id))
        .filter(
            Ticket.ticket_type_id.in_(ticket_type_ids),
            Ticket.status.in_([TicketStatus.ACTIVE, TicketStatus.USED])
        )
        .group_by(Ticket.ticket_type_id)
        .all()
    )
    return {tid: cnt for tid, cnt in rows}

def get_tickets_of_user(user_id: int, q: str = "", status: str = None,
                        page: int = 1, per_page: int = 12):
    query = (
        db.session.query(Ticket)
        .join(Order)
        .filter(Order.customer_id == user_id)
        .options(
            joinedload(Ticket.event),
            joinedload(Ticket.ticket_type)
        )
        .order_by(Ticket.created_at.desc())
    )
    if q:
        like_q = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Ticket.ticket_code.ilike(like_q),
                Ticket.ticket_type.has(TicketType.name.ilike(like_q)),
                Ticket.event.has(Event.name.ilike(like_q))
            )
        )
    if status:
        query = query.filter(Ticket.status == status)
    return query.paginate(page=page, per_page=per_page)

def get_ticket_by_id(ticket_id: int):
    return Ticket.query.get(ticket_id)

def get_ticket_by_qr(qr_data: str):
    return Ticket.query.filter_by(qr_data=qr_data).first()

def save_ticket_qr(ticket: Ticket, qr_data: str):
    ticket.qr_data = qr_data
    ticket.issued_at = datetime.utcnow()
    db.session.add(ticket)
    db.session.commit()

def mark_checked_in(ticket: Ticket):
    ticket.status = TicketStatus.USED
    ticket.use_at = datetime.utcnow()
    db.session.add(ticket)
    db.session.commit()
