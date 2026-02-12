// ==
// PRODUCT DETAIL JS
// ==

document.addEventListener("DOMContentLoaded", function () {
    const deleteBtn = document.querySelector(".btn-delete");

    if (deleteBtn) {
        deleteBtn.addEventListener("click", function (e) {
            const confirmDelete = confirm(
                "⚠️ Are you sure you want to delete this product?\nThis action cannot be undone."
            );
            if (!confirmDelete) {
                e.preventDefault();
            }
        });
    }
});
