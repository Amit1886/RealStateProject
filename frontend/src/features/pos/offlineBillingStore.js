const CACHE_KEY = "pos_offline_bill_queue_v1";
const CART_KEY = "pos_cart_draft_v1";

export function loadPendingBills() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function queueBillForSync(billPayload) {
  const queue = loadPendingBills();
  queue.push({ ...billPayload, queued_at: new Date().toISOString() });
  localStorage.setItem(CACHE_KEY, JSON.stringify(queue));
}

export function clearSyncedBills() {
  localStorage.setItem(CACHE_KEY, JSON.stringify([]));
}

export function saveDraftCart(cart) {
  localStorage.setItem(CART_KEY, JSON.stringify(cart || []));
}

export function loadDraftCart() {
  try {
    const raw = localStorage.getItem(CART_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}
