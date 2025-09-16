import io, qrcode
from base64 import b64encode

def make_qr_png_base64(data: str) -> str:
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + b64encode(buf.getvalue()).decode()
