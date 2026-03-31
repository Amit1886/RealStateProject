(function () {
  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
      return;
    }
    fn();
  }

  function ensureToastHost() {
    let host = document.getElementById("uiToastHost");
    if (host) return host;
    host = document.createElement("div");
    host.id = "uiToastHost";
    host.style.position = "fixed";
    host.style.right = "14px";
    host.style.bottom = "14px";
    host.style.zIndex = "99999";
    host.style.display = "grid";
    host.style.gap = "8px";
    host.style.maxWidth = "320px";
    document.body.appendChild(host);
    return host;
  }

  function toast(message, type) {
    if (!message) return;
    var host = ensureToastHost();
    var el = document.createElement("div");
    var bg = "#123a8f";
    if (type === "success") bg = "#0f766e";
    if (type === "warning") bg = "#a16207";
    if (type === "error") bg = "#b91c1c";
    el.style.background = bg;
    el.style.color = "#fff";
    el.style.padding = "10px 12px";
    el.style.borderRadius = "8px";
    el.style.boxShadow = "0 10px 24px rgba(15,23,42,.24)";
    el.style.fontSize = "12px";
    el.style.fontWeight = "700";
    el.style.lineHeight = "1.35";
    el.textContent = message;
    host.appendChild(el);
    window.setTimeout(function () {
      el.style.opacity = "0";
      el.style.transform = "translateY(6px)";
      el.style.transition = "all .2s ease";
      window.setTimeout(function () {
        if (el && el.parentNode) el.parentNode.removeChild(el);
      }, 220);
    }, 2100);
  }

  ready(function () {
    document.body.classList.add("ui-polished");

    window.addEventListener("ui:toast", function (e) {
      var detail = (e && e.detail) || {};
      toast(detail.message, detail.type || "info");
    });

    document.addEventListener("keydown", function (e) {
      // Ctrl+/ quickly focuses list search input.
      if (e.ctrlKey && e.key === "/") {
        var search = document.querySelector("[data-master-search]");
        if (search) {
          e.preventDefault();
          search.focus();
          if (typeof search.select === "function") search.select();
        }
      }
    });

    document.addEventListener("focusin", function (e) {
      var el = e.target;
      if (!el) return;
      var group = el.closest(".unified-section");
      if (group) group.style.boxShadow = "0 0 0 2px rgba(18,58,143,.12)";
    });

    document.addEventListener("focusout", function (e) {
      var el = e.target;
      if (!el) return;
      var group = el.closest(".unified-section");
      if (group) group.style.boxShadow = "";
    });
  });
})();
