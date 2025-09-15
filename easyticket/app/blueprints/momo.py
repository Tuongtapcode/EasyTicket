from flask import Blueprint, request, jsonify,render_template, abort
from flask_login import login_required,current_user
from app.services.momo_service import MoMoService
from app.dao.order_dao import *
bp = Blueprint("momo", __name__, url_prefix="/api/payment/momo")
svc = MoMoService()

@bp.post("/create")
@login_required
def create():
    data = request.get_json() or {}
    order_id = int(data.get("orderId"))
    amount = data.get("amount")
    order = get_order_by_id(order_id)
    if order.customer_id != current_user.id: #Neu khong phai nguoi so huu don hang do
        abort(403, description="Bạn không sở hữu đơn hàng này")

    res = svc.createMomoPayment(order_id=order_id, request=request,
                                amount_override=amount)
    return jsonify(res)

@bp.post("/ipn")
def ipn():
    res = svc.processIPN(request.get_json() or {})
    return jsonify(res)

@bp.get("/return")
def momo_return():
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