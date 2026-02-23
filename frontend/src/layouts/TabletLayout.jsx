import React from "react";

import AppHeader from "../components/shared/AppHeader";
import AppShell from "../components/shared/AppShell";

export default function TabletLayout() {
  return (
    <AppShell>
      <AppHeader title="Tablet Mode" subtitle="Hybrid split-screen layout" />
      <main className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        <section className="rounded-xl bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold">Billing Pane</h2>
          <div className="mt-2 space-y-2">
            {[1, 2, 3].map((x) => (
              <div key={x} className="rounded border p-2 text-sm">
                Product line #{x}
              </div>
            ))}
          </div>
        </section>
        <section className="rounded-xl bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold">Summary Pane</h2>
          <div className="mt-2 rounded border p-3 text-sm">
            Medium touch controls, collapsible sidebar compatible.
          </div>
        </section>
      </main>
    </AppShell>
  );
}
