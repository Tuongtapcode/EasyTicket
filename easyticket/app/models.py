
from sqlalchemy import Column, Integer, String

from app import app, db

class Event(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    address = Column(String(200), nullable=False)

    def __str__(self):
        return self.name

event = Event(
    id=1,
    name="Su kien A",
    address="112/Nguyen Van A"
)


if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()

        db.session.add(event)
        db.session.commit()