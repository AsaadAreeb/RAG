"use client";
import { useState } from "react";
import { Evidence } from "../lib/api";
import {
  ChevronDown, ChevronUp, FileText, Info,
  TrendingUp, Search,
} from "lucide-react";
import clsx from "clsx";

interface Props {
  evidence: Evidence[];
  additionalMatches?: Evidence[];
  confidence?: number;
  warnings?: string[];
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    score > 0.7
      ? "bg-green-500"
      : score > 0.4
      ? "bg-yellow-500"
      : "bg-red-500";
  return (
    <div className="flex items-center gap-2 min-w-[80px]">
      <div className="flex-1 h-1 bg-gray-700 rounded-full overflow-hidden">
        <div className={clsx("h-full rounded-full", color)}
             style={{ width: `${pct}%` }} />
      </div>
      <span className={clsx(
        "text-[11px] font-mono tabular-nums w-7 text-right",
        score > 0.7 ? "text-green-400" : score > 0.4 ? "text-yellow-400" : "text-red-400"
      )}>
        {pct}%
      </span>
    </div>
  );
}

function ChunkCard({
  item,
  dim,
  rank,
}: {
  item: Evidence;
  dim?: boolean;
  rank: number;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className={clsx(
      "rounded-xl border transition-all duration-150",
      dim
        ? "border-gray-700/50 bg-gray-900/30 opacity-60 hover:opacity-90"
        : "border-gray-700/70 bg-gray-900/60 hover:border-indigo-700/50",
    )}>
      {/* Header row */}
      <button
        onClick={() => setOpen((p) => !p)}
        className="w-full flex items-center gap-3 px-3 py-2.5 text-left"
      >
        {/* Rank badge */}
        <span className="shrink-0 w-5 h-5 rounded-full bg-gray-800 border border-gray-700
                         text-[10px] font-bold text-gray-400 flex items-center justify-center">
          {rank}
        </span>

        {/* File name */}
        <div className="flex items-center gap-1.5 min-w-0 flex-1">
          <FileText size={12} className="text-indigo-400 shrink-0" />
          <span className="text-xs text-indigo-300 truncate font-medium">
            {item.source}
          </span>
          {item.chunk_index !== undefined && (
            <span className="text-[10px] text-gray-600 shrink-0">
              §{item.chunk_index}
            </span>
          )}
        </div>

        {/* Score */}
        <ScoreBar score={item.score} />

        {/* Expand toggle */}
        <span className="text-gray-500 shrink-0">
          {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </span>
      </button>

      {/* Expanded excerpt */}
      {open && (
        <div className="px-3 pb-3">
          <div className="border-t border-gray-700/50 pt-2.5">
            <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap
                          font-mono bg-gray-950/50 rounded-lg px-3 py-2.5">
              {item.text}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default function EvidencePanel({
  evidence,
  additionalMatches,
  confidence,
  warnings,
}: Props) {
  const [showAdditional, setShowAdditional] = useState(false);

  return (
    <div className="bg-gray-900/40 border border-gray-700/40 rounded-2xl p-3.5 space-y-3">

      {/* Panel header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp size={13} className="text-indigo-400" />
          <span className="text-xs font-semibold text-gray-200">
            Sources Used ({evidence.length})
          </span>
        </div>
        {confidence !== undefined && (
          <div className="flex items-center gap-1.5">
            <Info size={11} className="text-gray-500" />
            <span className="text-[11px] text-gray-500">
              Confidence:
              <span className={clsx(
                "ml-1 font-mono font-semibold",
                confidence > 0.65 ? "text-green-400"
                : confidence > 0.35 ? "text-yellow-400"
                : "text-red-400"
              )}>
                {(confidence * 100).toFixed(0)}%
              </span>
            </span>
          </div>
        )}
      </div>

      {/* Warnings */}
      {warnings && warnings.length > 0 && (
        <div className="text-[11px] text-yellow-400 bg-yellow-950/30
                        border border-yellow-800/50 rounded-lg px-3 py-2 flex items-start gap-2">
          <span className="shrink-0 mt-0.5">⚠</span>
          <span>{warnings.join(" · ")}</span>
        </div>
      )}

      {/* Primary evidence */}
      <div className="space-y-1.5">
        {evidence.map((e, i) => (
          <ChunkCard key={`e-${i}`} item={e} rank={i + 1} />
        ))}
      </div>

      {/* Additional matches */}
      {additionalMatches && additionalMatches.length > 0 && (
        <div>
          <button
            onClick={() => setShowAdditional((p) => !p)}
            className="flex items-center gap-1.5 text-[11px] text-gray-500
                       hover:text-indigo-400 transition-colors w-full py-1"
          >
            <Search size={10} />
            {showAdditional ? "Hide" : "Show"}{" "}
            {additionalMatches.length} additional context matches
            {showAdditional ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
          </button>

          {showAdditional && (
            <div className="space-y-1.5 mt-1.5 pt-2 border-t border-gray-800">
              <p className="text-[10px] text-gray-600 px-1 mb-2">
                Not used in generation but retrieved as close matches — use for manual verification
              </p>
              {additionalMatches.map((e, i) => (
                <ChunkCard
                  key={`a-${i}`}
                  item={e}
                  rank={evidence.length + i + 1}
                  dim
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}