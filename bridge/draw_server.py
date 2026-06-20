"""Draw server — serves overlay shapes over BOTH WebSocket and HTTP.

Why two transports:
  - WebSocket (ws://127.0.0.1:8765) — low latency; works from pages that allow
    it (e.g. github) and from the console.
  - HTTP poll (http://127.0.0.1:8766/shapes) — works from a browser EXTENSION
    content script even on slither.io. slither blocks page-context WebSockets,
    and a content-script WebSocket is still checked against the page CSP, but a
    content-script `fetch` is not. So the extension polls this endpoint.

Both serve the same shared state. For now it's a red center box with a live
counter; later this carries real detections.

Setup:  pip install websockets
Run:    python bridge/draw_server.py
"""

import asyncio
import json
import logging
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

logging.getLogger("websockets").setLevel(logging.CRITICAL)  # hush port-scan noise

HOST = "127.0.0.1"   # pin IPv4 (localhost can resolve to ::1 and miss the browser)
WS_PORT = 8765
HTTP_PORT = 8766

_state = {"type": "draw", "shapes": []}
_lock = threading.Lock()


def set_shapes(shapes):
    with _lock:
        _state["shapes"] = shapes


def state_json() -> str:
    with _lock:
        return json.dumps(_state)


def center_box(label: str):
    return [{"kind": "rect", "x": 0.5, "y": 0.5, "w": 0.15, "h": 0.12,
             "color": "#ff0000", "label": label, "lineWidth": 3}]


# ---------- HTTP (for the extension content script to poll) ----------

class _Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/shapes"):
            body = state_json().encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self._cors()
            self.end_headers()

    def log_message(self, *args):  # silence per-request logging
        pass


def run_http():
    ThreadingHTTPServer((HOST, HTTP_PORT), _Handler).serve_forever()


# ---------- WebSocket (for console / permissive pages) ----------

async def ws_handler(ws, *_):
    try:
        while True:
            await ws.send(state_json())
            await asyncio.sleep(0.2)
    except Exception:
        pass


async def ticker():
    i = 0
    while True:
        set_shapes(center_box(f"CENTER {i}"))
        i += 1
        await asyncio.sleep(0.5)


async def serve(updater=None):
    """Start the WS + HTTP transports. If ``updater`` (an async coroutine) is
    given it runs alongside; otherwise shapes are expected to be pushed via
    ``set_shapes`` from elsewhere (e.g. live_overlay.py's capture thread)."""
    try:
        import websockets
    except ImportError:
        print("websockets not installed.  Run:  pip install websockets")
        sys.exit(1)

    threading.Thread(target=run_http, daemon=True).start()
    async with websockets.serve(ws_handler, HOST, WS_PORT):
        print(f"draw server up:")
        print(f"  ws   -> ws://{HOST}:{WS_PORT}            (extension service worker / console)")
        print(f"  http -> http://{HOST}:{HTTP_PORT}/shapes  (fetch fallback)")
        if updater is not None:
            await updater()
        else:
            await asyncio.Future()


async def main():
    await serve(ticker)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nstopped.")
