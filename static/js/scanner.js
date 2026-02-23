(function (global) {
  const state = { items: [] };

  function detectType(code) {
    if (!code) return "unknown";
    if (/^https?:\/\//.test(code) || code.length > 20) return "qr";
    if (/^\d{8,14}$/.test(code)) return "ean";
    if (code.includes("-")) return "code128";
    return "generic";
  }

  function addItem(code, refs) {
    const item = { code, type: detectType(code), qty: 1, price: 10 };
    state.items.push(item);
    render(refs);
  }

  function render(refs) {
    refs.lineItems.innerHTML = state.items.map((x, i) => `<div>${i + 1}. ${x.code} (${x.type}) x${x.qty} = ${(x.qty * x.price).toFixed(2)}</div>`).join("");
    const total = state.items.reduce((a, x) => a + x.qty * x.price, 0);
    refs.total.textContent = `Total: ${total.toFixed(2)}`;
  }

  function queueOffline(payload) {
    const key = "pos_offline_queue";
    const queue = JSON.parse(localStorage.getItem(key) || "[]");
    queue.push(payload);
    localStorage.setItem(key, JSON.stringify(queue));
  }

  function bindShortcuts(refs) {
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        state.items = [];
        render(refs);
      }
      if (e.key === "F5") queueOffline({ type: "hold_bill", items: state.items, at: Date.now() });
    });
  }

  function init(cfg) {
    const refs = {
      input: document.getElementById(cfg.inputId),
      lineItems: document.getElementById(cfg.lineItemsId),
      total: document.getElementById(cfg.totalId),
      sound: document.getElementById(cfg.soundId),
    };

    bindShortcuts(refs);

    refs.input.addEventListener("change", () => {
      addItem(refs.input.value.trim(), refs);
      refs.input.value = "";
      if (refs.sound) refs.sound.play().catch(() => {});
      if (navigator.vibrate) navigator.vibrate(20);
    });

    const syncBtn = document.getElementById("sync-btn");
    if (syncBtn) {
      syncBtn.addEventListener("click", () => {
        const key = "pos_offline_queue";
        const queue = JSON.parse(localStorage.getItem(key) || "[]");
        console.log("Sync placeholder", queue);
        localStorage.setItem(key, "[]");
      });
    }
  }

  global.POSScanner = { init, detectType };
})(window);
