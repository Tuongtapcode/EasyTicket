from app.models import Ticket,TicketType, TicketStatus,  Order, Event
from app import db
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from datetime import datetime
from app import db
from app.models import Ticket

#Lay danh sach loai ve cua 1 su kien
def get_ticket_type_by_event_id(event_id):
    return TicketType.query.filter_by(event_id=event_id).all()

#Dem so luong ve da ban
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

#Lay ve cua nguoi dung
def get_tickets_of_user(user_id: int, status: str | None = None,
                        q: str | None = None, page: int = 1, per_page: int = 12):
    qry = (Ticket.query
           .options(joinedload(Ticket.event), joinedload(Ticket.ticket_type))
           .join(Order, Ticket.order_id == Order.id)
           .filter(Order.customer_id == user_id))

    if status:
        # status truyền dạng chuỗi: ACTIVE / USED / CANCELLED / REFUNDED
        try:
            qry = qry.filter(Ticket.status == TicketStatus[status])
        except KeyError:
            pass  # nếu status không hợp lệ thì bỏ qua

    if q:
        kw = f"%{q.strip()}%"
        qry = qry.join(Event, Ticket.event)\
                 .join(TicketType, Ticket.ticket_type)\
                 .filter(or_(Ticket.ticket_code.ilike(kw),
                             Event.name.ilike(kw),
                             TicketType.name.ilike(kw)))

    return qry.order_by(Ticket.created_at.desc())\
              .paginate(page=page, per_page=per_page, error_out=False)
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
    from app.models import TicketStatus
    ticket.status = TicketStatus.USED
    ticket.use_at = datetime.utcnow()
    db.session.add(ticket)
    db.session.commit()