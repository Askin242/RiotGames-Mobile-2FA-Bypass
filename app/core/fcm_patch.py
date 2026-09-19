"""Runtime fix for a decryption crash in firebase-messaging 0.4.5.

`FcmPushClient._decrypt_raw_data` base64url-decodes the push `crypto-key` and
`salt` WITHOUT re-adding padding. Those values are unpadded base64url (an EC
public key is 65 bytes -> 87 chars, never a multiple of 4), so every encrypted
push raises `binascii.Error: Incorrect padding`. The library treats that as a
fatal "Unknown error" and shuts the whole listener down, so no pushes are ever
delivered. Upstream 0.4.5 is the latest release, so we patch it in place.
"""

import base64
import logging

log = logging.getLogger(__name__)

_applied = False


def _b64pad(value):
    """Add the base64url padding the library omits."""
    return value + "=" * (-len(value) % 4)


def apply():
    """Replace the buggy _decrypt_raw_data with a padding-safe version. Idempotent."""
    global _applied
    if _applied:
        return
    try:
        from firebase_messaging import fcmpushclient as _fpc
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.serialization import load_der_private_key
        from http_ece import decrypt as http_decrypt
    except Exception:
        log.exception("fcm_patch: could not import firebase-messaging internals")
        return

    @staticmethod
    def _decrypt_raw_data(credentials, crypto_key_str, salt_str, raw_data):
        crypto_key = base64.urlsafe_b64decode(_b64pad(crypto_key_str).encode("ascii"))
        salt = base64.urlsafe_b64decode(_b64pad(salt_str).encode("ascii"))
        der_data = base64.urlsafe_b64decode(
            _b64pad(credentials["keys"]["private"]).encode("ascii")
        )
        secret = base64.urlsafe_b64decode(
            _b64pad(credentials["keys"]["secret"]).encode("ascii")
        )
        privkey = load_der_private_key(der_data, password=None, backend=default_backend())
        return http_decrypt(
            raw_data,
            salt=salt,
            private_key=privkey,
            dh=crypto_key,
            version="aesgcm",
            auth_secret=secret,
        )

    _fpc.FcmPushClient._decrypt_raw_data = _decrypt_raw_data
    _applied = True
    log.debug("fcm_patch: applied padding-safe _decrypt_raw_data")
