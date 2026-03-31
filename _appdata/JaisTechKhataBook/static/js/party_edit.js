// Basic validation & confirm before submit
document.getElementById("editPartyForm").addEventListener("submit", function(e) {
    const name = document.querySelector("input[name='name']").value.trim();
    const mobile = document.querySelector("input[name='mobile']").value.trim();

    if (name === "" || mobile === "") {
        alert("Name and Mobile are mandatory fields.");
        e.preventDefault();
    }

    return true;
});
