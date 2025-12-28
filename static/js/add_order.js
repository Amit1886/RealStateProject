// PARTY SEARCH
document.getElementById("partySearch").addEventListener("keyup", function () {
    let value = this.value.toLowerCase();
    let options = document.querySelectorAll("#partySelect option");

    options.forEach(opt => {
        opt.style.display = opt.textContent.toLowerCase().includes(value) ? "block" : "none";
    });
});

// ADD ITEM ROW
document.getElementById("addItem").addEventListener("click", function () {
    let row = document.querySelector(".item-row").cloneNode(true);

    row.querySelectorAll("input").forEach(i => i.value = "");
    row.querySelector(".product").selectedIndex = 0;

    document.getElementById("orderBody").appendChild(row);
});

// REMOVE ITEM
document.addEventListener("click", function (e) {
    if (e.target.classList.contains("remove-btn")) {
        if (document.querySelectorAll(".item-row").length > 1) {
            e.target.closest("tr").remove();
            calculateTotal();
        }
    }
});

// AUTO PRICE & AMOUNT
document.addEventListener("change", function (e) {
    if (e.target.classList.contains("product")) {
        let row = e.target.closest("tr");
        let price = e.target.selectedOptions[0].dataset.price || 0;
        row.querySelector(".price").value = price;
        calculateRow(row);
    }
});

document.addEventListener("keyup", function (e) {
    if (e.target.classList.contains("qty") || e.target.classList.contains("price")) {
        calculateRow(e.target.closest("tr"));
    }
});

function calculateRow(row) {
    let qty = parseFloat(row.querySelector(".qty").value) || 0;
    let price = parseFloat(row.querySelector(".price").value) || 0;
    let amt = qty * price;

    row.querySelector(".amount").value = amt.toFixed(2);
    calculateTotal();
}

function calculateTotal() {
    let total = 0;
    document.querySelectorAll(".amount").forEach(a => {
        total += parseFloat(a.value) || 0;
    });
    document.getElementById("totalBox").innerHTML = "Total: ₹" + total.toFixed(2);
}

// PRODUCT SEARCH PER ROW
document.addEventListener("keyup", function (e) {
    if (e.target.classList.contains("product-search")) {
        let search = e.target.value.toLowerCase();
        let select = e.target.closest("td").querySelector(".product");

        for (let opt of select.options) {
            opt.style.display = opt.textContent.toLowerCase().includes(search) ? "block" : "none";
        }
    }
});

// SHORTCUTS
document.addEventListener("keydown", function (e) {
    if (e.altKey && e.key === "a") {
        e.preventDefault();
        document.getElementById("addItem").click();
    }

    if (e.ctrlKey && e.key === "Enter") {
        e.preventDefault();
        document.getElementById("saveBtn").click();
    }

    if (e.ctrlKey && e.key === "p") {
        e.preventDefault();
        document.getElementById("printBtn").click();
    }

    if (e.ctrlKey && e.key === "d") {
        e.preventDefault();
        document.getElementById("downloadPdfBtn").click();
    }
});

// PRINT
document.getElementById("printBtn").addEventListener("click", function () {
    window.print();
});

// PDF (You will handle via Django URL)
document.getElementById("downloadPdfBtn").addEventListener("click", function () {
    let orderId = document.getElementById("orderId")?.value;
    if (orderId) {
        window.location.href = `/commerce/order/${orderId}/pdf/`;
    }
});
