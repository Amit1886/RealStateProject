import React from "react";

export default function AppHeader({ title, subtitle, right }) {
  return (
    <header className="flex items-center justify-between rounded-xl bg-slate-900 p-4 text-white shadow">
      <div>
        <h1 className="text-lg font-semibold">{title}</h1>
        {subtitle ? <p className="text-xs text-slate-300">{subtitle}</p> : null}
      </div>
      <div>{right}</div>
    </header>
  );
}
