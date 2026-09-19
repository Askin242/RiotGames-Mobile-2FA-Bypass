"""Background Firebase Cloud Messaging listener.

Emulates the Riot mobile app's FCM client so Riot pushes login attempts to this
desktop. Runs the async `firebase-messaging` client on its own event loop in a
dedicated thread and surfaces received pushes to the Qt GUI via a signal.

Protocol / Firebase config recovered from the decompiled Riot mobile app.
"""

import asyncio
import logging
import threading

from PyQt6.QtCore import QObject, pyqtSignal

from firebase_messaging import FcmPushClient, FcmRegisterConfig

from app.core.storage import (
    load_fcm_credentials,
    save_fcm_credentials,
    load_persistent_ids,
    save_persistent_ids,
)
from app.core.debug_log import mask
from app.core import fcm_patch

log = logging.getLogger(__name__)

fcm_patch.apply()

FIREBASE_PROJECT_ID = "leagueconnect-1f13a"
FIREBASE_APP_ID = "1:595870631183:android:cdbf60becd73557e"
FIREBASE_API_KEY = "AIzaSyCxhfh9jZtDD2KBUUO6d7HySuzG4xjdR4o"
FIREBASE_SENDER_ID = "595870631183"
ANDROID_PACKAGE = "com.riotgames.mobile.leagueconnect"

logging.getLogger("firebase_messaging").setLevel(logging.CRITICAL)

class FcmService(QObject):
    """Owns the FCM client. Lives on the GUI thread; runs IO on a worker thread.

    Signals:
        push_received(dict): the MfaNotificationData payload of a login attempt.
        token_ready(str): emitted once the FCM token is known.
    """

    push_received = pyqtSignal(dict)
    token_ready = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loop = None
        self._thread = None
        self._client = None
        self._fcm_token = None
        self._token_event = threading.Event()
        self._persistent_ids = load_persistent_ids()

    @property
    def fcm_token(self):
        return self._fcm_token

    def wait_for_token(self, timeout=30):
        """Block (caller thread) until the FCM token is available, or timeout."""
        if self._token_event.wait(timeout):
            return self._fcm_token
        return None

    def start(self):
        if self._thread is not None:
            log.debug("FcmService.start() ignored — already running")
            return
        log.debug("FcmService.start() — launching listener thread")
        self._thread = threading.Thread(
            target=self._run, name="fcm-listener", daemon=True
        )
        self._thread.start()

    def stop(self):
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        self._loop.create_task(self._setup())
        try:
            self._loop.run_forever()
        finally:

            self._token_event.set()
            try:
                self._loop.run_until_complete(self._teardown())
            except Exception:
                pass
            self._loop.close()

    async def _setup(self):
        try:
            creds = load_fcm_credentials()
            log.debug(
                "FCM setup: stored credentials %s, seeded persistent_ids=%d",
                "present" if creds else "MISSING (will register fresh)",
                len(self._persistent_ids),
            )
            config = FcmRegisterConfig(
                project_id=FIREBASE_PROJECT_ID,
                app_id=FIREBASE_APP_ID,
                api_key=FIREBASE_API_KEY,
                messaging_sender_id=FIREBASE_SENDER_ID,
                bundle_id=ANDROID_PACKAGE,
            )
            self._client = FcmPushClient(
                self._on_notification,
                config,
                credentials=creds,
                credentials_updated_callback=self._on_credentials_updated,
                received_persistent_ids=list(self._persistent_ids),
            )

            last_exc = None
            for attempt in range(5):
                try:
                    log.debug("checkin_or_register attempt %d/5", attempt + 1)
                    self._fcm_token = await self._client.checkin_or_register()
                    last_exc = None
                    log.debug("FCM token acquired: %s", mask(self._fcm_token))
                    break
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    last_exc = exc
                    log.warning(
                        "checkin_or_register attempt %d failed: %r", attempt + 1, exc
                    )
                    await asyncio.sleep(min(2 ** attempt, 30))
            if last_exc is not None:
                raise last_exc
            self._token_event.set()
            self.token_ready.emit(self._fcm_token or "")
            log.debug("FCM listener starting (connecting to MCS)…")
            await self._client.start()
            log.debug("FCM listener connected and running")
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("FCM listener setup FAILED — no pushes will arrive")
            self._token_event.set()

    async def _teardown(self):
        if self._client is not None and self._client.is_started():
            await self._client.stop()

    def _on_credentials_updated(self, creds):
        log.debug("FCM credentials updated/persisted")
        save_fcm_credentials(creds)

    def _on_notification(self, notification, persistent_id, obj):
        log.debug(
            "PUSH received: persistent_id=%s raw=%r", persistent_id, notification
        )
        if persistent_id:
            self._persistent_ids.append(persistent_id)
            try:
                save_persistent_ids(self._persistent_ids)
            except Exception:
                log.exception("failed to persist persistent_ids")

        data = notification.get("data", notification) if notification else {}
        log.debug("PUSH data payload -> %r", dict(data))
        self.push_received.emit(dict(data))
