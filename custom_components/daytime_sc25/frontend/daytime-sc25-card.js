/*
 * daytime SC25 card — Lovelace card for the daytime_sc25 integration.
 *
 *   type: custom:daytime-sc25-card
 *   entity: light.sc25_12345678        # the lamp light of the integration
 *   name: Aquarium                     # optional
 *
 * All other entities (channels, mode, effects, sensors) are found through the
 * lamp's device. Each can be overridden: mode, white, blue, red, green,
 * moonlight, clouds, acclimation, temperature, favorite.
 *   settings: false                    # hide the editable settings sections
 *
 *   type: custom:daytime-sc25-info-card  # compact status, no settings
 *   entity: light.sc25_12345678
 */

const CARD_VERSION = "0.3.5";

const CHANNELS = [
  { key: "white", color: "#f1ead2", stroke: "#c9bb8a" },
  { key: "blue", color: "#2fa8e0", stroke: "#2fa8e0" },
  { key: "red", color: "#e40131", stroke: "#e40131" },
  { key: "green", color: "#49b384", stroke: "#49b384" },
];

const EFFECTS = [
  { key: "moonlight", icon: "mdi:weather-night" },
  { key: "clouds", icon: "mdi:weather-cloudy" },
  { key: "acclimation", icon: "mdi:fishbowl-outline" },
];

// Editable settings, grouped like the vendor app. Rows refer to entities by
// domain and translation key; "when" hides a row unless that switch is on.
const SECTIONS = [
  {
    key: "s_daycycle", icon: "mdi:sun-clock-outline", rows: [
      { d: "time", k: "day_start" }, { d: "time", k: "day_end" },
      { d: "number", k: "sunrise_duration" }, { d: "number", k: "sunset_duration" },
      { d: "number", k: "day_intensity", when: "!individual_intensities" },
      { d: "switch", k: "individual_intensities" },
      { d: "number", k: "day_intensity_white", when: "individual_intensities" },
      { d: "number", k: "day_intensity_blue", when: "individual_intensities" },
      { d: "number", k: "day_intensity_red", when: "individual_intensities" },
      { d: "number", k: "day_intensity_green", when: "individual_intensities" },
      { d: "switch", k: "midday_dimming" },
      { d: "time", k: "midday_start", when: "midday_dimming" },
      { d: "time", k: "midday_end", when: "midday_dimming" },
      { d: "number", k: "midday_intensity", when: "midday_dimming" },
      { d: "switch", k: "sun_glow" },
      { d: "number", k: "sunrise_glow_duration", when: "sun_glow" },
      { d: "number", k: "sunrise_glow_intensity", when: "sun_glow" },
      { d: "number", k: "sunset_glow_duration", when: "sun_glow" },
      { d: "number", k: "sunset_glow_intensity", when: "sun_glow" },
      { d: "button", k: "preview_daycycle" },
    ],
  },
  {
    key: "s_moon", icon: "mdi:weather-night", rows: [
      { d: "switch", k: "moonlight" },
      { d: "number", k: "moon_max" }, { d: "number", k: "moon_min" },
      { d: "switch", k: "moon_cycle" },
      { d: "switch", k: "moon_white" }, { d: "switch", k: "moon_blue" },
      { d: "switch", k: "moon_red" }, { d: "switch", k: "moon_green" },
      { d: "switch", k: "moon_individual_times" },
      { d: "time", k: "moon_start", when: "moon_individual_times" },
      { d: "time", k: "moon_end", when: "moon_individual_times" },
    ],
  },
  {
    key: "s_clouds", icon: "mdi:weather-cloudy", rows: [
      { d: "switch", k: "clouds" },
      { d: "number", k: "cloud_probability" }, { d: "number", k: "cloud_max_per_day" },
      { d: "number", k: "cloud_strength_min" }, { d: "number", k: "cloud_strength_max" },
      { d: "number", k: "cloud_duration_min" }, { d: "number", k: "cloud_duration_max" },
    ],
  },
  {
    key: "s_acclimation", icon: "mdi:fishbowl-outline", rows: [
      { d: "switch", k: "acclimation" }, { d: "switch", k: "acclimation_pause" },
      { d: "number", k: "acclimation_days" }, { d: "number", k: "acclimation_reduction" },
      { d: "number", k: "acclimation_current_day" },
    ],
  },
];

const TEXT = {
  de: {
    white: "Weiß", blue: "Blau", red: "Rot", green: "Grün",
    moonlight: "Mondlicht", clouds: "Wolken", acclimation: "Eingewöhnung",
    daycycle: "Tagesverlauf", manual: "Manuell", off: "Aus",
    channels: "Lichtfarben", effects: "Effekte", schedule: "Tagesverlauf",
    back_in: "zurück in", unavailable: "Nicht erreichbar",
    sunrise: "Sonnenaufgang", sunset: "Sonnenuntergang", now: "jetzt",
    missing: "Entität nicht gefunden",
    favorites: "Favoriten", settings: "Einstellungen", mix: "Mischfarbe",
    i_now: "Jetzt", i_plan: "Laut Plan", i_next: "Als Nächstes", i_clouds: "Wolken", i_moon: "Mond",
    i_accl: "Eingewöhnung", i_off: "aus", i_remaining: "noch", i_light: "Licht", i_at: "um",
    i_paused_until: "Tagesverlauf pausiert · zurück um {t}", i_paused_open: "Tagesverlauf pausiert · bis auf Weiteres",
    i_day_of: "Tag {d} von {n}", i_day_short: "Eingewöhnung Tag {d}/{n}", i_paused: "pausiert", i_brightness: "Helligkeit",
    e_sunrise: "Sonnenaufgang beginnt", e_full: "Volle Helligkeit", e_sunset: "Sonnenuntergang beginnt",
    e_night: "Nacht beginnt", e_midday: "Mittagsabsenkung", e_midday_end: "Mittagsabsenkung endet",
    tomorrow: "morgen", in: "in",
    m_new: "Neumond", m_wax_c: "Zunehmende Sichel", m_first: "Erstes Viertel", m_wax_g: "Zunehmender Mond",
    m_full: "Vollmond", m_wan_g: "Abnehmender Mond", m_last: "Letztes Viertel", m_wan_c: "Abnehmende Sichel",
    h_expert: "Eigene Tageskurve (Expertenmodus) – Einstellungen des einfachen Modus überschreiben sie.",
    h_update: "Firmware-Update verfügbar: {v}", h_unavailable: "Controller nicht erreichbar",
    next_cloud: "Nächste Wolke", cloud_now: "Wolke zieht durch", moon_day: "Mond",
    s_daycycle: "Tagesverlauf", s_moon: "Mondlicht", s_clouds: "Wolken", s_acclimation: "Eingewöhnung",
    day_start: "Tagesbeginn", day_end: "Tagesende", sunrise_duration: "Sonnenaufgang",
    sunset_duration: "Sonnenuntergang", day_intensity: "Helligkeit",
    individual_intensities: "Helligkeit je Lichtfarbe",
    day_intensity_white: "Weiß", day_intensity_blue: "Blau", day_intensity_red: "Rot", day_intensity_green: "Grün",
    midday_dimming: "Mittagsabsenkung", midday_start: "Beginn", midday_end: "Ende", midday_intensity: "Helligkeit",
    sun_glow: "Morgen-/Abendrot", sunrise_glow_duration: "Morgenrot Dauer", sunrise_glow_intensity: "Morgenrot Stärke",
    sunset_glow_duration: "Abendrot Dauer", sunset_glow_intensity: "Abendrot Stärke",
    preview_daycycle: "Vorschau im Zeitraffer", play: "Abspielen",
    moon_max: "Vollmond", moon_min: "Neumond", moon_cycle: "Mondphasen",
    moon_white: "Farbe Weiß", moon_blue: "Farbe Blau", moon_red: "Farbe Rot", moon_green: "Farbe Grün",
    moon_individual_times: "Eigene Zeiten", moon_start: "Beginn", moon_end: "Ende",
    cloud_probability: "Wahrscheinlichkeit", cloud_max_per_day: "Max. pro Tag",
    cloud_strength_min: "Stärke min.", cloud_strength_max: "Stärke max.",
    cloud_duration_min: "Dauer min.", cloud_duration_max: "Dauer max.",
    acclimation_pause: "Pausiert", acclimation_days: "Dauer", acclimation_reduction: "Absenkung",
    acclimation_current_day: "Aktueller Tag",
  },
  en: {
    white: "White", blue: "Blue", red: "Red", green: "Green",
    moonlight: "Moonlight", clouds: "Clouds", acclimation: "Acclimation",
    daycycle: "Daycycle", manual: "Manual", off: "Off",
    channels: "Channels", effects: "Effects", schedule: "Daycycle",
    back_in: "back in", unavailable: "Unavailable",
    sunrise: "Sunrise", sunset: "Sunset", now: "now",
    missing: "Entity not found",
    favorites: "Favorites", settings: "Settings", mix: "Mixed colour",
    i_now: "Now", i_plan: "Scheduled", i_next: "Next", i_clouds: "Clouds", i_moon: "Moon",
    i_accl: "Acclimation", i_off: "off", i_remaining: "", i_light: "light", i_at: "at",
    i_paused_until: "Daycycle paused · resumes at {t}", i_paused_open: "Daycycle paused · until changed",
    i_day_of: "Day {d} of {n}", i_day_short: "Acclimation day {d}/{n}", i_paused: "paused", i_brightness: "brightness",
    e_sunrise: "Sunrise starts", e_full: "Full brightness", e_sunset: "Sunset starts",
    e_night: "Night starts", e_midday: "Midday dimming", e_midday_end: "Midday dimming ends",
    tomorrow: "tomorrow", in: "in",
    m_new: "New moon", m_wax_c: "Waxing crescent", m_first: "First quarter", m_wax_g: "Waxing gibbous",
    m_full: "Full moon", m_wan_g: "Waning gibbous", m_last: "Last quarter", m_wan_c: "Waning crescent",
    h_expert: "Custom curve (expert mode) – easy-mode settings will overwrite it.",
    h_update: "Firmware update available: {v}", h_unavailable: "Controller unreachable",
    next_cloud: "Next cloud", cloud_now: "Cloud passing", moon_day: "Moon",
    s_daycycle: "Daycycle", s_moon: "Moonlight", s_clouds: "Clouds", s_acclimation: "Acclimation",
    day_start: "Day start", day_end: "Day end", sunrise_duration: "Sunrise",
    sunset_duration: "Sunset", day_intensity: "Brightness",
    individual_intensities: "Brightness per colour",
    day_intensity_white: "White", day_intensity_blue: "Blue", day_intensity_red: "Red", day_intensity_green: "Green",
    midday_dimming: "Midday dimming", midday_start: "Start", midday_end: "End", midday_intensity: "Brightness",
    sun_glow: "Sunrise/sunset glow", sunrise_glow_duration: "Sunrise glow length", sunrise_glow_intensity: "Sunrise glow strength",
    sunset_glow_duration: "Sunset glow length", sunset_glow_intensity: "Sunset glow strength",
    preview_daycycle: "Fast-motion preview", play: "Play",
    moon_max: "Full moon", moon_min: "New moon", moon_cycle: "Moon phases",
    moon_white: "Colour white", moon_blue: "Colour blue", moon_red: "Colour red", moon_green: "Colour green",
    moon_individual_times: "Custom times", moon_start: "Start", moon_end: "End",
    cloud_probability: "Probability", cloud_max_per_day: "Max. per day",
    cloud_strength_min: "Strength min.", cloud_strength_max: "Strength max.",
    cloud_duration_min: "Duration min.", cloud_duration_max: "Duration max.",
    acclimation_pause: "Paused", acclimation_days: "Duration", acclimation_reduction: "Reduction",
    acclimation_current_day: "Current day",
  },
};

const fmtTime = (minutes) => {
  const m = ((Math.round(minutes) % 1440) + 1440) % 1440;
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
};

const fmtDuration = (seconds) => {
  const m = Math.max(1, Math.ceil(seconds / 60));
  return m >= 60 ? `${Math.floor(m / 60)} h ${m % 60} min` : `${m} min`;
};

// Approximate emitted colour of each LED channel (sRGB).
const LED_RGB = { white: [255, 241, 224], blue: [20, 80, 255], red: [255, 25, 10], green: [20, 235, 70] };

const COLOR_NAMES = {
  de: { warm: "Warmweiß", neutral: "Neutralweiß", cool: "Kaltweiß", red: "Rot", orange: "Orange",
        yellow: "Gelb", green: "Grün", cyan: "Türkis", blue: "Blau", violet: "Blauviolett",
        purple: "Violett", pink: "Pink",
        pale: { red: "Rosa", orange: "Apricot", yellow: "Hellgelb", green: "Mintgrün", cyan: "Eisblau",
                blue: "Hellblau", violet: "Lavendel", purple: "Flieder", pink: "Rosa" } },
  en: { warm: "Warm white", neutral: "Neutral white", cool: "Cool white", red: "Red", orange: "Orange",
        yellow: "Yellow", green: "Green", cyan: "Cyan", blue: "Blue", violet: "Blue violet",
        purple: "Purple", pink: "Pink",
        pale: { red: "Rose", orange: "Apricot", yellow: "Pale yellow", green: "Mint", cyan: "Ice blue",
                blue: "Light blue", violet: "Lavender", purple: "Lilac", pink: "Rose" } },
};

/**
 * Additive mix of the channels as light, like the LEDs combine in the tank.
 * values: {white, blue, red, green} in percent. Returns the hue at full
 * brightness (css/hex) plus a colour name, or null when everything is off.
 */
function mixLight(values, lang = "en") {
  let r = 0, g = 0, b = 0;
  for (const [key, v] of Object.entries(values || {})) {
    const c = LED_RGB[key];
    if (!c || !v) continue;
    r += (c[0] * v) / 100; g += (c[1] * v) / 100; b += (c[2] * v) / 100;
  }
  const peak = Math.max(r, g, b);
  if (peak <= 0) return null;
  const rgb = [r, g, b].map((x) => Math.round((x / peak) * 255));
  const hex = "#" + rgb.map((x) => x.toString(16).padStart(2, "0")).join("");
  const names = COLOR_NAMES[lang] || COLOR_NAMES.en;
  // Name from hue and saturation.
  const [rn, gn, bn] = rgb.map((x) => x / 255);
  const max = Math.max(rn, gn, bn), min = Math.min(rn, gn, bn), d = max - min;
  const sat = max === 0 ? 0 : d / max;
  let name;
  if (sat < 0.18) {
    name = bn - rn > 0.04 ? names.cool : rn - bn > 0.08 ? names.warm : names.neutral;
  } else {
    let h = 0;
    if (d) h = max === rn ? ((gn - bn) / d) % 6 : max === gn ? (bn - rn) / d + 2 : (rn - gn) / d + 4;
    h = (h * 60 + 360) % 360;
    const bands = [[15, "red"], [40, "orange"], [70, "yellow"], [160, "green"], [195, "cyan"],
                   [245, "blue"], [270, "violet"], [320, "purple"], [345, "pink"], [360, "red"]];
    const band = bands.find(([limit]) => h < limit)[1];
    name = sat < 0.45 ? names.pale[band] : names[band];
  }
  return { css: `rgb(${rgb.join(", ")})`, hex, name };
}

class DaytimeSC25Card extends HTMLElement {
  static getStubConfig(hass) {
    const lamp = Object.values(hass.entities || {}).find(
      (e) => e.platform === "daytime_sc25" && e.translation_key === "lamp"
    );
    return { entity: lamp ? lamp.entity_id : "light.sc25" };
  }

  setConfig(config) {
    if (!config || !config.entity) throw new Error("entity (lamp light) is required");
    this._config = config;
    this._signature = null;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    if (this._dragging) return; // never re-render under the user's finger
    const sig = this._stateSignature();
    if (sig === this._signature) return;
    this._signature = sig;
    this._render();
  }

  getCardSize() {
    return 8;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  // -- entity lookup ------------------------------------------------------

  get _t() {
    const lang = (this._hass && this._hass.language) || "en";
    return TEXT[lang.split("-")[0]] || TEXT.en;
  }

  _resolve() {
    const hass = this._hass;
    const lampId = this._config.entity;
    const ids = { lamp: lampId };
    const reg = hass.entities || {};
    const deviceId = reg[lampId] && reg[lampId].device_id;
    const byKey = {};
    if (deviceId) {
      for (const e of Object.values(reg)) {
        if (e.device_id === deviceId && e.translation_key) {
          byKey[`${e.entity_id.split(".")[0]}:${e.translation_key}`] = e.entity_id;
        }
      }
    }
    const pick = (cfgKey, domain, tk) => this._config[cfgKey] || byKey[`${domain}:${tk}`];
    this._byKey = byKey;
    ids.mode = pick("mode", "select", "mode");
    ids.favorite = pick("favorite", "select", "favorite");
    ids.next_cloud = pick("next_cloud", "sensor", "next_cloud");
    ids.cloud_passing = pick("cloud_passing", "binary_sensor", "cloud_passing");
    ids.moon_phase = pick("moon_phase", "sensor", "moon_phase_day");
    ids.moon_level = pick("moon_level", "sensor", "moon_intensity");
    ids.accl_day = pick("acclimation_day", "sensor", "acclimation_day");
    ids.accl_level = pick("acclimation_level", "sensor", "acclimation_level");
    ids.firmware = pick("firmware", "update", "firmware");
    ids.wifi = pick("wifi", "sensor", "wifi_network");
    ids.temperature = pick("temperature", "sensor", "module_temperature");
    for (const ch of CHANNELS) ids[ch.key] = pick(ch.key, "light", `channel_${ch.key}`);
    for (const fx of EFFECTS) ids[fx.key] = pick(fx.key, "switch", fx.key);
    return ids;
  }

  _state(id) {
    return id ? this._hass.states[id] : undefined;
  }

  _stateSignature() {
    if (!this._hass || !this._config) return "";
    const ids = this._resolve();
    const minute = Math.floor(Date.now() / 60000);
    const all = new Set([...Object.values(ids), ...Object.values(this._byKey || {})]);
    return JSON.stringify([
      minute,
      this._hass.language,
      [...all].map((id) => {
        const s = this._state(id);
        return s ? [s.state, s.attributes.brightness, s.attributes.manual_fallback_remaining, s.attributes.daycycle, s.attributes.favorites] : null;
      }),
    ]);
  }

  // -- actions ------------------------------------------------------------

  _call(domain, service, data) {
    return this._hass.callService(domain, service, data);
  }

  _toast(message) {
    this.dispatchEvent(new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }));
  }

  _setBrightness(id, pct) {
    if (pct <= 0) return this._call("light", "turn_off", { entity_id: id });
    return this._call("light", "turn_on", { entity_id: id, brightness_pct: pct });
  }

  // -- rendering ----------------------------------------------------------

  _pct(state) {
    if (!state || state.state !== "on") return 0;
    return Math.round(((state.attributes.brightness || 0) * 100) / 255);
  }

  _glow(values) {
    const mix = mixLight(values);
    return mix ? mix.css : null;
  }

  _chart(attrs, activeChannels) {
    const points = Array.isArray(attrs.daycycle) ? attrs.daycycle : [];
    if (points.length < 2) return "";
    const W = 600, H = 120, pad = 4;
    const x = (min) => pad + (min / 1440) * (W - 2 * pad);
    const y = (v) => H - pad - (v / 100) * (H - 2 * pad);
    const t = this._t;
    const now = new Date();
    const nowMin = now.getHours() * 60 + now.getMinutes();

    const lines = activeChannels.map((ch) => {
      const idx = CHANNELS.indexOf(ch) + 1;
      const d = points.map((p, i) => `${i ? "L" : "M"}${x(p[0]).toFixed(1)},${y(p[idx] || 0).toFixed(1)}`).join(" ");
      return `<path d="${d}" fill="none" stroke="${ch.stroke}" stroke-width="2.5" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>`;
    });
    // Envelope fill under the brightest channel.
    const env = points.map((p) => [p[0], Math.max(...activeChannels.map((ch) => p[CHANNELS.indexOf(ch) + 1] || 0))]);
    const area = `M${x(env[0][0])},${y(0)} ` + env.map((p) => `L${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join(" ") + ` L${x(env[env.length - 1][0])},${y(0)} Z`;

    const grid = [0, 6, 12, 18, 24]
      .map((h) => `<line x1="${x(h * 60)}" x2="${x(h * 60)}" y1="${pad}" y2="${H - pad}" class="grid"/>`)
      .join("");

    const sunrise = attrs.day_start != null ? `<span>☀︎ ${fmtTime(attrs.day_start)}</span>` : "";
    const sunset = attrs.day_end != null ? `<span>☾ ${fmtTime(attrs.day_end)}</span>` : "";

    return `
      <div class="section-title">${t.schedule}<span class="meta">${sunrise}${sunset}</span></div>
      <div class="chart">
        <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <linearGradient id="fill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stop-color="var(--sc-accent)" stop-opacity="0.28"/>
              <stop offset="1" stop-color="var(--sc-accent)" stop-opacity="0.02"/>
            </linearGradient>
          </defs>
          ${grid}
          <path d="${area}" fill="url(#fill)"/>
          ${lines.join("")}
          <line x1="${x(nowMin)}" x2="${x(nowMin)}" y1="0" y2="${H}" class="now"/>
        </svg>
        <div class="axis"><span>00</span><span>06</span><span>12</span><span>18</span><span>24</span></div>
      </div>`;
  }

  /** One quiet line with Wi-Fi, IP address and firmware version. */
  _deviceFooter(ids) {
    const wifi = this._state(ids.wifi);
    const fw = this._state(ids.firmware);
    const parts = [
      wifi && wifi.state && !["unknown", "unavailable"].includes(wifi.state) ? this._esc(wifi.state) : "",
      wifi && wifi.attributes.ip_address ? this._esc(wifi.attributes.ip_address) : "",
      fw && fw.attributes.installed_version ? `FW ${this._esc(fw.attributes.installed_version)}` : "",
    ].filter(Boolean);
    return parts.length ? `<div class="ifooter"><ha-icon icon="mdi:wifi"></ha-icon>${parts.join(" · ")}</div>` : "";
  }

  _mixRow(values) {
    const lang = ((this._hass && this._hass.language) || "en").split("-")[0];
    const mix = mixLight(values, lang);
    return `<div class="mix"><span class="mix-swatch" style="background:${mix ? mix.css : "transparent"}"></span>
      <span class="mix-label">${this._t.mix}</span>
      <span class="mix-name">${mix ? `${mix.name} <small>${mix.hex}</small>` : this._t.off}</span></div>`;
  }

  _key(domain, tk) {
    return (this._byKey || {})[`${domain}:${tk}`];
  }

  _isOn(tk) {
    const s = this._state(this._key("switch", tk));
    return !!s && s.state === "on";
  }

  _favorites(ids) {
    const fav = this._state(ids.favorite);
    const list = (fav && fav.attributes.favorites) || [];
    if (!list.length) return "";
    const chips = list
      .map((f) => {
        const mix = this._glow({ white: f.channels[0], blue: f.channels[1], red: f.channels[2], green: f.channels[3] });
        return `<button class="chip fav ${fav.state === f.name ? "on" : ""}" data-favorite="${this._esc(f.name)}">
          <span class="swatch" style="background:${mix || "var(--sc-track)"}"></span><span>${this._esc(f.name)}</span></button>`;
      })
      .join("");
    return `<div class="section-title">${this._t.favorites}</div><div class="chips">${chips}</div>`;
  }

  _status(ids) {
    const t = this._t;
    const parts = [];
    const passing = this._state(ids.cloud_passing);
    const next = this._state(ids.next_cloud);
    if (passing && passing.state === "on") parts.push(`<span><ha-icon icon="mdi:weather-cloudy-clock"></ha-icon>${t.cloud_now}</span>`);
    else if (next && next.state && !["unknown", "unavailable"].includes(next.state)) {
      const d = new Date(next.state);
      if (!isNaN(d)) parts.push(`<span><ha-icon icon="mdi:weather-cloudy-clock"></ha-icon>${t.next_cloud} ${fmtTime(d.getHours() * 60 + d.getMinutes())}</span>`);
    }
    const moon = this._state(ids.moon_phase);
    if (moon && this._isOn("moonlight") && !isNaN(parseFloat(moon.state)))
      parts.push(`<span><ha-icon icon="mdi:moon-waxing-gibbous"></ha-icon>${t.moon_day} ${parseFloat(moon.state).toFixed(1)} / 29.5</span>`);
    return parts.length ? `<div class="status">${parts.join("")}</div>` : "";
  }

  _esc(v) {
    return String(v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  }

  _row(row, disabled) {
    const st = this._state(this._key(row.d, row.k));
    if (!st) return "";
    if (row.when) {
      const neg = row.when.startsWith("!");
      if (this._isOn(row.when.replace("!", "")) === neg) return "";
    }
    const id = this._esc(st.entity_id);
    const label = this._esc(this._t[row.k] || st.attributes.friendly_name);
    const dis = disabled || st.state === "unavailable" ? "disabled" : "";
    let control = "";
    if (row.d === "switch") {
      const on = st.state === "on";
      control = `<button class="toggle ${on ? "on" : ""}" role="switch" aria-checked="${on}" aria-label="${label}" data-switch="${id}" ${dis}><span></span></button>`;
    } else if (row.d === "number") {
      const a = st.attributes;
      const v = Number(st.state);
      const unit = this._esc(a.unit_of_measurement || "");
      if (unit === "%") {
        control = `<input type="range" class="mini" min="${this._esc(a.min)}" max="${this._esc(a.max)}" step="${this._esc(a.step)}" value="${isNaN(v) ? 0 : v}" data-number="${id}" aria-label="${label}" ${dis}>
          <span class="value">${isNaN(v) ? "–" : Math.round(v)}<small>%</small></span>`;
      } else {
        control = `<span class="numbox"><input type="number" min="${this._esc(a.min)}" max="${this._esc(a.max)}" step="${this._esc(a.step)}" value="${isNaN(v) ? "" : Math.round(v)}" data-number="${id}" aria-label="${label}" ${dis}><small>${unit}</small></span>`;
      }
    } else if (row.d === "time") {
      const v = this._esc((st.state || "").slice(0, 5));
      control = `<input type="time" value="${v}" data-time="${id}" aria-label="${label}" ${dis}>`;
    } else if (row.d === "button") {
      control = `<button class="action" data-press="${id}" ${dis}><ha-icon icon="mdi:play"></ha-icon>${this._t.play}</button>`;
    }
    return `<div class="row ${row.d} ${row.when ? "sub" : ""}"><span class="row-label">${label}</span><span class="row-control">${control}</span></div>`;
  }

  _settings(disabled) {
    if (this._config.settings === false) return "";
    this._open = this._open || {};
    const sections = SECTIONS.map((sec) => {
      const rows = sec.rows.map((r) => this._row(r, disabled)).join("");
      if (!rows) return "";
      return `<details data-section="${sec.key}" ${this._open[sec.key] ? "open" : ""}>
        <summary><ha-icon icon="${sec.icon}"></ha-icon><span>${this._t[sec.key]}</span><ha-icon class="chev" icon="mdi:chevron-down"></ha-icon></summary>
        <div class="rows">${rows}</div></details>`;
    }).join("");
    return sections ? `<div class="section-title">${this._t.settings}</div><div class="settings">${sections}</div>` : "";
  }

  _render() {
    if (!this._hass || !this._config) return;
    const t = this._t;
    const ids = this._resolve();
    const lamp = this._state(ids.lamp);
    const root = this.shadowRoot;

    if (!lamp) {
      root.innerHTML = `${STYLE}<ha-card><div class="warning">${t.missing}: ${this._esc(this._config.entity)}</div></ha-card>`;
      return;
    }

    const unavailable = lamp.state === "unavailable";
    const mode = this._state(ids.mode);
    const modeAttrs = (mode && mode.attributes) || {};
    const isManual = mode && mode.state === "manual";
    const temp = this._state(ids.temperature);
    const activeChannels = CHANNELS.filter((ch) => this._state(ids[ch.key]));
    const values = {};
    for (const ch of activeChannels) values[ch.key] = this._pct(this._state(ids[ch.key]));
    const master = this._pct(lamp);
    const glow = this._glow(values);
    const name = this._esc(this._config.name || lamp.attributes.friendly_name || "SC25");

    let subtitle = unavailable ? t.unavailable : isManual ? t.manual : t.daycycle;
    if (!unavailable) subtitle += ` · ${master ? master + " %" : t.off}`;
    const remaining = modeAttrs.manual_fallback_remaining;
    if (isManual && remaining != null) subtitle += ` · ${t.back_in} ${fmtDuration(remaining)}`;

    const channelRows = activeChannels
      .map((ch) => {
        const v = values[ch.key];
        return `
        <div class="channel" style="--ch:${ch.color}; --ch-stroke:${ch.stroke}">
          <span class="dot"></span>
          <span class="label">${t[ch.key]}</span>
          <input type="range" min="0" max="100" step="1" value="${v}" data-light="${this._esc(ids[ch.key])}" aria-label="${t[ch.key]}" ${unavailable ? "disabled" : ""}>
          <span class="value">${v}<small>%</small></span>
        </div>`;
      })
      .join("");

    const effectChips = EFFECTS.filter((fx) => this._state(ids[fx.key]))
      .map((fx) => {
        const on = this._state(ids[fx.key]).state === "on";
        return `<button class="chip ${on ? "on" : ""}" data-switch="${this._esc(ids[fx.key])}" aria-pressed="${on}" ${unavailable ? "disabled" : ""}>
          <ha-icon icon="${fx.icon}"></ha-icon><span>${t[fx.key]}</span></button>`;
      })
      .join("");

    root.innerHTML = `${STYLE}
      <ha-card class="${unavailable ? "unavailable" : ""}">
        <div class="header">
          <button class="orb ${master ? "lit" : ""}" style="${glow ? `--glow:${glow}` : ""}" data-toggle aria-label="${name}" ${unavailable ? "disabled" : ""}>
            <ha-icon icon="mdi:${master ? "lightbulb-on" : "lightbulb-outline"}"></ha-icon>
          </button>
          <div class="title">
            <div class="name">${name}</div>
            <div class="subtitle">${subtitle}</div>
          </div>
          ${temp && !isNaN(parseFloat(temp.state)) ? `<div class="badge" title="${this._esc(temp.attributes.friendly_name || "")}"><ha-icon icon="mdi:thermometer"></ha-icon>${parseFloat(temp.state).toFixed(1)} °C</div>` : ""}
        </div>

        <div class="master">
          <input type="range" min="0" max="100" step="1" value="${master}" data-light="${this._esc(ids.lamp)}" aria-label="${name}" ${unavailable ? "disabled" : ""}>
        </div>

        ${mode ? `
        <div class="segmented" role="radiogroup">
          <button data-mode="daycycle" class="${!isManual ? "active" : ""}" role="radio" aria-checked="${!isManual}" ${unavailable ? "disabled" : ""}>
            <ha-icon icon="mdi:sun-clock-outline"></ha-icon>${t.daycycle}</button>
          <button data-mode="manual" class="${isManual ? "active" : ""}" role="radio" aria-checked="${isManual}" ${unavailable ? "disabled" : ""}>
            <ha-icon icon="mdi:tune-variant"></ha-icon>${t.manual}</button>
        </div>` : ""}

        ${this._chart(modeAttrs, activeChannels)}

        ${channelRows ? `<div class="section-title">${t.channels}</div><div class="channels">${channelRows}</div>${this._mixRow(values)}` : ""}

        ${this._favorites(ids)}

        ${effectChips ? `<div class="section-title">${t.effects}</div><div class="chips">${effectChips}</div>` : ""}
        ${this._status(ids)}

        ${this._settings(unavailable)}
        ${this._deviceFooter(ids)}
      </ha-card>`;

    this._bind(ids, master);
  }

  _bind(ids, master) {
    const root = this.shadowRoot;
    root.querySelectorAll("input[type=range][data-light]").forEach((input) => {
      // WebKit has no progress pseudo-element; the track gradient uses --p.
      input.style.setProperty("--p", `${input.value}%`);
      const row = input.closest(".channel");
      const label = row && row.querySelector(".value");
      input.addEventListener("pointerdown", () => (this._dragging = true));
      input.addEventListener("input", () => {
        this._dragging = true;
        input.style.setProperty("--p", `${input.value}%`);
        if (label) label.innerHTML = `${input.value}<small>%</small>`;
      });
      input.addEventListener("change", async () => {
        try {
          await this._setBrightness(input.dataset.light, Number(input.value));
        } finally {
          this._dragging = false;
          this._signature = null;
          this.hass = this._hass;
        }
      });
    });
    const commit = async (fn) => {
      try {
        await fn();
      } catch (err) {
        // Show the integration's validation message (e.g. day too short).
        this._toast(err && err.message ? err.message : String(err));
      } finally {
        this._dragging = false;
        this._signature = null;
        this.hass = this._hass;
      }
    };
    root.querySelectorAll("input[data-number]").forEach((input) => {
      const label = input.type === "range" && input.parentElement.querySelector(".value");
      input.style.setProperty("--p", `${((input.value - input.min) / (input.max - input.min || 1)) * 100}%`);
      const hold = () => (this._dragging = true);
      input.addEventListener("pointerdown", hold);
      input.addEventListener("focus", hold);
      input.addEventListener("input", () => {
        this._dragging = true;
        input.style.setProperty("--p", `${((input.value - input.min) / (input.max - input.min || 1)) * 100}%`);
        if (label) label.innerHTML = `${input.value}<small>%</small>`;
      });
      input.addEventListener("blur", () => { if (input.type !== "range") { this._dragging = false; } });
      input.addEventListener("change", () =>
        commit(() => this._call("number", "set_value", { entity_id: input.dataset.number, value: Number(input.value) }))
      );
    });
    root.querySelectorAll("input[data-time]").forEach((input) => {
      input.addEventListener("focus", () => (this._dragging = true));
      input.addEventListener("blur", () => (this._dragging = false));
      input.addEventListener("change", () => {
        if (!input.value) return;
        commit(() => this._call("time", "set_value", { entity_id: input.dataset.time, time: `${input.value}:00` }));
      });
    });
    root.querySelectorAll("[data-press]").forEach((btn) =>
      btn.addEventListener("click", () => commit(() => this._call("button", "press", { entity_id: btn.dataset.press })))
    );
    root.querySelectorAll("[data-favorite]").forEach((btn) =>
      btn.addEventListener("click", () =>
        commit(() => this._call("select", "select_option", { entity_id: ids.favorite, option: btn.dataset.favorite }))
      )
    );
    root.querySelectorAll("details[data-section]").forEach((el) =>
      el.addEventListener("toggle", () => (this._open[el.dataset.section] = el.open))
    );
    const toggle = root.querySelector("[data-toggle]");
    if (toggle)
      toggle.addEventListener("click", () =>
        this._call("light", master ? "turn_off" : "turn_on", { entity_id: ids.lamp })
      );
    root.querySelectorAll("[data-mode]").forEach((btn) =>
      btn.addEventListener("click", () =>
        this._call("select", "select_option", { entity_id: ids.mode, option: btn.dataset.mode })
      )
    );
    root.querySelectorAll("[data-switch]").forEach((btn) =>
      btn.addEventListener("click", () =>
        commit(() =>
          this._call("switch", btn.classList.contains("on") ? "turn_off" : "turn_on", {
            entity_id: btn.dataset.switch,
          })
        )
      )
    );
  }
}

const STYLE = `<style>
  :host {
    --sc-accent: var(--primary-color, #e94e0e);
    --sc-muted: var(--secondary-text-color, #727272);
    --sc-line: var(--divider-color, rgba(127,127,127,.2));
    --sc-track: rgba(127,127,127,.18);
  }
  ha-card { padding: 16px; display: flex; flex-direction: column; gap: 14px; }
  ha-card.unavailable { opacity: .6; }
  .warning { color: var(--error-color, #db4437); }
  .header { display: flex; align-items: center; gap: 14px; }
  .orb {
    --glow: #9e9e9e;
    flex: none; width: 48px; height: 48px; border-radius: 50%; border: none; cursor: pointer;
    display: grid; place-items: center; color: var(--sc-muted);
    background: var(--sc-track); transition: box-shadow .3s, background .3s;
  }
  .orb.lit { background: radial-gradient(circle at 35% 30%, rgba(255,255,255,.75), var(--glow) 70%); color: #fff; box-shadow: 0 0 0 4px color-mix(in srgb, var(--glow) 25%, transparent), 0 0 22px var(--glow); }
  .orb.lit ha-icon { filter: drop-shadow(0 1px 1px rgba(0,0,0,.35)); }
  .title { flex: 1; min-width: 0; }
  .name { font-size: 1.15rem; font-weight: 500; color: var(--primary-text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .subtitle { font-size: .875rem; color: var(--sc-muted); margin-top: 2px; }
  .badge { display: flex; align-items: center; gap: 4px; font-size: .8rem; color: var(--sc-muted); padding: 4px 10px 4px 6px; border-radius: 999px; background: var(--sc-track); white-space: nowrap; }
  .badge ha-icon { --mdc-icon-size: 16px; }

  input[type=range] { -webkit-appearance: none; appearance: none; width: 100%; height: 28px; background: transparent; margin: 0; cursor: pointer; }
  input[type=range]:disabled { cursor: default; }
  input[type=range]::-webkit-slider-runnable-track { height: 8px; border-radius: 4px; background: linear-gradient(to right, var(--fill) 0 var(--p), var(--sc-track) var(--p) 100%); }
  input[type=range]::-moz-range-track { height: 8px; border-radius: 4px; background: var(--sc-track); }
  input[type=range]::-moz-range-progress { height: 8px; border-radius: 4px; background: var(--fill); }
  input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 20px; height: 20px; margin-top: -6px; border-radius: 50%; background: var(--card-background-color, #fff); border: 2px solid var(--thumb); box-shadow: 0 1px 3px rgba(0,0,0,.3); }
  input[type=range]::-moz-range-thumb { width: 16px; height: 16px; border-radius: 50%; background: var(--card-background-color, #fff); border: 2px solid var(--thumb); }
  .master input { --fill: var(--sc-accent); --thumb: var(--sc-accent); height: 32px; }
  .master input::-webkit-slider-runnable-track { height: 12px; border-radius: 6px; }
  .master input::-webkit-slider-thumb { margin-top: -4px; }

  .segmented { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; padding: 4px; border-radius: 12px; background: var(--sc-track); }
  .segmented button { display: flex; align-items: center; justify-content: center; gap: 6px; border: none; border-radius: 9px; padding: 8px; font: inherit; font-size: .9rem; cursor: pointer; background: transparent; color: var(--sc-muted); }
  .segmented button ha-icon { --mdc-icon-size: 18px; }
  .segmented button.active { background: var(--card-background-color, #fff); color: var(--primary-text-color); box-shadow: 0 1px 3px rgba(0,0,0,.15); font-weight: 500; }

  .section-title { display: flex; justify-content: space-between; align-items: baseline; font-size: .75rem; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--sc-muted); margin: 6px 0 -4px; }
  .section-title .meta { display: flex; gap: 12px; text-transform: none; letter-spacing: 0; font-weight: 400; font-variant-numeric: tabular-nums; }
  .chart { padding-top: 4px; }
  .chart svg { width: 100%; height: 96px; display: block; overflow: visible; }
  .chart .grid { stroke: var(--sc-line); stroke-width: 1; vector-effect: non-scaling-stroke; }
  .chart .now { stroke: var(--primary-text-color); stroke-width: 1.5; stroke-dasharray: 3 3; vector-effect: non-scaling-stroke; opacity: .6; }
  .axis { display: flex; justify-content: space-between; font-size: .7rem; color: var(--sc-muted); font-variant-numeric: tabular-nums; margin-top: 2px; }

  .channels { display: flex; flex-direction: column; gap: 2px; }
  .channel { display: grid; grid-template-columns: 12px 64px 1fr 44px; align-items: center; gap: 10px; }
  .channel input { --fill: var(--ch); --thumb: var(--ch-stroke); }
  .dot { width: 12px; height: 12px; border-radius: 50%; background: var(--ch); box-shadow: inset 0 0 0 1px var(--ch-stroke); }
  .label { font-size: .9rem; color: var(--primary-text-color); }
  .value { text-align: right; font-variant-numeric: tabular-nums; font-size: .9rem; color: var(--primary-text-color); }
  .value small { color: var(--sc-muted); margin-left: 1px; }

  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chip { display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px 7px 10px; border-radius: 999px; border: 1px solid var(--sc-line); background: transparent; color: var(--primary-text-color); font: inherit; font-size: .875rem; cursor: pointer; }
  .chip ha-icon { --mdc-icon-size: 18px; color: var(--sc-muted); }
  .chip.on { background: color-mix(in srgb, var(--sc-accent) 14%, transparent); border-color: color-mix(in srgb, var(--sc-accent) 50%, transparent); }
  .chip.on ha-icon { color: var(--sc-accent); }
  .mix { display: flex; align-items: center; gap: 10px; margin-top: 2px; font-size: .875rem; }
  .mix-swatch { width: 28px; height: 18px; border-radius: 6px; box-shadow: inset 0 0 0 1px var(--sc-line); background-image: none; }
  .mix-label { color: var(--sc-muted); }
  .mix-name { margin-left: auto; color: var(--primary-text-color); }
  .mix-name small { color: var(--sc-muted); font-variant-numeric: tabular-nums; margin-left: 4px; }
  .ifooter { display: flex; align-items: center; gap: 6px; font-size: .72rem; color: var(--sc-muted); font-variant-numeric: tabular-nums; }
  .ifooter ha-icon { --mdc-icon-size: 13px; }
  .chip.fav { padding-left: 8px; }
  .swatch { width: 16px; height: 16px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgba(0,0,0,.15); }
  .status { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: .8rem; color: var(--sc-muted); margin-top: -4px; }
  .status span { display: inline-flex; align-items: center; gap: 4px; }
  .status ha-icon { --mdc-icon-size: 16px; }

  .settings { display: flex; flex-direction: column; border: 1px solid var(--sc-line); border-radius: 12px; overflow: hidden; }
  details + details { border-top: 1px solid var(--sc-line); }
  summary { display: flex; align-items: center; gap: 10px; padding: 12px 14px; cursor: pointer; list-style: none; font-size: .95rem; color: var(--primary-text-color); }
  summary::-webkit-details-marker { display: none; }
  summary ha-icon { --mdc-icon-size: 20px; color: var(--sc-muted); }
  summary span { flex: 1; }
  summary .chev { transition: transform .2s; }
  details[open] summary .chev { transform: rotate(180deg); }
  .rows { padding: 0 14px 10px; display: flex; flex-direction: column; }
  .row { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 40px; }
  .row + .row { border-top: 1px dashed var(--sc-line); }
  .row-label { font-size: .875rem; color: var(--primary-text-color); }
  .row.sub .row-label { padding-left: 14px; color: var(--sc-muted); }
  .row-control .value { min-width: 44px; }
  .row-control { display: flex; align-items: center; gap: 8px; flex: 0 1 auto; justify-content: flex-end; }
  .row.number .row-control { flex: 1 1 50%; max-width: 60%; }
  input.mini { --fill: var(--sc-accent); --thumb: var(--sc-accent); height: 24px; }
  input.mini::-webkit-slider-runnable-track { height: 6px; border-radius: 3px; }
  input.mini::-webkit-slider-thumb { width: 16px; height: 16px; margin-top: -5px; }
  .numbox { display: inline-flex; align-items: center; gap: 4px; }
  .numbox small { color: var(--sc-muted); font-size: .8rem; min-width: 22px; }
  input[type=number], input[type=time] {
    font: inherit; font-size: .875rem; font-variant-numeric: tabular-nums; color: var(--primary-text-color);
    background: var(--sc-track); border: 1px solid transparent; border-radius: 8px; padding: 5px 8px;
  }
  input[type=number] { width: 64px; text-align: right; }
  input[type=time] { color-scheme: light dark; }
  input[type=number]:focus, input[type=time]:focus { outline: none; border-color: var(--sc-accent); }
  .toggle { width: 40px; height: 22px; border-radius: 11px; border: none; padding: 2px; cursor: pointer; background: var(--sc-track); transition: background .2s; flex: none; }
  .toggle span { display: block; width: 18px; height: 18px; border-radius: 50%; background: var(--card-background-color, #fff); box-shadow: 0 1px 2px rgba(0,0,0,.3); transition: transform .2s; }
  .toggle.on { background: var(--sc-accent); }
  .toggle.on span { transform: translateX(18px); }
  .action { display: inline-flex; align-items: center; gap: 4px; border: 1px solid var(--sc-line); background: transparent; color: var(--primary-text-color); border-radius: 999px; padding: 5px 12px 5px 8px; font: inherit; font-size: .85rem; cursor: pointer; }
  .action ha-icon { --mdc-icon-size: 18px; color: var(--sc-accent); }
  button:disabled { cursor: default; }
  button:focus-visible, input:focus-visible { outline: 2px solid var(--sc-accent); outline-offset: 2px; }
</style>`;

const MOON_PHASES = [[1.8, "m_new"], [5.5, "m_wax_c"], [9.2, "m_first"], [12.9, "m_wax_g"],
  [16.6, "m_full"], [20.3, "m_wan_g"], [24, "m_last"], [27.7, "m_wan_c"], [30, "m_new"]];

/** Compact status card: no settings, just what is going on. */
class DaytimeSC25InfoCard extends DaytimeSC25Card {
  static getStubConfig(hass) {
    return DaytimeSC25Card.getStubConfig(hass);
  }

  getCardSize() {
    return 4;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  _lang() {
    return ((this._hass && this._hass.language) || "en").split("-")[0];
  }

  _num(id) {
    const st = this._state(id);
    const v = st ? parseFloat(st.state) : NaN;
    return isNaN(v) ? null : v;
  }

  _nextEvent(attrs, nowMin) {
    const t = this._t;
    if (attrs.day_start == null || attrs.day_end == null) return null;
    const events = [
      [attrs.day_start, t.e_sunrise],
      [attrs.day_start + (attrs.sunrise_minutes || 0), t.e_full],
      [attrs.day_end - (attrs.sunset_minutes || 0), t.e_sunset],
      [attrs.day_end, t.e_night],
    ];
    if (attrs.midday_dimming) {
      const toMin = (id) => {
        const st = this._state(id);
        if (!st || !/^\d\d:\d\d/.test(st.state)) return null;
        const [h, m] = st.state.split(":").map(Number);
        return h * 60 + m;
      };
      const a = toMin(this._key("time", "midday_start"));
      const b = toMin(this._key("time", "midday_end"));
      if (a != null) events.push([a, t.e_midday]);
      if (b != null) events.push([b, t.e_midday_end]);
    }
    events.sort((x, y) => x[0] - y[0]);
    const upcoming = events.find(([m]) => m > nowMin);
    const [minute, label] = upcoming || events[0];
    const delta = upcoming ? minute - nowMin : minute + 1440 - nowMin;
    const rel = delta >= 60 ? `${Math.floor(delta / 60)} h ${delta % 60} min` : `${delta} min`;
    return { label, time: `${upcoming ? "" : t.tomorrow + " "}${fmtTime(minute)}`, rel: `${t.in} ${rel}` };
  }

  _levelsAt(curve, minute) {
    if (!curve.length) return [0, 0, 0, 0];
    let prev = curve[0];
    for (const row of curve) {
      if (row[0] >= minute) {
        const span = row[0] - prev[0];
        const f = span ? (minute - prev[0]) / span : 0;
        return [1, 2, 3, 4].map((i) => (prev[i] || 0) + ((row[i] || 0) - (prev[i] || 0)) * f);
      }
      prev = row;
    }
    return prev.slice(1, 5);
  }

  /** CSS gradient of the planned mixed colour and brightness over 24 h. */
  _dayStrip(curve, channelCount) {
    const stops = [];
    const keys = ["white", "blue", "red", "green"];
    for (let m = 0; m <= 1440; m += 10) {
      const lv = this._levelsAt(curve, m);
      const v = {};
      keys.forEach((k, i) => { if (i < channelCount) v[k] = lv[i]; });
      const mix = mixLight(v);
      const peak = Math.max(...keys.map((k) => v[k] || 0));
      const pos = ((m / 1440) * 100).toFixed(2);
      if (!mix || peak <= 0) stops.push(`transparent ${pos}%`);
      else {
        const alpha = (0.25 + 0.75 * (peak / 100)).toFixed(2);
        stops.push(`${mix.css.replace("rgb(", "rgba(").replace(")", `, ${alpha})`)} ${pos}%`);
      }
    }
    return `linear-gradient(to right, ${stops.join(", ")})`;
  }

  _chip(icon, text, sub, cls = "") {
    return `<span class="ichip ${cls}"><ha-icon icon="${icon}"></ha-icon><span>${text}${sub ? `<small>${sub}</small>` : ""}</span></span>`;
  }

  _render() {
    if (!this._hass || !this._config) return;
    const t = this._t;
    const lang = this._lang();
    const ids = this._resolve();
    const lamp = this._state(ids.lamp);
    const root = this.shadowRoot;
    if (!lamp) {
      root.innerHTML = `${STYLE}${INFO_STYLE}<ha-card><div class="warning">${t.missing}: ${this._esc(this._config.entity)}</div></ha-card>`;
      return;
    }
    const unavailable = lamp.state === "unavailable";
    const mode = this._state(ids.mode);
    const attrs = (mode && mode.attributes) || {};
    const isManual = mode && mode.state === "manual";
    const values = {};
    for (const ch of CHANNELS) if (this._state(ids[ch.key])) values[ch.key] = this._pct(this._state(ids[ch.key]));
    const channelCount = Object.keys(values).length || 4;
    const master = this._pct(lamp);
    const nowMix = mixLight(values, lang);
    const plan = Array.isArray(attrs.programmed_levels) ? attrs.programmed_levels : null;
    const planValues = plan ? Object.fromEntries(CHANNELS.slice(0, channelCount).map((c, i) => [c.key, plan[i]])) : null;
    const planMix = planValues ? mixLight(planValues, lang) : null;
    const planPeak = plan ? Math.round(Math.max(...plan.slice(0, channelCount))) : 0;
    const now = new Date();
    const nowMin = now.getHours() * 60 + now.getMinutes();
    const next = this._nextEvent(attrs, nowMin);
    const curve = Array.isArray(attrs.daycycle) ? attrs.daycycle : [];
    const name = this._config.name || lamp.attributes.friendly_name || "SC25";
    const temp = this._num(ids.temperature);

    let subtitle = unavailable ? t.unavailable : isManual ? t.manual : t.daycycle;
    if (isManual && attrs.manual_fallback_remaining != null) subtitle += ` · ${t.back_in} ${fmtDuration(attrs.manual_fallback_remaining)}`;

    // Plan only matters when it differs from what is shining now.
    const planDiffers = planMix && (!nowMix || planMix.hex !== nowMix.hex || Math.abs(planPeak - master) > 2);

    const chips = [];
    if (this._isOn("clouds")) {
      const passing = this._state(ids.cloud_passing);
      const nextCloud = this._state(ids.next_cloud);
      if (passing && passing.state === "on") {
        const rem = passing.attributes.remaining_seconds;
        chips.push(this._chip("mdi:weather-cloudy", t.cloud_now, rem != null ? fmtDuration(rem) : "", "active"));
      } else if (nextCloud && !["unknown", "unavailable"].includes(nextCloud.state)) {
        const d = new Date(nextCloud.state);
        chips.push(this._chip("mdi:weather-cloudy-clock", t.next_cloud, fmtTime(d.getHours() * 60 + d.getMinutes())));
      } else chips.push(this._chip("mdi:weather-cloudy", t.clouds, ""));
    }
    const moonDay = this._num(ids.moon_phase);
    if (moonDay != null) {
      const idx = MOON_PHASES.findIndex(([limit]) => moonDay < limit);
      const icons = ["moon-new", "moon-waxing-crescent", "moon-first-quarter", "moon-waxing-gibbous", "moon-full",
                     "moon-waning-gibbous", "moon-last-quarter", "moon-waning-crescent", "moon-new"];
      const on = this._isOn("moonlight");
      const lvl = this._num(ids.moon_level);
      chips.push(this._chip(`mdi:${icons[idx]}`, t[MOON_PHASES[idx][1]],
        on && lvl != null ? `${Math.round(lvl)} %` : "", on ? "" : "muted"));
    }
    if (this._isOn("acclimation")) {
      const day = this._num(ids.accl_day);
      const total = this._num(this._key("number", "acclimation_days"));
      const lvl = this._num(ids.accl_level);
      chips.push(this._chip("mdi:fishbowl-outline",
        day != null && total != null ? t.i_day_short.replace("{d}", Math.round(day)).replace("{n}", Math.round(total)) : t.i_accl,
        this._isOn("acclimation_pause") ? t.i_paused : lvl != null ? `${Math.round(lvl)} %` : ""));
    }

    const hints = [];
    if (attrs.expert_mode) hints.push(["mdi:chart-bell-curve", t.h_expert]);
    const fw = this._state(ids.firmware);
    if (fw && fw.state === "on") hints.push(["mdi:update", t.h_update.replace("{v}", () => this._esc(fw.attributes.latest_version || ""))]);



    const nowPos = ((nowMin / 1440) * 100).toFixed(2);
    const glow = nowMix && master ? nowMix.css : null;

    // Manual mode: the plan is paused. Paint the manual colour from now until
    // the automatic fallback; without one it holds, so fill to the end of the day.
    let manualSegs = "";
    let pausedLine = "";
    if (isManual) {
      const remaining = attrs.manual_fallback_remaining;
      const until = remaining != null ? nowMin + Math.ceil(remaining / 60) : null;
      const end = until != null ? until : 1440;
      const color = nowMix && master
        ? nowMix.css.replace("rgb(", "rgba(").replace(")", `, ${(0.35 + 0.65 * master / 100).toFixed(2)})`)
        : "rgba(255,255,255,.12)";
      const seg = (a, b) =>
        `<span class="strip-manual" style="left:${(a / 14.4).toFixed(2)}%;width:${((b - a) / 14.4).toFixed(2)}%;--mc:${color}"></span>`;
      manualSegs = end <= 1440 ? seg(nowMin, end) : seg(nowMin, 1440) + seg(0, end - 1440);
      pausedLine = until != null
        ? t.i_paused_until.replace("{t}", `${until >= 1440 ? t.tomorrow + " " : ""}${fmtTime(until)}`)
        : t.i_paused_open;
    }

    // Sunrise and sunset ramps, labelled above the band like the vendor app.
    let ramps = "";
    let rampBoxes = "";
    if (attrs.day_start != null && attrs.day_end != null) {
      const ramp = (cls, icon, a, b) => {
        const left = Math.min(Math.max(a, 0), 1440) / 14.4;
        const width = (Math.min(Math.max(b, a), 1440) - Math.min(Math.max(a, 0), 1440)) / 14.4;
        const center = left + width / 2;
        const anchor = center < 12 ? "start" : center > 88 ? "end" : "mid";
        const pos = anchor === "start" ? `left:${left.toFixed(2)}%` : anchor === "end"
          ? `right:${(100 - left - width).toFixed(2)}%` : `left:${center.toFixed(2)}%`;
        const box = `left:${left.toFixed(2)}%;width:${width.toFixed(2)}%`;
        return [
          `<span class="ramp-label ${cls} ${anchor}" style="${pos}"><ha-icon icon="${icon}"></ha-icon>${fmtTime(a)}–${fmtTime(b)}</span>
           <span class="ramp-mark ${cls}" style="${box}"></span>`,
          `<span class="strip-ramp ${cls}" style="${box}"></span>`,
        ];
      };
      const rise = ramp("rise", "mdi:weather-sunset-up", attrs.day_start, attrs.day_start + (attrs.sunrise_minutes || 0));
      const set = ramp("set", "mdi:weather-sunset-down", attrs.day_end - (attrs.sunset_minutes || 0), attrs.day_end);
      ramps = `<div class="ramps">${rise[0]}${set[0]}</div>`;
      rampBoxes = rise[1] + set[1];
    }

    root.innerHTML = `${STYLE}${INFO_STYLE}
      <ha-card class="info ${unavailable ? "unavailable" : ""}">
        <div class="ihead">
          <div class="ititle">
            <div class="name">${this._esc(name)}</div>
            <div class="subtitle">${subtitle}</div>
          </div>
          ${temp != null ? `<div class="itemp"><ha-icon icon="mdi:thermometer"></ha-icon>${temp.toLocaleString(lang, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} °C</div>` : ""}
        </div>

        <div class="hero">
          <div class="swatch-lg ${glow ? "lit" : ""}" style="${glow ? `--glow:${glow}` : ""}"></div>
          <div class="hero-text">
            <div class="hero-name">${nowMix && master ? nowMix.name : t.off}</div>
            <div class="hero-sub">${master ? `${master} %` : ""}${nowMix && master ? ` · <span class="hex">${nowMix.hex}</span>` : ""}</div>
            ${planDiffers ? `<div class="hero-plan"><span class="dot-mix" style="background:${planMix ? planMix.css : "transparent"}"></span>${t.i_plan}: ${planMix ? planMix.name : t.off}${planPeak ? ` · ${planPeak} %` : ""}</div>` : ""}
          </div>
        </div>

        ${curve.length >= 2 ? `
        <div class="strip-wrap">
          ${ramps}
          <div class="strip ${isManual ? "paused" : ""}">
            <span class="strip-plan" style="background-image:${this._dayStrip(curve, channelCount)}"></span>
            ${rampBoxes}
            ${manualSegs}
            <span class="strip-now" style="left:${nowPos}%"></span>
          </div>
          <div class="strip-axis"><span>0</span><span>6</span><span>12</span><span>18</span><span>24</span></div>
          ${isManual ? `<div class="next"><ha-icon icon="mdi:pause-circle-outline"></ha-icon><span>${pausedLine}</span></div>` : ""}
          ${next && !isManual ? `<div class="next"><ha-icon icon="mdi:clock-outline"></ha-icon><span>${next.label} <b>${next.time}</b></span><span class="rel">${next.rel}</span></div>` : ""}
        </div>` : ""}

        ${chips.length ? `<div class="ichips">${chips.join("")}</div>` : ""}
        ${hints.map(([icon, text]) => `<div class="hint"><ha-icon icon="${icon}"></ha-icon><span>${text}</span></div>`).join("")}
      </ha-card>`;
  }
}

const INFO_STYLE = `<style>
  ha-card.info { gap: 16px; padding: 16px 16px 14px; --sc-night: #0d1420; --rise: #f6b73c; --set: #f07f3c; }
  .ihead { display: flex; align-items: flex-start; gap: 12px; }
  .ititle { flex: 1; min-width: 0; }
  .itemp { display: inline-flex; align-items: center; gap: 2px; font-size: .875rem; color: var(--sc-muted); font-variant-numeric: tabular-nums; white-space: nowrap; padding-top: 2px; }
  .itemp ha-icon { --mdc-icon-size: 16px; }

  .hero { display: flex; align-items: center; gap: 14px; }
  /* A small "look into the tank": light falls in from the top onto dark water. */
  .swatch-lg {
    --glow: transparent;
    flex: none; width: 56px; height: 56px; border-radius: 16px;
    background: var(--sc-night); box-shadow: inset 0 0 0 1px rgba(255,255,255,.08);
  }
  .swatch-lg.lit {
    background:
      radial-gradient(90% 70% at 50% 0%, color-mix(in srgb, var(--glow) 85%, white), transparent 75%),
      linear-gradient(to bottom, var(--glow), color-mix(in srgb, var(--glow) 30%, var(--sc-night)));
    box-shadow: 0 8px 24px -10px var(--glow), inset 0 0 0 1px rgba(255,255,255,.12);
  }
  .hero-text { min-width: 0; }
  .hero-name { font-size: 1.35rem; font-weight: 500; line-height: 1.2; color: var(--primary-text-color); }
  .hero-sub { font-size: .875rem; color: var(--sc-muted); margin-top: 2px; font-variant-numeric: tabular-nums; }
  .hero-sub .hex { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .8rem; }
  .hero-plan { display: flex; align-items: center; gap: 6px; font-size: .8rem; color: var(--sc-muted); margin-top: 6px; }
  .dot-mix { width: 10px; height: 10px; border-radius: 50%; box-shadow: inset 0 0 0 1px var(--sc-line); flex: none; }

  .strip-wrap { display: flex; flex-direction: column; gap: 4px; }
  .strip {
    position: relative; height: 22px; border-radius: 11px;
    background-color: var(--sc-night); box-shadow: inset 0 0 0 1px rgba(255,255,255,.08);
  }
  .strip-plan { position: absolute; inset: 0; border-radius: inherit; transition: opacity .3s, filter .3s; }
  .strip.paused .strip-plan { opacity: .35; filter: saturate(.4); }
  /* Raised slightly above the band so even a short manual period stands out. */
  .strip-manual {
    position: absolute; top: -3px; bottom: -3px; min-width: 10px; background: var(--mc);
    border-radius: 5px; box-shadow: 0 0 0 1.5px var(--sc-night), 0 0 12px -2px var(--mc);
  }
  .strip-now {
    position: absolute; top: -4px; bottom: -4px; width: 3px; margin-left: -1.5px; border-radius: 2px;
    background: #fff; box-shadow: 0 0 0 1.5px var(--sc-night), 0 1px 4px rgba(0,0,0,.4);
  }
  /* Sunrise/sunset: label with time range, bracket down onto the band. */
  .ramps { position: relative; height: 28px; margin-bottom: -6px; }
  .ramp-label {
    position: absolute; top: 0; display: inline-flex; align-items: center; gap: 4px; white-space: nowrap;
    font-size: .8rem; color: var(--primary-text-color); font-variant-numeric: tabular-nums;
  }
  .ramp-label.mid { transform: translateX(-50%); }
  .ramp-label ha-icon { --mdc-icon-size: 18px; }
  .ramp-label.rise ha-icon { color: var(--rise); }
  .ramp-label.set ha-icon { color: var(--set); }
  /* Short stem from the label down to the outlined ramp on the band. */
  .ramp-mark { position: absolute; bottom: 0; height: 6px; display: flex; justify-content: center; }
  .ramp-mark::after { content: ""; width: 2px; border-radius: 1px; background: var(--rise); }
  .ramp-mark.set::after { background: var(--set); }
  .strip-ramp {
    position: absolute; top: -2px; bottom: -2px; min-width: 6px; margin-left: -1px; padding-right: 2px;
    border-radius: 6px; box-shadow: inset 0 0 0 2px var(--rise), 0 0 10px -3px var(--rise);
  }
  .strip-ramp.set { box-shadow: inset 0 0 0 2px var(--set), 0 0 10px -3px var(--set); }
  .strip-axis { display: flex; justify-content: space-between; font-size: .7rem; color: var(--sc-muted); font-variant-numeric: tabular-nums; padding: 0 2px; }
  .next { display: flex; align-items: center; gap: 6px; font-size: .875rem; color: var(--primary-text-color); margin-top: 4px; }
  .next ha-icon { --mdc-icon-size: 16px; color: var(--sc-muted); }
  .next b { font-weight: 500; font-variant-numeric: tabular-nums; }
  .next .rel { margin-left: auto; color: var(--sc-muted); font-size: .8rem; white-space: nowrap; }

  .ichips { display: flex; flex-wrap: wrap; gap: 6px; }
  .ichip { display: inline-flex; align-items: center; gap: 6px; padding: 5px 10px 5px 8px; border-radius: 999px; background: var(--sc-track); font-size: .8rem; color: var(--primary-text-color); }
  .ichip ha-icon { --mdc-icon-size: 16px; color: var(--sc-muted); }
  .ichip small { margin-left: 5px; color: var(--sc-muted); font-variant-numeric: tabular-nums; }
  .ichip.active { background: color-mix(in srgb, var(--sc-accent) 16%, transparent); }
  .ichip.active ha-icon { color: var(--sc-accent); }
  .ichip.muted { color: var(--sc-muted); }

  .hint { display: flex; gap: 8px; align-items: flex-start; font-size: .8rem; padding: 8px 10px; border-radius: 10px; background: var(--sc-track); color: var(--primary-text-color); }
  .hint ha-icon { --mdc-icon-size: 16px; color: var(--sc-accent); flex: none; margin-top: 1px; }
</style>`;

// Registration. The HA frontend installs a scoped custom-element registry
// polyfill that replaces window.customElements during boot. When this file
// comes from the browser cache it can run before that and register in the
// old registry, so HA never sees the card ("Configuration error"). Register
// again in whatever registry is current until boot has settled.
const CARDS = [
  [ "daytime-sc25-card", DaytimeSC25Card, "daytime SC25", "Aquarium lamp control for the daytime Smart Control SC25" ],
  [ "daytime-sc25-info-card", DaytimeSC25InfoCard, "daytime SC25 Info", "Status of the daytime SC25: colour, schedule, clouds, moon, acclimation" ],
];
const registeredOnce = new Set();
const register = () => {
  for (const [tag, cls] of CARDS) {
    if (customElements.get(tag)) continue;
    try {
      // A constructor can only be defined once natively; later registries
      // need a fresh subclass.
      customElements.define(tag, registeredOnce.has(tag) ? class extends cls {} : cls);
      registeredOnce.add(tag);
    } catch (err) {
      console.warn(`${tag}: registration failed`, err);
    }
  }
};
register();
const started = Date.now();
const watch = setInterval(() => {
  register();
  if (Date.now() - started > 60000) clearInterval(watch);
}, 250);

window.customCards = window.customCards || [];
for (const [type, , name, description] of CARDS) {
  if (!window.customCards.some((c) => c.type === type)) {
    window.customCards.push({ type, name, description, preview: true });
  }
}
console.info(`%c DAYTIME-SC25-CARD %c ${CARD_VERSION} `, "background:#e94e0e;color:#fff", "");
