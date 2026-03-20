"use client";
import { useState, useRef } from "react";
import { uploadPdf, UploadResponse } from "../lib/api";
import {
  Upload, FileText, CheckCircle2, AlertTriangle,
  Loader2, CloudUpload, Layers, SkipForward, Plus,
} from "lucide-react";
import clsx from "clsx";

export default function AdminPanel() {
  const [result, setResult]   = useState<UploadResponse | null>(null);
  const [error, setError]     = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [fileName, setFileName] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    setFileName(file.name);
    try {
      const r = await uploadPdf(file);
      setResult(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function reset() {
    setResult(null);
    setError("");
    setFileName("");
    if (inputRef.current) inputRef.current.value = "";
  }

  const stats: [string, number, string, React.ReactNode][] = result
    ? [
        ["Total Chunks",   result.total_chunks,   "text-white",       <Layers size={14} />],
        ["New / Indexed",  result.new_chunks,      "text-indigo-400",  <Plus size={14} />],
        ["Skipped",        result.skipped_chunks,  "text-gray-500",    <SkipForward size={14} />],
      ]
    : [];

  return (
    <div className="w-full max-w-lg space-y-5">

      {/* Card header */}
      <div>
        <h1 className="text-xl font-bold text-white">Document Upload</h1>
        <p className="text-sm text-gray-500 mt-1">
          Upload PDFs to index them into the vector store. Unchanged chunks are skipped automatically.
        </p>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !loading && inputRef.current?.click()}
        className={clsx(
          "relative border-2 border-dashed rounded-2xl p-10 text-center",
          "transition-all duration-200 cursor-pointer",
          loading
            ? "pointer-events-none border-gray-700 bg-gray-900/30"
            : dragging
            ? "border-indigo-500 bg-indigo-950/30 scale-[1.01]"
            : "border-gray-700 bg-gray-900/20 hover:border-indigo-600 hover:bg-indigo-950/20"
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />

        {loading ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-indigo-600/20 flex items-center justify-center">
              <Loader2 size={22} className="text-indigo-400 animate-spin" />
            </div>
            <div>
              <p className="text-sm font-medium text-white">Processing…</p>
              <p className="text-xs text-gray-500 mt-0.5 truncate max-w-[240px]">{fileName}</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className={clsx(
              "w-12 h-12 rounded-full flex items-center justify-center transition-colors",
              dragging ? "bg-indigo-600/40" : "bg-gray-800"
            )}>
              <CloudUpload size={22} className={dragging ? "text-indigo-300" : "text-gray-400"} />
            </div>
            <div>
              <p className="text-sm font-medium text-white">
                Drag & drop your PDF here
              </p>
              <p className="text-xs text-gray-500 mt-1">
                or{" "}
                <span className="text-indigo-400 underline underline-offset-2">
                  click to browse
                </span>
                {" "}· PDF only · max 50 MB
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Success card */}
      {result && (
        <div className="bg-green-950/20 border border-green-800/50 rounded-2xl p-4 space-y-3">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-2.5">
              <CheckCircle2 size={18} className="text-green-400 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-semibold text-green-300 leading-snug">
                  {result.filename}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">{result.message}</p>
              </div>
            </div>
            <button
              onClick={reset}
              className="text-[11px] text-gray-500 hover:text-white transition-colors
                         px-2 py-1 rounded-lg hover:bg-gray-800 shrink-0 ml-2"
            >
              Upload another
            </button>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-3 gap-2">
            {stats.map(([label, val, textColor, icon]) => (
              <div key={label as string}
                   className="bg-gray-900/60 border border-gray-800 rounded-xl p-3 text-center">
                <div className={clsx(
                  "flex items-center justify-center gap-1 mb-1",
                  textColor
                )}>
                  {icon}
                </div>
                <div className={clsx("text-xl font-bold tabular-nums", textColor)}>
                  {val}
                </div>
                <div className="text-[10px] text-gray-500 mt-0.5">{label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-start gap-2.5 text-sm text-red-300
                        bg-red-950/30 border border-red-800/50 rounded-xl px-4 py-3">
          <AlertTriangle size={15} className="shrink-0 mt-0.5 text-red-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Tips */}
      {!result && !loading && (
        <div className="bg-gray-900/30 border border-gray-800/50 rounded-xl p-4 space-y-2">
          <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
            How it works
          </p>
          {[
            ["📄", "Text is extracted from each page"],
            ["✂️", "Split into overlapping 600-token chunks"],
            ["🔢", "Each chunk is embedded (local model)"],
            ["⚡", "Unchanged chunks are skipped (hash check)"],
          ].map(([icon, text]) => (
            <div key={text as string} className="flex items-center gap-2 text-xs text-gray-500">
              <span>{icon}</span>
              <span>{text}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}