from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_admin import Admin
from flask_babel import Babel
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.config["BABEL_DEFAULT_LOCALE"] = "en"   # hoặc "vi"
app.config["BABEL_DEFAULT_TIMEZONE"] = "Asia/Ho_Chi_Minh"
app.secret_key='easyticketnhom11'
babel = Babel(app)

RAILWAY_USER = os.getenv("DB_USER", "root")
RAILWAY_PASSWORD = os.getenv("DB_PASSWORD", "KYrheRlKRriAUqwhMBcJFlxlItWEMPMB")
RAILWAY_HOST = os.getenv("DB_HOST", "shinkansen.proxy.rlwy.net")
RAILWAY_PORT = int(os.getenv("DB_PORT", 27884))
RAILWAY_DB   = os.getenv("DB_NAME", "railway")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{RAILWAY_USER}:{quote(RAILWAY_PASSWORD)}@{RAILWAY_HOST}:{RAILWAY_PORT}/{RAILWAY_DB}?charset=utf8mb4"
)
# app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:%s@localhost/ticketdb?charset=utf8mb4" % quote(
#     'Admin@123')

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "auth.login"
migrate = Migrate(app, db)

#Flask_Admin
admin = Admin(app=app,name="EasyTicket Admin",template_mode="bootstrap4")


#import tất cả models để Alembic detect
from app.models import (
    User, Category, EventType, Event,
    TicketType, Ticket, Order, OrderDetail,
    Payment
)

from app.blueprints.auth import auth
from app.blueprints.main import main
from app.blueprints.event import events_bp
from app.blueprints.order import orders_bp
from app.blueprints.organizer import organizer_bp
from app.blueprints.vnpay import vnpay_bp
from app.blueprints.momo import bp as momo_bp
app.register_blueprint(auth)
app.register_blueprint(main)
app.register_blueprint(events_bp)
app.register_blueprint(orders_bp)
app.register_blueprint(organizer_bp)
app.register_blueprint(vnpay_bp)
app.register_blueprint(momo_bp)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))