# app/services/momo_service.py (bản sync)
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from decimal import Decimal
import base64, json, requests
from app.utils.momo_utils import hmac_sha256_hex
from flask import Request
from app.models import Order, Payment, PaymentStatus
from app.configs import momo_configs as MoMoConfigs
from app.dao.payment_dao import create_payment, update_payment_status

class AccessDeniedException(Exception):
    pass

class MoMoService:

    @staticmethod
    def _build_create_raw(*, amount:int, order_id:str, order_info:str, request_id:str, request_type:str, extra_data_b64:str) -> str:
        parts = [
            f"accessKey={MoMoConfigs.MOMO_ACCESS_KEY}",
            f"amount={amount}",
            f"extraData={extra_data_b64}",
            f"ipnUrl={MoMoConfigs.MOMO_IPN_URL}",
            f"orderId={order_id}",
            f"orderInfo={order_info}",
            f"partnerCode={MoMoConfigs.MOMO_PARTNER_CODE}",
            f"redirectUrl={MoMoConfigs.MOMO_REDIRECT_URL}",
            f"requestId={request_id}",
            f"requestType={request_type}",
        ]
        return "&".join(parts)

    def createMomoPayment(self, *, order_id:int, amount_override:Optional[int]=None, order_info:Optional[str]=None) -> dict:
        # 1) Lấy order + đối chiếu tiền
        order = Order.query.get(order_id)
        if not order:
            raise AccessDeniedException("Không tìm thấy đơn hàng")
        amount_vnd = int(Decimal(order.total_amount))
        if amount_override is not None and int(amount_override) != amount_vnd:
            raise AccessDeniedException("Số tiền không khớp đơn hàng")

        # 3) Tạo Payment(PENDING) mới
        pay = create_payment(order.id, amount_vnd)
        print(pay)

        # 3) Tham số MoMo
        tz = timezone(timedelta(hours=7))
        request_id = str(int(datetime.now(tz).timestamp() * 1000))
        momo_order_id = f"{order.id}-{pay.id}"
        order_info = (order_info or "Thanh toan ve su kien").strip()
        request_type = MoMoConfigs.MOMO_REQUEST_TYPE.strip()

        extra_json = json.dumps({"orderId": order.id, "paymentId": pay.id}, separators=(",", ":"))
        extra_b64 = base64.b64encode(extra_json.encode("utf-8")).decode("utf-8")

        raw = self._build_create_raw(
            amount=amount_vnd,
            order_id=momo_order_id,
            order_info=order_info,
            request_id=request_id,
            request_type=request_type,
            extra_data_b64=extra_b64
        )
        signature = hmac_sha256_hex(raw, MoMoConfigs.MOMO_SECRET_KEY)

        payload = {
            "partnerCode": MoMoConfigs.MOMO_PARTNER_CODE,
            "partnerName": "MoMo",
            "storeId": "TicketApp",
            "requestId": request_id,
            "amount": amount_vnd,
            "orderId": momo_order_id,
            "orderInfo": order_info,
            "redirectUrl": MoMoConfigs.MOMO_REDIRECT_URL,
            "ipnUrl": MoMoConfigs.MOMO_IPN_URL,
            "lang": "vi",
            "requestType": request_type,
            "extraData": extra_b64,
            "signature": signature,
        }

        # 4) Gọi MoMo /create (sync)
        try:
            resp = requests.post(MoMoConfigs.MOMO_ENDPOINT, json=payload, timeout=45)
            data = resp.json()
        except Exception as e:
            update_payment_status(pay.id, PaymentStatus.FAILED, transaction_no=None)
            return {"error": f"MoMo create exception: {e.__class__.__name__}", "paymentId": pay.id}

        pay_url = (data or {}).get("payUrl") or (data or {}).get("deeplink")
        if not pay_url:
            update_payment_status(pay.id, PaymentStatus.FAILED, transaction_no=None)
            return {"error": "MoMo create failed", "momo": data, "paymentId": pay.id}

        return {"payUrl": pay_url, "paymentId": pay.id}

    # IPN cho momo gọi về
    def processIPN(self, ipn: Dict[str, Any]) -> Dict[str, Any]:
        order = [
            "accessKey","amount","extraData","message","orderId","orderInfo","orderType",
            "partnerCode","payType","requestId","responseTime","resultCode","transId"
        ]
        def safe(v): return "" if v is None else str(v).strip()
        raw = "&".join(f"{k}={safe(ipn.get(k))}" for k in order)
        # thay accessKey bằng của mình như Java
        raw = raw.replace(f"accessKey={safe(ipn.get('accessKey'))}", f"accessKey={MoMoConfigs.MOMO_ACCESS_KEY}", 1)

        my_sig = hmac_sha256_hex(raw, MoMoConfigs.MOMO_SECRET_KEY)
        momo_sig = (ipn.get("signature") or "").strip()
        if my_sig != momo_sig:
            return {"resultCode": 97, "message": "Invalid signature"}

        try:
            order_id_str, payment_id_str = (ipn.get("orderId") or "0-0").split("-", 1)
            order_id = int(order_id_str); payment_id = int(payment_id_str)
        except Exception:
            return {"resultCode": 98, "message": "Invalid orderId format"}

        amount = int(ipn.get("amount", 0))
        result_code = str(ipn.get("resultCode", ""))
        trans_id = ipn.get("transId")

        pay: Payment | None = Payment.query.get(payment_id)
        ord: Order | None = Order.query.get(order_id)
        if not pay or not ord or pay.order_id != ord.id:
            return {"resultCode": 96, "message": "Payment/Order mismatch"}

        if int(Decimal(pay.amount)) != amount:
            return {"resultCode": 95, "message": "Amount mismatched"}

        if result_code == "0":
            update_payment_status(payment_id, PaymentStatus.SUCCESS, trans_id)
            return {"resultCode": 0, "message": "Success"}
        else:
            update_payment_status(payment_id, PaymentStatus.FAILED, trans_id)
            return {"resultCode": 0, "message": "Payment failed"}

#Xac minh tu return cua momo
    def verifyReturn(self, params: Dict[str, Any]) -> Dict[str, Any]:
        order = [
            "accessKey", "amount", "extraData", "message", "orderId", "orderInfo", "orderType",
            "partnerCode", "payType", "requestId", "responseTime", "resultCode", "transId"
        ]

        def safe(v):
            return "" if v is None else str(v).strip()

        raw = "&".join(f"{k}={safe(params.get(k))}" for k in order)
        raw = raw.replace(
            f"accessKey={safe(params.get('accessKey'))}",
            f"accessKey={MoMoConfigs.MOMO_ACCESS_KEY}",
            1
        )

        #Van kiem tra lai chu ky cho chac
        my_sig = hmac_sha256_hex(raw, MoMoConfigs.MOMO_SECRET_KEY)
        momo_sig = (params.get("signature") or "").strip()
        ok = (my_sig == momo_sig)

        # parse orderId -> orderId, paymentId (để hiện lên UI)
        o_id, p_id = None, None
        try:
            o_id, p_id = (params.get("orderId") or "0-0").split("-", 1)
        except Exception:
            pass

        return {
            "ok": ok,
            "resultCode": params.get("resultCode"),
            "message": params.get("message"),
            "orderId": o_id,
            "paymentId": p_id,
            "amount": params.get("amount"),
            "transId": params.get("transId"),
        }