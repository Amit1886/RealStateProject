document.addEventListener("input", () => {
  let total = 0;

  document.querySelectorAll("#itemTable tbody tr").forEach(row => {
    const qty = row.querySelector('[name="qty"]').value || 0;
    const price = row.querySelector('[name="price"]').value || 0;
    const amount = qty * price;
    row.querySelector(".amount").innerText = amount.toFixed(2);
    total += amount;
  });

  document.getElementById("taxable").innerText = total.toFixed(2);

  const saleType = document.getElementById("saleType").value;

  let cgst = 0, sgst = 0, igst = 0;

  if (saleType === "central_12") {
    cgst = total * 0.06;
    sgst = total * 0.06;
  } else {
    igst = total * 0.12;
  }

  document.getElementById("cgst").innerText = cgst.toFixed(2);
  document.getElementById("sgst").innerText = sgst.toFixed(2);
  document.getElementById("igst").innerText = igst.toFixed(2);
  document.getElementById("grand").innerText = (total + cgst + sgst + igst).toFixed(2);
});
