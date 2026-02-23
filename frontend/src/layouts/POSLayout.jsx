import React, { useEffect, useMemo, useState } from "react";

import AppHeader from "../components/shared/AppHeader";
import AppShell from "../components/shared/AppShell";
import {
  loadDraftCart,
  queueBillForSync,
  saveDraftCart,
} from "../features/pos/offlineBillingStore";

export default function POSLayout() {
  const [barcode, setBarcode] = useState("");
  const [cart, setCart] = useState(loadDraftCart());

  useEffect(() => {
    const barcodeInput = document.getElementById("pos-barcode-input");
    if (barcodeInput) barcodeInput.focus();
  }, []);

  useEffect(() => {
    saveDraftCart(cart);
  }, [cart]);

  useEffect(() => {
    function onKeyDown(e) {
      if (e.key === "F8") {
        e.preventDefault();
        handleCheckout();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  });

  function addQuickItem(codeValue) {
    if (!codeValue.trim()) return;
    const item = {
      id: `${Date.now()}`,
      name: `Item ${codeValue}`,
      qty: 1,
      rate: 100,
      amount: 100,
    };
    setCart((prev) => [...prev, item]);
    setBarcode("");
  }

  function removeItem(itemId) {
    setCart((prev) => prev.filter((x) => x.id !== itemId));
  }

  function handleCheckout() {
    if (!cart.length) return;
    queueBillForSync({ items: cart, total: totalAmount, mode: "POS" });
    setCart([]);
    alert("Bill queued. Instant stock deduction should be triggered by backend sync worker.");
  }

  const totalAmount = useMemo(
    () => cart.reduce((acc, item) => acc + Number(item.amount || 0), 0),
    [cart]
  );

  return (
    <AppShell className="bg-slate-900 text-white">
      <AppHeader
        title="POS Embedded Mode"
        subtitle="Touch optimized fast billing screen"
        right={<div className="rounded-md bg-emerald-500 px-3 py-1 text-xs">F8 Checkout</div>}
      />
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <section className="rounded-xl bg-slate-800 p-4 lg:col-span-2">
          <label className="text-sm text-slate-300">Barcode Scan</label>
          <input
            id="pos-barcode-input"
            value={barcode}
            onChange={(e) => setBarcode(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addQuickItem(barcode);
              }
            }}
            placeholder="Scan or type barcode and press Enter"
            className="mt-2 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-4 text-lg text-white outline-none"
          />
          <div className="mt-3 flex gap-2">
            <button
              className="rounded-lg bg-blue-600 px-4 py-3 text-lg font-semibold"
              onClick={() => addQuickItem(barcode)}
            >
              Add Item
            </button>
            <button className="rounded-lg bg-emerald-600 px-4 py-3 text-lg font-semibold" onClick={handleCheckout}>
              Checkout
            </button>
          </div>
        </section>

        <aside className="rounded-xl bg-white p-4 text-slate-900">
          <h3 className="text-sm font-semibold">Cart Items</h3>
          <ul className="mt-2 space-y-2">
            {cart.map((item) => (
              <li key={item.id} className="flex items-center justify-between rounded border p-2">
                <span className="text-sm">{item.name}</span>
                <button className="text-xs text-red-600" onClick={() => removeItem(item.id)}>
                  Remove
                </button>
              </li>
            ))}
          </ul>
          <div className="mt-4 border-t pt-3 text-lg font-bold">Total: {totalAmount.toFixed(2)}</div>
        </aside>
      </div>
    </AppShell>
  );
}
