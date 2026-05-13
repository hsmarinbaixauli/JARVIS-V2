/**
 * Chat panel — message rendering, streaming, and input handling.
 *
 * Exports:
 *   initChat(el, onSend)    — wire up input form
 *   showEmptyState()        — splash screen
 *   clearMessages()         — remove all messages
 *   loadHistory(messages)   — render messages from API
 *   appendUserMsg(text)     — add user bubble
 *   beginStream()           — returns stream controller object:
 *       { addTool(id, name), finishTool(id, isErr), appendText(delta),
 *         finalise() }
 *   appendErrorMsg(text)    — show error line in chat
 *   setInputEnabled(bool)   — enable/disable textarea + button
 */

let _messagesEl = null;
let _inputField = null;
let _sendBtn    = null;

export function initChat(panelEl, onSend) {
  _messagesEl = panelEl.querySelector("#messages");
  _inputField = panelEl.querySelector("#input-field");
  _sendBtn    = panelEl.querySelector("#btn-send");

  _inputField.addEventListener("input", _autoResize);

  panelEl.querySelector("#input-form").addEventListener("submit", e => {
    e.preventDefault();
    const text = _inputField.value.trim();
    if (!text || _sendBtn.disabled) return;
    _inputField.value = "";
    _autoResize();
    onSend(text);
  });

  // Enter sends; Shift+Enter inserts newline
  _inputField.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      panelEl.querySelector("#input-form").requestSubmit();
    }
  });

  // Enable send button only when there is text
  _inputField.addEventListener("input", () => {
    _sendBtn.disabled = !_inputField.value.trim();
  });

  showEmptyState();
}

export function showEmptyState() {
  _messagesEl.innerHTML = `
    <div class="empty-state">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="3"/>
        <path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12"/>
      </svg>
      <h2>Jarvis V2</h2>
      <p>Tu asistente de productividad empresarial.<br>Pregunta sobre calendario, emails, pedidos ERP, o cualquier otra cosa.</p>
    </div>`;
}

export function clearMessages() {
  _messagesEl.innerHTML = "";
}

export function loadHistory(messages) {
  clearMessages();
  if (!messages.length) { showEmptyState(); return; }
  for (const m of messages) {
    if (m.role === "user") {
      appendUserMsg(m.content);
    } else {
      const row = _makeAssistantRow();
      _messagesEl.appendChild(row.el);
      row.body.innerHTML = _renderMarkdown(m.content);
    }
  }
  _scrollToBottom();
}

export function appendUserMsg(text) {
  _removeEmptyState();
  const row = document.createElement("div");
  row.className = "msg user";
  row.innerHTML = `<div class="msg-body">${_esc(text).replace(/\n/g,"<br>")}</div>`;
  _messagesEl.appendChild(row);
  _scrollToBottom();
}

export function beginStream() {
  _removeEmptyState();

  const row = _makeAssistantRow();
  _messagesEl.appendChild(row.el);

  // Tool indicators container
  const toolRow = document.createElement("div");
  toolRow.className = "tool-row";
  row.el.insertBefore(toolRow, row.body);

  const tools = {};   // id → { chip, nameSpan }
  let textBuf = "";
  let cursorActive = false;

  function _setCursor(on) {
    cursorActive = on;
    row.body.classList.toggle("typing-cursor", on);
  }

  _setCursor(true);

  return {
    addTool(id, name) {
      const chip = document.createElement("span");
      chip.className = "tool-chip";
      chip.dataset.toolId = id;
      chip.innerHTML = `<span class="chip-spinner"></span><span>${_esc(name)}</span>`;
      toolRow.appendChild(chip);
      tools[id] = chip;
      _scrollToBottom();
    },

    finishTool(id, isError) {
      const chip = tools[id];
      if (!chip) return;
      chip.innerHTML = `<span class="chip-dot"></span><span>${chip.querySelector("span:last-child").textContent}</span>`;
      chip.classList.add(isError ? "error" : "done");
    },

    appendText(delta) {
      textBuf += delta;
      row.body.textContent = textBuf;
      if (!cursorActive) _setCursor(true);
      _scrollToBottom();
    },

    finalise() {
      _setCursor(false);
      row.body.innerHTML = _renderMarkdown(textBuf);
      _scrollToBottom();
    },
  };
}

export function appendErrorMsg(text) {
  const div = document.createElement("div");
  div.className = "msg-error";
  div.textContent = text;
  _messagesEl.appendChild(div);
  _scrollToBottom();
}

export function setInputEnabled(enabled) {
  _inputField.disabled = !enabled;
  _sendBtn.disabled = !enabled || !_inputField.value.trim();
  if (enabled) _inputField.focus();
}

// ─── Markdown renderer ─────────────────────────────────────────────────────

function _renderMarkdown(raw) {
  // HTML-escape first, then unescape inside code blocks at end
  let s = raw
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Fenced code blocks (```lang\ncode```)
  s = s.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const cls = lang ? ` class="lang-${_esc(lang)}"` : "";
    return `<pre><code${cls}>${code.trim()}</code></pre>`;
  });

  // Inline code
  s = s.replace(/`([^`\n]+)`/g, "<code>$1</code>");

  // Bold + italic
  s = s.replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>");
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/\*([^*\n]+)\*/g, "<em>$1</em>");

  // Headings
  s = s.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  s = s.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  s = s.replace(/^# (.+)$/gm, "<h1>$1</h1>");

  // Horizontal rule
  s = s.replace(/^---+$/gm, "<hr>");

  // Unordered lists
  s = s.replace(/((?:^[*\-] .+\n?)+)/gm, match => {
    const items = match.trim().split("\n").map(l => `<li>${l.replace(/^[*\-] /, "")}</li>`).join("");
    return `<ul>${items}</ul>`;
  });

  // Ordered lists
  s = s.replace(/((?:^\d+\. .+\n?)+)/gm, match => {
    const items = match.trim().split("\n").map(l => `<li>${l.replace(/^\d+\. /, "")}</li>`).join("");
    return `<ol>${items}</ol>`;
  });

  // Blockquote
  s = s.replace(/^&gt; (.+)$/gm, "<blockquote>$1</blockquote>");

  // Paragraphs — split on blank lines (not inside block elements)
  const blocks = s.split(/\n{2,}/);
  s = blocks.map(block => {
    const trimmed = block.trim();
    if (!trimmed) return "";
    // Don't wrap block elements
    if (/^<(pre|ul|ol|h[1-6]|blockquote|hr)/.test(trimmed)) return trimmed;
    return `<p>${trimmed.replace(/\n/g, "<br>")}</p>`;
  }).join("\n");

  return s;
}

// ─── Internal ──────────────────────────────────────────────────────────────

function _makeAssistantRow() {
  const el = document.createElement("div");
  el.className = "msg assistant";
  const body = document.createElement("div");
  body.className = "msg-body";
  el.appendChild(body);
  return { el, body };
}

function _removeEmptyState() {
  const e = _messagesEl.querySelector(".empty-state");
  if (e) e.remove();
}

function _scrollToBottom() {
  _messagesEl.scrollTop = _messagesEl.scrollHeight;
}

function _autoResize() {
  _inputField.style.height = "auto";
  _inputField.style.height = Math.min(_inputField.scrollHeight, 148) + "px";
}

function _esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
