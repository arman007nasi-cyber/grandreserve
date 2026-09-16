// Point this at your running API (see docker-compose.yml).
const API_BASE = "http://localhost:8000";
const WS_URL = "ws://localhost:8000/ws/tables";

// Demo restaurant/slot are filled in after scripts/seed_demo_data.py runs.
// For a quick demo, hardcode the restaurant id it prints here:
const RESTAURANT_ID = "PASTE_RESTAURANT_ID_HERE";
const SLOT_START = "2026-12-31T20:00:00+00:00";

document.getElementById("slot-label").textContent = new Date(SLOT_START).toLocaleString();

function log(message, kind) {
  const el = document.getElementById("log");
  const line = document.createElement("div");
  line.className = kind || "";
  line.textContent = message;
  el.prepend(line);
}

function getToken() {
  return localStorage.getItem("access_token");
}

function setToken(token) {
  if (token) {
    localStorage.setItem("access_token", token);
  } else {
    localStorage.removeItem("access_token");
  }
  refreshAuthStatus();
}

async function refreshAuthStatus() {
  const el = document.getElementById("auth-status");
  const token = getToken();
  if (!token) {
    el.textContent = "Not signed in";
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error();
    const user = await res.json();
    el.innerHTML = `Signed in as <strong>${user.full_name}</strong>`;
  } catch {
    el.textContent = "Session expired — please sign in again";
    setToken(null);
  }
}

async function register() {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  const full_name = document.getElementById("full-name").value || "Guest Diner";

  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name }),
  });
  const data = await res.json();
  if (!res.ok) return log(`Registration failed: ${data.detail}`, "err");

  setToken(data.access_token);
  log("Account created and signed in.", "ok");
}

async function login() {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) return log(`Sign-in failed: ${data.detail}`, "err");

  setToken(data.access_token);
  log("Signed in.", "ok");
}

function logout() {
  setToken(null);
  log("Signed out.");
}

async function loadFloor() {
  const floor = document.getElementById("floor");
  if (RESTAURANT_ID === "PASTE_RESTAURANT_ID_HERE") {
    floor.textContent = "Run scripts/seed_demo_data.py, then paste the restaurant_id into frontend/app.js.";
    return;
  }

  const res = await fetch(
    `${API_BASE}/restaurants/${RESTAURANT_ID}/availability?slot_start=${encodeURIComponent(SLOT_START)}`
  );
  const availableTables = await res.json();
  const availableIds = new Set(availableTables.map((t) => t.id));

  const allRes = await fetch(`${API_BASE}/restaurants/${RESTAURANT_ID}`);
  const restaurant = await allRes.json();

  floor.innerHTML = "";
  restaurant.tables.forEach((table) => {
    const isFree = availableIds.has(table.id);
    const card = document.createElement("button");
    card.className = `table-card ${isFree ? "status-free" : "status-taken"}`;
    card.dataset.tableId = table.id;
    card.disabled = !isFree;
    card.innerHTML = `
      <div class="label">${table.label}</div>
      <div class="seats">${table.seats} seats</div>
      <div><span class="status-dot"></span><span class="status-label">${isFree ? "Available" : "Booked"}</span></div>
    `;
    card.onclick = () => bookTable(table.id, table.label);
    floor.appendChild(card);
  });
}

async function bookTable(tableId, label) {
  const token = getToken();
  if (!token) return log("Sign in first to book a table.", "err");

  const res = await fetch(`${API_BASE}/reservations`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      table_id: tableId,
      slot_start: SLOT_START,
      party_size: 2,
      idempotency_key: crypto.randomUUID(),
    }),
  });
  const data = await res.json();
  if (!res.ok) return log(`${label}: ${data.detail}`, "err");

  log(`Booked ${label} for ${new Date(SLOT_START).toLocaleString()}.`, "ok");
  loadFloor();
}

function connectLiveUpdates() {
  const ws = new WebSocket(WS_URL);
  ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    log(`Live update: table ${update.table_id.slice(0, 8)}… is now ${update.status}.`);
    loadFloor();
  };
  ws.onclose = () => setTimeout(connectLiveUpdates, 2000); // auto-reconnect
}

refreshAuthStatus();
loadFloor();
connectLiveUpdates();
