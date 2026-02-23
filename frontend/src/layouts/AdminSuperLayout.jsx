import React from "react";

import AppHeader from "../components/shared/AppHeader";
import AppShell from "../components/shared/AppShell";

export default function AdminSuperLayout() {
  return (
    <AppShell className="bg-slate-950 text-white">
      <AppHeader title="Admin Super Control Mode" subtitle="Global command center" />
      <main className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
        <section className="rounded-xl bg-slate-900 p-4">
          <h2 className="text-sm font-semibold">System Health</h2>
          <ul className="mt-2 space-y-2 text-xs text-slate-300">
            <li>API Gateway: healthy</li>
            <li>Redis: healthy</li>
            <li>WebSocket: healthy</li>
          </ul>
        </section>
        <section className="rounded-xl bg-slate-900 p-4 md:col-span-2">
          <h2 className="text-sm font-semibold">Global Controls</h2>
          <div className="mt-2 text-xs text-slate-300">
            RBAC permissions, mode lock, audit trails, and emergency toggles.
          </div>
        </section>
      </main>
    </AppShell>
  );
}
