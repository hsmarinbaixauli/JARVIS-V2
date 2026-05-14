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
