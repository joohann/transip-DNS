const BASE = new URL(".", import.meta.url).href;
const FALLBACK_LANGUAGE = "en";
const POLL_INTERVAL = 30000;
const RELOAD_DELAY = 1200;
const INTEGRATION_PATH = "/config/integrations/integration/transip_dns";

const WS = {
  info: "transip_dns/info",
  domains: "transip_dns/domains",
  setRecords: "transip_dns/records/set",
  setOptions: "transip_dns/options/set",
  refresh: "transip_dns/refresh",
};

const translations = {};

async function loadLanguage(language) {
  if (translations[language]) return translations[language];
  try {
    const response = await fetch(`${BASE}translations/${language}.json`);
    if (!response.ok) throw new Error(response.statusText);
    translations[language] = await response.json();
  } catch (err) {
    translations[language] = null;
  }
  return translations[language];
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

const ICON = {
  back: "M20,11V13H8L13.5,18.5L12.08,19.92L4.16,12L12.08,4.08L13.5,5.5L8,11H20Z",
  refresh:
    "M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z",
  settings:
    "M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.21,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.21,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.67 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z",
  close:
    "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
  plus: "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z",
  check: "M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z",
};

const icon = (name, size = 22) =>
  `<svg viewBox="0 0 24 24" width="${size}" height="${size}" aria-hidden="true" focusable="false"><path fill="currentColor" d="${ICON[name]}"/></svg>`;

const STYLE = `
/* The light the glass refracts. Painted as gradients on the element itself:
   an earlier version used fixed-position blurred <div>s, which covered the
   whole viewport and rendered blank in browsers that struggle with a large
   blur under a backdrop-filter. Gradients cost the compositor nothing. */
:host { display: block; position: relative; min-height: 100%;
  color: var(--primary-text-color, #212121);
  background-color: var(--primary-background-color, #f2f4f7);
  background-image:
    radial-gradient(42vmax 42vmax at 8% -6%,
      color-mix(in srgb, var(--primary-color, #03a9f4) 32%, transparent), transparent 70%),
    radial-gradient(34vmax 34vmax at 96% 10%, rgba(124, 92, 255, .22), transparent 70%),
    radial-gradient(30vmax 30vmax at 55% 108%, rgba(46, 230, 197, .20), transparent 70%);
  background-attachment: scroll; background-repeat: no-repeat; }
@supports not (background: color-mix(in srgb, white 50%, transparent)) {
  :host { background-image:
    radial-gradient(42vmax 42vmax at 8% -6%, rgba(3, 169, 244, .28), transparent 70%),
    radial-gradient(34vmax 34vmax at 96% 10%, rgba(124, 92, 255, .22), transparent 70%),
    radial-gradient(30vmax 30vmax at 55% 108%, rgba(46, 230, 197, .20), transparent 70%); }
}
* { box-sizing: border-box; }
:host { --control-h: 42px; }

/* Liquid glass: translucent fill, wide blur with a saturation lift, a specular
   highlight along the top edge and a soft shade along the bottom. */
.glass { position: relative;
  background: color-mix(in srgb, var(--card-background-color, #ffffff) 52%, transparent);
  backdrop-filter: blur(26px) saturate(180%); -webkit-backdrop-filter: blur(26px) saturate(180%);
  border: 1px solid color-mix(in srgb, var(--primary-text-color, #000) 8%, transparent);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .45), inset 0 -1px 0 rgba(0, 0, 0, .06),
    0 10px 30px rgba(0, 0, 0, .14); }
@supports not (background: color-mix(in srgb, white 50%, transparent)) {
  .glass { background: var(--card-background-color, #fff); }
}

.bar { position: sticky; top: 0; z-index: 5; display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; border-radius: 0; border-left: none; border-right: none; border-top: none; }
.bar h1 { font-size: 20px; font-weight: 400; margin: 0 4px; flex: 1; }
.wrap { position: relative; z-index: 1; max-width: 1000px; margin: 0 auto;
  padding: 16px; display: grid; gap: 16px; }
.card { border-radius: 22px; overflow: hidden; }
.card h2 { font-size: 16px; font-weight: 500; margin: 0; padding: 15px 18px;
  border-bottom: 1px solid color-mix(in srgb, var(--primary-text-color, #000) 8%, transparent);
  display: flex; align-items: center; gap: 8px; }
.card h2 .spacer { flex: 1; }
.body { padding: 16px 18px; }
.grid { display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); }
.tile { border-radius: 20px; padding: 15px 17px; }
.tile .label { font-size: 13px; color: var(--secondary-text-color, #727272); margin-bottom: 6px; }
.tile .value { font-size: 20px; line-height: 1.3; font-family: var(--code-font-family, monospace);
  overflow-wrap: anywhere; }
/* An IPv6 address is 39 characters; at 20px it would wrap to three lines. */
.tile .value.long { font-size: 14px; line-height: 1.45; letter-spacing: -.01em; }
.tile .sub { font-size: 12px; color: var(--secondary-text-color, #727272); margin-top: 6px;
  overflow-wrap: anywhere; line-height: 1.5; }
.row { display: flex; align-items: center; gap: 12px; padding: 12px 18px;
  border-bottom: 1px solid color-mix(in srgb, var(--primary-text-color, #000) 7%, transparent); }
.row:last-of-type { border-bottom: none; }
.row.editing { background: var(--accent-soft, rgba(3, 169, 244, .10)); }
.row .main { flex: 1; min-width: 0; }
.row .name { font-size: 14px; }
.row .acts { display: flex; align-items: center; gap: 6px; }
.row .acts button { min-height: 28px; font-size: 13px; padding: 0 12px; }
.row .meta { font-size: 12px; color: var(--secondary-text-color, #727272);
  font-family: var(--code-font-family, monospace); margin-top: 2px; overflow-wrap: anywhere; }

.chip { font-size: 12px; height: 28px; display: inline-flex; align-items: center; padding: 0 12px;
  border-radius: 999px; white-space: nowrap;
  background: color-mix(in srgb, var(--primary-text-color, #000) 8%, transparent);
  color: var(--secondary-text-color, #727272);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .35); }
.chip.ok { background: rgba(76, 175, 80, .20); color: var(--success-color, #2e7d32); }
.chip.updated { background: rgba(3, 169, 244, .20); color: var(--info-color, #0277bd); }
.chip.warn { background: rgba(255, 152, 0, .22); color: var(--warning-color, #ef6c00); }
.chip.error { background: rgba(244, 67, 54, .20); color: var(--error-color, #c62828); }

button { font: inherit; font-size: 14px; padding: 0 16px; min-height: var(--control-h); border-radius: 999px; cursor: pointer;
  color: var(--primary-text-color, #212121);
  border: 1px solid color-mix(in srgb, var(--primary-text-color, #000) 12%, transparent);
  background: color-mix(in srgb, var(--card-background-color, #fff) 55%, transparent);
  backdrop-filter: blur(14px) saturate(160%); -webkit-backdrop-filter: blur(14px) saturate(160%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .45);
  transition: transform .12s ease, background .12s ease, box-shadow .12s ease; }
button:hover { background: color-mix(in srgb, var(--card-background-color, #fff) 78%, transparent);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .6), 0 6px 18px rgba(0, 0, 0, .14); }
button:active { transform: scale(.96); }
button.primary { background: var(--primary-color, #03a9f4); border-color: transparent;
  color: var(--text-primary-color, #fff);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .4), 0 8px 20px color-mix(in srgb, var(--primary-color, #03a9f4) 40%, transparent); }
button.primary:hover { filter: brightness(1.08); }
button.danger { color: var(--error-color, #c62828);
  border-color: color-mix(in srgb, var(--error-color, #c62828) 45%, transparent); }
button.quiet { border-color: transparent; background: transparent; box-shadow: none; }
button.quiet:hover { background: color-mix(in srgb, var(--primary-text-color, #000) 8%, transparent); }
button.icon { width: 40px; height: 40px; padding: 0; display: grid; place-items: center; }
button.icon svg { display: block; }
button[disabled] { opacity: .45; cursor: default; transform: none; }
button.busy svg { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

input[type=text], input[type=number], select { font: inherit; font-size: 14px; padding: 0 16px;
  height: var(--control-h); border-radius: 999px; width: 100%; color: var(--primary-text-color, #212121);
  appearance: none; -webkit-appearance: none;
  border: 1px solid color-mix(in srgb, var(--primary-text-color, #000) 12%, transparent);
  background: color-mix(in srgb, var(--card-background-color, #fff) 60%, transparent); }
input:focus-visible, select:focus-visible, button:focus-visible, .combo-field:focus-visible {
  outline: 2px solid var(--primary-color, #03a9f4); outline-offset: 2px; }
select { background-image: linear-gradient(45deg, transparent 50%, currentColor 50%),
    linear-gradient(135deg, currentColor 50%, transparent 50%);
  background-position: right 18px top 50%, right 13px top 50%;
  background-size: 5px 5px, 5px 5px; background-repeat: no-repeat;
  padding-right: 34px; }
label.field { display: block; font-size: 13px; color: var(--secondary-text-color, #727272); margin-bottom: 5px; }
.form { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); align-items: end; }
.form .submit { display: flex; gap: 8px; justify-content: flex-end; }
.form-hint { text-align: center; margin-top: 12px; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
button.primary#add-record { display: inline-flex; align-items: center; }
.banner { padding: 12px 16px; border-radius: 16px; font-size: 14px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .3); }
.banner.error { background: rgba(244, 67, 54, .16); color: var(--error-color, #c62828); }
.banner.info { background: rgba(3, 169, 244, .16); color: var(--info-color, #0277bd); }
.muted { color: var(--secondary-text-color, #727272); font-size: 14px; }
.hist { display: flex; gap: 12px; font-size: 13px; padding: 6px 0; align-items: baseline; }
.hist .when { color: var(--secondary-text-color, #727272); min-width: 140px; font-size: 12px; }
.hist .what { font-family: var(--code-font-family, monospace); overflow-wrap: anywhere; }

.scrim { position: fixed; inset: 0; z-index: 20; display: flex; align-items: center;
  justify-content: center; padding: 16px; background: rgba(4, 8, 10, .42);
  backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px); }
.dialog { width: min(520px, 100%); max-height: calc(100vh - 32px); overflow: auto;
  border-radius: 28px; position: relative;
  background: color-mix(in srgb, var(--card-background-color, #ffffff) 58%, transparent);
  backdrop-filter: blur(34px) saturate(190%); -webkit-backdrop-filter: blur(34px) saturate(190%);
  border: 1px solid rgba(255, 255, 255, .24);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .55), inset 0 -1px 0 rgba(0, 0, 0, .08),
    0 30px 70px rgba(0, 0, 0, .42); }
/* The specular sweep that makes the surface read as a lens rather than a pane. */
.dialog::before { content: ""; position: absolute; inset: 0; border-radius: inherit;
  pointer-events: none; opacity: .5;
  background: linear-gradient(140deg, rgba(255, 255, 255, .45) 0%, rgba(255, 255, 255, 0) 38%,
    rgba(255, 255, 255, 0) 62%, rgba(255, 255, 255, .16) 100%); }
@supports not (background: color-mix(in srgb, white 50%, transparent)) {
  .dialog { background: var(--card-background-color, #fff); }
}
.dialog > * { position: relative; }
.dialog header { display: flex; align-items: center; gap: 12px; padding: 18px 20px 6px; }
.dialog header h2 { font-size: 20px; font-weight: 500; margin: 0; flex: 1; border: none; padding: 0; }
.dialog .dbody { padding: 6px 20px 4px; }
.dialog footer { display: flex; align-items: center; gap: 8px; padding: 14px 20px 18px;
  position: sticky; bottom: 0;
  background: linear-gradient(to top,
    color-mix(in srgb, var(--card-background-color, #fff) 70%, transparent) 55%, transparent); }
.dialog footer .spacer { flex: 1; }
.dgroup { padding: 14px 0;
  border-top: 1px solid color-mix(in srgb, var(--primary-text-color, #000) 9%, transparent); }
.dgroup:first-child { border-top: none; }
.dgroup > .label { font-size: 13px; font-weight: 500; letter-spacing: .02em;
  color: var(--secondary-text-color, #727272); margin-bottom: 10px; }
.srow { display: flex; align-items: center; gap: 12px; padding: 7px 0; }
.srow .main { flex: 1; min-width: 0; font-size: 14px; }
.srow .hint { display: block; font-size: 12px; color: var(--secondary-text-color, #727272); margin-top: 2px; }
.srow input[type=number] { width: 104px; text-align: right; }

input.switch { appearance: none; -webkit-appearance: none; width: 44px; height: 26px; flex: none;
  border-radius: 999px; position: relative; cursor: pointer;
  background: color-mix(in srgb, var(--primary-text-color, #000) 18%, transparent);
  border: 1px solid rgba(255, 255, 255, .22);
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, .22);
  transition: background .18s ease; }
input.switch::after { content: ""; position: absolute; top: 2px; left: 2px; width: 20px; height: 20px;
  border-radius: 50%; background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, .35), inset 0 1px 0 rgba(255, 255, 255, .9);
  transition: transform .18s cubic-bezier(.2, .9, .3, 1.2); }
input.switch:checked { background: var(--primary-color, #03a9f4); border-color: transparent; }
input.switch:checked::after { transform: translateX(18px); }

.combo { position: relative; }
.combo-field { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; min-height: 42px;
  padding: 6px 34px 6px 8px; border-radius: 14px; cursor: pointer;
  border: 1px solid color-mix(in srgb, var(--primary-text-color, #000) 12%, transparent);
  background: color-mix(in srgb, var(--card-background-color, #fff) 45%, transparent);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .4); }
.combo-field:hover { border-color: var(--primary-color, #03a9f4); }
.combo-caret { position: absolute; right: 12px; top: 13px; pointer-events: none;
  color: var(--secondary-text-color, #727272); font-size: 12px; }
.tag { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; padding: 4px 5px 4px 11px;
  border-radius: 999px; background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .4); }
.tag button { all: unset; cursor: pointer; width: 18px; height: 18px; border-radius: 50%;
  display: grid; place-items: center; font-size: 13px; line-height: 1; opacity: .85; }
.tag button:hover { background: rgba(0, 0, 0, .2); }
.combo-placeholder { font-size: 14px; color: var(--secondary-text-color, #727272); padding: 0 4px; }
.combo-pop { position: absolute; left: 0; right: 0; top: calc(100% + 6px); z-index: 2;
  border-radius: 18px; overflow: hidden; border: 1px solid rgba(255, 255, 255, .22);
  background: color-mix(in srgb, var(--card-background-color, #fff) 74%, transparent);
  backdrop-filter: blur(26px) saturate(180%); -webkit-backdrop-filter: blur(26px) saturate(180%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .5), 0 16px 34px rgba(0, 0, 0, .3); }
@supports not (background: color-mix(in srgb, white 50%, transparent)) {
  .combo-pop { background: var(--card-background-color, #fff); }
}
.combo-pop input { border: none; border-radius: 0; background: transparent;
  border-bottom: 1px solid color-mix(in srgb, var(--primary-text-color, #000) 10%, transparent); }
.combo-list { max-height: 210px; overflow: auto; }
.option { display: flex; align-items: center; gap: 10px; padding: 10px 13px; font-size: 14px; cursor: pointer; }
.option:hover { background: color-mix(in srgb, var(--primary-text-color, #000) 8%, transparent); }
.option .mark { width: 16px; flex: none; color: var(--primary-color, #03a9f4); }
.option.empty { color: var(--secondary-text-color, #727272); cursor: default; }
.option.empty:hover { background: none; }

a.back { color: inherit; text-decoration: none; display: grid; place-items: center; }
@media (prefers-reduced-motion: reduce) {
  button, input.switch, input.switch::after { transition: none; }
  button.busy svg { animation: none; }
}
`;

class TransipDnsPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._info = null;
    this._domains = [];
    this._error = null;
    this._notice = null;
    this._busy = false;
    this._strings = null;
    this._timer = null;
    this._loaded = false;
    this._dialog = false;
    this._draft = null;
    this._combo = false;
    this._comboQuery = "";
    this._editing = null;
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._start();
  }

  get hass() {
    return this._hass;
  }

  set panel(panel) {
    this._panel = panel;
  }

  set narrow(narrow) {
    this._narrow = narrow;
  }

  set route(route) {
    this._route = route;
  }

  connectedCallback() {
    this.addEventListener("keydown", this._onKeyDown);
    if (this._hass && !this._loaded) this._start();
    if (!this._timer) {
      this._timer = setInterval(() => {
        // Re-rendering while someone is filling in a field would wipe what
        // they typed, so the poll waits its turn.
        if (!this._busy && !this._dialog && this._editing === null && !this._hasFocusedField()) {
          this._loadInfo();
        }
      }, POLL_INTERVAL);
    }
  }

  disconnectedCallback() {
    this.removeEventListener("keydown", this._onKeyDown);
    clearInterval(this._timer);
    this._timer = null;
  }

  _hasFocusedField() {
    const active = this.shadowRoot?.activeElement;
    return Boolean(active && ["INPUT", "SELECT", "TEXTAREA"].includes(active.tagName));
  }

  get _entryId() {
    const fromUrl = new URLSearchParams(window.location.search).get("config_entry");
    return fromUrl || this._info?.entry_id || undefined;
  }

  async _start() {
    this._loaded = true;
    const language = this._hass?.language || FALLBACK_LANGUAGE;
    const fallback = await loadLanguage(FALLBACK_LANGUAGE);
    const preferred =
      language === FALLBACK_LANGUAGE ? null : await loadLanguage(language.split("-")[0]);
    this._strings = { ...(fallback || {}), ...(preferred || {}) };
    await this._loadInfo();
    this._loadDomains();
  }

  t(key, vars) {
    let value = this._strings?.[key] ?? key;
    if (vars) {
      for (const [name, replacement] of Object.entries(vars)) {
        value = value.replace(new RegExp(`\\{${name}\\}`, "g"), replacement);
      }
    }
    return value;
  }

  async _call(message) {
    return this._hass.callWS({ entry_id: this._entryId, ...message });
  }

  async _loadInfo() {
    // A plain (re)load clears a stale "saved" notice; during a mutation the
    // notice belongs to what is being saved, so it is kept.
    if (!this._busy) this._notice = null;
    try {
      this._info = await this._call({ type: WS.info });
      this._error = null;
    } catch (err) {
      this._error = err?.message || String(err);
    }
    this._render();
  }

  async _loadDomains() {
    try {
      const result = await this._call({ type: WS.domains });
      this._domains = result?.domains || [];
    } catch (err) {
      this._domains = [];
    }
    this._render();
  }

  async _mutate(message, notice) {
    this._busy = true;
    this._notice = this.t("saving");
    this._render();
    try {
      await this._call(message);
      this._error = null;
      this._notice = notice ? this.t(notice) : null;
      await new Promise((resolve) => setTimeout(resolve, RELOAD_DELAY));
      await this._loadInfo();
    } catch (err) {
      this._error = err?.message || String(err);
      this._notice = null;
    } finally {
      this._busy = false;
      this._render();
    }
  }

  _navigate(path) {
    // The way the Home Assistant frontend moves between panels: push the
    // URL and let the router react, instead of reloading the whole app.
    history.pushState(null, "", path);
    this.dispatchEvent(
      new CustomEvent("location-changed", {
        bubbles: true,
        composed: true,
        detail: { replace: false },
      })
    );
  }

  _formatTime(iso) {
    if (!iso) return this.t("unknown");
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return this.t("unknown");
    return date.toLocaleString(this._hass?.locale?.language || undefined, {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  _formatAgo(iso) {
    if (!iso) return "";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "";
    const seconds = Math.round((date.getTime() - Date.now()) / 1000);
    const units = [
      ["day", 86400],
      ["hour", 3600],
      ["minute", 60],
    ];
    const formatter = new Intl.RelativeTimeFormat(
      this._hass?.locale?.language || undefined,
      { numeric: "auto" }
    );
    for (const [unit, size] of units) {
      if (Math.abs(seconds) >= size) {
        return formatter.format(Math.round(seconds / size), unit);
      }
    }
    return formatter.format(Math.round(seconds / 60), "minute");
  }

  _statusChip(status) {
    const map = {
      ok: "ok",
      updated: "updated",
      record_not_found: "warn",
      error: "error",
    };
    if (!status) return `<span class="chip">${escapeHtml(this.t("status_pending"))}</span>`;
    const cls = map[status] || "";
    return `<span class="chip ${cls}">${escapeHtml(this.t(`status_${status}`))}</span>`;
  }

  _render() {
    if (!this.shadowRoot) return;
    const info = this._info;
    const body = info ? this._renderSections(info) : this._renderEmpty();

    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <div class="bar glass">
        <a class="back" href="${INTEGRATION_PATH}" title="${escapeHtml(this.t("back"))}"
           aria-label="${escapeHtml(this.t("back"))}">${icon("back")}</a>
        <h1>${escapeHtml(info?.name || "TransIP DNS")}</h1>
        <button class="icon ${this._busy ? "busy" : ""}" id="refresh" ${this._busy ? "disabled" : ""}
          title="${escapeHtml(this.t("refresh_now"))}"
          aria-label="${escapeHtml(this.t("refresh_now"))}">${icon("refresh")}</button>
        <button class="icon" id="open-settings" ${info ? "" : "disabled"}
          title="${escapeHtml(this.t("settings"))}"
          aria-label="${escapeHtml(this.t("settings"))}">${icon("settings")}</button>
      </div>
      <div class="wrap">
        ${this._error ? `<div class="banner error">${escapeHtml(this._error)}</div>` : ""}
        ${this._notice ? `<div class="banner info">${escapeHtml(this._notice)}</div>` : ""}
        ${body}
      </div>
      ${this._dialog && info ? this._renderDialog(info) : ""}`;

    this._bind();
  }

  _renderEmpty() {
    return `<div class="card glass"><div class="body muted">${escapeHtml(this.t("loading"))}</div></div>`;
  }

  _renderSections(info) {
    return [
      this._renderStatus(info),
      this._renderRecords(info),
      this._renderHistory(info),
    ].join("");
  }

  _renderStatus(info) {
    const state = info.state;
    const long = (value) => (String(value || "").length > 20 ? " long" : "");
    const tiles = [];

    // One tile per address family: the address it has now, and underneath the
    // one it replaced. Splitting those over two tiles left an odd row out as
    // soon as IPv6 was in play.
    for (const family of ["ipv4", "ipv6"]) {
      const entry = state[family];
      const used = info.options.records.some(
        (record) => record.record_type === (family === "ipv4" ? "A" : "AAAA")
      );
      if (!entry.current && !used) continue;

      const sub = [];
      if (entry.previous) sub.push(this.t("was", { ip: entry.previous }));
      if (entry.changed_at) {
        sub.push(this.t("since", { when: this._formatAgo(entry.changed_at) }));
      }

      tiles.push(`
        <div class="tile glass">
          <div class="label">${escapeHtml(this.t(`external_${family}`))}</div>
          <div class="value${long(entry.current)}">${escapeHtml(
            entry.current || this.t("unknown")
          )}</div>
          <div class="sub">${escapeHtml(sub.join(" \u00b7 "))}</div>
        </div>`);
    }

    const records = state.records;
    const counts = {};
    for (const record of records) {
      const key = record.status || "pending";
      counts[key] = (counts[key] || 0) + 1;
    }
    const summary = Object.entries(counts)
      .map(([status, count]) => `${count} ${this.t(`status_${status}`)}`)
      .join(" \u00b7 ");

    tiles.push(`
      <div class="tile glass">
        <div class="label">${escapeHtml(this.t("records"))}</div>
        <div class="value">${records.length}</div>
        <div class="sub">${escapeHtml(summary || this.t("no_records_short"))}</div>
      </div>`);

    const failed = !state.last_update_success;
    tiles.push(`
      <div class="tile glass">
        <div class="label">${escapeHtml(this.t("status"))}</div>
        <div class="value" style="font-size:16px;font-family:inherit">${escapeHtml(
          failed ? this.t("health_error") : this.t("health_ok")
        )}</div>
        <div class="sub">${escapeHtml(
          this.t("interval_every", { minutes: info.options.update_interval })
        )}</div>
      </div>`);

    return `<div class="grid">${tiles.join("")}</div>
      ${state.error ? `<div class="banner error">${escapeHtml(state.error)}</div>` : ""}`;
  }

  _renderRecords(info) {
    const records = info.state.records;
    const editing = this._editing;
    const rows = records.length
      ? records
          .map(
            (record, index) => `
        <div class="row${editing === index ? " editing" : ""}">
          <div class="main">
            <div class="name">${escapeHtml(record.name)} &middot; ${escapeHtml(record.domain)}</div>
            <div class="meta">${escapeHtml(record.record_type)} &rarr; ${escapeHtml(
              record.ip || this.t("unknown")
            )}${record.error ? ` &middot; ${escapeHtml(record.error)}` : ""}</div>
          </div>
          ${this._statusChip(record.status)}
          <div class="acts">
            <button class="quiet" data-edit="${index}">${escapeHtml(this.t("edit"))}</button>
            <button class="quiet danger" data-remove="${index}">${escapeHtml(this.t("remove"))}</button>
          </div>
        </div>`
          )
          .join("")
      : `<div class="body muted">${escapeHtml(this.t("no_records"))}</div>`;

    const current = editing !== null ? info.options.records[editing] : null;
    const options = info.limits.record_types
      .map(
        (type) =>
          `<option value="${escapeHtml(type)}"${
            current && current.record_type === type ? " selected" : ""
          }>${escapeHtml(type)}</option>`
      )
      .join("");
    const domainList = this._domains
      .map((domain) => `<option value="${escapeHtml(domain)}"></option>`)
      .join("");

    return `
      <div class="card glass">
        <h2>${escapeHtml(this.t("records"))}</h2>
        ${rows}
        <div class="body" style="border-top:1px solid color-mix(in srgb, var(--primary-text-color, #000) 7%, transparent)">
          <div class="form">
            <div>
              <label class="field" for="new-domain">${escapeHtml(this.t("domain"))}</label>
              <input type="text" id="new-domain" list="domain-options" placeholder="example.nl"
                value="${escapeHtml(current ? current.domain : "")}" />
              <datalist id="domain-options">${domainList}</datalist>
            </div>
            <div>
              <label class="field" for="new-name">${escapeHtml(this.t("record_name"))}</label>
              <input type="text" id="new-name" value="${escapeHtml(current ? current.name : "@")}" />
            </div>
            <div>
              <label class="field" for="new-type">${escapeHtml(this.t("record_type"))}</label>
              <select id="new-type">${options}</select>
            </div>
            <div class="submit">
              ${
                editing !== null
                  ? `<button id="cancel-edit">${escapeHtml(this.t("cancel"))}</button>`
                  : ""
              }
              <button class="primary" id="add-record" ${this._busy ? "disabled" : ""}>${icon(
                editing !== null ? "check" : "plus",
                18
              )}<span style="margin-left:6px">${escapeHtml(
                this.t(editing !== null ? "save_record" : "add_record")
              )}</span></button>
            </div>
          </div>
          <div class="muted form-hint">${escapeHtml(this.t("record_hint"))}</div>
        </div>
      </div>`;
  }

  _renderHistory(info) {
    const blocks = [];
    for (const family of ["ipv4", "ipv6"]) {
      const changes = info.state[family].changes;
      if (!changes.length) continue;
      blocks.push(`
        <div style="margin-bottom:12px">
          <div class="label muted" style="margin-bottom:4px">${escapeHtml(
            this.t(`family_${family}`)
          )}</div>
          ${changes
            .map(
              (change) => `
            <div class="hist">
              <span class="when">${escapeHtml(this._formatTime(change.at))}</span>
              <span class="what">${escapeHtml(change.from)} &rarr; ${escapeHtml(change.to)}</span>
            </div>`
            )
            .join("")}
        </div>`);
    }

    return `
      <div class="card glass">
        <h2>${escapeHtml(this.t("history"))}</h2>
        <div class="body">
          ${blocks.length ? blocks.join("") : `<span class="muted">${escapeHtml(this.t("no_history"))}</span>`}
        </div>
      </div>`;
  }

  _openSettings() {
    const options = this._info.options;
    // A draft so the dialog can be cancelled without touching anything.
    this._draft = {
      update_interval: options.update_interval,
      notify_persistent: options.notify_persistent,
      notify_event: options.notify_event,
      notify_targets: [...options.notify_targets],
      panel_sidebar: options.panel_sidebar,
    };
    this._dialog = true;
    this._combo = false;
    this._comboQuery = "";
    this._render();
  }

  _closeSettings() {
    this._dialog = false;
    this._combo = false;
    this._draft = null;
    this._render();
  }

  _comboOptions(info) {
    const known = Array.from(
      new Set([...info.notify_targets, ...this._draft.notify_targets])
    ).sort();
    const query = this._comboQuery.trim().toLowerCase();
    return known.filter((target) => target.toLowerCase().includes(query));
  }

  _renderCombo(info) {
    const selected = this._draft.notify_targets;
    const chips = selected
      .map(
        (target) => `<span class="tag">${escapeHtml(target)}<button data-untag="${escapeHtml(
          target
        )}" aria-label="${escapeHtml(this.t("remove"))}">&times;</button></span>`
      )
      .join("");

    if (!this._combo) {
      return `
        <div class="combo">
          <div class="combo-field" id="combo-toggle" role="combobox" tabindex="0"
               aria-expanded="false" aria-haspopup="listbox">
            ${chips || `<span class="combo-placeholder">${escapeHtml(this.t("targets_empty"))}</span>`}
            <span class="combo-caret">&#9662;</span>
          </div>
        </div>`;
    }

    const matches = this._comboOptions(info);
    const query = this._comboQuery.trim();
    const custom =
      query && !matches.some((target) => target.toLowerCase() === query.toLowerCase())
        ? `<div class="option" data-add="${escapeHtml(query)}">
             <span class="mark">+</span>
             <span>${escapeHtml(this.t("add_custom", { name: query }))}</span>
           </div>`
        : "";
    const list = matches.length
      ? matches
          .map((target) => {
            const on = selected.includes(target);
            return `<div class="option" data-toggle="${escapeHtml(target)}" role="option"
                      aria-selected="${on}">
                <span class="mark">${on ? "&#10003;" : ""}</span>
                <span>notify.${escapeHtml(target)}</span>
              </div>`;
          })
          .join("")
      : `<div class="option empty">${escapeHtml(this.t("no_match"))}</div>`;

    return `
      <div class="combo">
        <div class="combo-field" id="combo-toggle" role="combobox" tabindex="0"
             aria-expanded="true" aria-haspopup="listbox">
          ${chips || `<span class="combo-placeholder">${escapeHtml(this.t("targets_empty"))}</span>`}
          <span class="combo-caret">&#9652;</span>
        </div>
        <div class="combo-pop">
          <input type="text" id="combo-search" autocomplete="off"
                 placeholder="${escapeHtml(this.t("search_targets"))}"
                 value="${escapeHtml(this._comboQuery)}" />
          <div class="combo-list" role="listbox">${list}${custom}</div>
        </div>
      </div>`;
  }

  _renderDialog(info) {
    const draft = this._draft;
    return `
      <div class="scrim" id="scrim">
        <div class="dialog" role="dialog" aria-modal="true" aria-label="${escapeHtml(
          this.t("settings")
        )}">
          <header>
            <h2>${escapeHtml(this.t("settings"))}</h2>
            <button class="quiet icon" id="close-settings" title="${escapeHtml(
              this.t("close")
            )}" aria-label="${escapeHtml(this.t("close"))}">${icon("close", 20)}</button>
          </header>
          <div class="dbody">

            <div class="dgroup">
              <div class="label">${escapeHtml(this.t("interval"))}</div>
              <div class="srow">
                <span class="main">${escapeHtml(this.t("interval_minutes", {
                  min: info.limits.min_interval,
                  max: info.limits.max_interval,
                }))}</span>
                <input type="number" id="interval" min="${info.limits.min_interval}"
                  max="${info.limits.max_interval}" step="1"
                  value="${escapeHtml(draft.update_interval)}" />
              </div>
            </div>

            <div class="dgroup">
              <div class="label">${escapeHtml(this.t("notifications"))}</div>
              <div class="srow">
                <span class="main">${escapeHtml(this.t("notify_persistent"))}</span>
                <input type="checkbox" class="switch" id="notify-persistent" ${
                  draft.notify_persistent ? "checked" : ""
                } />
              </div>
              <div class="srow">
                <span class="main">${escapeHtml(this.t("notify_event"))}
                  <span class="hint">${escapeHtml(this.t("notify_event_hint"))}</span></span>
                <input type="checkbox" class="switch" id="notify-event" ${
                  draft.notify_event ? "checked" : ""
                } />
              </div>
              <div style="margin-top:10px">
                <div class="label" style="margin-bottom:6px">${escapeHtml(
                  this.t("notify_targets")
                )}</div>
                ${this._renderCombo(info)}
              </div>
            </div>

            <div class="dgroup">
              <div class="label">${escapeHtml(this.t("panel"))}</div>
              <div class="srow">
                <span class="main">${escapeHtml(this.t("panel_sidebar"))}</span>
                <input type="checkbox" class="switch" id="panel-sidebar" ${
                  draft.panel_sidebar ? "checked" : ""
                } />
              </div>
              <div class="srow">
                <span class="main">${escapeHtml(this.t("panel_disable"))}
                  <span class="hint">${escapeHtml(this.t("panel_disable_hint"))}</span></span>
                <button class="danger" id="disable-panel" ${
                  this._busy ? "disabled" : ""
                }>${escapeHtml(this.t("turn_off"))}</button>
              </div>
            </div>

          </div>
          <footer>
            <span class="spacer"></span>
            <button id="cancel-settings">${escapeHtml(this.t("cancel"))}</button>
            <button class="primary" id="save-settings" ${
              this._busy ? "disabled" : ""
            }>${escapeHtml(this.t("save"))}</button>
          </footer>
        </div>
      </div>`;
  }

  _bind() {
    const root = this.shadowRoot;
    const on = (selector, handler, event = "click") => {
      const element = root.querySelector(selector);
      if (element) element.addEventListener(event, handler);
    };

    on("#refresh", () => this._mutate({ type: WS.refresh }, "refreshed"));
    on("#open-settings", () => this._openSettings());

    on("#add-record", () => {
      const domain = root.querySelector("#new-domain").value.trim();
      const name = root.querySelector("#new-name").value.trim();
      const recordType = root.querySelector("#new-type").value;
      if (!domain || !name) {
        this._error = this.t("record_incomplete");
        this._render();
        return;
      }
      const entry = { domain, name, record_type: recordType };
      const existing = this._info.options.records;
      // Editing replaces the record in place; adding appends.
      const records =
        this._editing !== null
          ? existing.map((record, i) => (i === this._editing ? entry : record))
          : existing.concat([entry]);
      this._editing = null;
      this._mutate({ type: WS.setRecords, records }, "saved");
    });

    on("#cancel-edit", () => {
      this._editing = null;
      this._render();
    });

    root.querySelectorAll("[data-edit]").forEach((button) => {
      button.addEventListener("click", () => {
        this._editing = Number(button.dataset.edit);
        this._render();
        root.querySelector("#new-domain")?.focus();
      });
    });

    root.querySelectorAll("[data-remove]").forEach((button) => {
      button.addEventListener("click", () => {
        const index = Number(button.dataset.remove);
        const records = this._info.options.records.filter((_, i) => i !== index);
        if (this._editing === index) this._editing = null;
        this._mutate({ type: WS.setRecords, records }, "saved");
      });
    });

    const back = root.querySelector("a.back");
    if (back) {
      back.addEventListener("click", (event) => {
        event.preventDefault();
        this._navigate(INTEGRATION_PATH);
      });
    }

    if (this._dialog) this._bindDialog(root);
  }

  _bindDialog(root) {
    const on = (selector, handler, event = "click") => {
      const element = root.querySelector(selector);
      if (element) element.addEventListener(event, handler);
    };
    // Keep the draft in step with the controls, so a re-render (opening the
    // combobox) never loses what was already changed.
    const readControls = () => {
      const interval = root.querySelector("#interval");
      const persistent = root.querySelector("#notify-persistent");
      const event = root.querySelector("#notify-event");
      const sidebar = root.querySelector("#panel-sidebar");
      if (interval) this._draft.update_interval = Number(interval.value);
      if (persistent) this._draft.notify_persistent = persistent.checked;
      if (event) this._draft.notify_event = event.checked;
      if (sidebar) this._draft.panel_sidebar = sidebar.checked;
    };

    on("#scrim", (event) => {
      if (event.target === root.querySelector("#scrim")) this._closeSettings();
    });
    on("#close-settings", () => this._closeSettings());
    on("#cancel-settings", () => this._closeSettings());

    on("#combo-toggle", () => {
      readControls();
      this._combo = !this._combo;
      this._comboQuery = "";
      this._render();
    });

    root.querySelectorAll("[data-untag]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        readControls();
        const target = button.dataset.untag;
        this._draft.notify_targets = this._draft.notify_targets.filter((t) => t !== target);
        this._render();
      });
    });

    root.querySelectorAll("[data-toggle]").forEach((option) => {
      option.addEventListener("click", () => {
        readControls();
        const target = option.dataset.toggle;
        const selected = this._draft.notify_targets;
        this._draft.notify_targets = selected.includes(target)
          ? selected.filter((t) => t !== target)
          : selected.concat([target]);
        this._render();
      });
    });

    root.querySelectorAll("[data-add]").forEach((option) => {
      option.addEventListener("click", () => {
        readControls();
        const target = option.dataset.add;
        if (!this._draft.notify_targets.includes(target)) {
          this._draft.notify_targets = this._draft.notify_targets.concat([target]);
        }
        this._comboQuery = "";
        this._render();
      });
    });

    const search = root.querySelector("#combo-search");
    if (search) {
      search.addEventListener("input", () => {
        this._comboQuery = search.value;
        this._render();
      });
      // The list is rebuilt on every keystroke, so put the cursor back.
      search.focus();
      search.setSelectionRange(search.value.length, search.value.length);
    }

    on("#save-settings", () => {
      readControls();
      this._mutate(
        {
          type: WS.setOptions,
          options: {
            update_interval: this._draft.update_interval,
            notify_persistent: this._draft.notify_persistent,
            notify_event: this._draft.notify_event,
            notify_targets: this._draft.notify_targets,
            panel_sidebar: this._draft.panel_sidebar,
          },
        },
        "saved"
      ).then(() => {
        if (!this._error) this._closeSettings();
      });
    });

    on("#disable-panel", async () => {
      if (!window.confirm(this.t("panel_disable_confirm"))) return;
      await this._mutate({ type: WS.setOptions, options: { panel_enabled: false } });
      this._navigate(INTEGRATION_PATH);
    });
  }

  _onKeyDown = (event) => {
    if (event.key !== "Escape") return;
    if (this._combo) {
      this._combo = false;
      this._render();
    } else if (this._dialog) {
      this._closeSettings();
    } else if (this._editing !== null) {
      this._editing = null;
      this._render();
    }
  };

}

// After the panel file changes, Home Assistant imports it under a new
// version URL in a browser tab that already defined the element. Defining
// it twice throws, so guard it: a page refresh picks up the new code.
if (!customElements.get("transip-dns-panel")) {
  customElements.define("transip-dns-panel", TransipDnsPanel);
}
export default TransipDnsPanel;
