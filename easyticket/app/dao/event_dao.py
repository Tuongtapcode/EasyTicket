from app.models import db,Event,EventStatus
from sqlalchemy import or_
#Lay het
def get_all_events():
    return Event.query.all()

#lay theo id
def get_event_by_id(event_id):
    return Event.query.get(event_id)

#tim kiem su kien
def search_events(q:str| None, page: int = 1, per_page: int = 12):

    qry = Event.query.filter(Event.status == EventStatus.PUBLISHED)
    if q:
        kw = f"%{q.strip()}%"
        qry = qry.filter(or_(Event.name.ilike(kw),
                             Event.description.ilike(kw),
                             Event.address.ilike(kw)))
    return qry.order_by(Event.created_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)