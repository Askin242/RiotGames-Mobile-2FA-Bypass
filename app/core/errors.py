"""Error types and a verbose exception describer shared by the API and UI.

The describer turns any exception — a plain error, a `requests` failure, or a
`RiotApiError` — into a full text dump (request line, status, headers, body,
traceback) suitable for a copy-paste "details" pane. This is an open-source
tool, so the dump is deliberately exhaustive to make issue reports easy.
"""

import json
import traceback

_MAX_BODY_CHARS = 20000

class RiotApiError(Exception):
    """An API call that completed but returned an unexpected or failed payload.

    Carries the originating `requests.Response` (when there is one) so the UI
    can surface the full server reply.
    """

    def __init__(self, message, response=None):
        super().__init__(message)
        self.response = response

def _format_body(response):
    try:
        parsed = response.json()
        return json.dumps(parsed, indent=2, ensure_ascii=False)[:_MAX_BODY_CHARS]
    except Exception:
        pass
    try:
        text = response.text
    except Exception:
        return "(body unavailable)"
    if not text:
        return "(empty body)"
    return text[:_MAX_BODY_CHARS]

def describe_exception(exc):
    """Return an exhaustive, copy-pasteable description of `exc`."""
    lines = [f"{type(exc).__name__}: {exc}"]

    response = getattr(exc, "response", None)
    request = getattr(response, "request", None) or getattr(exc, "request", None)

    if request is not None:
        method = getattr(request, "method", "?")
        url = getattr(request, "url", "?")
        lines += ["", f"Request: {method} {url}"]

    if response is not None:
        reason = getattr(response, "reason", "") or ""
        lines += ["", f"Status: {response.status_code} {reason}".rstrip()]
        try:
            headers = "\n".join(f"  {k}: {v}" for k, v in response.headers.items())
            if headers:
                lines += ["Response headers:", headers]
        except Exception:
            pass
        lines += ["Response body:", _format_body(response)]

    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).rstrip()
    if tb:
        lines += ["", "Traceback:", tb]

    return "\n".join(lines)
