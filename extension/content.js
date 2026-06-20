// slitherbot overlay — content-script version (load via chrome://extensions).
//
// Same overlay as bridge/overlay_client.js, but run as an extension content
// script. It executes in the extension's ISOLATED WORLD, which:
//   - is NOT subject to the page's Content-Security-Policy, and
//   - uses its own native WebSocket (so a page that monkeypatches/blocks
//     window.WebSocket can't stop it).
// That's why this connects to ws://127.0.0.1:8765 on slither.io while a
// console-pasted script does not.

(function () {
  const WS_URL = "ws://127.0.0.1:8765";
  const ID = "slitherbot-overlay";

  if (document.getElementById(ID)) return; // already injected

  const cv = document.createElement("canvas");
  cv.id = ID;
  Object.assign(cv.style, {
    position: "fixed", left: "0", top: "0",
    width: "100vw", height: "100vh",
    pointerEvents: "none",
    zIndex: "2147483647",
  });
  document.documentElement.appendChild(cv);
  const ctx = cv.getContext("2d");

  let shapes = [{ kind: "rect", x: 0.5, y: 0.5, w: 0.15, h: 0.12,
                  color: "#ff0000", label: "CENTER", lineWidth: 3 }];
  let wsState = "connecting";

  function resize() {
    const dpr = window.devicePixelRatio || 1;
    cv.width = Math.floor(window.innerWidth * dpr);
    cv.height = Math.floor(window.innerHeight * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  resize();
  window.addEventListener("resize", resize);

  function draw() {
    const W = window.innerWidth, H = window.innerHeight;
    ctx.clearRect(0, 0, W, H);
    for (const s of shapes) {
      if (s.kind !== "rect") continue;
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
    ctx.fillStyle = wsState === "open" ? "#00ff66" : "#ffaa00";
    ctx.font = "13px monospace";
    ctx.fillText("slitherbot overlay (extension) | ws: " + wsState, 8, 16);
    requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);

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
      } catch (e) { /* ignore */ }
    };
  }
  connect();

  console.log("[slitherbot] overlay content-script active (isolated world) -> " + WS_URL);
})();
