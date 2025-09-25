import hmac, hashlib

def hmac_sha256_hex(message: str, secret_key: str) -> str:
    signature = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return signature