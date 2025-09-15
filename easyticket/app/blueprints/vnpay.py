from flask import Blueprint, request, jsonify,abort
from flask_login import login_required, current_user
from app.dao.order_dao import *
from app.services.vnpay_service import VNPayServiceImpl, AccessDeniedException
from app.models import Payment, PaymentStatus

vnpay_bp = Blueprint("vnpay", __name__)
vnpay_service = VNPayServiceImpl()

@vnpay_bp.get("/payment/vnpay/return")
def vnp_return():
    params = request.args.to_dict()
    result = vnpay_service.processReturnUrl(params)  # None = hash sai
    #Lấy paymentId để hiển thị trạng thái thật từ DB
    try:
        order_id, payment_id = map(int, (params.get("vnp_OrderInfo", "0-0").split("-")))
    except Exception:
        order_id = payment_id = 0

    pay = Payment.query.get(payment_id)

    if result is None:
        msg = "Yêu cầu không hợp lệ (signature sai)."
        http = 400
    elif not pay:
        msg = "Không tìm thấy giao dịch. Vui lòng thử lại."
        http = 404
    elif pay.status == PaymentStatus.SUCCESS:
        msg = "Thanh toán thành công 🎉"
        http = 200
    elif pay.status == PaymentStatus.PENDING:
        msg = "Đang xác nhận thanh toán… (vui lòng đợi vài giây)"
        http = 200
    else:
        msg = "Thanh toán thất bại."
        http = 200

    return msg, http

@vnpay_bp.route("/payment/vnpay/ipn", methods=["GET","POST"])
def vnp_ipn():
    params = request.values.to_dict()
    print("IPN HIT:", params)                # log theo dõi
    result = vnpay_service.processReturnUrl(params)  # verify + cập nhật DB + idempotent
    if result is None:
        return jsonify({"RspCode":"97","Message":"Invalid signature"}), 200
    if isinstance(result, dict) and "error" in result:
        return jsonify({"RspCode":"99","Message":result["error"]}), 200
    return jsonify({"RspCode":"00","Message":"Confirm Success"}), 200


@vnpay_bp.post("/test/payments/vnpay/create")
@login_required
def vnpay_create_test():
    data = request.get_json(force=True)
    try:
        order_id = int(data["orderId"])
        amount_override = data.get("amount")
        order = get_order_by_id(order_id)
        if order.customer_id != current_user.id:  # Neu khong phai nguoi so huu don hang do
            abort(403, description="Bạn không sở hữu đơn hàng này")
        result = vnpay_service.createVnpayPayment(
            order_id=order_id,
            request=request,
            amount_override=amount_override,
        )
        return jsonify(result), 200

    except AccessDeniedException as ex:
        return jsonify({"error": str(ex)}), 403
    except KeyError as ex:
        return jsonify({"error": f"Thiếu field: {ex}"}), 400
    except Exception as ex:
        return jsonify({"error": f"{ex}"}), 500