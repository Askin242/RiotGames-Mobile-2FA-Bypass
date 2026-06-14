import time
import hmac
import hashlib
import base64
import urllib.parse

PERIOD = 30
DIGITS = 6

def totp_sha256(seed_b32, period=PERIOD, digits=DIGITS, t=None):
    if t is None:
        t = int(time.time())
    key = base64.b32decode(seed_b32.upper().encode("ascii"))
    counter = int(t / period)
    msg = counter.to_bytes(8, "big")
    h = hmac.new(key, msg, hashlib.sha256).digest()
    offset = h[-1] & 0x0F
    code_int = (
        ((h[offset] & 0x7F) << 24)
        | ((h[offset + 1] & 0xFF) << 16)
        | ((h[offset + 2] & 0xFF) << 8)
        | (h[offset + 3] & 0xFF)
    )
    code_int %= 10**digits
    return str(code_int).zfill(digits)

def get_code(seed):
    return totp_sha256(seed)

def extract_seed(s):
    s = s.strip()
    if s.startswith(("http://", "https://", "otpauth://")):
        u = urllib.parse.urlparse(s)
        qs = urllib.parse.parse_qs(u.query)

        for key in ("seed", "secret"):
            if qs.get(key):
                return qs[key][0]
        parts = s.split("?", 1)
        if len(parts) > 1:
            for kv in parts[1].split("&"):
                for key in ("seed=", "secret="):
                    if kv.startswith(key):
                        return kv.split("=", 1)[1]
        return None
    return s or None
