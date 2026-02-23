import React from "react";

export default function ReceiptTemplate({ bill }) {
  const items = bill?.items || [];
  const total = items.reduce((acc, item) => acc + Number(item.amount || 0), 0);

  return (
    <div className="mx-auto w-[300px] bg-white p-3 text-xs text-black">
      <div className="text-center font-bold">Thermal Receipt</div>
      <div className="mb-2 mt-1 text-center text-[10px]">Universal Billing POS</div>
      <hr className="my-2" />
      {items.map((item, idx) => (
        <div key={idx} className="mb-1 flex items-center justify-between">
          <span>{item.name}</span>
          <span>{item.amount}</span>
        </div>
      ))}
      <hr className="my-2" />
      <div className="flex justify-between font-bold">
        <span>Total</span>
        <span>{total.toFixed(2)}</span>
      </div>
    </div>
  );
}
