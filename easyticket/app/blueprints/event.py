from flask import Blueprint, render_template, abort, request
from decimal import Decimal
from app.dao.event_dao import get_event_by_id, search_events
from datetime import datetime
from flask import Blueprint, render_template, abort, flash, redirect, url_for
from flask_login import login_required, current_user
from app.dao.event_dao import get_event_by_id
from app.dao.ticket_dao import get_ticket_type_by_event_id, count_sold_by_ticket_type
from app.dao.ticket_type_dao import get_ticket_types_by_event
from app.forms import EventForm, TicketTypeForm
from app import db, dao
from app.models import Event, EventType, Category, TicketType
from app.services.cloudinary_service import CloudinaryService

events_bp = Blueprint("event", __name__, url_prefix="/events")


@events_bp.route("/<int:event_id>")
def event_details(event_id: int):
    # Load event
    event = get_event_by_id(event_id)
    if not event:
        abort(404)

    # Load ticket types
    ticket_types = get_ticket_type_by_event_id(event_id) or []
    sold_map = count_sold_by_ticket_type([t.id for t in ticket_types])

    # Tính remaining cho từng loại vé (nếu có DAO đếm số vé đã phát hành)
    # count_sold_by_ticket_type trả về dict {ticket_type_id: sold_count}
    for t in ticket_types:
        sold = sold_map.get(t.id, 0)
        t.remaining = max(0, (t.quantity or 0) - sold)

    return render_template("events/detail.html", event=event, ticket_types=ticket_types)

def _parse_date(s: str | None):
    if not s: return None
    try:
        # nhận 'YYYY-MM-DD' hoặc full ISO
        return datetime.fromisoformat(s)
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except Exception:
            return None

@events_bp.route("/search")
def search():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    event_type_id = request.args.get("event_type_id", type=int)
    category_id = request.args.get("category_id", type=int)
    start_date = _parse_date(request.args.get("start_date"))
    end_date = _parse_date(request.args.get("end_date"))
    location = request.args.get("location") or None
    order_by = request.args.get("order_by", "newest")

    is_free_param = request.args.get("is_free")  # "1" | "0" | None
    is_free = None
    if is_free_param == "1":
        is_free = True
    elif is_free_param == "0":
        is_free = False

    page_obj = search_events(
        q=q,
        page=page, per_page=12,
        event_type_id=event_type_id,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        location=location,
        is_free=is_free,
        order_by=order_by
    )

    events_type = EventType.query.filter_by(active=True).order_by(EventType.name.asc()).all()
    categories = Category.query.filter_by(active=True).order_by(Category.name.asc()).all()

    return render_template(
        "events/search.html",
        page_obj=page_obj,
        q=q,
        events_type=events_type,
        categories=categories,
        selected_event_type_id=event_type_id,
        selected_category_id=category_id,
        start_date=start_date.isoformat() if start_date else "",
        end_date=end_date.isoformat() if end_date else "",
        location=location or "",
        is_free=("1" if is_free is True else ("0" if is_free is False else "")),
        order_by=order_by
    )


# Create Event - ORGANIZER
@events_bp.route("/create", methods=["GET", "POST"])  # <-- đã sửa lại
@login_required
def create_event():
    if current_user.user_role.name != "ORGANIZER":
        flash("Bạn không có quyền tạo sự kiện.", "danger")
        return redirect(url_for("main.index"))

    form = EventForm()
    form.set_choices()

    if form.validate_on_submit():
        uploaded_url = None
        file = form.banner_image.data
        if file and getattr(file, "filename", ""):
            cloud_service = CloudinaryService()
            uploaded_result = cloud_service.upload(file)
            if uploaded_result:
                uploaded_url = uploaded_result["url"]

        new_event = Event(
            organizer_id=current_user.id,
            name=form.name.data,
            description=form.description.data,
            event_type_id=form.event_type_id.data,
            category_id=form.category_id.data,
            start_datetime=form.start_datetime.data,
            end_datetime=form.end_datetime.data,
            address=form.address.data,
            banner_image=uploaded_url,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.session.add(new_event)
        db.session.commit()

        flash("Sự kiện đã được tạo thành công!", "success")
        return redirect(url_for("organizer.dashboard"))

    return render_template("events/create_event.html", form=form)


@events_bp.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    event = get_event_by_id(event_id)
    if current_user.user_role.name != "ORGANIZER" or event.organizer_id != current_user.id:
        flash("Bạn không có quyền chỉnh sửa sự kiện này.", "danger")
        return redirect(url_for("main.index"))
    form = EventForm(obj=event)
    form.set_choices()
    if form.validate_on_submit():
        event.name = form.name.data
        event.description = form.description.data
        event.event_type_id = form.event_type_id.data
        event.category_id = form.category_id.data
        event.start_datetime = form.start_datetime.data
        event.end_datetime = form.end_datetime.data
        event.address = form.address.data
        event.banner_image = form.banner_image.data or None
        event.updated_at = datetime.now()

        db.session.commit()
        flash("Sự kiện đã được cập nhật!", "success")
        return redirect(url_for("event.view_event", event_id=event.id))

    return render_template("events/create_event.html", form=form, event=event)


@events_bp.route("/<int:event_id>/delete", methods=["DELETE"])
@login_required
def api_delete_event(event_id):
    event = get_event_by_id(event_id)
    if not event:
        return {"error": "Event not found"}, 404

    # kiểm tra quyền
    if current_user.user_role.name != "ORGANIZER" or event.organizer_id != current_user.id:
        return {"error": "Unauthorized"}, 403

    # xoá sự kiện
    db.session.delete(event)
    db.session.commit()
    return {"message": "Deleted successfully"}, 200


@events_bp.route("/<int:event_id>/ticket-types", methods=["GET"])
def api_get_ticket_types(event_id):
    q = request.args.get("q", "")

    # Lấy tất cả ticket types (không phân trang)
    query = TicketType.query.filter(TicketType.event_id == event_id)
    if q:
        query = query.filter(TicketType.name.ilike(f"%{q}%"))

    ticket_types = query.order_by(TicketType.price.asc()).all()
    event = get_event_by_id(event_id)

    # Tính toán số liệu
    total_quantity = sum(t.quantity for t in ticket_types)
    total_sold = 0
    total_revenue = 0
    best_selling_ticket = 0

    return render_template(
        "events/event_ticket_types.html",
        event=event,
        ticket_types=ticket_types,
        total_quantity=total_quantity,
        total_sold=total_sold,
        total_revenue=total_revenue,
        best_selling_ticket=best_selling_ticket,
        q=q
    )


@events_bp.route("/<int:event_id>/ticket-types/create", methods=["GET", "POST"])
@login_required
def create_ticket_type(event_id):
    event = get_event_by_id(event_id)

    # chỉ organizer của sự kiện mới được tạo vé
    if current_user.user_role.name != "ORGANIZER" or event.organizer_id != current_user.id:
        flash("Bạn không có quyền tạo loại vé cho sự kiện này.", "danger")
        return redirect(url_for("main.index"))

    form = TicketTypeForm()

    if form.validate_on_submit():
        new_ticket_type = TicketType(
            event_id=event.id,
            name=form.name.data,
            description=form.description.data,
            quantity=form.quantity.data,
            price=form.price.data,
            active=bool(form.active.data),  # 1 → True, 0 → False
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.session.add(new_ticket_type)
        db.session.commit()

        flash("Loại vé đã được tạo thành công!", "success")
        return redirect(url_for("event.api_get_ticket_types", event_id=event.id))
    return render_template("events/create_ticket_types.html", form=form, event=event)


@events_bp.route("/ticket-types/<int:ticket_type_id>/edit", methods=["GET", "POST"])
@login_required
def edit_ticket_type(ticket_type_id):
    ticket_type = dao.ticket_type_dao.get_ticket_type_by_id(ticket_type_id)  # <-- đổi tên hàm cho đúng
    event = ticket_type.event

    if current_user.user_role.name != "ORGANIZER" or event.organizer_id != current_user.id:
        flash("Bạn không có quyền chỉnh sửa loại vé này.", "danger")
        return redirect(url_for("main.index"))

    form = TicketTypeForm(obj=ticket_type)
    form.set_active_value(ticket_type)  # set giá trị active ban đầu

    if form.validate_on_submit():
        ticket_type.name = form.name.data
        ticket_type.description = form.description.data
        ticket_type.quantity = form.quantity.data
        ticket_type.price = form.price.data
        ticket_type.active = bool(form.active.data)
        ticket_type.updated_at = datetime.now()

        db.session.commit()
        flash("Loại vé đã được cập nhật!", "success")
        return redirect(url_for("event.api_get_ticket_types", event_id=event.id))

    return render_template("events/create_ticket_types.html", form=form, ticket_type=ticket_type, event=event)


@events_bp.route("/ticket-types/<int:ticket_type_id>/delete", methods=["DELETE"])
@login_required
def api_delete_ticket_type(ticket_type_id):
    ticket_type = dao.ticket_type_dao.get_ticket_type_by_id(ticket_type_id)
    if not ticket_type:
        return {"error": "Ticket type not found"}, 404

    event = ticket_type.event
    # chỉ organizer của sự kiện mới có quyền xoá loại vé
    if current_user.user_role.name != "ORGANIZER" or event.organizer_id != current_user.id:
        return {"error": "Unauthorized"}, 403

    try:
        db.session.delete(ticket_type)
        db.session.commit()
        return {"message": "Deleted successfully"}, 200
    except Exception as e:
        db.session.rollback()
        return {"error": f"Error deleting ticket type: {str(e)}"}, 500
