(function () {
  const form = document.getElementById("orderForm");
  if (!form) return;

  const partySearch = document.getElementById("partySearch");
  const partySelect = document.getElementById("partySelect");
  const partySuggest = document.getElementById("partySuggest");
  const orderBody = document.getElementById("orderBody");
  const productMaster = document.getElementById("productMaster");
  const itemInfo = document.getElementById("itemInfo");

  const discountModal = document.getElementById("discountModal");
  const popupPrice = document.getElementById("popupPrice");
  const popupDiscount = document.getElementById("popupDiscount");
  const applyDiscountBtn = document.getElementById("applyDiscountBtn");
  const closeDiscountBtn = document.getElementById("closeDiscountBtn");

  let activePartyIndex = -1;
  let activeRow = null;
  const MIN_BLANK_ROWS = 5;
  let ensuringRows = false;
  let scanBuffer = "";
  let scanTimer = null;

  const parties = [...partySelect.options]
    .filter((o) => o.value)
    .map((o) => ({ id: o.value, name: o.textContent.trim() }));

  const products = [...productMaster.options]
    .filter((o) => o.value)
    .map((o) => ({
      id: o.value,
      name: o.dataset.name || o.textContent.trim(),
      price: Number(o.dataset.price || 0),
      stock: Number(o.dataset.stock || 0),
      unit: o.dataset.unit || "Nos",
      barcode: o.dataset.barcode || "",
    }));

  function money(n) {
    return (Number(n) || 0).toFixed(2);
  }

  function notify(message, type = "info") {
    window.dispatchEvent(
      new CustomEvent("ui:toast", {
        detail: { message, type },
      })
    );
  }

  function buildPartySuggest(list) {
    if (!list.length) {
      partySuggest.style.display = "none";
      return;
    }
    partySuggest.innerHTML = list
      .map(
        (p, idx) =>
          `<div class="suggest-item ${idx === activePartyIndex ? "active" : ""}" data-party-id="${p.id}">
            ${p.name}
          </div>`
      )
      .join("");
    partySuggest.style.display = "block";
  }

  function pickParty(id) {
    const party = parties.find((p) => String(p.id) === String(id));
    if (!party) return;
    partySelect.value = party.id;
    partySearch.value = party.name;
    partySuggest.style.display = "none";
    document.getElementById("partyMeta").textContent = `Selected: ${party.name}`;
    const firstProduct = firstBlankRowProductInput() || orderBody.querySelector("tr:first-child .product-search");
    if (firstProduct) firstProduct.focus();
  }

  function firstBlankRowProductInput() {
    const blankRow = [...orderBody.querySelectorAll("tr")].find((tr) => !rowIsFilled(tr));
    return blankRow ? blankRow.querySelector(".product-search") : null;
  }

  partySearch.addEventListener("input", function () {
    const text = this.value.trim().toLowerCase();
    activePartyIndex = -1;
    if (!text) {
      partySuggest.style.display = "none";
      return;
    }
    const result = parties.filter((p) => p.name.toLowerCase().includes(text)).slice(0, 15);
    buildPartySuggest(result);
  });

  partySearch.addEventListener("keydown", function (e) {
    const items = [...partySuggest.querySelectorAll(".suggest-item")];
    if (!items.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      activePartyIndex = Math.min(activePartyIndex + 1, items.length - 1);
      items.forEach((el, idx) => el.classList.toggle("active", idx === activePartyIndex));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activePartyIndex = Math.max(activePartyIndex - 1, 0);
      items.forEach((el, idx) => el.classList.toggle("active", idx === activePartyIndex));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const target = items[activePartyIndex] || items[0];
      if (target) pickParty(target.dataset.partyId);
    }
  });

  partySuggest.addEventListener("click", (e) => {
    const item = e.target.closest(".suggest-item");
    if (!item) return;
    pickParty(item.dataset.partyId);
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".party-search-wrap")) partySuggest.style.display = "none";
  });

  function recalcRow(tr) {
    const qty = Number(tr.querySelector(".qty").value || 0);
    const price = Number(tr.querySelector(".price").value || 0);
    const discount = Number(tr.querySelector(".discount").value || 0);
    const gross = qty * price;
    const net = gross - gross * (discount / 100);
    tr.querySelector(".amount").value = money(net);
  }

  function recalcTotals() {
    let subtotal = 0;
    [...orderBody.querySelectorAll("tr")].forEach((tr) => {
      recalcRow(tr);
      subtotal += Number(tr.querySelector(".amount").value || 0);
    });
    document.getElementById("subTotal").textContent = money(subtotal);
    const taxValue = subtotal * 0.18;
    const grandValue = subtotal + taxValue;
    document.getElementById("tax").textContent = money(taxValue);
    document.getElementById("grandTotal").textContent = money(grandValue);
    const taxableAmt = document.getElementById("taxableAmt");
    const igstAmt = document.getElementById("igstAmt");
    const taxTotalFooter = document.getElementById("taxTotalFooter");
    if (taxableAmt) taxableAmt.textContent = money(subtotal);
    if (igstAmt) igstAmt.textContent = money(taxValue);
    if (taxTotalFooter) taxTotalFooter.textContent = money(grandValue);
  }

  function rowIsFilled(tr) {
    const pid = tr.querySelector(".product-id").value;
    const name = tr.querySelector(".product-search").value.trim();
    const price = Number(tr.querySelector(".price").value || 0);
    return Boolean(pid || name || price > 0);
  }

  function blankRowCount() {
    return [...orderBody.querySelectorAll("tr")].filter((tr) => !rowIsFilled(tr)).length;
  }

  function closeSuggest(tr) {
    const box = tr.querySelector(".product-suggest");
    if (box) box.style.display = "none";
  }

  function buildProductSuggest(tr, list) {
    const box = tr.querySelector(".product-suggest");
    if (!box) return;
    tr.dataset.pidx = "-1";
    if (!list.length) {
      box.style.display = "none";
      return;
    }
    box.innerHTML = list
      .map(
        (p) =>
          `<div class="suggest-item" data-product-id="${p.id}">
            ${p.name}
            <small>Stock: ${p.stock} | Price: ${money(p.price)} | Unit: ${p.unit}</small>
          </div>`
      )
      .join("");
    box.style.display = "block";
  }

  function fillProduct(tr, product) {
    tr.querySelector(".product-id").value = product.id;
    tr.querySelector(".product-search").value = product.name;
    tr.querySelector(".unit").value = product.unit;
    tr.querySelector(".price").value = money(product.price);
    tr.dataset.stock = String(product.stock);
    tr.dataset.basePrice = String(product.price);
    closeSuggest(tr);
    recalcTotals();
    itemInfo.innerHTML = `Name: <strong>${product.name}</strong><br>Stock: <strong>${product.stock}</strong> ${product.unit}<br>Rate: <strong>${money(product.price)}</strong>`;
    tr.querySelector(".qty").focus();
    tr.scrollIntoView({ block: "nearest" });
    ensureBlankRows();
  }

  function rowHTML(index) {
    return `
      <td>${index}</td>
      <td>
        <input class="product-search" autocomplete="off" placeholder="Type item name">
        <input type="hidden" name="product[]" class="product-id">
        <div class="product-suggest suggest-box"></div>
      </td>
      <td><input type="number" min="1" value="1" name="qty[]" class="qty"></td>
      <td><input type="text" class="unit" value="Nos" readonly></td>
      <td><input type="number" step="0.01" name="price[]" class="price"></td>
      <td><input type="number" step="0.01" min="0" max="100" value="0" class="discount"></td>
      <td><input type="text" class="amount" readonly></td>
    `;
  }

  function reindexRows() {
    [...orderBody.querySelectorAll("tr")].forEach((tr, idx) => {
      tr.children[0].textContent = String(idx + 1);
    });
  }

  function openDiscountPopup(tr) {
    activeRow = tr;
    popupPrice.value = tr.querySelector(".price").value || "0";
    popupDiscount.value = tr.querySelector(".discount").value || "0";
    discountModal.style.display = "flex";
    popupPrice.focus();
  }

  function applyPopup() {
    if (!activeRow) return;
    activeRow.querySelector(".price").value = popupPrice.value || "0";
    activeRow.querySelector(".discount").value = popupDiscount.value || "0";
    recalcTotals();
    discountModal.style.display = "none";
    focusNextRowProduct(activeRow);
  }

  function focusNextRowProduct(tr) {
    ensureBlankRows();
    let next = tr.nextElementSibling;
    while (next && rowIsFilled(next)) {
      next = next.nextElementSibling;
    }
    if (!next) next = tr.nextElementSibling || addRow();
    const input = next ? next.querySelector(".product-search") : null;
    if (input) input.focus();
  }

  function attachRowEvents(tr) {
    const search = tr.querySelector(".product-search");
    const qty = tr.querySelector(".qty");
    const price = tr.querySelector(".price");
    const discount = tr.querySelector(".discount");
    const amount = tr.querySelector(".amount");
    const productId = tr.querySelector(".product-id");

    search.addEventListener("input", () => {
      const text = search.value.trim().toLowerCase();
      if (!text) {
        buildProductSuggest(tr, []);
        productId.value = "";
        return;
      }
      const result = products.filter((p) => p.name.toLowerCase().includes(text)).slice(0, 15);
      buildProductSuggest(tr, result);
    });

    search.addEventListener("keydown", (e) => {
      const list = [...tr.querySelectorAll(".product-suggest .suggest-item")];
      if (e.key === "ArrowDown") {
        e.preventDefault();
        let idx = Number(tr.dataset.pidx || -1);
        idx = Math.min(idx + 1, list.length - 1);
        tr.dataset.pidx = String(idx);
        list.forEach((el, i) => el.classList.toggle("active", i === idx));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        let idx = Number(tr.dataset.pidx || -1);
        idx = Math.max(idx - 1, 0);
        tr.dataset.pidx = String(idx);
        list.forEach((el, i) => el.classList.toggle("active", i === idx));
        return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        if (list.length) {
          const idx = Number(tr.dataset.pidx || -1);
          const target = idx >= 0 ? list[idx] : list[0];
          const product = products.find((p) => String(p.id) === String(target.dataset.productId));
          if (product) fillProduct(tr, product);
          return;
        }
        const text = search.value.trim().toLowerCase();
        const exact = products.find((p) => p.name.toLowerCase() === text);
        if (exact) {
          fillProduct(tr, exact);
        } else if (tr.querySelector(".product-id").value) {
          qty.focus();
        }
      }
    });

    tr.querySelector(".product-suggest").addEventListener("click", (e) => {
      const item = e.target.closest(".suggest-item");
      if (!item) return;
      const product = products.find((p) => String(p.id) === String(item.dataset.productId));
      if (product) fillProduct(tr, product);
    });

    [qty, price, discount].forEach((input) => {
      input.addEventListener("input", () => {
        if (input === qty && Number(qty.value || 0) <= 0) qty.value = "1";
        recalcTotals();
        ensureBlankRows();
      });
      input.addEventListener("focus", () => {
        if (typeof input.select === "function") input.select();
      });
    });

    tr.addEventListener("focusin", () => {
      [...orderBody.querySelectorAll("tr")].forEach((row) => row.classList.remove("row-active"));
      tr.classList.add("row-active");
    });

    qty.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        price.focus();
      }
    });

    price.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        openDiscountPopup(tr);
      }
    });

    discount.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        focusNextRowProduct(tr);
      }
    });

    amount.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        openDiscountPopup(tr);
      }
    });
  }

  function addRow() {
    const tr = document.createElement("tr");
    tr.innerHTML = rowHTML(orderBody.querySelectorAll("tr").length + 1);
    orderBody.appendChild(tr);
    attachRowEvents(tr);
    reindexRows();
    recalcTotals();
    return tr;
  }

  function bindExistingRows() {
    const rows = [...orderBody.querySelectorAll("tr")];
    rows.forEach((tr) => {
      if (tr.dataset.bound === "1") return;
      attachRowEvents(tr);
      tr.dataset.bound = "1";
    });
    reindexRows();
    recalcTotals();
  }

  function ensureBlankRows() {
    if (ensuringRows) return;
    ensuringRows = true;
    let guard = 0;
    while (blankRowCount() < MIN_BLANK_ROWS && guard < 20) {
      addRow();
      guard += 1;
    }
    ensuringRows = false;
  }

  function getTargetRowForScan() {
    const focusedRow = document.activeElement ? document.activeElement.closest("tr") : null;
    if (focusedRow) return focusedRow;
    const firstBlank = [...orderBody.querySelectorAll("tr")].find((tr) => !rowIsFilled(tr));
    if (firstBlank) return firstBlank;
    return addRow();
  }

  function applyScannedCode(code) {
    const normalized = (code || "").trim().toLowerCase();
    if (!normalized) return false;
    const product = products.find(
      (p) =>
        String(p.barcode || "").trim().toLowerCase() === normalized ||
        String(p.name || "").trim().toLowerCase() === normalized
    );
    if (!product) return false;
    const targetRow = getTargetRowForScan();
    fillProduct(targetRow, product);
    notify(`Scanned: ${product.name}`, "success");
    return true;
  }

  applyDiscountBtn.addEventListener("click", applyPopup);
  closeDiscountBtn.addEventListener("click", () => {
    discountModal.style.display = "none";
    if (activeRow) activeRow.querySelector(".discount").focus();
  });
  discountModal.addEventListener("click", (e) => {
    if (e.target === discountModal) discountModal.style.display = "none";
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "F2") {
      e.preventDefault();
      partySearch.focus();
    } else if (e.key === "F3") {
      e.preventDefault();
      const active = document.activeElement.closest("tr");
      const target = active ? active.querySelector(".product-search") : firstBlankRowProductInput() || orderBody.querySelector("tr:last-child .product-search");
      if (target) target.focus();
    } else if (e.key === "F4") {
      e.preventDefault();
      const row = addRow();
      row.querySelector(".product-search").focus();
    } else if (e.key === "F7") {
      e.preventDefault();
      const row = document.activeElement.closest("tr");
      if (row) openDiscountPopup(row);
    } else if (e.key === "F8") {
      e.preventDefault();
      form.requestSubmit();
    } else if (e.ctrlKey && e.key.toLowerCase() === "s") {
      e.preventDefault();
      form.requestSubmit();
    } else if (e.ctrlKey && e.key === "Enter") {
      e.preventDefault();
      form.requestSubmit();
    }

    if (e.key === "Enter" && scanBuffer.length >= 4) {
      const consumed = applyScannedCode(scanBuffer);
      scanBuffer = "";
      if (scanTimer) window.clearTimeout(scanTimer);
      if (consumed) e.preventDefault();
      return;
    }

    if (
      e.key.length === 1 &&
      !e.ctrlKey &&
      !e.altKey &&
      !e.metaKey &&
      !["Tab", "Shift"].includes(e.key)
    ) {
      scanBuffer += e.key;
      if (scanTimer) window.clearTimeout(scanTimer);
      scanTimer = window.setTimeout(() => {
        scanBuffer = "";
      }, 120);
    }
  });

  window.addEventListener("global:scan:data", (event) => {
    const code = (event.detail && event.detail.code) || "";
    applyScannedCode(code);
  });

  form.addEventListener("submit", (e) => {
    if (!partySelect.value) {
      e.preventDefault();
      notify("Please select party.", "warning");
      partySearch.focus();
      return;
    }
    const rows = [...orderBody.querySelectorAll("tr")];
    const valid = rows.some((tr) => tr.querySelector(".product-id").value && Number(tr.querySelector(".qty").value || 0) > 0);
    if (!valid) {
      e.preventDefault();
      notify("Add at least one valid item.", "warning");
      return;
    }
  });

  bindExistingRows();
  ensureBlankRows();
})();
