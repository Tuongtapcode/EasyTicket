# app/admin.py
import flask
from flask import redirect, url_for, request, render_template,flash
from flask_login import current_user, logout_user
from flask_admin import Admin, BaseView, expose, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from app.models import *
from app import admin,db
from sqlalchemy import func, extract, case
from datetime import datetime, timedelta

# Chỉ cho phép user role=ADMIN vào Admin
class SecureModelView(ModelView):
    def is_accessible(self):
        if current_user.is_authenticated and current_user.user_role.value == "ADMIN":
            return True
        else:
            flash("Bạn không có quyền truy cập trang này!", "danger")
            return False

    #Callback khi is_accessible la false
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("auth.forbidden", next=request.url))


class CustomAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not self.is_accessible():
            flash("Bạn không có quyền truy cập trang này!", "danger")
            return self.inaccessible_callback("auth.login")

        return self.render('admin/index.html')
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role.value == "ADMIN"

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("auth.forbidden", next=request.url))

#Logout
class Logout(BaseView):
    @expose('/')
    def index(self):
        if current_user.is_authenticated:
            logout_user()
        return redirect(url_for('auth.login'))

class StatsView(BaseView):
    @expose('/')
    def index(self):
        # Tổng số liệu cơ bản
        total_users = User.query.count()
        total_events = Event.query.count()
        total_orders = Order.query.count()
        total_revenue = db.session.query(func.sum(Order.total_amount)).scalar() or 0

        # Thống kê 7 ngày gần nhất
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_revenue = 0
        new_orders = 0
        new_users = User.query.filter(User.created_at >= seven_days_ago).count()
        new_events = Event.query.filter(Event.created_at >= seven_days_ago).count()

        # Thống kê trạng thái sự kiện
        event_status_stats = db.session.query(Event.status, func.count(Event.id)).group_by(Event.status).all()

        # Thống kê vai trò người dùng
        user_role_stats = db.session.query(User.user_role, func.count(User.id)).group_by(User.user_role).all()

        # Top 5 sự kiện có nhiều vé bán nhất
        top_events = db.session.query(
            Event.name,
            func.sum(OrderDetail.quantity).label('tickets_sold')
        ).join(Event.ticket_types).join(TicketType.order_details).join(OrderDetail.order)\
         .group_by(Event.id, Event.name).order_by(func.sum(OrderDetail.quantity).desc()).limit(5).all()

        # THỐNG KÊ THEO THỜI GIAN
        # Theo tháng (12 tháng gần nhất)
        monthly_stats = db.session.query(
            extract('year', Event.created_at).label('year'),
            extract('month', Event.created_at).label('month'),
            func.count(Event.id).label('event_count'),
            func.coalesce(func.sum(Order.total_amount), 0).label('revenue')
        ).outerjoin(Event.tickets).outerjoin(Ticket.order)\
         .filter(Event.created_at >= datetime.now() - timedelta(days=365))\
         .group_by('year', 'month').order_by('year', 'month').all()

        # Theo quý (4 quý gần nhất)
        quarterly_stats = db.session.query(
            extract('year', Event.created_at).label('year'),
            case(
                (extract('month', Event.created_at) <= 3, 1),
                (extract('month', Event.created_at) <= 6, 2),
                (extract('month', Event.created_at) <= 9, 3),
                else_=4
            ).label('quarter'),
            func.count(Event.id).label('event_count'),
            func.coalesce(func.sum(Order.total_amount), 0).label('revenue')
        ).outerjoin(Event.tickets).outerjoin(Ticket.order)\
         .filter(Event.created_at >= datetime.now() - timedelta(days=365))\
         .group_by('year', 'quarter').order_by('year', 'quarter').all()

        # Theo năm (3 năm gần nhất)
        yearly_stats = db.session.query(
            extract('year', Event.created_at).label('year'),
            func.count(Event.id).label('event_count'),
            func.coalesce(func.sum(Order.total_amount), 0).label('revenue')
        ).outerjoin(Event.tickets).outerjoin(Ticket.order)\
         .group_by('year').order_by('year').limit(3).all()

        # Chuẩn bị dữ liệu cho biểu đồ
        monthly_labels = []
        monthly_events = []
        monthly_revenues = []

        for stat in monthly_stats:
            monthly_labels.append(f"T{int(stat.month)}/{int(stat.year)}")
            monthly_events.append(stat.event_count)
            monthly_revenues.append(float(stat.revenue or 0))

        quarterly_labels = []
        quarterly_events = []
        quarterly_revenues = []

        for stat in quarterly_stats:
            quarterly_labels.append(f"Q{int(stat.quarter)}/{int(stat.year)}")
            quarterly_events.append(stat.event_count)
            quarterly_revenues.append(float(stat.revenue or 0))

        yearly_labels = []
        yearly_events = []
        yearly_revenues = []

        for stat in yearly_stats:
            yearly_labels.append(f"Năm {int(stat.year)}")
            yearly_events.append(stat.event_count)
            yearly_revenues.append(float(stat.revenue or 0))

        return self.render('admin/stats.html',
            total_users=total_users,
            total_events=total_events,
            total_orders=total_orders,
            total_revenue=total_revenue,
            recent_revenue=recent_revenue,
            new_orders=new_orders,
            new_users=new_users,
            new_events=new_events,
            event_status_stats=event_status_stats,
            user_role_stats=user_role_stats,
            top_events=top_events,
            monthly_labels=monthly_labels,
            monthly_events=monthly_events,
            monthly_revenues=monthly_revenues,
            quarterly_labels=quarterly_labels,
            quarterly_events=quarterly_events,
            quarterly_revenues=quarterly_revenues,
            yearly_labels=yearly_labels,
            yearly_events=yearly_events,
            yearly_revenues=yearly_revenues
        )

    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role == UserRole.ADMIN

    def inaccessible_callback(self, name, **kwargs):
        flash('Bạn không có quyền truy cập trang này.', 'error')
        return redirect(url_for('auth.forbidden', next=request.url))


class UserView(SecureModelView):
    can_view_details = True
    edit_modal = True
    details_modal = True
    column_exclude_list = ['password','avatar']
    column_filters = ['username', 'email','phone']

class EventView(SecureModelView):
    can_view_details = True
    edit_modal = True
    details_modal = True
    can_view_details_modal = True
    column_exclude_list = ['banner_image']
    column_editable_list = ['status'] #Chỉnh trực tiếp
    form_excluded_columns = ['ticket_types','tickets','banner_image','updated_at','created_at','published_at']

class EventTypeView(SecureModelView):
    edit_modal = True
    details_modal = True
    can_view_details_modal = True
    form_excluded_columns =['events']

class CategoryView(SecureModelView):
    edit_modal = True
    details_modal = True
    can_view_details_modal = True
    form_excluded_columns = ['ticket_types']

def init_admin(admin, db_session):
    admin.add_view(UserView(User, db.session))
    admin.add_view(EventView(Event, db.session,name="Sự kiện", endpoint="admin_events", url="/admin/events" ))
    admin.add_view(EventTypeView(EventType, db.session,name="Loại sự kiện", endpoint="admin_event_types", url="/admin/event_types" ))
    admin.add_view(CategoryView(Category, db.session,name="Thể loại sự kiện", endpoint="admin_categories", url="/admin/categories" ))
    admin.add_view(StatsView(name="Thống kê", endpoint="stats", url="/admin/stats"))
    admin.add_view(Logout(name="Đăng xuất",endpoint="logout",url="/admin/logout"))

