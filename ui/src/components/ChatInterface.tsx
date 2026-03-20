"use client";
import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { sendQuery, clearMemory, Evidence, QueryResponse } from "../lib/api";
import EvidencePanel from "./EvidencePanel";
import SQLPanel from "./SQLPanel";
import {
  Send, Trash2, Loader2, Bot, User, AlertTriangle,
  Zap, ChevronRight,
} from "lucide-react";
import clsx from "clsx";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  evidence?: Evidence[];
  additionalMatches?: Evidence[];
  confidence?: number;
  warnings?: string[];
  provider?: string;
  route?: string;
  sql?: string;
  pendingId?: string;
}

const STORAGE_KEY    = "rag_messages";
const SESSION_KEY    = "rag_session_id";
const MAX_STORED     = 100;

const WELCOME: Message = {
  role: "system",
  content: "Ask me anything about your uploaded documents, or query your database in plain English.",
};

// ── Helpers ────────────────────────────────────────────────────────────────
function loadMessages(): Message[] {
  if (typeof window === "undefined") return [WELCOME];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [WELCOME];
    const parsed = JSON.parse(raw) as Message[];
    return parsed.length > 0 ? parsed : [WELCOME];
  } catch {
    return [WELCOME];
  }
}

function getOrCreateSessionId(): string {
  if (typeof window === "undefined") return "ssr-session";
  const stored = localStorage.getItem(SESSION_KEY);
  if (stored) return stored;
  const newId = `session_${Math.random().toString(36).slice(2, 10)}`;
  localStorage.setItem(SESSION_KEY, newId);
  return newId;
}

// ── Component ──────────────────────────────────────────────────────────────
export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>(loadMessages);
  const [input,    setInput]    = useState("");
  const [loading,  setLoading]  = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLTextAreaElement>(null);

  const [SESSION_ID, setSessionId] = useState<string>("");

  useEffect(() => {
    setSessionId(getOrCreateSessionId());
  }, []);

  /* ── Persist messages to localStorage on every change ─────────────────── */
  useEffect(() => {
    try {
      // Keep only the last MAX_STORED messages to avoid quota issues
      const toStore = messages.slice(-MAX_STORED);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toStore));
    } catch {
      // Silently ignore quota exceeded errors
    }
  }, [messages]);

  /* ── Auto-scroll ─────────────────────────────────────────────────────── */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  /* ── Auto-resize textarea ────────────────────────────────────────────── */
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  /* ── Send message ────────────────────────────────────────────────────── */
  const handleSend = useCallback(async () => {
    const q = input.trim();
    if (!q || loading || !SESSION_ID) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setLoading(true);

    try {
      const res: QueryResponse = await sendQuery(q, SESSION_ID);

      if (res.blocked) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `⚠ Query blocked: ${res.reason}`,
            warnings: ["Blocked by safety filter"],
          },
        ]);
        return;
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          evidence:         res.evidence,
          additionalMatches: res.additional_matches,
          confidence:       res.confidence,
          warnings:         res.warnings,
          provider:         res.provider,
          route:            res.route,
          sql:              res.sql,
          pendingId:        res.pending_id,
        },
      ]);
    } catch (e: unknown) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Something went wrong: ${e instanceof Error ? e.message : "Unknown error"}`,
          warnings: ["Network or server error"],
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, SESSION_ID]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  /* ── Clear — wipes both Redis memory AND localStorage ──────────────────── */
  async function handleClear() {
    if (!SESSION_ID) return; 
    await clearMemory(SESSION_ID);
    localStorage.removeItem(STORAGE_KEY);
    setMessages([
      { role: "system", content: "Memory cleared. Start a fresh conversation." },
    ]);
  }

  /* ── SQL result callback ─────────────────────────────────────────────── */
  function handleSqlResult(res: QueryResponse, idx: number) {
    setMessages((prev) =>
      prev.map((m, i) =>
        i === idx ? { ...m, content: res.answer, pendingId: undefined } : m
      )
    );
  }

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="flex-1 min-h-0 flex flex-col">

      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-5 py-3
                      border-b border-gray-800/60 bg-gray-950">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-indigo-600/20
                          flex items-center justify-center">
            <Bot size={16} className="text-indigo-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white leading-none">
              RAG Assistant
            </p>
            <p suppressHydrationWarning className="text-[11px] text-gray-500 mt-0.5">
              {loading ? (
                <span className="text-indigo-400 flex items-center gap-1">
                  <Loader2 size={10} className="animate-spin" /> Thinking…
                </span>
              ) : SESSION_ID ? (
                `Session · ${SESSION_ID.slice(-6)}`
              ) : (
                "Ready"
              )}
            </p>
          </div>
        </div>
        <button
          onClick={handleClear}
          title="Clear conversation and memory"
          className="flex items-center gap-1.5 text-xs text-gray-500
                     hover:text-red-400 transition-colors px-2 py-1
                     rounded-md hover:bg-red-950/30"
        >
          <Trash2 size={12} />
          <span className="hidden sm:inline">Clear Memory</span>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-5 space-y-5">
        {messages.map((msg, idx) => (
          <div key={idx}>

            {msg.role === "system" && (
              <div className="flex items-center justify-center gap-2
                              text-xs text-gray-500 py-1">
                <ChevronRight size={11} />
                {msg.content}
              </div>
            )}

            {msg.role === "user" && (
              <div className="flex justify-end items-end gap-2.5">
                <div className="max-w-[75%] bg-indigo-600 rounded-2xl
                                rounded-br-sm px-4 py-2.5 text-sm text-white
                                leading-relaxed shadow-lg shadow-indigo-900/30">
                  {msg.content}
                </div>
                <div className="w-7 h-7 shrink-0 rounded-full bg-gray-700
                                flex items-center justify-center mb-0.5">
                  <User size={13} className="text-gray-300" />
                </div>
              </div>
            )}

            {msg.role === "assistant" && (
              <div className="flex justify-start items-start gap-2.5">
                <div className="w-7 h-7 shrink-0 rounded-full bg-indigo-600/20
                                flex items-center justify-center mt-0.5">
                  <Bot size={13} className="text-indigo-400" />
                </div>

                <div className="max-w-[85%] space-y-2.5">
                  <div className="bg-gray-800/80 border border-gray-700/50
                                  rounded-2xl rounded-bl-sm px-4 py-3 text-sm
                                  text-gray-100 leading-relaxed shadow-md">
                    <p className="whitespace-pre-wrap">{msg.content}</p>

                    {msg.provider && (
                      <div className="mt-2.5 pt-2 border-t border-gray-700/50
                                      flex gap-1.5 flex-wrap">
                        <span className="inline-flex items-center gap-1 text-[11px]
                                         bg-gray-900 border border-gray-700
                                         text-gray-400 px-2 py-0.5 rounded-full">
                          <Zap size={9} className="text-yellow-500" />
                          {msg.provider}
                        </span>
                        {msg.route && (
                          <span className="text-[11px] bg-gray-900 border
                                           border-gray-700 text-gray-500
                                           px-2 py-0.5 rounded-full">
                            {msg.route}
                          </span>
                        )}
                        {msg.confidence !== undefined && (
                          <span className={clsx(
                            "text-[11px] px-2 py-0.5 rounded-full border font-mono",
                            msg.confidence > 0.65
                              ? "bg-green-950/50 border-green-800 text-green-400"
                              : msg.confidence > 0.35
                              ? "bg-yellow-950/50 border-yellow-800 text-yellow-400"
                              : "bg-red-950/50 border-red-800 text-red-400"
                          )}>
                            {(msg.confidence * 100).toFixed(0)}% confidence
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {msg.sql && msg.pendingId && (
                    <SQLPanel
                      sql={msg.sql}
                      pendingId={msg.pendingId}
                      onResult={(r) => handleSqlResult(r, idx)}
                    />
                  )}

                  {msg.evidence && msg.evidence.length > 0 && (
                    <EvidencePanel
                      evidence={msg.evidence}
                      additionalMatches={msg.additionalMatches}
                      confidence={msg.confidence}
                      warnings={msg.warnings}
                    />
                  )}

                  {msg.warnings && msg.warnings.length > 0 &&
                    !msg.evidence?.length && (
                    <div className="flex items-start gap-1.5 text-xs text-yellow-400
                                    bg-yellow-950/30 border border-yellow-800/50
                                    rounded-lg px-3 py-2">
                      <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                      <span>{msg.warnings.join(" · ")}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex justify-start items-start gap-2.5">
            <div className="w-7 h-7 shrink-0 rounded-full bg-indigo-600/20
                            flex items-center justify-center">
              <Bot size={13} className="text-indigo-400" />
            </div>
            <div className="bg-gray-800/80 border border-gray-700/50
                            rounded-2xl rounded-bl-sm px-4 py-3">
              <div className="flex gap-1 items-center h-4">
                <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full
                                 animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full
                                 animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full
                                 animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 px-4 py-3 border-t border-gray-800/60 bg-gray-950">
        <div className="flex items-end gap-2.5 bg-gray-800/60 border border-gray-700
                        rounded-2xl px-3 py-2 focus-within:border-indigo-500
                        transition-colors duration-150">
          <textarea
            ref={inputRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your documents or database… (Shift+Enter for new line)"
            disabled={loading}
            className="flex-1 bg-transparent resize-none text-sm text-white
                       placeholder-gray-500 focus:outline-none min-h-[36px]
                       max-h-40 py-1.5 leading-relaxed disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className={clsx(
              "shrink-0 w-9 h-9 rounded-xl flex items-center justify-center",
              "transition-all duration-150 mb-0.5",
              loading || !input.trim()
                ? "bg-gray-700 text-gray-500 cursor-not-allowed"
                : "bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-900/40"
            )}
          >
            {loading
              ? <Loader2 size={15} className="animate-spin" />
              : <Send size={15} />
            }
          </button>
        </div>
        <p className="text-[11px] text-gray-600 mt-1.5 text-center">
          Answers are grounded in retrieved documents · SQL requires approval
        </p>
      </div>
    </div>
  );
}
