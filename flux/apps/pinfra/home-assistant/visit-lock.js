// While there is a visit (input_boolean.hay_visita on), the kitchen display
// only shows the kitchen and energy dashboards: the other sidebar entries are
// hidden, and any other page reached anyway is covered by a full-viewport
// message. kiosk-mode only acts on the dashboard that holds its config, so it
// cannot cover the built-in panels (calendar, map, ...) itself.

const DISPLAY_USER = "bccfedc6e53a414da0b87ee6277f0e6a"; // "Family", the kitchen display
const VISIT_ENTITY = "input_boolean.hay_visita";
const ALLOWED = [
  { path: "/dashboard-kitchen", label: "Cocina" },
  { path: "/energy", label: "Energía" },
];

// Sidebar entries are <ha-list-item-button id="sidebar-panel-<url_path>">; the
// account and notifications entries go too, as kiosk-mode hides them on the
// kitchen dashboard.
const SIDEBAR_CSS = `
  ha-list-item-button[id^="sidebar-panel-"]${ALLOWED.map((a) => `:not(#sidebar-panel-${a.path.slice(1)})`).join("")},
  #sidebar-profile,
  #sidebar-notifications {
    display: none !important;
  }
`;

let overlay;

function navigate(path) {
  // Same as the frontend's own navigate().
  history.pushState(null, "", path);
  window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
}

function buildOverlay() {
  const el = document.createElement("div");
  el.id = "visit-lock";
  el.style.cssText = [
    "position: fixed",
    "inset: 0",
    "z-index: 2147483647",
    "display: none",
    "flex-direction: column",
    "align-items: center",
    "justify-content: center",
    "gap: 24px",
    "padding: 16px",
    "text-align: center",
    "background: var(--primary-background-color, #fafafa)",
    "color: var(--primary-text-color, #212121)",
    "font-family: var(--ha-font-family-body, Roboto, sans-serif)",
  ].join(";");

  const title = document.createElement("div");
  title.textContent = "Hay visita";
  title.style.cssText = "font-size: 48px; font-weight: 500";

  const text = document.createElement("div");
  text.textContent = "Mientras hay visita, esta pantalla solo muestra la cocina y la energía.";
  text.style.cssText = "font-size: 20px; color: var(--secondary-text-color, #727272)";

  const buttons = document.createElement("div");
  buttons.style.cssText = "display: flex; gap: 16px; flex-wrap: wrap; justify-content: center";
  for (const { path, label } of ALLOWED) {
    const button = document.createElement("button");
    button.textContent = label;
    button.style.cssText = [
      "font: inherit",
      "font-size: 20px",
      "padding: 12px 32px",
      "border: none",
      "border-radius: 24px",
      "cursor: pointer",
      "background: var(--primary-color, #03a9f4)",
      "color: var(--text-primary-color, #fff)",
    ].join(";");
    button.addEventListener("click", () => navigate(path));
    buttons.append(button);
  }

  el.append(title, text, buttons);
  // Swallow everything so nothing underneath can be reached.
  el.addEventListener("contextmenu", (ev) => ev.preventDefault());
  document.body.append(el);
  return el;
}

function lockSidebar(visit) {
  const sidebar = document
    .querySelector("home-assistant")
    ?.shadowRoot?.querySelector("home-assistant-main")
    ?.shadowRoot?.querySelector("ha-sidebar")?.shadowRoot;
  if (!sidebar) return;

  let style = sidebar.getElementById("visit-lock-sidebar");
  if (!style) {
    style = document.createElement("style");
    style.id = "visit-lock-sidebar";
    sidebar.append(style);
  }
  const css = visit ? SIDEBAR_CSS : "";
  if (style.textContent !== css) style.textContent = css;
}

function update() {
  const hass = document.querySelector("home-assistant")?.hass;
  if (!hass?.user || !hass.states) return;

  const path = location.pathname;
  const visit = hass.user.id === DISPLAY_USER && hass.states[VISIT_ENTITY]?.state === "on";
  const locked = visit && !ALLOWED.some((a) => path === a.path || path.startsWith(`${a.path}/`));

  lockSidebar(visit);
  overlay ??= buildOverlay();
  overlay.style.display = locked ? "flex" : "none";
}

window.addEventListener("location-changed", () => setTimeout(update));
window.addEventListener("popstate", () => setTimeout(update));
// hass is replaced on every state change; polling is simpler than hooking it
// and cheap enough for one boolean.
setInterval(update, 500);
update();
