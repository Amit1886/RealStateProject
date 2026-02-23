const API_BASE = "";

async function parseJson(response) {
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(errorBody || `HTTP ${response.status}`);
  }
  return response.json();
}

export async function fetchCurrentMode() {
  const response = await fetch(`${API_BASE}/api/current-mode/`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  return parseJson(response);
}

export async function fetchSystemMode() {
  const response = await fetch(`${API_BASE}/api/system-mode/`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  });
  return parseJson(response);
}

export async function changeSystemMode(payload) {
  const response = await fetch(`${API_BASE}/api/change-mode/`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson(response);
}
