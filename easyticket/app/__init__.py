# app/__init__.py
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_admin import Admin
from flask_babel import Babel
import os

# ---- lazy init extensions ----
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
migrate = Migrate()
admin = Admin(name="EasyTicket Admin", template_mode="bootstrap4")
babel = Babel()


RAILWAY_USER = os.getenv("DB_USER", "root")
RAILWAY_PASSWORD = os.getenv("DB_PASSWORD", "tLZxofCVyJIatBeoVLrEWbJjCCOwqgrg")
RAILWAY_HOST = os.getenv("DB_HOST", "centerbeam.proxy.rlwy.net")
RAILWAY_PORT = int(os.getenv("DB_PORT", 46411))
RAILWAY_DB   = os.getenv("DB_NAME", "railway")

def _default_db_uri() -> str:
    pwd = quote(RAILWAY_PASSWORD)
    return (
        f"mysql+pymysql://{RAILWAY_USER}:{pwd}@{RAILWAY_HOST}:{RAILWAY_PORT}/"
        f"{RAILWAY_DB}?charset=utf8mb4"
    )


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)

    # -------- default config --------
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")
    app.config["BABEL_DEFAULT_LOCALE"] = "en"
    app.config["BABEL_DEFAULT_TIMEZONE"] = "Asia/Ho_Chi_Minh"

    app.config.setdefault("SQLALCHEMY_DATABASE_URI", _default_db_uri())
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["QR_SECRET"] = os.getenv("QR_SECRET", "change-this-to-a-long-random-secret")


    # -------- override khi test --------
    if test_config:
        app.config.update(test_config)

    # -------- init extensions --------
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    migrate.init_app(app, db)
    babel.init_app(app)

    from app.admin import CustomAdminIndexView, init_admin
    #Flask_Admin
    admin.index_view = CustomAdminIndexView(name="Home")
    admin.init_app(app)


    # import models để Alembic detect
    with app.app_context():
        from app.models import (
            User, Category, EventType, Event,
            TicketType, Ticket, Order, OrderDetail, Payment
        )
        # Đăng ký admin views (sau khi models và Admin đã có)
        init_admin(admin, db.session)

    # register blueprints
    from app.blueprints.auth import auth
    from app.blueprints.main import main
    from app.blueprints.event import events_bp
    from app.blueprints.order import orders_bp
    from app.blueprints.organizer import organizer_bp
    from app.blueprints.vnpay import vnpay_bp
    from app.blueprints.momo import bp as momo_bp
    from app.blueprints.qr import qr_bp
    
    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(events_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(organizer_bp)
    app.register_blueprint(vnpay_bp)
    app.register_blueprint(momo_bp)
    app.register_blueprint(qr_bp)

    @login_manager.user_loader
    def load_user(user_id: str):
        from app.models import User
        return User.query.get(int(user_id))

    return app

# giữ app = create_app() cho Flask run bình thường
app = create_app()
