from app.models import db,Event

#Lay het
def get_all_events():
    return Event.query.all()

#lay theo id
def get_event_by_id(event_id):
    return Event.query.get(event_id)