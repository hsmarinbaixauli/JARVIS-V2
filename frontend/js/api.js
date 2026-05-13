/**
 * Backend API client.
 *
 * Exports:
 *   listConversations()           → Promise<ConversationSummary[]>
 *   getMessages(id)               → Promise<MessageRecord[]>
 *   deleteConversation(id)        → Promise<void>
 *   streamChat(msg, cid, cbs)     → EventSource  (close() to abort)
 */

const BASE = "";   // same-origin — FastAPI serves the frontend

// ─── REST helpers ──────────────────────────────────────────────────────────

async function _json(res) {
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}${body ? ": " + body : ""}`);
  }
  return res.json();
}

export async function listConversations() {
  return _json(await fetch(`${BASE}/api/conversations`));
}

export async function getMessages(conversationId) {
  return _json(await fetch(`${BASE}/api/conversations/${conversationId}/messages`));
}

export async function deleteConversation(conversationId) {
  return _json(await fetch(`${BASE}/api/conversations/${conversationId}`, { method: "DELETE" }));
}

// ─── SSE streaming ─────────────────────────────────────────────────────────

/**
 * Open a streaming chat connection.
 *
 * @param {string}      message
 * @param {string|null} conversationId
 * @param {{
 *   onTextDelta:     (d:{delta:string}) => void,
 *   onToolStart:     (d:{id:string, name:string}) => void,
 *   onToolExecuting: (d:{id:string, name:string}) => void,
 *   onToolResult:    (d:{id:string, name:string, output:string, is_error:boolean}) => void,
 *   onError:         (d:{message:string}) => void,
 *   onDone:          (d:{conversation_id:string}) => void,
 * }} callbacks
 * @returns {EventSource}
 */
export function streamChat(message, conversationId, callbacks) {
  const params = new URLSearchParams({ message });
  if (conversationId) params.set("conversation_id", conversationId);

  const es = new EventSource(`${BASE}/api/chat/stream?${params}`);
  let completed = false;

  function safe(name, raw) {
    try {
      const fn = callbacks[name];
      if (fn) fn(JSON.parse(raw));
    } catch (e) {
      console.error(`[api] error in ${name} handler`, e);
    }
  }

  es.addEventListener("text_delta",       e => safe("onTextDelta",     e.data));
  es.addEventListener("tool_use_start",   e => safe("onToolStart",     e.data));
  es.addEventListener("tool_use_executing", e => safe("onToolExecuting", e.data));
  es.addEventListener("tool_result",      e => safe("onToolResult",    e.data));

  es.addEventListener("error", e => {
    // Custom "error" event from server (has data)
    if (e.data) safe("onError", e.data);
  });

  es.addEventListener("done", e => {
    completed = true;
    es.close();
    safe("onDone", e.data);
  });

  es.onerror = () => {
    if (!completed) {
      es.close();
      callbacks.onError?.({ message: "Error de conexión con el servidor." });
    }
  };

  return es;
}
