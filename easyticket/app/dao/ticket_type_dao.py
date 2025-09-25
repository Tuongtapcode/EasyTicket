from app.models import db, TicketType
from sqlalchemy import or_, func


def get_ticket_type_by_id(ticket_type_id):
    return TicketType.query.get_or_404(ticket_type_id)

def get_ticket_types_by_event(event_id: int):
    return (
        db.session.query(TicketType)
        .filter(TicketType.event_id == event_id, TicketType.active == True)
        .order_by(TicketType.price.asc())
        .all()
    )

def delete_ticket_type_by_id(ticket_type_id):
    ticket_type = TicketType.query.get(ticket_type_id)
    if not ticket_type:
        return False
    try:
        db.session.delete(ticket_type)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting ticket type {ticket_type_id}: {e}")
        return False