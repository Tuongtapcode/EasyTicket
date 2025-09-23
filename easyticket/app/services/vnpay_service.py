# -*- coding: utf-8 -*-
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from urllib.parse import quote_plus
from decimal import Decimal

from flask import Request
from flask_login import current_user

from app import db
from app.models import Order, Payment, PaymentStatus, PaymentMethod
from app.configs import vnpay_configs as VNPayConfigs
from app.utils.vnpay_utils import hmac_sha512
from app.dao.payment_dao import *


class AccessDeniedException(Exception):
    pass


class VNPayServiceImpl:
    """
    Flow mới:
      - Client chỉ gửi: orderId (+ amount nếu muốn đối chiếu)
      - Server tự tạo Payment(PENDING)
      - vnp_OrderInfo = "{orderId}-{paymentId}"
      - Return/IPN cập nhật Payment & Order
    """

    # --------- helper: sort & encode giống Java URLEncoder ----------
    @staticmethod
    def _encode_pairs_sorted(params: Dict[str, Any]) -> str:
        items = sorted((k, str(v)) for k, v in params.items() if v not in (None, ""))
        return "&".join(f"{k}={quote_plus(v, safe='')}" for k, v in items)

    # ---------------------- tạo URL thanh toán -----------------------
    def createVnpayPayment(
        self,
        *,
        order_id: int,
        request: Request,
        amount_override: int | None = None,   # nếu muốn gửi kèm từ client để đối chiếu
    ) -> dict:

        # 1) Lấy order & kiểm tra quyền
        order = Order.query.get(order_id)
        if not order:
            raise AccessDeniedException("Không tìm thấy đơn hàng")

            """
        if current_user.is_authenticated and order.customer_id != current_user.id:
            # nếu tắt login để tests thì current_user có thể không auth: bỏ qua check này
            raise AccessDeniedException("Bạn không sở hữu đơn hàng này")
            
            """

        # 2) Tính số tiền cần thanh toán từ Order (khuyến nghị dùng số này, không tin client)
        order_amount_vnd = int(Decimal(order.total_amount))
        if amount_override is not None and int(amount_override) != order_amount_vnd:
            raise AccessDeniedException("Số tiền không khớp đơn hàng")

        # 3) Tạo Payment(PENDING) mới
        pay = create_payment(order.id, order_amount_vnd)

        # 4) Build tham số VNPay
        tz = timezone(timedelta(hours=7))
        vnp_TxnRef = str(int(datetime.now(tz).timestamp() * 1000))
        pay.transaction_id = vnp_TxnRef  # lưu lại để trace
        db.session.commit()

        vnp_amount = str(order_amount_vnd * 100)
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1")
        order_info = f"{order.id}-{pay.id}"  # để IPN/Return tra ngược

        base_params = {
            "vnp_Version": VNPayConfigs.VNP_VERSION or "2.1.0",
            "vnp_Command": VNPayConfigs.VNP_COMMAND or "pay",
            "vnp_TmnCode": VNPayConfigs.VNP_TMNCODE,
            "vnp_Amount": vnp_amount,
            "vnp_CurrCode": "VND",
            "vnp_TxnRef": vnp_TxnRef,
            "vnp_OrderInfo": order_info,
            "vnp_OrderType": "other",
            "vnp_Locale": "vn",
            "vnp_ReturnUrl": VNPayConfigs.VNP_RETURNURL,
            "vnp_IpAddr": client_ip,
            "vnp_CreateDate": datetime.now(tz).strftime("%Y%m%d%H%M%S"),
        }

        raw = self._encode_pairs_sorted(base_params)
        secure_hash = hmac_sha512(VNPayConfigs.VNP_HASHSECRET, raw)
        pay_url = f"{VNPayConfigs.VNP_URL}?{raw}&vnp_SecureHash={secure_hash}"
        print("DEBUG VNP_IPNURL:", VNPayConfigs.VNP_IPNURL)
        print("DEBUG payUrl:", pay_url)
        return {"payUrl": pay_url, "paymentId": pay.id}

    #Cap nhat DB
    def processReturnUrl(self, params: Dict[str, str]) -> Dict[str, str] | None:
        received = (params.get("vnp_SecureHash") or "").lower() #SecureHash tu MoMo gui ve

        filtered = {k: v for k, v in params.items() if k not in ("vnp_SecureHash", "vnp_SecureHashType")}
        raw = self._encode_pairs_sorted(filtered)
        calc = hmac_sha512(VNPayConfigs.VNP_HASHSECRET, raw).lower()

        if calc != received:
            return None  # chữ ký sai

        try:
            order_id_str, payment_id_str = (params.get("vnp_OrderInfo") or "0-0").split("-")
            order_id = int(order_id_str)
            payment_id = int(payment_id_str)
        except Exception:
            return None

        trans_status = params.get("vnp_TransactionStatus")
        rsp_code = params.get("vnp_ResponseCode")
        trans_no = params.get("vnp_TransactionNo")
        amount_vnp = int(params.get("vnp_Amount", "0")) // 100  # đổi lại VND

        pay: Payment | None = Payment.query.get(payment_id)
        order: Order | None = Order.query.get(order_id)
        if not pay or not order or pay.order_id != order.id:
            return {"error": "Payment/Order mismatch", **params}

        # Đối chiếu số tiền để an toàn
        if int(Decimal(pay.amount)) != amount_vnp:
            return {"error": "Amount mismatched", **params}

        if trans_status == "00" and rsp_code == "00":
            update_payment_status(payment_id, PaymentStatus.SUCCESS, trans_no)
        else:
            update_payment_status(payment_id, PaymentStatus.FAILED, trans_no)

        return params

    @staticmethod
    def verifyReturn(params: dict) -> dict:
        """
        Xác thực gói RETURN từ VNPay để hiển thị cho người dùng.
        KHÔNG cập nhật DB (IPN mới là nguồn sự thật).
        Trả về:
          {
            ok: bool (đã verify chữ ký),
            resultCode: str (vnp_ResponseCode),
            message: str | None,
            orderId: str | None,
            paymentId: str | None,
            amount: int | None,      # VND (đã /100)
            transId: str | None,     # vnp_TransactionNo
          }
        """
        received = (params.get("vnp_SecureHash") or "").lower()

        # Lọc các tham số vnp_*, loại SecureHash & SecureHashType
        filtered = {
            k: v for k, v in params.items()
            if k.startswith("vnp_") and k not in ("vnp_SecureHash", "vnp_SecureHashType")
        }

        # Chuỗi raw theo quy tắc VNPay: sort key + URL-encode
        raw = VNPayServiceImpl._encode_pairs_sorted(filtered)

        # Tính chữ ký
        calc = hmac_sha512(VNPayConfigs.VNP_HASHSECRET, raw).lower()
        ok = (calc == received)

        # Parse thông tin phục vụ UI
        try:
            order_id_str, payment_id_str = (params.get("vnp_OrderInfo") or "0-0").split("-")
        except Exception:
            order_id_str, payment_id_str = None, None

        # vnp_Amount là số tiền *100
        try:
            amount_vnd = int(params.get("vnp_Amount", "0")) // 100
        except Exception:
            amount_vnd = None

        return {
            "ok": ok,
            "resultCode": params.get("vnp_ResponseCode"),
            "message": params.get("vnp_Message") or None,  # thường không có, để None cũng được
            "orderId": order_id_str,
            "paymentId": payment_id_str,
            "amount": amount_vnd,
            "transId": params.get("vnp_TransactionNo"),
        }
