"use client";

import { useCallback, useEffect, useState } from "react";
import ChatInterface from "@/components/ChatInterface";
import type { ChatSession } from "@/lib/types";

export default function ChatPage() {
  const [sessions, setSessions]   = useState<ChatSession[]>([]);
  const [activeId, setActiveId]   = useState<string>(() => crypto.randomUUID());
  const [sidebarOpen, setSidebar] = useState(true);

  const loadSessions = useCallback(async () => {
    const r = await fetch("/api/chat/sessions");
    if (r.ok) setSessions(await r.json());
  }, []);

  useEffect(() => { loadSessions(); }, [loadSessions]);

  async function deleteSession(id: string) {
    await fetch(`/api/chat/${id}`, { method: "DELETE" });
    setSessions(prev => prev.filter(s => s.session_id !== id));
    if (activeId === id) setActiveId(crypto.randomUUID());
  }

  function newSession() {
    setActiveId(crypto.randomUUID());
    loadSessions();
  }

  return (
    <div className="flex h-[calc(100vh-120px)] gap-0 rounded-lg overflow-hidden"
      style={{ border: "1px solid var(--border)" }}
    >
      {/* Sidebar */}
      {sidebarOpen && (
        <div
          className="w-60 flex-none flex flex-col border-r"
          style={{ background: "var(--card)", borderColor: "var(--border)" }}
        >
          <div className="p-3 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
            <span className="text-xs uppercase tracking-widest" style={{ color: "var(--muted-foreground)" }}>
              Sessions
            </span>
            <button
              onClick={newSession}
              className="text-xs px-2 py-0.5 rounded transition-colors"
              style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}
            >
              + New
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {sessions.length === 0 && (
              <div className="p-3 text-xs" style={{ color: "var(--muted-foreground)" }}>
                No sessions yet
              </div>
            )}
            {sessions.map(s => (
              <div
                key={s.session_id}
                className="group flex items-center gap-1 px-3 py-2 cursor-pointer border-b transition-colors"
                style={{
                  borderColor: "var(--border)",
                  background: s.session_id === activeId ? "var(--accent)" : "transparent",
                }}
                onClick={() => setActiveId(s.session_id)}
              >
                <div className="flex-1 min-w-0">
                  <div className="text-xs truncate" style={{ color: "var(--foreground)" }}>
                    {s.session_id.substring(0, 8)}…
                  </div>
                  <div className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                    {s.message_count} msgs · {s.last_at?.substring(5, 16)}
                  </div>
                </div>
                <button
                  className="opacity-0 group-hover:opacity-100 text-xs px-1 transition-opacity"
                  style={{ color: "oklch(0.65 0.22 25)" }}
                  onClick={e => { e.stopPropagation(); deleteSession(s.session_id); }}
                  title="Delete session"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
          <div
            className="p-2 border-t text-xs text-center"
            style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}
          >
            Powered by Claude + The Analyst persona
          </div>
        </div>
      )}

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Chat toolbar */}
        <div
          className="flex items-center gap-2 px-3 py-2 border-b text-xs"
          style={{
            borderColor: "var(--border)",
            background: "var(--card)",
            color: "var(--muted-foreground)",
          }}
        >
          <button onClick={() => setSidebar(v => !v)} className="hover:text-white transition-colors">
            {sidebarOpen ? "◁" : "▷"}
          </button>
          <span>Session: {activeId.substring(0, 8)}…</span>
          <button
            onClick={newSession}
            className="ml-auto hover:text-white transition-colors"
            title="New session"
          >
            + New session
          </button>
        </div>

        <ChatInterface
          sessionId={activeId}
          onNewSession={id => {
            setActiveId(id);
            loadSessions();
          }}
        />
      </div>
    </div>
  );
}
