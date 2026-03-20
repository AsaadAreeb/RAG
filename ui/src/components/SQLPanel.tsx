"use client";
import { useState } from "react";
import { approveSql, QueryResponse } from "../lib/api";
import {
  Database, CheckCircle2, XCircle, Loader2,
  ShieldAlert, Terminal,
} from "lucide-react";

interface Props {
  sql: string;
  pendingId: string;
  onResult: (r: QueryResponse) => void;
}

type Status = "idle" | "loading" | "done" | "rejected" | "error";

export default function SQLPanel({ sql, pendingId, onResult }: Props) {
  const [status, setStatus] = useState<Status>("idle");
  const [errMsg, setErrMsg] = useState("");

  async function handleApprove() {
    setStatus("loading");
    setErrMsg("");
    try {
      const result = await approveSql(pendingId);
      onResult(result);
      setStatus("done");
    } catch (e: unknown) {
      setErrMsg(e instanceof Error ? e.message : "Execution failed");
      setStatus("error");
    }
  }

  return (
    <div className="bg-gray-900/60 border border-amber-800/40 rounded-2xl overflow-hidden">

      {/* Header */}
      <div className="flex items-center gap-2.5 px-4 py-3
                      border-b border-amber-800/30 bg-amber-950/20">
        <ShieldAlert size={14} className="text-amber-400 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-amber-300">SQL Requires Your Approval</p>
          <p className="text-[10px] text-amber-600/80 mt-0.5">
            Review before execution — only SELECT queries are permitted
          </p>
        </div>
        <Database size={14} className="text-amber-500/60 shrink-0" />
      </div>

      {/* SQL block */}
      <div className="px-4 py-3">
        <div className="flex items-center gap-1.5 mb-2">
          <Terminal size={11} className="text-gray-500" />
          <span className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">
            Generated Query
          </span>
        </div>
        <pre className="bg-gray-950 border border-gray-800 rounded-xl p-3.5
                        text-xs text-emerald-300 overflow-x-auto whitespace-pre-wrap
                        font-mono leading-relaxed">
          {sql}
        </pre>
      </div>

      {/* Action buttons */}
      <div className="px-4 pb-4">
        {status === "idle" && (
          <div className="flex gap-2.5">
            <button
              onClick={handleApprove}
              className="flex items-center gap-2 px-4 py-2 bg-green-700
                         hover:bg-green-600 active:bg-green-800 rounded-xl
                         text-sm font-medium text-white transition-colors
                         shadow-lg shadow-green-900/30"
            >
              <CheckCircle2 size={14} />
              Approve & Execute
            </button>
            <button
              onClick={() => setStatus("rejected")}
              className="flex items-center gap-2 px-4 py-2 bg-gray-800
                         hover:bg-gray-700 active:bg-gray-900 border border-gray-700
                         rounded-xl text-sm font-medium text-gray-300 transition-colors"
            >
              <XCircle size={14} className="text-red-400" />
              Reject
            </button>
          </div>
        )}

        {status === "loading" && (
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <Loader2 size={14} className="animate-spin text-indigo-400" />
            Executing query…
          </div>
        )}

        {status === "done" && (
          <div className="flex items-center gap-2 text-sm text-green-400">
            <CheckCircle2 size={14} />
            Executed successfully
          </div>
        )}

        {status === "rejected" && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <XCircle size={14} className="text-red-500" />
            Query rejected — not executed
          </div>
        )}

        {status === "error" && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-red-400">
              <XCircle size={14} />
              Execution failed
            </div>
            {errMsg && (
              <p className="text-xs text-red-300/70 bg-red-950/30 border
                            border-red-800/40 rounded-lg px-3 py-2 font-mono">
                {errMsg}
              </p>
            )}
            <button
              onClick={() => setStatus("idle")}
              className="text-xs text-indigo-400 hover:text-indigo-300 underline"
            >
              Try again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}