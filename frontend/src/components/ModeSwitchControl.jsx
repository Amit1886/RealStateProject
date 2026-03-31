import React, { useState } from "react";

import { changeSystemMode } from "../services/systemModeApi";

const MODES = ["DESKTOP", "MOBILE", "TABLET", "ADMIN_SUPER", "AUTO"];

export default function ModeSwitchControl({ modeState, onChanged }) {
  const [selectedMode, setSelectedMode] = useState(modeState.current_mode || "DESKTOP");
  const [locked, setLocked] = useState(Boolean(modeState.is_locked));
  const [saving, setSaving] = useState(false);
  const canChange = Boolean(modeState.can_change);

  async function handleApply() {
    setSaving(true);
    try {
      const updated = await changeSystemMode({
        current_mode: selectedMode,
        is_locked: locked,
      });
      onChanged?.(updated);
      window.location.reload();
    } catch (err) {
      alert("Mode update failed. " + String(err.message || err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-xl border bg-white p-3 shadow-sm">
      <div className="mb-2 text-sm font-semibold">System Mode</div>
      <div className="mb-2 text-xs text-slate-500">Current: {modeState.current_mode}</div>
      <div className="grid grid-cols-2 gap-2">
        <select
          value={selectedMode}
          onChange={(e) => setSelectedMode(e.target.value)}
          disabled={!canChange || saving}
          className="rounded-md border px-2 py-2 text-sm"
        >
          {MODES.map((mode) => (
            <option key={mode} value={mode}>
              {mode}
            </option>
          ))}
        </select>

        <label className="flex items-center gap-2 rounded-md border px-2 py-2 text-sm">
          <input
            type="checkbox"
            checked={locked}
            onChange={(e) => setLocked(e.target.checked)}
            disabled={!canChange || saving}
          />
          Lock Global
        </label>
      </div>
      <button
        type="button"
        onClick={handleApply}
        disabled={!canChange || saving}
        className="mt-3 w-full rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
      >
        {saving ? "Applying..." : "Apply Mode"}
      </button>
      {!canChange ? <div className="mt-2 text-xs text-amber-600">Admin only control.</div> : null}
    </div>
  );
}
