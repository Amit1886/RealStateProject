document.addEventListener("keydown", function (e) {
    const acceptBtn = document.querySelector(".btn-success.action-btn");
    const rejectBtn = document.querySelector(".btn-danger.action-btn");
    const backBtn = document.querySelector(".back-btn");

    if (e.key.toLowerCase() === "a" && acceptBtn) {
        acceptBtn.click();
    }
    if (e.key.toLowerCase() === "r" && rejectBtn) {
        rejectBtn.click();
    }
    if (e.key.toLowerCase() === "b" && backBtn) {
        backBtn.click();
    }
});
