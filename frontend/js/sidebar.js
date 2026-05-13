/**
 * Sidebar component — conversation list.
 *
 * Exports:
 *   initSidebar(el, handlers)      — first render
 *   setSidebarActive(id)           — highlight active conversation
 *   prependConversation(conv)      — add new item at top
 *   removeSidebarItem(id)          — remove item by id
 *   replaceSidebarList(convs, id)  — full re-render of conversation list
 */

const _CHAT_ICON = `<svg class="conv-icon" viewBox="0 0 24 24" fill="none"
  stroke="currentColor" stroke-width="1.8">
  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
</svg>`;

const _DEL_ICON = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none"
  stroke="currentColor" stroke-width="2.5">
  <path d="M18 6 6 18M6 6l12 12"/>
</svg>`;

let _listEl = null;
let _handlers = null;  // { onSelect(id), onDelete(id), onNew() }

export function initSidebar(sidebarEl, handlers) {
  _handlers = handlers;
  _listEl = sidebarEl.querySelector("#conversation-list");

  sidebarEl.querySelector("#btn-new-chat").addEventListener("click", () => {
    _handlers.onNew();
  });

  _showEmpty();
}

export function replaceSidebarList(conversations, activeId) {
  _listEl.innerHTML = "";
  if (!conversations.length) { _showEmpty(); return; }
  for (const c of conversations) {
    _listEl.appendChild(_makeItem(c, c.id === activeId));
  }
}

export function prependConversation(conv) {
  const emptyEl = _listEl.querySelector(".conv-empty");
  if (emptyEl) emptyEl.remove();
  _listEl.prepend(_makeItem(conv, true));
}

export function setSidebarActive(id) {
  for (const item of _listEl.querySelectorAll(".conv-item")) {
    item.classList.toggle("active", item.dataset.id === id);
  }
}

export function removeSidebarItem(id) {
  const el = _listEl.querySelector(`[data-id="${id}"]`);
  if (el) el.remove();
  if (!_listEl.querySelector(".conv-item")) _showEmpty();
}

// ─── Internal ──────────────────────────────────────────────────────────────

function _showEmpty() {
  _listEl.innerHTML = `<div class="conv-empty">Sin conversaciones</div>`;
}

function _makeItem(conv, active) {
  const div = document.createElement("div");
  div.className = "conv-item" + (active ? " active" : "");
  div.dataset.id = conv.id;
  div.setAttribute("role", "button");
  div.setAttribute("tabindex", "0");
  div.setAttribute("aria-label", conv.title || "Conversación");

  div.innerHTML = `
    ${_CHAT_ICON}
    <span class="conv-title">${_esc(conv.title || "Conversación")}</span>
    <button class="conv-del" title="Eliminar" aria-label="Eliminar conversación" tabindex="-1">
      ${_DEL_ICON}
    </button>`;

  div.addEventListener("click", e => {
    if (!e.target.closest(".conv-del")) _handlers.onSelect(conv.id);
  });

  div.addEventListener("keydown", e => {
    if (e.key === "Enter" || e.key === " ") _handlers.onSelect(conv.id);
  });

  div.querySelector(".conv-del").addEventListener("click", e => {
    e.stopPropagation();
    _handlers.onDelete(conv.id);
  });

  return div;
}

function _esc(str) {
  return str.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
