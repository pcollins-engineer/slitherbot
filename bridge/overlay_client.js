// slitherbot overlay client — paste into the slither.io page devtools console.
//
// Creates a transparent click-through <canvas> on top of the page and draws
// shapes onto it. On load it draws a red box at screen center (the "is this
// alive" test). If the Python draw server (bridge/draw_server.py) is running,
// it streams shapes over WebSocket and overrides the self-test box.
//
// We draw on our OWN overlay canvas, not the game's canvas — the game clears
// and repaints its canvas every frame, so anything drawn there vanishes.
//
// Remove it later with:  window.__slitherbotOverlay.stop()

(function () {
  const WS_URL = "ws://127.0.0.1:8765";  // IPv4 explicitly (avoids localhost->::1 mismatch)
  const ID = "slitherbot-overlay";

  const existing = document.getElementById(ID);
  if (existing) existing.remove();

  const cv = document.createElement("canvas");
  cv.id = ID;
  Object.assign(cv.style, {
    position: "fixed", left: "0", top: "0",
    width: "100vw", height: "100vh",
    pointerEvents: "none",           // click-through: never steals input
    zIndex: "2147483647",            // above everything
  });
  document.body.appendChild(cv);
  const ctx = cv.getContext("2d");

  let shapes = [];
  let wsState = "connecting";

  function resize() {
    const dpr = window.devicePixelRatio || 1;
    cv.width = Math.floor(window.innerWidth * dpr);
    cv.height = Math.floor(window.innerHeight * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); // draw in CSS pixels, crisp on HiDPI
  }
  resize();
  window.addEventListener("resize", resize);

  function draw() {
    const W = window.innerWidth, H = window.innerHeight;
    ctx.clearRect(0, 0, W, H);

    for (const s of shapes) {
      if (s.kind !== "rect") continue;
      // x,y,w,h are RELATIVE (0..1); x,y = center of the box.
      const x = (s.x ?? 0.5) * W, y = (s.y ?? 0.5) * H;
      const w = (s.w ?? 0.1) * W, h = (s.h ?? 0.1) * H;
      ctx.lineWidth = s.lineWidth || 3;
      ctx.strokeStyle = s.color || "#ff0000";
      ctx.strokeRect(x - w / 2, y - h / 2, w, h);
      if (s.label) {
        ctx.fillStyle = s.color || "#ff0000";
        ctx.font = "16px monospace";
        ctx.fillText(s.label, x - w / 2, y - h / 2 - 6);
      }
    }

    // tiny status readout
    ctx.fillStyle = wsState === "open" ? "#00ff66" : "#ffaa00";
    ctx.font = "13px monospace";
    ctx.fillText("slitherbot overlay | ws: " + wsState, 8, 16);

    requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);

  // fun self-test: red box at center until/unless the server sends shapes
  shapes = [{ kind: "rect", x: 0.5, y: 0.5, w: 0.15, h: 0.12,
              color: "#ff0000", label: "CENTER", lineWidth: 3 }];

  function connect() {
    let ws;
    try {
      ws = new WebSocket(WS_URL);
    } catch (e) {
      wsState = "error";
      return setTimeout(connect, 2000);
    }
    wsState = "connecting";
    ws.onopen = () => { wsState = "open"; };
    ws.onclose = () => { wsState = "closed"; setTimeout(connect, 2000); };
    ws.onerror = () => { wsState = "error"; };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "draw" && Array.isArray(msg.shapes)) shapes = msg.shapes;
      } catch (e) { /* ignore malformed */ }
    };
  }
  connect();

  window.__slitherbotOverlay = {
    stop() { window.removeEventListener("resize", resize); cv.remove(); },
  };
  console.log("[slitherbot] overlay injected — red CENTER box should be visible. "
            + "window.__slitherbotOverlay.stop() to remove.");
})();
