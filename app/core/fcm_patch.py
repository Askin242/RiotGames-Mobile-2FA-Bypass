"""Runtime fixes for firebase-messaging 0.4.5 that break push delivery.

Two problems, both patched here because 0.4.5 is the latest release:

1. `_decrypt_raw_data` base64url-decodes the push `crypto-key` and `salt`
   WITHOUT re-adding padding. Those values are unpadded base64url (an EC public
   key is 65 bytes -> 87 chars, never a multiple of 4), so every encrypted push
   raised `binascii.Error: Incorrect padding`. We pad correctly.

2. The library aborts the ENTIRE listener on any exception while handling a data
   message (`_handle_data_message`). A single undecryptable/malformed message —
   e.g. a replayed backlog or housekeeping message whose crypto-key isn't a
   valid EC point ("Invalid EC key") — therefore permanently kills push, and
   since it dies before acking, the same message replays on every connect. We
   wrap `_handle_data_message` so a bad message is logged and skipped; the
   caller then acks it (so it stops replaying) and the listener keeps running.
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

    # Make data-message handling resilient: one bad push must not kill the
    # listener. Returning normally lets the caller ack the message so it stops
    # replaying on every connect.
    _orig_handle = _fpc.FcmPushClient._handle_data_message
    if not getattr(_orig_handle, "_riot2fa_wrapped", False):

        def _safe_handle_data_message(self, msg):
            try:
                return _orig_handle(self, msg)
            except Exception:
                pid = getattr(msg, "persistent_id", None)
                log.warning(
                    "fcm_patch: skipping a push that could not be handled "
                    "(persistent_id=%s) — listener stays up",
                    pid,
                    exc_info=True,
                )
                return None

        _safe_handle_data_message._riot2fa_wrapped = True
        _fpc.FcmPushClient._handle_data_message = _safe_handle_data_message

    _applied = True
    log.debug("fcm_patch: applied padding-safe decrypt + resilient message handling")
