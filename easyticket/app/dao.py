from app.models import Event


def load_event():
    query = Event.query
    return query.all()
