import os
from dotenv import load_dotenv
load_dotenv()

MOMO_PARTNER_CODE = os.getenv("MOMO_PARTNER_CODE")
MOMO_ACCESS_KEY = os.getenv("MOMO_ACCESS_KEY")
MOMO_SECRET_KEY = os.getenv("MOMO_SECRET_KEY")
MOMO_REDIRECT_URL = os.getenv("MOMO_REDIRECT_URL")
MOMO_IPN_URL = os.getenv("MOMO_IPN_URL")
MOMO_ENDPOINT = os.getenv("MOMO_ENDPOINT")
MOMO_REQUEST_TYPE = os.getenv("MOMO_REQUEST_TYPE", "payWithATM")