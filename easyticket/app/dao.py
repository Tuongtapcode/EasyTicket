from app import db
from app.models import User, Event, UserRole
from werkzeug.security import generate_password_hash

#Them user
def add_user(first_name, last_name, username, email, phone, password):

    hashed_password = generate_password_hash(password)#bam mat khau
    new_user = User(
        first_name=first_name,
        last_name=last_name,
        username=username,
        email=email,
        phone=phone,
        password=hashed_password,
        user_role=UserRole.USER
    )
    db.session.add(new_user)
    db.session.commit()
    return new_user

#Lấy user
def get_user_by_username(username):
    return User.query.filter_by(username=username).first()