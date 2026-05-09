// Urban Grid GIS — frontend logic.
// Single file, vanilla JavaScript. Talks to the FastAPI backend that is
// served from the same origin (so we can use relative URLs).

const API = ""; // same-origin
const $ = (sel) => document.querySelector(sel);

// --- Map setup ----------------------------------------------------------

const map = L.map("map").setView([47.21, 38.93], 13); // Taganrog

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution:
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);

// All loaded section layers, keyed by id, so we can highlight by id.
const sectionLayers = new Map();
let selectedId = null;

const COLORS = {
  default: "#5cc8ff",
  selected: "#ffb454",
  matched: "#7af4c8",
};

function styleFor(id) {
  if (id === selectedId) return { color: COLORS.selected, weight: 6, opacity: 0.95 };
  return { color: COLORS.default, weight: 4, opacity: 0.85 };
}

function applyMatchHighlight(matchedIds) {
  const set = new Set(matchedIds || []);
  sectionLayers.forEach((layer, id) => {
    if (set.has(id)) {
      layer.setStyle({ color: COLORS.matched, weight: 6, opacity: 0.95 });
    } else {
      layer.setStyle(styleFor(id));
    }
  });
}

function clearMatchHighlight() {
  sectionLayers.forEach((layer, id) => layer.setStyle(styleFor(id)));
}

// --- Data load ----------------------------------------------------------

async function loadSections() {
  const r = await fetch(`${API}/api/sections`);
  if (!r.ok) throw new Error(`Failed to load sections: ${r.status}`);
  const sections = await r.json();

  // Populate the forecast dropdown.
  const sel = $("#fc-section");
  sel.innerHTML = "";
  sections.forEach((s) => {
    const opt = document.createElement("option");
    opt.value = s.id;
    opt.textContent = `${s.id} · ${s.district || "—"} · ${s.wire_type}`;
    sel.appendChild(opt);
  });

  // Draw lines.
  const bounds = [];
  sections.forEach((s) => {
    const coords = s.geometry.coordinates.map(([lon, lat]) => [lat, lon]);
    const layer = L.polyline(coords, styleFor(s.id))
      .addTo(map)
      .bindTooltip(`#${s.id} · ${s.district || "—"}`, { sticky: true });
    layer.on("click", () => selectSection(s.id));
    sectionLayers.set(s.id, layer);
    bounds.push(...coords);
  });
  if (bounds.length) map.fitBounds(bounds, { padding: [40, 40] });
}

async function selectSection(id) {
  selectedId = id;
  clearMatchHighlight();

  const [section, readings] = await Promise.all([
    fetch(`${API}/api/sections/${id}`).then((r) => r.json()),
    fetch(`${API}/api/sections/${id}/readings`).then((r) => r.json()),
  ]);
  const info = $("#selected-info");
  info.innerHTML = `
    <div><strong>#${section.id}</strong> · ${section.district || "—"} · ${section.wire_type}</div>
    <pre>${JSON.stringify(
      {
        cable_length_m: section.cable_length_m,
        rated_power_kw: section.rated_power_kw,
        rated_current_a: section.rated_current_a,
        installed_on: section.installed_on?.slice(0, 10),
        avg_consumption_kwh: section.avg_consumption_kwh,
        readings: readings.length,
      },
      null,
      2
    )}</pre>
  `;
  $("#fc-section").value = String(id);
}

// --- Specialized analytics ---------------------------------------------

document.querySelectorAll("[data-endpoint]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const out = $("#analytics-out");
    out.textContent = "Loading…";
    try {
      const r = await fetch(`${API}${btn.dataset.endpoint}`);
      const data = await r.json();
      out.textContent = JSON.stringify(data, null, 2);
      // If response includes a list of sections with `id`, highlight them.
      const ids = Array.isArray(data)
        ? data.map((row) => row.id).filter((x) => typeof x === "number")
        : data && typeof data.id === "number"
        ? [data.id]
        : [];
      applyMatchHighlight(ids);
    } catch (err) {
      out.textContent = `Error: ${err.message}`;
    }
  });
});

// --- Forecast ----------------------------------------------------------

$("#fc-value").addEventListener("click", async () => {
  const body = {
    section_id: Number($("#fc-section").value),
    parameter: $("#fc-param").value,
    target_date: $("#fc-date").value
      ? new Date($("#fc-date").value).toISOString()
      : new Date(Date.now() + 365 * 86400 * 1000).toISOString(),
  };
  const r = await fetch(`${API}/api/forecast/value-on-date`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  $("#fc-out").textContent = JSON.stringify(await r.json(), null, 2);
});

$("#fc-when").addEventListener("click", async () => {
  const body = {
    section_id: Number($("#fc-section").value),
    parameter: $("#fc-param").value,
    target_value: Number($("#fc-target").value || 0),
  };
  const r = await fetch(`${API}/api/forecast/date-for-value`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  $("#fc-out").textContent = JSON.stringify(await r.json(), null, 2);
});

// --- AI query ---------------------------------------------------------

async function askAI(question) {
  const out = $("#ai-out");
  out.innerHTML = `<em>Thinking…</em>`;
  try {
    const r = await fetch(`${API}/api/ai/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await r.json();
    out.innerHTML = `
      <div>${escapeHtml(data.answer)}</div>
      ${
        data.interpretation
          ? `<div class="interp">↳ ${escapeHtml(data.interpretation)}</div>`
          : ""
      }
    `;
    applyMatchHighlight(data.matched_section_ids || []);
  } catch (err) {
    out.textContent = `Error: ${err.message}`;
  }
}

$("#ai-go").addEventListener("click", () => askAI($("#ai-input").value.trim()));
$("#ai-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
    e.preventDefault();
    $("#ai-go").click();
  }
});
document.querySelectorAll(".chip").forEach((c) =>
  c.addEventListener("click", () => {
    $("#ai-input").value = c.dataset.q;
    askAI(c.dataset.q);
  })
);

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// --- Boot --------------------------------------------------------------

loadSections().catch((err) => {
  console.error(err);
  alert(`Could not load sections: ${err.message}`);
});
