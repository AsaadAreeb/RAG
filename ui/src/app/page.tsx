"use client";
import { useState } from "react";
import ChatInterface from "../components/ChatInterface";
import AdminPanel from "../components/AdminPanel";
import { MessageSquare, Upload, Cpu } from "lucide-react";
import clsx from "clsx";

type Tab = "chat" | "upload";

export default function Home() {
  const [tab, setTab] = useState<Tab>("chat");

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "chat",   label: "Chat",         icon: <MessageSquare size={15} /> },
    { id: "upload", label: "Upload Docs",  icon: <Upload size={15} /> },
  ];

  return (
    /* h-screen + flex col = full-viewport shell, nothing overflows */
    <main className="h-screen flex flex-col overflow-hidden bg-gray-950">

      {/* ── Top bar ───────────────────────────────────────────────────── */}
      <header className="shrink-0 border-b border-gray-800 bg-gray-950/90 backdrop-blur
                         px-5 py-3 flex items-center justify-between z-10">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 bg-indigo-600/20 rounded-lg">
            <Cpu size={18} className="text-indigo-400" />
          </div>
          <span className="font-semibold text-white tracking-tight">Enterprise RAG</span>
          <span className="text-[11px] bg-indigo-950 border border-indigo-800
                           text-indigo-300 px-2 py-0.5 rounded-full font-medium">
            Grok · Gemini
          </span>
        </div>

        <nav className="flex gap-1">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={clsx(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-150",
                tab === t.id
                  ? "bg-indigo-600 text-white shadow-lg shadow-indigo-900/40"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              )}
            >
              {t.icon}
              <span className="hidden sm:inline">{t.label}</span>
            </button>
          ))}
        </nav>
      </header>

      {/* ── Content: flex-1 + min-h-0 = fills remaining height exactly ── */}
      <div className="flex-1 min-h-0 flex overflow-hidden">
        {tab === "chat" ? (
          /* Chat wrapper — max width centred, full height */
          <div className="flex-1 min-h-0 flex flex-col max-w-5xl mx-auto w-full">
            <ChatInterface />
          </div>
        ) : (
          /* Upload tab — scrollable, centred */
          <div className="flex-1 overflow-y-auto flex items-start justify-center pt-12 px-4 pb-12">
            <AdminPanel />
          </div>
        )}
      </div>
    </main>
  );
}