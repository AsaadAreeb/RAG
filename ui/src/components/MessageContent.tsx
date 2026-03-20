/**
 * MessageContent
 * Renders LLM text that may contain markdown tables and **bold** text.
 * Uses react-markdown for full fidelity — no extra plugins needed for
 * the table / bold subset the LLM produces.
 */
"use client";
import ReactMarkdown from "react-markdown";

interface Props {
  content: string;
}

export default function MessageContent({ content }: Props) {
  return (
    <ReactMarkdown
      components={{
        /* ── Paragraphs ─────────────────────────────── */
        p: ({ children }) => (
          <p className="text-sm text-gray-100 leading-relaxed whitespace-pre-wrap mb-2 last:mb-0">
            {children}
          </p>
        ),

        /* ── Bold ───────────────────────────────────── */
        strong: ({ children }) => (
          <strong className="font-semibold text-white">{children}</strong>
        ),

        /* ── Table wrapper ──────────────────────────── */
        table: ({ children }) => (
          <div className="overflow-x-auto my-3 rounded-xl border border-gray-700">
            <table className="min-w-full text-xs text-left">{children}</table>
          </div>
        ),

        /* ── Table head ─────────────────────────────── */
        thead: ({ children }) => (
          <thead className="bg-gray-800 text-gray-300 uppercase tracking-wider">
            {children}
          </thead>
        ),

        /* ── Table body ─────────────────────────────── */
        tbody: ({ children }) => (
          <tbody className="divide-y divide-gray-800">{children}</tbody>
        ),

        /* ── Rows ───────────────────────────────────── */
        tr: ({ children }) => (
          <tr className="hover:bg-gray-800/50 transition-colors">{children}</tr>
        ),

        /* ── Header cells ───────────────────────────── */
        th: ({ children }) => (
          <th className="px-4 py-2.5 font-semibold text-gray-300 whitespace-nowrap">
            {children}
          </th>
        ),

        /* ── Data cells ─────────────────────────────── */
        td: ({ children }) => (
          <td className="px-4 py-2 text-gray-200 whitespace-nowrap">{children}</td>
        ),

        /* ── Inline code ────────────────────────────── */
        code: ({ children }) => (
          <code className="bg-gray-900 border border-gray-700 rounded px-1
                           text-emerald-300 font-mono text-[11px]">
            {children}
          </code>
        ),

        /* ── Unordered list ─────────────────────────── */
        ul: ({ children }) => (
          <ul className="list-disc list-inside space-y-1 text-sm text-gray-200 my-2">
            {children}
          </ul>
        ),

        /* ── Ordered list ───────────────────────────── */
        ol: ({ children }) => (
          <ol className="list-decimal list-inside space-y-1 text-sm text-gray-200 my-2">
            {children}
          </ol>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
