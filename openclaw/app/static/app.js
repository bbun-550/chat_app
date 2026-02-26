const state = {
  currentConversationId: null,
  runs: [],
  conversations: [],
  sending: false,
};

const el = {
  newConversationBtn: document.getElementById("newConversationBtn"),
  conversationList: document.getElementById("conversationList"),
  activeConversationLabel: document.getElementById("activeConversationLabel"),
  providerSelect: document.getElementById("providerSelect"),
  modelInput: document.getElementById("modelInput"),
  systemPromptSelect: document.getElementById("systemPromptSelect"),
  messages: document.getElementById("messages"),
  messageInput: document.getElementById("messageInput"),
  sendBtn: document.getElementById("sendBtn"),
  errorBox: document.getElementById("errorBox"),
  statsBody: document.getElementById("statsBody"),
  charCount: document.getElementById("charCount"),
  openConversationsBtn: document.getElementById("openConversationsBtn"),
  openStatsBtn: document.getElementById("openStatsBtn"),
};

marked.setOptions({
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value;
    }
    return hljs.highlightAuto(code).value;
  },
  breaks: true,
});

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function toLocale(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(navigator.language || "ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function setError(message = "") {
  el.errorBox.textContent = message;
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.detail || `${res.status} request failed`);
  }
  return body;
}

function setSending(isSending) {
  state.sending = isSending;
  el.sendBtn.disabled = isSending;
  el.sendBtn.textContent = isSending ? "Sending…" : "Send";
}

function updateCharCount() {
  el.charCount.textContent = `${new Intl.NumberFormat().format(el.messageInput.value.length)} chars`;
}

function addLoadingMessage() {
  const article = document.createElement("article");
  article.className = "msg assistant loading";
  article.id = "loadingIndicator";
  article.innerHTML =
    '<div class="msg-role">assistant</div><div>Thinking… <span class="loading-dots"><span></span><span></span><span></span></span></div>';
  el.messages.appendChild(article);
  el.messages.scrollTop = el.messages.scrollHeight;
}

function removeLoadingMessage() {
  const loading = document.getElementById("loadingIndicator");
  if (loading) loading.remove();
}

function injectCodeCopyButtons(container) {
  for (const pre of container.querySelectorAll("pre")) {
    if (pre.querySelector(".copy-btn")) continue;

    const code = pre.querySelector("code");
    if (!code) continue;

    const button = document.createElement("button");
    button.className = "copy-btn";
    button.type = "button";
    button.textContent = "Copy";
    button.setAttribute("aria-label", "Copy code block");

    button.addEventListener("click", async () => {
      await navigator.clipboard.writeText(code.innerText);
      button.textContent = "Copied";
      setTimeout(() => {
        button.textContent = "Copy";
      }, 1200);
    });

    pre.appendChild(button);
  }
}

function renderMessages(messages) {
  el.messages.innerHTML = "";

  if (!messages.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "Start a conversation to build your research log.";
    el.messages.appendChild(empty);
    return;
  }

  for (const message of messages) {
    const node = document.createElement("article");
    node.className = `msg ${message.role}`;

    let contentHtml = "";
    if (message.role === "assistant") {
      contentHtml = DOMPurify.sanitize(marked.parse(message.content || ""));
    } else {
      contentHtml = escapeHtml(message.content || "").replace(/\n/g, "<br />");
    }

    node.innerHTML = `
      <div class="msg-role">${message.role}</div>
      <div>${contentHtml}</div>
    `;

    el.messages.appendChild(node);
  }

  injectCodeCopyButtons(el.messages);
  el.messages.scrollTop = el.messages.scrollHeight;
}

function buildConversationItem(conversation) {
  const item = document.createElement("article");
  item.className = "conversation-item";

  if (conversation.id === state.currentConversationId) {
    item.classList.add("active");
  }

  const row = document.createElement("div");
  row.className = "conversation-row";

  const titleBtn = document.createElement("button");
  titleBtn.type = "button";
  titleBtn.className = "conversation-title";
  titleBtn.textContent = conversation.title;
  titleBtn.title = "Open or rename conversation";

  titleBtn.addEventListener("click", async () => {
    if (conversation.id === state.currentConversationId) {
      startInlineRename(conversation, item);
      return;
    }

    state.currentConversationId = conversation.id;
    closeMobilePanels();
    await refreshConversation();
    await refreshSidebar();
  });

  const deleteBtn = document.createElement("button");
  deleteBtn.type = "button";
  deleteBtn.className = "icon-btn danger";
  deleteBtn.textContent = "×";
  deleteBtn.setAttribute("aria-label", `Delete ${conversation.title}`);

  deleteBtn.addEventListener("click", async () => {
    const ok = confirm(`Delete \"${conversation.title}\"? This cannot be undone.`);
    if (!ok) return;

    await api(`/conversations/${conversation.id}`, { method: "DELETE" });

    if (state.currentConversationId === conversation.id) {
      state.currentConversationId = null;
      state.runs = [];
    }

    await refreshSidebar();
    await refreshConversation();
  });

  row.appendChild(titleBtn);
  row.appendChild(deleteBtn);

  const meta = document.createElement("div");
  meta.className = "conversation-meta";
  meta.textContent = `Updated ${toLocale(conversation.updated_at)}`;

  item.appendChild(row);
  item.appendChild(meta);
  return item;
}

function startInlineRename(conversation, item) {
  const row = item.querySelector(".conversation-row");
  if (!row) return;

  const existing = row.querySelector(".conversation-title-input");
  if (existing) return;

  const titleBtn = row.querySelector(".conversation-title");
  if (!titleBtn) return;

  const input = document.createElement("input");
  input.type = "text";
  input.className = "conversation-title-input";
  input.value = conversation.title;
  input.name = "conversation_title";
  input.autocomplete = "off";
  input.setAttribute("aria-label", "Conversation title");

  async function commitRename() {
    const next = input.value.trim();
    if (!next || next === conversation.title) {
      titleBtn.style.display = "";
      input.remove();
      return;
    }

    await api(`/conversations/${conversation.id}`, {
      method: "PATCH",
      body: JSON.stringify({ title: next }),
    });

    if (state.currentConversationId === conversation.id) {
      el.activeConversationLabel.textContent = next;
    }

    await refreshSidebar();
  }

  input.addEventListener("keydown", async (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      await commitRename();
    }

    if (event.key === "Escape") {
      titleBtn.style.display = "";
      input.remove();
    }
  });

  input.addEventListener("blur", async () => {
    await commitRename();
  });

  titleBtn.style.display = "none";
  row.prepend(input);
  input.focus();
  input.select();
}

async function refreshSidebar() {
  const conversations = await api("/conversations");
  state.conversations = conversations;

  el.conversationList.innerHTML = "";

  if (!conversations.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No conversations yet.";
    el.conversationList.appendChild(empty);
    return;
  }

  for (const conversation of conversations) {
    el.conversationList.appendChild(buildConversationItem(conversation));
  }

  if (!state.currentConversationId) {
    state.currentConversationId = conversations[0].id;
  }
}

async function refreshSystemPrompts() {
  const prompts = await api("/system-prompts");
  const previous = el.systemPromptSelect.value;

  el.systemPromptSelect.innerHTML = '<option value="">No system prompt</option>';

  for (const prompt of prompts) {
    const option = document.createElement("option");
    option.value = prompt.id;
    option.textContent = prompt.name;
    el.systemPromptSelect.appendChild(option);
  }

  if (previous) {
    el.systemPromptSelect.value = previous;
  }
}

function renderStats() {
  const latest = state.runs[0];
  el.statsBody.innerHTML = "";

  const conversation = state.conversations.find((it) => it.id === state.currentConversationId);

  const block = document.createElement("div");

  if (!latest) {
    block.innerHTML = '<div class="empty">No run data yet.</div>';
    el.statsBody.appendChild(block);
    return;
  }

  const stats = [
    ["Provider", latest.provider],
    ["Model", latest.model],
    ["Latency", `${latest.latency_ms} ms`],
    ["Input", latest.input_tokens ?? "-"],
    ["Output", latest.output_tokens ?? "-"],
    ["Prompt", latest.system_prompt_id ? "Attached" : "None"],
  ];

  const statGrid = document.createElement("div");
  statGrid.className = "stat-grid";

  for (const [label, value] of stats) {
    const node = document.createElement("div");
    node.className = "stat";
    node.innerHTML = `
      <div class="stat-label">${label}</div>
      <div class="stat-value">${value}</div>
    `;
    statGrid.appendChild(node);
  }

  block.appendChild(statGrid);

  const actions = document.createElement("div");
  actions.className = "action-stack";
  actions.innerHTML = `
    <button type="button" id="exportJsonBtn" class="ghost">Export Conversation JSON</button>
    <button type="button" id="exportSftBtn" class="ghost">Export Conversation SFT</button>
    <button type="button" id="exportAllSftBtn" class="ghost">Export All SFT (min=4)</button>
  `;
  block.appendChild(actions);

  if (conversation) {
    const meta = document.createElement("div");
    meta.className = "run-item";
    meta.innerHTML = `
      <div><strong>Conversation</strong></div>
      <div class="mono">${conversation.title}</div>
      <div class="mono" style="margin-top:4px; font-size:11px; color:#607080;">${conversation.id}</div>
    `;
    block.appendChild(meta);
  }

  const runLog = document.createElement("div");
  runLog.className = "run-log";

  for (const run of state.runs.slice(0, 6)) {
    const item = document.createElement("div");
    item.className = "run-item";
    item.innerHTML = `
      <div><strong>${run.model}</strong></div>
      <div class="mono">${run.latency_ms} ms / in ${run.input_tokens ?? "-"} / out ${run.output_tokens ?? "-"}</div>
      <div class="mono" style="color:#607080;">${toLocale(run.created_at)}</div>
    `;
    runLog.appendChild(item);
  }

  block.appendChild(runLog);
  el.statsBody.appendChild(block);

  document.getElementById("exportJsonBtn")?.addEventListener("click", async () => {
    await exportConversation("json");
  });

  document.getElementById("exportSftBtn")?.addEventListener("click", async () => {
    await exportConversation("sft");
  });

  document.getElementById("exportAllSftBtn")?.addEventListener("click", async () => {
    await exportAllSft();
  });
}

function downloadJson(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

async function exportConversation(format) {
  if (!state.currentConversationId) {
    setError("Create or open a conversation first.");
    return;
  }

  const data = await api(`/export/${state.currentConversationId}?format=${format}`);
  downloadJson(data, `openclaw-${state.currentConversationId}-${format}.json`);
}

async function exportAllSft() {
  const data = await api("/export/all/sft?min_quality=4");
  downloadJson(data, "openclaw-all-sft-min4.json");
}

async function refreshConversation() {
  if (!state.currentConversationId) {
    el.activeConversationLabel.textContent = "No conversation";
    renderMessages([]);
    state.runs = [];
    renderStats();
    return;
  }

  const [conversation, messages, runs] = await Promise.all([
    api(`/conversations/${state.currentConversationId}`),
    api(`/conversations/${state.currentConversationId}/messages`),
    api(`/runs?conversation_id=${state.currentConversationId}`),
  ]);

  el.activeConversationLabel.textContent = `${conversation.title}`;
  renderMessages(messages);
  state.runs = runs;
  renderStats();
}

async function createConversation() {
  const created = await api("/conversations", {
    method: "POST",
    body: JSON.stringify({ title: "New Chat" }),
  });

  state.currentConversationId = created.id;
  await refreshSidebar();
  await refreshConversation();
}

async function sendMessage() {
  const message = el.messageInput.value.trim();
  if (!message || state.sending) return;

  if (!state.currentConversationId) {
    await createConversation();
  }

  setError();
  setSending(true);
  addLoadingMessage();

  try {
    await api("/chat", {
      method: "POST",
      body: JSON.stringify({
        conversation_id: state.currentConversationId,
        message,
        provider: el.providerSelect.value,
        model: el.modelInput.value.trim() || null,
        system_prompt_id: el.systemPromptSelect.value || null,
        temperature: 0.7,
        max_tokens: 2048,
      }),
    });

    el.messageInput.value = "";
    updateCharCount();

    await refreshConversation();
    await refreshSidebar();
  } catch (error) {
    setError(`${error.message}. Try again with a shorter message or check provider settings.`);
  } finally {
    removeLoadingMessage();
    setSending(false);
    el.messageInput.focus();
  }
}

function closeMobilePanels() {
  document.body.classList.remove("left-open", "right-open");
}

function wireMobilePanelActions() {
  el.openConversationsBtn?.addEventListener("click", () => {
    const next = !document.body.classList.contains("left-open");
    document.body.classList.toggle("left-open", next);
    document.body.classList.remove("right-open");
  });

  el.openStatsBtn?.addEventListener("click", () => {
    const next = !document.body.classList.contains("right-open");
    document.body.classList.toggle("right-open", next);
    document.body.classList.remove("left-open");
  });

  document.addEventListener("click", (event) => {
    if (window.innerWidth > 1150) return;

    const target = event.target;
    if (!(target instanceof Element)) return;

    if (
      target.closest(".panel") ||
      target.closest("#openConversationsBtn") ||
      target.closest("#openStatsBtn")
    ) {
      return;
    }

    closeMobilePanels();
  });
}

function wireEvents() {
  el.newConversationBtn.addEventListener("click", async () => {
    await createConversation();
    closeMobilePanels();
  });

  el.sendBtn.addEventListener("click", async () => {
    await sendMessage();
  });

  el.messageInput.addEventListener("keydown", async (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      await sendMessage();
    }
  });

  el.messageInput.addEventListener("input", updateCharCount);
}

(async function init() {
  try {
    wireEvents();
    wireMobilePanelActions();
    updateCharCount();

    await Promise.all([refreshSystemPrompts(), refreshSidebar()]);
    await refreshConversation();
  } catch (error) {
    setError(`Failed to initialize UI: ${error.message}`);
  }
})();
