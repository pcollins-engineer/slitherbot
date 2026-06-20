// slitherbot overlay — background service worker.
//
// Holds the WebSocket to the local draw server and relays shapes to the
// content script(s) over a runtime Port. Doing the network from the SW is
// what makes this work on slither.io:
//   - SW requests are attributed to the chrome-extension:// origin, which is
//     a SECURE CONTEXT with our host_permissions, so they're exempt from both
//     the page CSP and Private Network Access (the loopback block that stops a
//     page-origin fetch to 127.0.0.1).
//   - Chrome 116+ keeps the SW alive while a WebSocket is receiving messages,
//     and the server streams every 0.2s, so it won't be culled.

const WS_URL = "ws://127.0.0.1:8765";
const ports = new Set();
let ws = null;
let latest = null;

function broadcast(msg) {
  for (const p of ports) {
    try { p.postMessage(msg); } catch (e) { /* port gone */ }
  }
}

function connectWS() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
  try {
    ws = new WebSocket(WS_URL);
  } catch (e) {
    return setTimeout(connectWS, 1500);
  }
  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      latest = msg;
      broadcast(msg);
    } catch (e) { /* ignore */ }
  };
  ws.onclose = () => { ws = null; setTimeout(connectWS, 1500); };
  ws.onerror = () => { try { ws.close(); } catch (e) {} };
}

chrome.runtime.onConnect.addListener((port) => {
  ports.add(port);
  if (latest) { try { port.postMessage(latest); } catch (e) {} }
  port.onDisconnect.addListener(() => ports.delete(port));
  connectWS(); // a page connecting wakes the SW -> (re)open the socket
});

connectWS(); // also attempt on SW startup
