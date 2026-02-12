/* =
   DASHBOARD JS – FINAL WORKING FILE
   = */

console.log("dashboard.js loaded"); // DEBUG LINE

/* ---------------------------------------------------------
   SIDEBAR TOGGLE
--------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", function () {

    const toggleBtn = document.getElementById("togglePin");
    const sidebar = document.getElementById("sidebar");
    const main = document.querySelector(".main-content");

    if (toggleBtn && sidebar && main) {
        toggleBtn.addEventListener("click", function () {
            sidebar.classList.toggle("closed");
            main.classList.toggle("full");
        });
    }

    /* Close action menus when clicking outside */
    document.addEventListener("click", function (e) {
        if (!e.target.closest(".action-card")) {
            document.querySelectorAll(".action-menu").forEach(menu => {
                menu.style.display = "none";
            });
        }
    });

});

/* ---------------------------------------------------------
   TODAY SUMMARY – MORE DETAILS TOGGLE
   (Called from onclick="")
--------------------------------------------------------- */
window.toggleSummaryDetails = function () {
    const box = document.getElementById("summaryDetails");

    if (!box) {
        console.warn("summaryDetails not found");
        return;
    }

    box.style.display =
        box.style.display === "none" || box.style.display === ""
            ? "block"
            : "none";
};

/* ---------------------------------------------------------
   ACTION CARD DROPDOWN (⋮ MENU)
   (Commerce / Accounts / Billing etc.)
--------------------------------------------------------- */
window.toggleActionMenu = function (id) {
    const menu = document.getElementById(id);
    if (!menu) return;

    /* Close other open menus */
    document.querySelectorAll(".action-menu").forEach(el => {
        if (el !== menu) el.style.display = "none";
    });

    menu.style.display =
        menu.style.display === "block" ? "none" : "block";
};
