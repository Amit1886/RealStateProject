// sidebar.js
document.addEventListener("DOMContentLoaded", function () {

    const sidebar = document.getElementById("sidebar");
    const toggleBtn = document.getElementById("togglePin");

    if (!sidebar || !toggleBtn) return;

    // true = pinned (always open)
    // false = collapsed (hover open)
    let pinned = true;

    /* ====
       TOGGLE (PIN / UNPIN)
    ===== */
    toggleBtn.addEventListener("click", function () {
        sidebar.classList.toggle("collapsed");
        pinned = !sidebar.classList.contains("collapsed");
        sidebar.classList.remove("hover-open");
    });

    /* ====
       HOVER OPEN WHEN COLLAPSED
    ===== */
    sidebar.addEventListener("mouseenter", function () {
        if (!pinned) {
            sidebar.classList.add("hover-open");
        }
    });

    sidebar.addEventListener("mouseleave", function () {
        if (!pinned) {
            sidebar.classList.remove("hover-open");
        }
    });

    /* ====
       SUBMENU TOGGLE
    ===== */
    document.querySelectorAll(".submenu-toggle").forEach(btn => {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            this.parentElement.classList.toggle("open");
        });
    });

});
