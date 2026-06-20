"""WebSocket draw server — streams overlay shapes to the in-page JS client.

This is the "painting back to the page" channel: Python decides what to draw,
the browser overlay (bridge/overlay_client.js) renders it. For now it just
streams a red box at screen center with a live counter, to prove the pipe.
Later this carries real detections from the perceiver.

Setup:
    pip install websockets

Run:
    python bridge/draw_server.py
    # then open slither.io, F12 console, paste bridge/overlay_client.js

Shapes are relative (0..1) so they map to any viewport size:
    {"kind":"rect","x":0.5,"y":0.5,"w":0.15,"h":0.12,"color":"#ff0000",
     "label":"CENTER","lineWidth":3}   # x,y = box center
"""

import asyncio
import json
import logging
import sys

# Quiet the noisy "did not receive a valid HTTP request" tracebacks from port
# probes / scanners hitting the listening socket — not real WS clients.
logging.getLogger("websockets").setLevel(logging.CRITICAL)

# Bind IPv4 loopback explicitly. Using "localhost" is a trap on Windows: it
# can resolve to IPv6 ::1 while the browser connects to 127.0.0.1 (or vice
# versa) and they never meet. Pin both ends to 127.0.0.1 to avoid that.
HOST = "127.0.0.1"
PORT = 8765


def center_box(label: str) -> dict:
    return {
        "type": "draw",
        "shapes": [{
            "kind": "rect", "x": 0.5, "y": 0.5, "w": 0.15, "h": 0.12,
            "color": "#ff0000", "label": label, "lineWidth": 3,
        }],
    }


async def handler(ws, *_):  # *_ tolerates the older (ws, path) signature
    print("client connected")
    i = 0
    try:
        while True:
            await ws.send(json.dumps(center_box(f"CENTER {i}")))
            i += 1
            await asyncio.sleep(0.5)  # visible live updates
    except Exception:
        pass
    finally:
        print("client disconnected")


async def main():
    try:
        import websockets
    except ImportError:
        print("websockets not installed.  Run:  pip install websockets")
        sys.exit(1)

    async with websockets.serve(handler, HOST, PORT):
        print(f"draw server: ws://{HOST}:{PORT}")
        print("paste bridge/overlay_client.js into the slither.io console to see the box.")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nstopped.")
