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

from app.core.storage import load_fcm_credentials, save_fcm_credentials

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
            return
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
                credentials=load_fcm_credentials(),
                credentials_updated_callback=self._on_credentials_updated,
            )

            last_exc = None
            for attempt in range(5):
                try:
                    self._fcm_token = await self._client.checkin_or_register()
                    last_exc = None
                    break
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    last_exc = exc
                    await asyncio.sleep(min(2 ** attempt, 30))
            if last_exc is not None:
                raise last_exc
            self._token_event.set()
            self.token_ready.emit(self._fcm_token or "")
            await self._client.start()
        except asyncio.CancelledError:
            raise
        except Exception:
            logging.getLogger(__name__).exception("FCM listener setup failed")
            self._token_event.set()

    async def _teardown(self):
        if self._client is not None and self._client.is_started():
            await self._client.stop()

    def _on_credentials_updated(self, creds):
        save_fcm_credentials(creds)

    def _on_notification(self, notification, persistent_id, obj):

        data = notification.get("data", notification) if notification else {}
        self.push_received.emit(dict(data))
