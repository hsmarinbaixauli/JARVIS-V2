/**
 * Rich tool-result card renderers. Step 8.
 *
 * Each function returns a DOM element to insert into the chat,
 * or null if the data doesn't warrant a card (fall back to plain text).
 *
 * All DOM is built with createElement — no innerHTML with untrusted data.
 */

// ─── Helpers ───────────────────────────────────────────────────────────────

function _esc(s) {
  const d = document.createElement("div");
  d.textContent = String(s);
  return d.textContent; // we only use this for textContent assignments
}

/** Set element textContent safely (no XSS). */
function _setText(el, s) {
  el.textContent = String(s == null ? "" : s);
  return el;
}

/** Create an element with optional className and textContent. */
function _el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = String(text);
  return e;
}

/**
 * Parse a sender field like "Name <email>" → just the display name,
 * or the full address if there is no display name.
 */
function _senderName(sender) {
  if (!sender) return "Unknown";
  const m = String(sender).match(/^(.+?)\s*<[^>]+>\s*$/);
  if (m && m[1].trim()) return m[1].trim();
  // Strip angle-bracket-only form
  const addr = String(sender).replace(/^<|>$/g, "").trim();
  return addr || sender;
}

const _URGENT_WORDS = [
  "urgent", "urgente", "asap", "importante", "crítico",
  "vence", "plazo", "deadline", "hoy", "ahora",
];

function _isUrgent(subject) {
  const s = String(subject).toLowerCase();
  return _URGENT_WORDS.some(w => s.includes(w));
}

/**
 * Format an RFC2822 date string as relative time in Spanish.
 * Falls back to a locale date string on parse failure.
 */
function _relativeDate(dateStr) {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    if (isNaN(d)) return dateStr;
    const now = Date.now();
    const diffMs = now - d.getTime();
    const diffMin = Math.round(diffMs / 60000);
    const diffH = Math.round(diffMs / 3600000);
    const diffD = Math.round(diffMs / 86400000);

    if (diffMin < 1)  return "ahora";
    if (diffMin < 60) return `hace ${diffMin}min`;
    if (diffH < 24)   return `hace ${diffH}h`;
    if (diffD === 1)  return "ayer";
    if (diffD < 7)    return `hace ${diffD} días`;
    return d.toLocaleDateString("es-ES", { day: "numeric", month: "short" });
  } catch {
    return dateStr;
  }
}

/**
 * Format a Google Calendar event time range.
 * Returns "HH:MM – HH:MM" for timed events or "Todo el día" for all-day.
 */
function _eventTime(event) {
  const start = event.start || {};
  const end   = event.end   || {};

  if (start.date) {
    // All-day event
    return "Todo el día";
  }

  const fmt = (iso) => {
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit", hour12: false });
    } catch {
      return iso;
    }
  };
  return `${fmt(start.dateTime)} – ${fmt(end.dateTime)}`;
}

/** Get YYYY-MM-DD date key for grouping calendar events by day. */
function _eventDateKey(event) {
  const start = (event.start || {});
  if (start.date) return start.date;
  if (start.dateTime) {
    try { return new Date(start.dateTime).toISOString().slice(0, 10); } catch { /**/ }
  }
  return "unknown";
}

/** Format a date key (YYYY-MM-DD) to a human-readable day label in Spanish. */
function _dayLabel(key) {
  if (key === "unknown") return "Fecha desconocida";
  try {
    const d = new Date(key + "T00:00:00");
    const today    = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(today.getDate() + 1);

    const sameDay = (a, b) =>
      a.getFullYear() === b.getFullYear() &&
      a.getMonth() === b.getMonth() &&
      a.getDate() === b.getDate();

    if (sameDay(d, today))    return "Hoy";
    if (sameDay(d, tomorrow)) return "Mañana";
    return d.toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" });
  } catch {
    return key;
  }
}

/** Create a simple SVG icon by path data. */
function _svgIcon(pathD, size = 14) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("width", String(size));
  svg.setAttribute("height", String(size));
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", pathD);
  svg.appendChild(path);
  return svg;
}

// Mail icon path
const _MAIL_PATH =
  "M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z M22 6l-10 7L2 6";

// Calendar icon path
const _CAL_PATH =
  "M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z";

// ─── Email card ─────────────────────────────────────────────────────────────

/**
 * Render a card for get_unread_emails results.
 * @param {Array} emails  Array of email dicts from src/gmail/messages.py
 * @returns {HTMLElement|null}
 */
export function renderEmailCard(emails) {
  if (!Array.isArray(emails) || emails.length === 0) return null;

  const card = _el("div", "card");

  // Header
  const header = _el("div", "card-header");
  header.appendChild(_svgIcon(_MAIL_PATH));
  _setText(_el("span"), "Correos no leídos"); // label created below
  const labelSpan = _el("span");
  _setText(labelSpan, "Correos no leídos");
  header.appendChild(labelSpan);
  const countBadge = _el("span", "card-header-count");
  _setText(countBadge, String(emails.length));
  header.appendChild(countBadge);
  card.appendChild(header);

  // Rows
  for (const email of emails) {
    const row = _el("div", "card-row");

    // Top line: sender + meta (date) + optional badge
    const top = _el("div", "card-row-top");

    const sender = _el("span", "card-row-sender");
    _setText(sender, _senderName(email.sender));
    top.appendChild(sender);

    if (_isUrgent(email.subject)) {
      const badge = _el("span", "badge urgent");
      _setText(badge, "URGENTE");
      top.appendChild(badge);
    }

    const meta = _el("span", "card-row-meta");
    _setText(meta, _relativeDate(email.date));
    top.appendChild(meta);

    row.appendChild(top);

    // Subject line
    const subject = _el("div", "card-row-subject");
    _setText(subject, email.subject || "(sin asunto)");
    row.appendChild(subject);

    // Snippet
    if (email.snippet) {
      const snippet = _el("div", "card-row-snippet");
      _setText(snippet, email.snippet);
      row.appendChild(snippet);
    }

    card.appendChild(row);
  }

  return card;
}

// ─── Calendar card ──────────────────────────────────────────────────────────

/**
 * Render a card for get_today_events / get_upcoming_events results.
 * Groups events by day when the list spans multiple dates.
 * @param {Array} events  Array of Google Calendar event objects
 * @returns {HTMLElement|null}
 */
export function renderCalendarCard(events) {
  if (!Array.isArray(events) || events.length === 0) return null;

  const card = _el("div", "card");

  // Header
  const header = _el("div", "card-header");
  header.appendChild(_svgIcon(_CAL_PATH));
  const labelSpan = _el("span");
  _setText(labelSpan, "Eventos");
  header.appendChild(labelSpan);
  const countBadge = _el("span", "card-header-count");
  _setText(countBadge, String(events.length));
  header.appendChild(countBadge);
  card.appendChild(header);

  // Group by day
  const groups = new Map(); // dateKey → [event, ...]
  for (const ev of events) {
    const key = _eventDateKey(ev);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(ev);
  }

  const multiDay = groups.size > 1;

  for (const [dateKey, dayEvents] of groups) {
    if (multiDay) {
      const dayLabel = _el("div", "card-day-label");
      _setText(dayLabel, _dayLabel(dateKey));
      card.appendChild(dayLabel);
    }

    for (const ev of dayEvents) {
      const row = _el("div", "card-row");

      const top = _el("div", "card-row-top");

      const timeEl = _el("span", "card-event-time");
      const timeStr = _eventTime(ev);
      _setText(timeEl, timeStr);
      top.appendChild(timeEl);

      if (timeStr === "Todo el día") {
        const badge = _el("span", "badge allday");
        _setText(badge, "Todo el día");
        // Replace the text node with the badge style
        timeEl.textContent = "";
        timeEl.appendChild(badge);
      }

      const title = _el("span", "card-event-title");
      _setText(title, ev.summary || "(sin título)");
      top.appendChild(title);

      row.appendChild(top);

      if (ev.location) {
        const loc = _el("div", "card-event-location");
        _setText(loc, ev.location);
        row.appendChild(loc);
      }

      card.appendChild(row);
    }
  }

  return card;
}

// ─── ERP cards ─────────────────────────────────────────────────────────────

// Package/box icon (Feather "package" outer hexagon)
const _ERP_PATH =
  "M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z";

function _erpBadgeClass(estado) {
  if (!estado) return "erp-neutral";
  const s = estado.toLowerCase();
  if (s.includes("cancel"))                                              return "erp-cancelled";
  if (s.includes("serv") || s.includes("entregad") || s.includes("completad")) return "erp-done";
  if (s.includes("proceso") || s.includes("curso") || s.includes("tramit") || s.includes("fabric")) return "erp-progress";
  if (s.includes("pendiente"))                                           return "erp-pending";
  return "erp-neutral";
}

/**
 * Render a card for erp_get_order_status results.
 * @param {{ found: boolean, order_id: string, rows: Array<Object> }} data
 */
export function renderErpOrderCard(data) {
  if (!data || typeof data !== "object") return null;

  const card = _el("div", "card");

  // Header
  const header = _el("div", "card-header");
  header.appendChild(_svgIcon(_ERP_PATH));
  const label = _el("span");
  _setText(label, "Pedido ERP");
  header.appendChild(label);
  if (data.order_id) {
    const idBadge = _el("span", "card-header-count");
    _setText(idBadge, "#" + data.order_id);
    header.appendChild(idBadge);
  }
  card.appendChild(header);

  // Not-found state
  if (!data.found || !Array.isArray(data.rows) || data.rows.length === 0) {
    const row = _el("div", "card-row");
    const msg = _el("span", "card-row-snippet");
    _setText(msg, "Pedido" + (data.order_id ? " #" + data.order_id : "") + " no encontrado");
    row.appendChild(msg);
    card.appendChild(row);
    return card;
  }

  for (const order of data.rows) {
    const row = _el("div", "card-row");

    // Top line: order number + status badge + date
    const top = _el("div", "card-row-top");

    const numEl = _el("span", "card-erp-num");
    _setText(numEl, order["Pedido"] || data.order_id || "—");
    top.appendChild(numEl);

    const estado = order["Estado Pedido"] || "";
    if (estado) {
      const badge = _el("span", "badge " + _erpBadgeClass(estado));
      _setText(badge, estado);
      top.appendChild(badge);
    }

    const fecha = order["Fecha pedido"] || "";
    if (fecha) {
      const meta = _el("span", "card-row-meta");
      _setText(meta, fecha);
      top.appendChild(meta);
    }

    row.appendChild(top);

    // Customer name
    const nombre = order["Nombre"] || "";
    if (nombre) {
      const nameEl = _el("div", "card-row-subject");
      _setText(nameEl, nombre);
      row.appendChild(nameEl);
    }

    // Detail: amount · last update
    const importe = order["B.Imponible"] || "";
    const avance  = order["Ult. avance"] || "";
    if (importe || avance) {
      const detail = _el("div", "card-erp-detail");
      if (importe) {
        const amt = _el("span", "card-erp-amount");
        _setText(amt, importe + " €");
        detail.appendChild(amt);
      }
      if (avance) {
        const adv = _el("span");
        _setText(adv, avance);
        detail.appendChild(adv);
      }
      row.appendChild(detail);
    }

    card.appendChild(row);
  }

  return card;
}

/**
 * Render a card for erp_search_by_customer results.
 * @param {Array<Object>} data  Array of order rows
 */
export function renderErpSearchCard(data) {
  if (!Array.isArray(data) || data.length === 0) return null;

  const card = _el("div", "card");

  // Header
  const header = _el("div", "card-header");
  header.appendChild(_svgIcon(_ERP_PATH));
  const label = _el("span");
  _setText(label, "Resultados ERP");
  header.appendChild(label);
  const countBadge = _el("span", "card-header-count");
  _setText(countBadge, String(data.length));
  header.appendChild(countBadge);
  card.appendChild(header);

  for (const order of data) {
    const row = _el("div", "card-row");

    // Top: order number + status badge + customer name
    const top = _el("div", "card-row-top");

    const numEl = _el("span", "card-erp-num");
    _setText(numEl, order["Pedido"] || "—");
    top.appendChild(numEl);

    const estado = order["Estado Pedido"] || "";
    if (estado) {
      const badge = _el("span", "badge " + _erpBadgeClass(estado));
      _setText(badge, estado);
      top.appendChild(badge);
    }

    const nombre = order["Nombre"] || "";
    if (nombre) {
      const nameEl = _el("span", "card-erp-customer");
      _setText(nameEl, nombre);
      top.appendChild(nameEl);
    }

    row.appendChild(top);

    // Detail: date + amount
    const fecha   = order["Fecha pedido"] || "";
    const importe = order["B.Imponible"]  || "";
    if (fecha || importe) {
      const detail = _el("div", "card-erp-detail");
      if (fecha) {
        const f = _el("span");
        _setText(f, fecha);
        detail.appendChild(f);
      }
      if (importe) {
        const amt = _el("span", "card-erp-amount");
        _setText(amt, importe + " €");
        detail.appendChild(amt);
      }
      row.appendChild(detail);
    }

    card.appendChild(row);
  }

  return card;
}
