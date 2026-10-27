// Scan button and the analyst chat. Text is always inserted with textContent, never as HTML.
(function () {
  const btn = document.getElementById("scan-btn");
  function poll() {
    fetch("/api/scan/state").then(r => r.json()).then(s => {
      if (s.running) setTimeout(poll, 3000); else location.reload();
    });
  }
  if (btn) {
    if (btn.disabled) poll();
    btn.addEventListener("click", () => {
      btn.disabled = true; btn.textContent = "Scanning…";
      fetch("/api/scan", { method: "POST" }).then(() => setTimeout(poll, 3000));
    });
  }

  const log = document.getElementById("chat-log");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const messages = [];
  function add(role, text) {
    const el = document.createElement("div");
    el.className = "msg " + role;
    el.textContent = text;
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  }
  input.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });
  form.addEventListener("submit", e => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q) return;
    input.value = "";
    add("user", q);
    messages.push({ role: "user", content: q });
    while (messages.length > 20) messages.shift();
    while (messages.length && messages[0].role !== "user") messages.shift();
    const pending = add("assistant", "Thinking…");
    fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ messages }) })
      .then(r => r.json())
      .then(d => {
        const reply = d.reply || d.error || "Something went wrong.";
        pending.textContent = reply;
        if (d.reply) messages.push({ role: "assistant", content: reply.slice(0, 4000) });
        else messages.pop();
      })
      .catch(() => { pending.textContent = "Couldn't reach the agent."; messages.pop(); });
  });
})();
