
from flask import Blueprint, render_template, abort
from decimal import Decimal
from app.dao.event_dao import get_event_by_id
from app.dao.ticket_dao import get_ticket_type_by_event_id, count_sold_by_ticket_type

events_bp = Blueprint("event", __name__, url_prefix="/events")

@events_bp.route("/<int:event_id>")
def event_details(event_id: int):
    #Load event
    event = get_event_by_id(event_id)
    if not event:
        abort(404)

    #Load ticket types
    ticket_types = get_ticket_type_by_event_id(event_id) or []
    sold_map = count_sold_by_ticket_type([t.id for t in ticket_types])

    #Tính remaining cho từng loại vé (nếu có DAO đếm số vé đã phát hành)
    # count_sold_by_ticket_type trả về dict {ticket_type_id: sold_count}
    for t in ticket_types:
        sold = sold_map.get(t.id, 0)
        t.remaining = max(0, (t.quantity or 0) - sold)

    return render_template("events/detail.html", event=event, ticket_types=ticket_types)
