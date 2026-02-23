export function createSystemModeSocket({ onModeChanged }) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${protocol}//${window.location.host}/ws/system-mode/`;
  const socket = new WebSocket(url);

  socket.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.event_type === "system.mode.changed") {
        onModeChanged?.(payload.payload || {});
      }
    } catch (err) {
      // ignore malformed messages
    }
  };

  return socket;
}
