from decimal import Decimal
from flask import Blueprint, request, redirect, url_for, render_template, flash, abort
from flask_login import login_required
from sqlalchemy.orm import joinedload
from app import db
from app.blueprints.vnpay import vnpay_service
from app.dao.ticket_dao import count_sold_by_ticket_type
from app.models import (
    Order, OrderDetail, Payment, Ticket, TicketType,
    TicketStatus, PaymentStatus, PaymentMethod
)
from app.dao.order_dao import *
from app.dao.ticket_dao import get_tickets_of_user
from flask_login import current_user
from app.services.momo_service import MoMoService, AccessDeniedException
from app.services.vnpay_service import VNPayServiceImpl, AccessDeniedException
orders_bp = Blueprint("order", __name__, url_prefix="/orders")

def _gen_order_code():
    from uuid import uuid4
    return f"ORD-{str(uuid4())[:8].upper()}"

def _gen_txn_id():
    from uuid import uuid4
    return f"TXN-{str(uuid4())[:10].upper()}"

def _gen_ticket_code():
    from uuid import uuid4
    return f"TKT-{str(uuid4())[:10].upper()}"

@orders_bp.route("/create", methods=["POST"])
def create():
    # Lưu ý: nếu dùng Flask-Login thì thay current_user.id
    customer_id = request.form.get("current_user.id", 2, type=int)  # tạm
    event_id = request.form.get("event_id", type=int)

    # Parse items[<ticket_type_id>] = qty
    raw = {k: v for k, v in request.form.items() if k.startswith("items[")}
    items = []
    for k, v in raw.items():
        try:
            tid = int(k[6:-1])
            qty = int(v or 0)
        except ValueError:
            continue
        if qty > 0:
            items.append((tid, qty))

    if not items:
        flash("Bạn chưa chọn vé nào.", "warning")
        return redirect(url_for("event.event_details", event_id=event_id))

    # Lấy TicketType & kiểm tra cùng event
    ttype_ids = [tid for tid, _ in items]
    ttypes = (
        db.session.query(TicketType)
        .filter(TicketType.id.in_(ttype_ids))
        .all()
    )
    tt_map = {t.id: t for t in ttypes}
    errors = []
    for tid, _ in items:
        t = tt_map.get(tid)
        if not t or t.event_id != event_id:
            errors.append("Loại vé không hợp lệ hoặc không thuộc sự kiện.")
    if errors:
        flash(" ".join(errors), "danger")
        return redirect(url_for("event.event_details", event_id=event_id))

    # Kiểm tra remaining
    sold = count_sold_by_ticket_type(ttype_ids)
    lacks = []
    for tid, qty in items:
        t = tt_map[tid]
        remaining = max(0, (t.quantity or 0) - sold.get(t.id, 0))
        if qty > remaining:
            lacks.append(f"'{t.name}' chỉ còn {remaining} vé.")
    if lacks:
        flash(" ".join(lacks), "danger")
        return redirect(url_for("event.event_details", event_id=event_id))

    # Tạo Order + OrderDetail (snapshot giá = TicketType.price)
    order = Order(
        order_code=_gen_order_code(),
        customer_id=customer_id,
        extra_fee=Decimal("0.00"),
        discount=Decimal("0.00"),
        total_amount=Decimal("0.00"),
    )
    db.session.add(order); db.session.flush()

    total = Decimal("0.00")
    for tid, qty in items:
        t = tt_map[tid]
        db.session.add(OrderDetail(
            order_id=order.id,
            ticket_type_id=tid,
            quantity=qty,
            price=t.price
        ))
        total += (t.price or Decimal("0")) * qty

    order.total_amount = total + (order.extra_fee or 0) - (order.discount or 0)
    db.session.commit()

    return redirect(url_for("order.checkout", order_id=order.id))


# ========== 2) Trang checkout ==========
@orders_bp.route("/<int:order_id>/checkout")
def checkout(order_id):
    order = (
        db.session.query(Order)
        .options(joinedload(Order.order_details).joinedload(OrderDetail.ticket_type))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        abort(404)
    return render_template("order/checkout.html", order=order)

def method_for_gateway(gateway: str) -> PaymentMethod:
    gateway = (gateway or "").upper()
    if gateway == "MOMO":
        return PaymentMethod.DIGITAL_WALLET
    if gateway == "VN_PAY":
        return PaymentMethod.BANK_TRANSFER
        # return PaymentMethod.CREDIT_CARD
    return PaymentMethod.BANK_TRANSFER

# ========== 3) Tạo Payment và “giả lập” thanh toán thành công ==========
@orders_bp.route("/<int:order_id>/pay", methods=["POST"])
@login_required
def pay(order_id):
    order = db.session.get(Order, order_id) or abort(404)

    if order.customer_id != current_user.id:
        abort(403, description="Bạn không sở hữu đơn hàng này")


    gateway = (request.form.get("gateway") or "").upper()

    if gateway == "VNPAY":
        try:
           res = VNPayServiceImpl().createVnpayPayment(order_id=order_id,request=request, amount_override=order.total_amount)
        except AccessDeniedException as ex:
            flash(str(ex), "danger")
            return redirect(url_for("order.checkout", order_id=order_id))
        pay_url = res.get("payUrl")
        if not pay_url:
            flash("Không tạo được phiên thanh toán VNPay", "danger")
            return redirect(url_for("order.checkout", order_id=order_id))
        return redirect(pay_url, code=302)#Di thang toi trang thanh toan vnpay

    if gateway == "MOMO":
        try:
            res = MoMoService().createMomoPayment(order_id=order_id, amount_override=order.total_amount)
        except AccessDeniedException as ex:
            flash(str(ex), "danger")
            return redirect(url_for("order.checkout", order_id=order_id))
        pay_url = res.get("payUrl")
        if not pay_url:
            flash("Không tạo được phiên thanh toán MoMo", "danger")
            return redirect(url_for("order.checkout", order_id=order_id))
        return redirect(pay_url, 302)

    flash("Vui lòng chọn phương thức thanh toán.", "warning")
    return redirect(url_for("order.checkout", order_id=order_id))

# ========== 4) Trang thành công + danh sách vé ==========
@orders_bp.route("/<int:order_id>/success")
def success(order_id):
    tickets = db.session.query(Ticket).filter(Ticket.order_id == order_id).all()
    if tickets is None:
        abort(404)
    return render_template("order/success.html", tickets=tickets)

# ========== Helper: phát hành vé sau khi thanh toán ==========
def _issue_tickets(order_id: int):
    # Lấy các dòng order
    ods = (
        db.session.query(OrderDetail)
        .options(joinedload(OrderDetail.ticket_type))
        .filter(OrderDetail.order_id == order_id)
        .all()
    )
    if not ods:
        return

    # Re-check capacity lần cuối (flow A)
    ttype_ids = [od.ticket_type_id for od in ods]
    sold = count_sold_by_ticket_type((ttype_ids))
    for od in ods:
        t = od.ticket_type
        remaining = max(0, (t.quantity or 0) - sold.get(t.id, 0))
        if od.quantity > remaining:
            # Ở bản thật: đánh dấu Payment REFUND và báo hết vé.
            raise ValueError(f"Hết vé {t.name} trong lúc thanh toán.")
        sold[od.ticket_type_id] = sold.get(od.ticket_type_id, 0) + od.quantity

    # Tạo Ticket
    for od in ods:
        t = od.ticket_type
        for _ in range(od.quantity):
            db.session.add(Ticket(
                ticket_code=_gen_ticket_code(),
                status=TicketStatus.ACTIVE,
                order_id=order_id,
                ticket_type_id=od.ticket_type_id,
                event_id=t.event_id,
            ))


@orders_bp.route("/my-tickets")
@login_required
def my_tickets():
    q = request.args.get("q", "")
    status = request.args.get("status")  # ACTIVE/USED/CANCELLED/REFUNDED hoặc None
    page = request.args.get("page", 1, type=int)

    page_obj = get_tickets_of_user(
        user_id=current_user.id, status=status, q=q, page=page, per_page=12
    )

    return render_template("order/my_tickets.html",
                           page_obj=page_obj, q=q, selected_status=status)

@orders_bp.route("/payment/momo/return")
def momo_return():
    svc = MoMoService()
    info = svc.verifyReturn(request.args.to_dict())

    status = "SUCCESS" if info["ok"] and str(info["resultCode"]) == "0" else "FAILED"
    return render_template(
        "payment/payment_return.html",
        status=status,
        orderId=info["orderId"],
        paymentId=info["paymentId"],
        amount=info["amount"],
        transId=info["transId"],
        message=info["message"],
        resultCode=info["resultCode"],
    ), (200 if status=="SUCCESS" else 400)

@orders_bp.route("/payment/vnpay/return")
def vnpay_return():
    info = VNPayServiceImpl.verifyReturn(request.args.to_dict())
    status = "SUCCESS" if info["ok"] and str(info["resultCode"]) == "00" else "FAILED"
    return render_template("payment/payment_return.html", **{
        "status": status,
        "orderId": info["orderId"],
        "paymentId": info["paymentId"],
        "amount": info["amount"],
        "transId": info["transId"],
        "message": info["message"],
        "resultCode": info["resultCode"],
    }), (200 if status == "SUCCESS" else 400)