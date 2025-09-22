from app.models import db, Event, EventStatus, EventType
from app.models import db, Event
from sqlalchemy import or_


# Lay het
def get_all_events(page: int =1, per_page: int = 12):
    return Event.query.order_by(Event.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)


# lay theo id
def get_event_by_id(event_id):
    return Event.query.get(event_id)


# tim kiem su kien
def search_events(q: str | None, page: int = 1, per_page: int = 12, event_type_id: int | None = None):
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


def get_events_by_organizer(organizer_id, page=1, per_page=10, status=None, keyword=None):
    query = Event.query.filter_by(organizer_id=organizer_id)

    # Lọc theo trạng thái (status)
    if status:
        query = query.filter(Event.status == status)

    # Tìm kiếm theo tên hoặc mô tả
    if keyword:
        query = query.filter(
            or_(
                Event.name.ilike(f"%{keyword}%"),
                Event.description.ilike(f"%{keyword}%")
            )
        )

    # Trả về đối tượng phân trang
    return query.order_by(Event.start_datetime.desc()).paginate(page=page, per_page=per_page, error_out=False)


def delete_event_by_id(event_id):
    event = get_event_by_id(event_id)
    if not event:
        return False
    try:
        db.session.delete(event)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting event {event_id}: {e}")
        return False