// Smooth hover animation effect (extra polish)
document.querySelectorAll(".plan-card").forEach(card => {
    card.addEventListener("mouseenter", () => {
        card.style.transition = "0.3s";
    });
});
