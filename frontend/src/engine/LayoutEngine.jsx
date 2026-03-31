import React from "react";

import ModeSwitchControl from "../components/ModeSwitchControl";
import { useSystemMode } from "../hooks/useSystemMode";
import AdminSuperLayout from "../layouts/AdminSuperLayout";
import DesktopLayout from "../layouts/DesktopLayout";
import MobileLayout from "../layouts/MobileLayout";
import TabletLayout from "../layouts/TabletLayout";

function pickLayout(mode) {
  switch (mode) {
    case "MOBILE":
      return MobileLayout;
    case "TABLET":
      return TabletLayout;
    case "ADMIN_SUPER":
      return AdminSuperLayout;
    case "DESKTOP":
    default:
      return DesktopLayout;
  }
}

export default function LayoutEngine() {
  const { modeState, resolvedMode, loading } = useSystemMode();
  const CurrentLayout = pickLayout(resolvedMode);

  if (loading) {
    return <div className="p-6 text-sm text-slate-500">Loading system mode...</div>;
  }

  return (
    <div>
      <div className="fixed right-3 top-3 z-50 w-72">
        <ModeSwitchControl modeState={modeState} onChanged={() => {}} />
      </div>
      <CurrentLayout />
    </div>
  );
}
