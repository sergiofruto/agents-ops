"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessage } from "@/lib/types";

interface Props {
  sessionId: string;
  initialMessages?: ChatMessage[];
  onNewSession?: (id: string) => void;
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className="max-w-3xl"
        style={{
          background: isUser ? "oklch(0.22 0.06 270)" : "var(--card)",
          border: `1px solid ${isUser ? "oklch(0.35 0.08 270)" : "var(--border)"}`,
          borderRadius: isUser ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
          padding: "12px 16px",
        }}
      >
        {!isUser && (
          <div
            className="text-xs mb-2 tracking-widest uppercase"
            style={{ color: "var(--primary)" }}
          >
            ⬡ The Analyst
          </div>
        )}
        <div
          className="text-sm leading-relaxed whitespace-pre-wrap"
          style={{ color: isUser ? "oklch(0.92 0 0)" : "var(--foreground)" }}
        >
          {msg.content}
        </div>
        <div
          className="text-xs mt-2 text-right"
          style={{ color: "var(--muted-foreground)", opacity: 0.6 }}
        >
          {msg.created_at?.substring(11, 16)} UTC
        </div>
      </div>
    </div>
  );
}

function StreamingBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-start mb-4">
      <div
        className="max-w-3xl"
        style={{
          background: "var(--card)",
          border: "1px solid var(--border)",
          borderRadius: "16px 16px 16px 4px",
          padding: "12px 16px",
        }}
      >
        <div
          className="text-xs mb-2 tracking-widest uppercase"
          style={{ color: "var(--primary)" }}
        >
          ⬡ The Analyst
        </div>
        <div className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: "var(--foreground)" }}>
          {text}
          <span
            className="inline-block w-2 h-4 ml-0.5 align-middle"
            style={{
              background: "var(--primary)",
              animation: "pulse 1s ease-in-out infinite",
            }}
          />
        </div>
      </div>
    </div>
  );
}

export default function ChatInterface({ sessionId, initialMessages = [], onNewSession }: Props) {
  const [messages, setMessages]   = useState<ChatMessage[]>(initialMessages);
  const [input, setInput]         = useState("");
  const [streaming, setStreaming] = useState("");
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLTextAreaElement>(null);

  const currentSession = useRef(sessionId);
  useEffect(() => { currentSession.current = sessionId; }, [sessionId]);

  // Scroll to bottom on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  const send = useCallback(async () => {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput("");
    setError(null);
    setLoading(true);
    setStreaming("");

    // Optimistic user message
    const userMsg: ChatMessage = {
      role: "user",
      content: msg,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg, session_id: currentSession.current }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;

          try {
            const data = JSON.parse(raw);
            if (data.error) {
              setError(data.error);
              break;
            }
            if (data.text) {
              accumulated += data.text;
              setStreaming(accumulated);
            }
            if (data.done) {
              // Flush streaming to messages
              const assistantMsg: ChatMessage = {
                role: "assistant",
                content: accumulated,
                created_at: new Date().toISOString(),
              };
              setMessages(prev => [...prev, assistantMsg]);
              setStreaming("");
              if (data.session_id && onNewSession) {
                onNewSession(data.session_id);
              }
            }
          } catch {
            // ignore parse errors on partial chunks
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
      setStreaming("");
      inputRef.current?.focus();
    }
  }, [input, loading, onNewSession]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  const isEmpty = messages.length === 0 && !streaming;

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-2 py-4" style={{ minHeight: 0 }}>
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
            <div className="text-4xl opacity-40">⬡</div>
            <div>
              <div
                className="text-sm font-semibold tracking-widest uppercase mb-2"
                style={{ color: "var(--primary)" }}
              >
                The Analyst is ready
              </div>
              <div className="text-xs max-w-sm leading-relaxed" style={{ color: "var(--muted-foreground)" }}>
                Ask about threat actors, infrastructure vulnerabilities, geopolitical signals,
                or what the sky says about the current landscape.
              </div>
            </div>
            <div
              className="text-xs italic max-w-md"
              style={{ color: "var(--muted-foreground)", opacity: 0.7 }}
            >
              "The Lips of Wisdom are closed, except to the ears of Understanding."
            </div>
            {/* Suggested prompts */}
            <div className="flex flex-wrap gap-2 justify-center max-w-lg">
              {[
                "What's the current threat landscape?",
                "Tell me about the sky right now",
                "What does the solar weather mean for SIGINT?",
                "Explain the Hermetic correspondence to this week's CVEs",
                "What should I watch in the South China Sea?",
              ].map(prompt => (
                <button
                  key={prompt}
                  onClick={() => { setInput(prompt); inputRef.current?.focus(); }}
                  className="text-xs px-3 py-1.5 rounded-full transition-colors"
                  style={{
                    background: "var(--muted)",
                    color: "var(--muted-foreground)",
                    border: "1px solid var(--border)",
                  }}
                  onMouseEnter={e => (e.currentTarget.style.borderColor = "var(--primary)")}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = "var(--border)")}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} />
            ))}
            {streaming && <StreamingBubble text={streaming} />}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Error */}
      {error && (
        <div
          className="mx-2 mb-2 px-3 py-2 rounded text-xs"
          style={{
            background: "oklch(0.65 0.22 25 / 15%)",
            border: "1px solid oklch(0.65 0.22 25 / 40%)",
            color: "oklch(0.80 0.20 25)",
          }}
        >
          {error}
        </div>
      )}

      {/* Input area */}
      <div
        className="border-t px-3 py-3"
        style={{ borderColor: "var(--border)", background: "var(--card)" }}
      >
        <div
          className="flex gap-2 items-end rounded-xl px-3 py-2"
          style={{ background: "var(--muted)", border: "1px solid var(--border)" }}
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask The Analyst…"
            rows={1}
            disabled={loading}
            className="flex-1 bg-transparent resize-none text-sm outline-none leading-relaxed"
            style={{
              color: "var(--foreground)",
              maxHeight: "180px",
              overflowY: "auto",
            }}
            onInput={e => {
              const t = e.currentTarget;
              t.style.height = "auto";
              t.style.height = `${Math.min(t.scrollHeight, 180)}px`;
            }}
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            className="flex-none rounded-lg px-3 py-1.5 text-xs font-semibold tracking-wider uppercase transition-all"
            style={{
              background: loading || !input.trim() ? "var(--muted)" : "var(--primary)",
              color: loading || !input.trim() ? "var(--muted-foreground)" : "var(--primary-foreground)",
              border: "1px solid transparent",
            }}
          >
            {loading ? "…" : "Send"}
          </button>
        </div>
        <div className="text-xs mt-1 text-center" style={{ color: "var(--muted-foreground)", opacity: 0.5 }}>
          Enter to send · Shift+Enter for new line
        </div>
      </div>
    </div>
  );
}
