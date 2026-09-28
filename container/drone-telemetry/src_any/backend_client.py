"""Container -> Container backend link (C5): POST telemetry JSON over HTTP."""

import json
import urllib.error
import urllib.request


class BackendClient(object):
    def __init__(self, url, timeout=3.0):
        self.url = url
        self.timeout = timeout
        self._last_ok = None

    @property
    def enabled(self):
        return bool(self.url)

    def send(self, telemetry):
        """POST one telemetry record. Never raises; returns True on HTTP 2xx."""
        if not self.enabled:
            return False
        body = json.dumps(telemetry).encode("utf-8")
        request = urllib.request.Request(
            self.url, data=body, method="POST",
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                ok = 200 <= response.status < 300
        except (urllib.error.URLError, OSError, ValueError) as exc:
            ok = False
            if self._last_ok is not False:
                print("[backend] cannot deliver telemetry to %s: %s" % (self.url, exc), flush=True)
        if ok and self._last_ok is not True:
            print("[backend] delivering telemetry to %s" % self.url, flush=True)
        self._last_ok = ok
        return ok
