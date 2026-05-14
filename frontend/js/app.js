/**
 * Jarvis V2 — application entry point.
 *
 * Responsibilities:
 *   - Bootstrap sidebar and chat panel
 *   - Manage current conversation state
 *   - Drive SSE streaming lifecycle
 *   - Keyboard shortcuts
 *   - Toast notification system
 */

import {
  listConversations, getMessages, deleteConversation, streamChat,
} from "./api.js";

import {
  initSidebar, replaceSidebarList, prependConversation,
  removeSidebarItem, setSidebarActive,
} from "./sidebar.js";

import {
  initChat, showEmptyState, clearMessages, loadHistory,
  appendUserMsg, beginStream, appendErrorMsg, setInputEnabled,
} from "./chat.js";

// ─── State ─────────────────────────────────────────────────────────────────

let currentId   = null;   // active conversation_id (null = new)
let streaming   = false;  // guard against concurrent sends
let activeSource = null;  // live EventSource (so we can abort)

// ─── Toast ─────────────────────────────────────────────────────────────────

function _ensureToastContainer() {
  let el = document.getElementById("toast-container");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast-container";
    document.body.appendChild(el);
  }
  return el;
}

export function showToast(message, type = "error") {
  const container = _ensureToastContainer();
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("fade-out");
    toast.addEventListener("transitionend", () => toast.remove(), { once: true });
  }, 3000);
}

// ─── Bootstrap ─────────────────────────────────────────────────────────────

const sidebarEl = document.getElementById("sidebar");
const panelEl   = document.getElementById("chat-panel");
const titleEl   = document.getElementById("chat-title");

initSidebar(sidebarEl, {
  onNew:    () => _openNewChat(),
  onSelect: id => _selectConversation(id),
  onDelete: id => _deleteConversation(id),
});

initChat(panelEl, text => _sendMessage(text));

// Keyboard shortcuts
document.addEventListener("keydown", e => {
  const inputField = document.getElementById("input-field");
  const inputFocused = document.activeElement === inputField;

  // Press "/" anywhere (no modifier, input not focused) → focus input
  if (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey && !e.shiftKey && !inputFocused) {
    e.preventDefault();
    inputField.focus();
    return;
  }

  // Escape when input is focused → blur
  if (e.key === "Escape" && inputFocused) {
    inputField.blur();
    return;
  }

  // Legacy Ctrl+/ → focus input
  if ((e.ctrlKey || e.metaKey) && e.key === "/") {
    e.preventDefault();
    inputField.focus();
  }
});

// Load initial conversation list
_refreshSidebar(null);

// Initialise Outlook connect button / status indicator
_initOutlookConnect();

// ─── Actions ───────────────────────────────────────────────────────────────

function _openNewChat() {
  if (streaming) { activeSource?.close(); streaming = false; }
  currentId = null;
  titleEl.textContent = "Nueva conversación";
  clearMessages();
  showEmptyState();
  setSidebarActive(null);
  setInputEnabled(true);
}

async function _selectConversation(id) {
  if (streaming) { activeSource?.close(); streaming = false; }
  currentId = id;
  setSidebarActive(id);
  setInputEnabled(false);

  try {
    const msgs = await getMessages(id);
    // Title from first user message
    const firstUser = msgs.find(m => m.role === "user");
    titleEl.textContent = firstUser ? _truncate(firstUser.content, 60) : "Conversación";
    loadHistory(msgs);
  } catch (err) {
    appendErrorMsg("Error al cargar la conversación: " + err.message);
    showToast("Error al cargar la conversación: " + err.message, "error");
  } finally {
    setInputEnabled(true);
  }
}

async function _deleteConversation(id) {
  try {
    await deleteConversation(id);
  } catch (err) {
    console.error("[app] delete failed", err);
    showToast("Error al eliminar la conversación.", "error");
  }
  removeSidebarItem(id);
  if (currentId === id) _openNewChat();
}

async function _sendMessage(text) {
  if (streaming) return;
  streaming = true;
  setInputEnabled(false);

  appendUserMsg(text);
  const ctrl = beginStream();

  activeSource = streamChat(text, currentId, {
    onTextDelta:     ({ delta }) => ctrl.appendText(delta),
    onToolStart:     ({ id, name }) => ctrl.addTool(id, name),
    onToolExecuting: () => {},
    onToolResult: ({ id, name, is_error, card_data }) => {
      ctrl.finishTool(id, is_error);
      if (!is_error && card_data) ctrl.appendCard(name, card_data);
    },

    onError: ({ message }) => {
      ctrl.finalise();
      const errText = message || "Error inesperado.";
      appendErrorMsg(errText);
      showToast(errText, "error");
      _finishStream(null);
    },

    onDone: ({ conversation_id }) => {
      ctrl.finalise();
      _finishStream(conversation_id);
    },
  });
}

async function _finishStream(newId) {
  streaming = false;
  activeSource = null;
  setInputEnabled(true);

  if (!newId) return;

  // First message in a new conversation — add it to sidebar
  const isNew = !currentId;
  currentId = newId;
  titleEl.textContent = document.getElementById("input-field").value.trim()
    || titleEl.textContent;

  if (isNew) {
    // Fetch the conversation record so we have the title
    try {
      const convs = await listConversations();
      const conv = convs.find(c => c.id === newId);
      if (conv) {
        prependConversation(conv);
        titleEl.textContent = _truncate(conv.title || "Conversación", 60);
      }
    } catch (_) {}
    setSidebarActive(newId);
  }
}

async function _refreshSidebar(activeId) {
  try {
    const convs = await listConversations();
    replaceSidebarList(convs, activeId);
  } catch (err) {
    console.error("[app] failed to load conversations", err);
    showToast("No se pudieron cargar las conversaciones.", "error");
  }
}

// ─── Utilities ─────────────────────────────────────────────────────────────

function _truncate(str, max) {
  return str.length <= max ? str : str.slice(0, max).trimEnd() + "…";
}

// ─── Outlook Connect ───────────────────────────────────────────────────────

async function _initOutlookConnect() {
  const headerEl = document.getElementById("chat-header");
  if (!headerEl) return;

  try {
    const res = await fetch("/api/outlook/auth-status");
    if (!res.ok) return;
    const { authenticated } = await res.json();
    if (authenticated) {
      _showOutlookConnected(headerEl);
    } else {
      _showOutlookConnectBtn(headerEl);
    }
  } catch (_) {
    // Non-fatal: if the request fails, no Outlook UI is shown.
  }
}

function _showOutlookConnected(headerEl) {
  const indicator = document.createElement("div");
  indicator.className = "outlook-status connected";
  indicator.setAttribute("title", "Microsoft 365 conectado");
  const icon = document.createElement("span");
  icon.textContent = "✓";
  const label = document.createElement("span");
  label.textContent = "Outlook";
  indicator.appendChild(icon);
  indicator.appendChild(label);
  headerEl.appendChild(indicator);
}

function _showOutlookConnectBtn(headerEl) {
  const btn = document.createElement("button");
  btn.className = "outlook-connect-btn";
  btn.setAttribute("title", "Conectar Microsoft 365");
  const icon = document.createElement("span");
  icon.textContent = "⊞";
  const label = document.createElement("span");
  label.textContent = "Conectar Outlook";
  btn.appendChild(icon);
  btn.appendChild(label);
  headerEl.appendChild(btn);

  btn.addEventListener("click", () => _startOutlookAuth(btn, headerEl));
}

async function _startOutlookAuth(btn, headerEl) {
  btn.disabled = true;
  const labelSpan = btn.querySelector("span:last-child");
  if (labelSpan) labelSpan.textContent = "Conectando...";

  try {
    const res = await fetch("/api/outlook/authenticate", { method: "POST" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showToast(err.detail || "No se pudo iniciar la autenticación de Outlook.", "error");
      btn.disabled = false;
      if (labelSpan) labelSpan.textContent = "Conectar Outlook";
      return;
    }
    const flow = await res.json();
    const modal = _buildOutlookModal(flow);
    document.body.appendChild(modal.backdrop);

    let pollInterval = null;
    let countdownInterval = null;
    const expiresMs = (flow.expires_in || 900) * 1000;
    const expiresAt = Date.now() + expiresMs;

    // Countdown timer
    countdownInterval = setInterval(() => {
      const remaining = Math.max(0, expiresAt - Date.now());
      const totalSecs = Math.floor(remaining / 1000);
      const mins = String(Math.floor(totalSecs / 60)).padStart(2, "0");
      const secs = String(totalSecs % 60).padStart(2, "0");
      if (modal.countdownEl) modal.countdownEl.textContent = `Caduca en: ${mins}:${secs}`;
      if (remaining === 0) {
        clearInterval(countdownInterval);
        clearInterval(pollInterval);
        _removeModal(modal.backdrop);
        showToast("Tiempo de autenticación agotado. Inténtalo de nuevo.", "error");
        btn.disabled = false;
        if (labelSpan) labelSpan.textContent = "Conectar Outlook";
      }
    }, 1000);

    // Poll auth status every 2500ms
    pollInterval = setInterval(async () => {
      try {
        const statusRes = await fetch("/api/outlook/auth-status");
        if (!statusRes.ok) return;
        const { authenticated } = await statusRes.json();
        if (authenticated) {
          clearInterval(pollInterval);
          clearInterval(countdownInterval);
          _removeModal(modal.backdrop);
          // Swap button for connected indicator
          btn.remove();
          _showOutlookConnected(headerEl);
          showToast("Outlook conectado correctamente.", "success");
        }
      } catch (_) {}
    }, 2500);

    // Timeout safeguard
    setTimeout(() => {
      clearInterval(pollInterval);
      clearInterval(countdownInterval);
      _removeModal(modal.backdrop);
      if (!document.querySelector(".outlook-status.connected")) {
        btn.disabled = false;
        if (labelSpan) labelSpan.textContent = "Conectar Outlook";
        showToast("Tiempo de autenticación agotado. Inténtalo de nuevo.", "error");
      }
    }, expiresMs);

  } catch (err) {
    showToast("Error al conectar Outlook: " + err.message, "error");
    btn.disabled = false;
    if (labelSpan) labelSpan.textContent = "Conectar Outlook";
  }
}

function _removeModal(backdrop) {
  if (backdrop && backdrop.parentNode) backdrop.parentNode.removeChild(backdrop);
}

/**
 * Build and return the device-code modal DOM structure.
 * All user-facing strings use textContent / href attributes (no innerHTML with external data).
 */
function _buildOutlookModal(flow) {
  // Backdrop
  const backdrop = document.createElement("div");
  backdrop.className = "outlook-modal-backdrop";

  // Modal box
  const modal = document.createElement("div");
  modal.className = "outlook-modal";
  backdrop.appendChild(modal);

  // Header
  const header = document.createElement("div");
  header.className = "outlook-modal-header";

  const title = document.createElement("span");
  title.textContent = "Conectar Microsoft Outlook";

  const closeBtn = document.createElement("button");
  closeBtn.className = "outlook-modal-close";
  closeBtn.setAttribute("title", "Cerrar");
  closeBtn.setAttribute("aria-label", "Cerrar modal");
  closeBtn.textContent = "×";
  // Closing the modal does NOT stop polling — user may have already authed in browser.
  closeBtn.addEventListener("click", () => _removeModal(backdrop));

  header.appendChild(title);
  header.appendChild(closeBtn);
  modal.appendChild(header);

  // Body
  const body = document.createElement("div");
  body.className = "outlook-modal-body";
  modal.appendChild(body);

  // URL section
  const urlLabel = document.createElement("div");
  urlLabel.className = "outlook-modal-label";
  urlLabel.textContent = "Abre el enlace en tu navegador:";
  body.appendChild(urlLabel);

  const urlLink = document.createElement("a");
  urlLink.className = "outlook-modal-link";
  urlLink.href = flow.verification_uri;
  urlLink.target = "_blank";
  urlLink.rel = "noopener noreferrer";
  urlLink.textContent = flow.verification_uri;
  body.appendChild(urlLink);

  // Code section
  const codeLabel = document.createElement("div");
  codeLabel.className = "outlook-modal-label";
  codeLabel.textContent = "E introduce el código:";
  body.appendChild(codeLabel);

  const codeRow = document.createElement("div");
  codeRow.className = "outlook-modal-code-row";

  const codeBox = document.createElement("div");
  codeBox.className = "outlook-modal-code";
  codeBox.textContent = flow.user_code;

  const copyBtn = document.createElement("button");
  copyBtn.className = "outlook-modal-copy";
  copyBtn.setAttribute("title", "Copiar código");
  copyBtn.setAttribute("aria-label", "Copiar código al portapapeles");
  copyBtn.textContent = "Copiar";
  copyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(flow.user_code).then(() => {
      copyBtn.textContent = "Copiado";
      copyBtn.classList.add("copied");
      setTimeout(() => {
        copyBtn.textContent = "Copiar";
        copyBtn.classList.remove("copied");
      }, 1500);
    }).catch(() => {});
  });

  codeRow.appendChild(codeBox);
  codeRow.appendChild(copyBtn);
  body.appendChild(codeRow);

  // Waiting indicator
  const waitingRow = document.createElement("div");
  waitingRow.className = "outlook-modal-waiting";

  const waitingText = document.createElement("span");
  waitingText.textContent = "Esperando confirmación...";

  const dotsEl = document.createElement("span");
  dotsEl.className = "outlook-modal-dots";
  for (let i = 0; i < 3; i++) {
    const dot = document.createElement("span");
    dotsEl.appendChild(dot);
  }

  waitingRow.appendChild(waitingText);
  waitingRow.appendChild(dotsEl);
  body.appendChild(waitingRow);

  // Countdown timer
  const countdownEl = document.createElement("div");
  countdownEl.className = "outlook-modal-countdown";
  const totalSecs = flow.expires_in || 900;
  const mins = String(Math.floor(totalSecs / 60)).padStart(2, "0");
  const secs = String(totalSecs % 60).padStart(2, "0");
  countdownEl.textContent = `Caduca en: ${mins}:${secs}`;
  body.appendChild(countdownEl);

  return { backdrop, countdownEl };
}
