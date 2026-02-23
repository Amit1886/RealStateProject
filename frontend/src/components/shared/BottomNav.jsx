import React from "react";

const ITEMS = ["Home", "Billing", "Orders", "Stock", "Settings"];

export default function BottomNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 border-t bg-white p-2 shadow">
      <ul className="grid grid-cols-5 gap-2 text-center text-xs">
        {ITEMS.map((item) => (
          <li key={item} className="rounded-md p-2 text-slate-600 hover:bg-slate-100">
            {item}
          </li>
        ))}
      </ul>
    </nav>
  );
}
