from flask_login import current_user, login_required
from flask import (
    render_template, request, jsonify,
    flash, redirect, url_for, abort
)

from flask import render_template, abort, Blueprint, request

from app.models import UserRole
from app.dao import event_dao
organizer_bp = Blueprint("organizer", __name__, url_prefix="/organizer")
@organizer_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.user_role != UserRole.ORGANIZER:
        abort(403)

    page = request.args.get("page", 1, type=int)
    status = request.args.get("status")
    keyword = request.args.get("q")


    events_pagination = event_dao.get_events_by_organizer(
        organizer_id=current_user.id,
        page=page,
        per_page=5,
        status=status,
        keyword=keyword
    )

    return render_template(
        "organizer/dashboard.html",
        events=events_pagination.items,
        pagination=events_pagination,
        status=status,
        keyword=keyword
    )

@organizer_bp.route("/events/<int:event_id>/scan")
@login_required
def scan_qr_view(event_id:int):
    # chỉ organizer của event (hoặc admin) mới có quyền
    from app.dao.event_dao import get_event_by_id
    event = get_event_by_id(event_id)
    if not event:
        abort(404)
    # kiểm tra quyền: organizer hoặc admin
    if current_user.user_role.name != "ORGANIZER" or event.organizer_id != current_user.id:
        flash("Bạn không có quyền truy cập trang quét QR này.", "danger")
        return redirect(url_for("organizer.dashboard"))
    return render_template("organizer/scan_qr.html", event=event)



