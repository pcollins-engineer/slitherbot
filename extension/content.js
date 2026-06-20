// slitherbot overlay — content script (drawing only).
//
// The network lives in background.js (service worker) to get past slither's
// page CSP and Chrome's Private Network Access loopback block. This script
// just draws an overlay canvas and fills it from shapes relayed over a
// runtime Port from the SW.

(function () {
  const ID = "slitherbot-overlay";
  // The overlay canvas IS the web viewport, which already excludes Chrome's
  // tabs/address bar. The capture region (on the Python side) is set to the
  // matching on-screen gameplay rect, so shapes map straight onto the full
  // viewport here — no extra offset.
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

  function connectPort() {
    let port;
    try {
      port = chrome.runtime.connect({ name: "overlay" });
    } catch (e) {
      linkState = "down";
      return setTimeout(connectPort, 1500);
    }
    port.onMessage.addListener((msg) => {
      if (msg && msg.type === "draw" && Array.isArray(msg.shapes)) {
        shapes = msg.shapes;
        linkState = "ok";
      }
    });
    port.onDisconnect.addListener(() => {
      linkState = "down";
      setTimeout(connectPort, 1500); // SW recycled -> reconnect
    });
  }
  connectPort();

  console.log("[slitherbot] overlay content-script active (network via service worker)");
})();
