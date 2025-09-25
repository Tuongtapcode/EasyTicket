# app/utils/qr_utils.py
import base64, hmac, hashlib, json
from flask import current_app

def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

def _b64url_decode(s: str) -> bytes:
    pad = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

def sign_payload(payload: dict) -> str:
    """
    Tạo token QR: base64url(header).base64url(payload).base64url(signature)
    """
    secret = current_app.config["QR_SECRET"].encode()
    header = {"alg": "HS256", "typ": "QR"}
    h = _b64url(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode())
    p = _b64url(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode())
    sig = _b64url(hmac.new(secret, f"{h}.{p}".encode(), hashlib.sha256).digest())
    return f"{h}.{p}.{sig}"

def verify_token(token: str):
    """
    Trả (is_valid: bool, payload: dict|None, message: str)
    """
    try:
        h, p, sig = token.split(".")
        secret = current_app.config["QR_SECRET"].encode()
        expect = _b64url(hmac.new(secret, f"{h}.{p}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expect, sig):
            return False, None, "Invalid signature"
        payload = json.loads(_b64url_decode(p))
        return True, payload, "OK"
    except Exception as ex:
        return False, None, f"Malformed QR: {ex}"
