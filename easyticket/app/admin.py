# app/admin.py
from flask import redirect, url_for, request, render_template
from flask_login import current_user
from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from sqlalchemy import text
from app import admin,db
from app.models import User,Event


# Chỉ cho phép user role=ADMIN vào Admin
class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, "role", "") == "ADMIN"

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("auth.login", next=request.url))


# (Tuỳ chọn) Trang thống kê nhỏ trong Admin
class StatsView(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, "role", "") == "ADMIN"

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("auth.login", next=request.url))

    @expose("/")
    def index(self):
        # Ví dụ: doanh thu theo ngày từ bảng orders (MySQL/SQLite ok)
        # Nếu dùng Postgres, bạn có thể đổi sang date_trunc.
        session = self.admin.app.extensions["sqlalchemy"].db.session
        rows = session.execute(text("""
            SELECT DATE(created_at) AS d, COALESCE(SUM(amount),0) AS revenue
            FROM orders
            GROUP BY DATE(created_at)
            ORDER BY d
        """)).fetchall()
        labels = [str(r[0]) for r in rows]
        data = [float(r[1]) for r in rows]
        return self.render("admin/stats.html", labels=labels, data=data)

admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Event, db.session, endpoint="admin_events", url="/admin/events" ))
admin.add_view(StatsView(name="Thống kê", endpoint="stats"))

