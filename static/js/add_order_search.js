document.addEventListener("DOMContentLoaded", () => {

    // Global search functionality
    const globalSearchInput = document.createElement('input');
    globalSearchInput.type = 'text';
    globalSearchInput.id = 'globalSearch';
    globalSearchInput.className = 'form-control mb-3';
    globalSearchInput.placeholder = '🔍 Global Search (Products, Parties, Orders...)';

    const searchResultsDiv = document.createElement('div');
    searchResultsDiv.id = 'globalSearchResults';
    searchResultsDiv.style.display = 'none';

    // Insert global search at the top of the card body
    const cardBody = document.querySelector('.card-body');
    cardBody.insertBefore(globalSearchInput, cardBody.firstChild);
    cardBody.insertBefore(searchResultsDiv, globalSearchInput.nextSibling);

    /* =====
       GLOBAL SEARCH
    ===== */
    let searchTimeout;
    globalSearchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(performGlobalSearch, 300);
    });

    function performGlobalSearch() {
        const query = globalSearchInput.value.toLowerCase().trim();
        if (query.length < 2) {
            searchResultsDiv.style.display = 'none';
            return;
        }

        const results = [];

        // Search products
        document.querySelectorAll('.product option').forEach(option => {
            if (option.value && option.text.toLowerCase().includes(query)) {
                results.push({
                    type: 'Product',
                    text: option.text,
                    action: () => addProductToOrder(option.value)
                });
            }
        });

        // Search parties
        document.querySelectorAll('#partySelect option').forEach(option => {
            if (option.value && option.text.toLowerCase().includes(query)) {
                results.push({
                    type: 'Party',
                    text: option.text,
                    action: () => selectParty(option.value)
                });
            }
        });

        // Mock order history search
        if (query.includes('order') || query.includes('history')) {
            results.push({
                type: 'Order History',
                text: 'View recent orders',
                action: () => window.location.href = '/commerce/order_list/'
            });
        }

        displaySearchResults(results);
    }

    function displaySearchResults(results) {
        if (results.length === 0) {
            searchResultsDiv.style.display = 'none';
            return;
        }

        searchResultsDiv.innerHTML = results.map(result =>
            `<div class="search-result-item" onclick="this.action()">
                <strong>${result.type}:</strong> ${result.text}
            </div>`
        ).join('');

        // Add click handlers
        searchResultsDiv.querySelectorAll('.search-result-item').forEach((item, index) => {
            item.action = results[index].action;
        });

        searchResultsDiv.style.display = 'block';
    }

    function addProductToOrder(productId) {
        // Find first empty row or add new
        let emptyRow = null;
        document.querySelectorAll('.item-row').forEach(row => {
            const select = row.querySelector('.product');
            if (!select.value) {
                emptyRow = row;
                return;
            }
        });

        if (!emptyRow) {
            document.getElementById('addRow').click();
            emptyRow = document.querySelector('.item-row:last-child');
        }

        const select = emptyRow.querySelector('.product');
        select.value = productId;
        select.dispatchEvent(new Event('change'));

        // Hide search results
        searchResultsDiv.style.display = 'none';
        globalSearchInput.value = '';
    }

    function selectParty(partyId) {
        document.getElementById('partySelect').value = partyId;
        searchResultsDiv.style.display = 'none';
        globalSearchInput.value = '';
    }

    // Hide search results when clicking outside
    document.addEventListener('click', (e) => {
        if (!globalSearchInput.contains(e.target) && !searchResultsDiv.contains(e.target)) {
            searchResultsDiv.style.display = 'none';
        }
    });

    /* =====
       PARTY SEARCH
    ===== */
    const partySearch = document.getElementById("partySearch");
    const partySelect = document.getElementById("partySelect");

    partySearch.addEventListener("keyup", () => {
        const text = partySearch.value.toLowerCase();
        [...partySelect.options].forEach(opt => {
            if (!opt.value) return;
            opt.style.display = opt.text.toLowerCase().includes(text) ? "block" : "none";
        });
    });

    /* =====
       PRODUCT SEARCH PER ROW
    ===== */
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

    /* =====
       CALCULATION
    ===== */
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

    /* =====
       ADD ITEM
    ===== */
    document.getElementById("addItem").addEventListener("click", () => {
        const body = document.getElementById("orderBody");
        const row = body.querySelector(".item-row").cloneNode(true);

        row.querySelectorAll("input").forEach(i => i.value = "");
        row.querySelector(".qty").value = 1;

        body.appendChild(row);
        setupProductRow(row);
    });

    /* =====
       REMOVE ITEM
    ===== */
    document.addEventListener("click", e => {
        if (e.target.classList.contains("remove-btn")) {
            e.target.closest("tr").remove();
            calculateTotal();
        }
    });

    /* INIT FIRST ROW */
    setupProductRow(document.querySelector(".item-row"));
});
