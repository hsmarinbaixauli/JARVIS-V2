/**
 * Jarvis V2 — application entry point.
 *
 * Responsibilities:
 *   - Bootstrap sidebar and chat panel
 *   - Manage current conversation state
 *   - Drive SSE streaming lifecycle
 *   - Keyboard shortcut: Ctrl+/ → focus input
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

// Keyboard shortcut: Ctrl+/ → focus input
document.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key === "/") {
    e.preventDefault();
    document.getElementById("input-field").focus();
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
  } finally {
    setInputEnabled(true);
  }
}

async function _deleteConversation(id) {
  try {
    await deleteConversation(id);
  } catch (err) {
    console.error("[app] delete failed", err);
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
      appendErrorMsg(message || "Error inesperado.");
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
  }
}

// ─── Utilities ─────────────────────────────────────────────────────────────

function _truncate(str, max) {
  return str.length <= max ? str : str.slice(0, max).trimEnd() + "…";
}
