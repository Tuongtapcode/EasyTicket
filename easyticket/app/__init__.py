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

# Khởi tạo extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
migrate = Migrate()
babel = Babel()
# Nhớ đổi tên instance để flask đỡ nhầm
admin_instance = Admin(name="EasyTicket Admin", template_mode="bootstrap4")

# Cấu hình database
RAILWAY_USER = os.getenv("DB_USER", "root")
RAILWAY_PASSWORD = os.getenv("DB_PASSWORD", "tLZxofCVyJIatBeoVLrEWbJjCCOwqgrg")
RAILWAY_HOST = os.getenv("DB_HOST", "centerbeam.proxy.rlwy.net")
RAILWAY_PORT = int(os.getenv("DB_PORT", 46411))
RAILWAY_DB = os.getenv("DB_NAME", "railway")

def _default_db_uri() -> str:
    pwd = quote(RAILWAY_PASSWORD)
    return (
        f"mysql+pymysql://{RAILWAY_USER}:{pwd}@{RAILWAY_HOST}:{RAILWAY_PORT}/"
        f"{RAILWAY_DB}?charset=utf8mb4"
    )

# Hàm Factory để tạo app
def create_app(test_config=None):
    app = Flask(__name__)

    # Cấu hình app
    if test_config:
        app.config.from_mapping(test_config)
    else:
        app.config.from_mapping(
            SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret-change-me"),
            BABEL_DEFAULT_LOCALE="en",
            BABEL_DEFAULT_TIMEZONE="Asia/Ho_Chi_Minh",
            SQLALCHEMY_DATABASE_URI=_default_db_uri(),
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            QR_SECRET=os.getenv("QR_SECRET", "change-this-to-a-long-random-secret")
        )

    # Khởi tạo extensions với app
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    migrate.init_app(app, db)
    babel.init_app(app)

    # Đăng ký admin views
    with app.app_context():
        from app.admin import init_admin
        # Truyền đối tượng admin và db.session vào hàm init_admin
        init_admin(admin_instance, db.session)

    #Gắn đối tượng admin đã có các views vào ứng dụng Flask
    admin_instance.init_app(app)

    # Đăng ký blueprints
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

    #  User loader
    @login_manager.user_loader
    def load_user(user_id: str):
        from app.models import User
        return User.query.get(int(user_id))

    return app

#Tạo một instance app mặc định để các file khác có thể import
app = create_app()