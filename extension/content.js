// slitherbot overlay — content-script version (load via chrome://extensions).
//
// Draws an overlay canvas on top of slither.io and fills it from the local
// draw server. It POLLS http://127.0.0.1:8766/shapes with fetch rather than
// using a WebSocket, because:
//   - slither blocks page-context WebSockets, and
//   - a content-script WebSocket is STILL checked against the page CSP, but
//   - a content-script `fetch` is NOT (it uses the extension's net stack).
// So fetch-polling is the transport that actually gets through on slither.io.

(function () {
  const URL = "http://127.0.0.1:8766/shapes";
  const POLL_MS = 100; // 10 Hz; plenty for an overlay
  const ID = "slitherbot-overlay";

  if (document.getElementById(ID)) return;

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
  let linkState = "connecting";

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
    ctx.fillStyle = linkState === "ok" ? "#00ff66" : "#ffaa00";
    ctx.font = "13px monospace";
    ctx.fillText("slitherbot overlay (extension) | link: " + linkState, 8, 16);
    requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);

  async function poll() {
    try {
      const res = await fetch(URL, { cache: "no-store" });
      const msg = await res.json();
      if (msg.type === "draw" && Array.isArray(msg.shapes)) shapes = msg.shapes;
      linkState = "ok";
    } catch (e) {
      linkState = "down";
    }
  }
  setInterval(poll, POLL_MS);
  poll();

  console.log("[slitherbot] overlay content-script active, polling " + URL);
})();
