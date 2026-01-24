document.addEventListener("DOMContentLoaded", () => {

    /* ==========================
       PARTY SEARCH
    ========================== */
    const partySearch = document.getElementById("partySearch");
    const partySelect = document.getElementById("partySelect");

    partySearch.addEventListener("keyup", () => {
        const text = partySearch.value.toLowerCase();
        [...partySelect.options].forEach(opt => {
            if (!opt.value) return;
            opt.style.display = opt.text.toLowerCase().includes(text) ? "block" : "none";
        });
    });

    /* ==========================
       PRODUCT SEARCH PER ROW
    ========================== */
    function setupProductRow(row) {

        const searchInput = row.querySelector(".product-search");
        const select = row.querySelector(".product");
        const priceInput = row.querySelector(".price");
        const qtyInput = row.querySelector(".qty");
        const amountInput = row.querySelector(".amount");

        /* PRODUCT SEARCH */
        searchInput.addEventListener("keyup", () => {
            const val = searchInput.value.toLowerCase();
            [...select.options].forEach(opt => {
                if (!opt.value) return;
                opt.style.display = opt.text.toLowerCase().includes(val) ? "block" : "none";
            });
        });

        /* AUTO PRICE */
        select.addEventListener("change", () => {
            const price = select.selectedOptions[0]?.dataset.price || 0;
            priceInput.value = price;
            calculateRow(row);
        });

        qtyInput.addEventListener("input", () => calculateRow(row));
        priceInput.addEventListener("input", () => calculateRow(row));
    }

    /* ==========================
       CALCULATION
    ========================== */
    function calculateRow(row) {
        const qty = parseFloat(row.querySelector(".qty").value) || 0;
        const price = parseFloat(row.querySelector(".price").value) || 0;
        const amount = qty * price;
        row.querySelector(".amount").value = amount.toFixed(2);
        calculateTotal();
    }

    function calculateTotal() {
        let total = 0;
        document.querySelectorAll(".amount").forEach(a => {
            total += parseFloat(a.value) || 0;
        });
        document.getElementById("totalBox").innerText = `Total: ₹${total.toFixed(2)}`;
    }

    /* ==========================
       ADD ITEM
    ========================== */
    document.getElementById("addItem").addEventListener("click", () => {
        const body = document.getElementById("orderBody");
        const row = body.querySelector(".item-row").cloneNode(true);

        row.querySelectorAll("input").forEach(i => i.value = "");
        row.querySelector(".qty").value = 1;

        body.appendChild(row);
        setupProductRow(row);
    });

    /* ==========================
       REMOVE ITEM
    ========================== */
    document.addEventListener("click", e => {
        if (e.target.classList.contains("remove-btn")) {
            e.target.closest("tr").remove();
            calculateTotal();
        }
    });

    /* INIT FIRST ROW */
    setupProductRow(document.querySelector(".item-row"));
});
