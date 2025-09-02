from app.models import Ticket,TicketType, TicketStatus
from app import db
from sqlalchemy import func

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