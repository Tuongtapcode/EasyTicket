import os
from dotenv import load_dotenv
#Load bien moi truong
load_dotenv()

VNP_TMNCODE = os.getenv("VNP_TMNCODE")
VNP_HASHSECRET = os.getenv("VNP_HASHSECRET")
VNP_URL = os.getenv("VNP_URL")
VNP_RETURNURL = os.getenv("VNP_RETURNURL")
VNP_IPNURL = os.getenv("VNP_IPNURL")
VNP_VERSION=os.getenv("VNP_VERSION")
VNP_COMMAND=os.getenv("COMMAND")
