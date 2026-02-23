import { useEffect, useMemo, useState } from "react";

import { fetchCurrentMode } from "../services/systemModeApi";
import { createSystemModeSocket } from "../realtime/systemModeSocket";

const DEFAULT_STATE = {
  current_mode: "DESKTOP",
  resolved_mode: "DESKTOP",
  is_locked: false,
  can_change: false,
  route_profile: {
    entry_route: "/accounts/dashboard/",
    layout_key: "desktop",
  },
};

export function useSystemMode() {
  const [state, setState] = useState(DEFAULT_STATE);
  const [loading, setLoading] = useState(true);
  const [viewportMode, setViewportMode] = useState("DESKTOP");

  function detectViewportMode() {
    const width = window.innerWidth;
    if (width <= 767) return "MOBILE";
    if (width <= 1199) return "TABLET";
    return "DESKTOP";
  }

  useEffect(() => {
    let mounted = true;
    let socket;

    async function load() {
      try {
        const modeState = await fetchCurrentMode();
        if (!mounted) return;
        setState((prev) => ({ ...prev, ...modeState }));
      } catch (err) {
        // Keep UI usable with default mode.
      } finally {
        if (mounted) setLoading(false);
      }
    }

    load();

    socket = createSystemModeSocket({
      onModeChanged(next) {
        setState((prev) => ({
          ...prev,
          ...next,
          resolved_mode: next.current_mode || prev.resolved_mode,
        }));
        window.location.reload();
      },
    });

    return () => {
      mounted = false;
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, []);

  useEffect(() => {
    function onResize() {
      setViewportMode(detectViewportMode());
    }
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const resolvedMode = useMemo(
    () =>
      String(
        state.current_mode === "AUTO"
          ? viewportMode
          : state.resolved_mode || state.current_mode || "DESKTOP"
      ).toUpperCase(),
    [state.current_mode, state.resolved_mode, viewportMode]
  );

  return {
    modeState: state,
    resolvedMode,
    loading,
  };
}
