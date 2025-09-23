import hmac
import hashlib

def hmac_sha512(key: str, data: str) -> str:
    try:
        hm = hmac.new(key.encode("utf-8"), data.encode("utf-8"), hashlib.sha512)
        return hm.hexdigest()
    except Exception as ex:
        raise RuntimeError(f"Lỗi ký HMAC: {ex}")
