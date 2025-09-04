from app.models import db,Event,EventStatus, EventType
from sqlalchemy import or_
#Lay het
def get_all_events():
    return Event.query.all()

#lay theo id
def get_event_by_id(event_id):
    return Event.query.get(event_id)

#tim kiem su kien
def search_events(q:str| None, page: int = 1, per_page: int = 12,event_type_id: int | None = None):

    qry = Event.query.filter(Event.status == EventStatus.PUBLISHED)
    if q:
        kw = f"%{q.strip()}%"
        qry = qry.filter(or_(Event.name.ilike(kw),
                             Event.description.ilike(kw),
                             Event.address.ilike(kw)))

    if event_type_id:
        qry = qry.filter(Event.event_type_id == event_type_id)

    return qry.order_by(Event.created_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)


def get_all_event_types():
    return EventType.query.all()