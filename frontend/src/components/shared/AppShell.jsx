import React from "react";

export default function AppShell({ children, className = "" }) {
  return <div className={`min-h-screen bg-slate-100 p-4 ${className}`}>{children}</div>;
}
