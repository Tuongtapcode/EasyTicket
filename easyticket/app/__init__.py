from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

RAILWAY_USER = os.getenv("DB_USER", "root")
RAILWAY_PASSWORD = os.getenv("DB_PASSWORD", "KYrheRlKRriAUqwhMBcJFlxlItWEMPMB")
RAILWAY_HOST = os.getenv("DB_HOST", "shinkansen.proxy.rlwy.net")
RAILWAY_PORT = int(os.getenv("DB_PORT", 27884))
RAILWAY_DB   = os.getenv("DB_NAME", "railway")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{RAILWAY_USER}:{quote(RAILWAY_PASSWORD)}@{RAILWAY_HOST}:{RAILWAY_PORT}/{RAILWAY_DB}?charset=utf8mb4"
)


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "auth.login"
migrate = Migrate(app, db)

#import tất cả models để Alembic detect
from app.models import (
    User, Category, EventType, Event,
    TicketType, Ticket, Order, OrderDetail,
    Payment
)

from app.blueprints.auth import auth
app.register_blueprint(auth)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))