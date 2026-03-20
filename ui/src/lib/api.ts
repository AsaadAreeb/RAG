const BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Types ──────────────────────────────────────────────────────────────────
export interface Evidence {
  text: string;
  source: string;
  score: number;
  rank: number;
  chunk_index?: number;
}

export interface QueryResponse {
  answer: string;
  evidence?: Evidence[];
  additional_matches?: Evidence[];
  confidence?: number;
  is_grounded?: boolean;
  warnings?: string[];
  route?: string;
  provider?: string;
  sql?: string;
  pending_id?: string;
  status?: string;
  blocked?: boolean;
  reason?: string;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  total_chunks: number;
  new_chunks: number;
  skipped_chunks: number;
  message: string;
}

// ── API calls ──────────────────────────────────────────────────────────────
export async function sendQuery(
  query: string,
  sessionId: string,
  requireSqlApproval = true
): Promise<QueryResponse> {
  const res = await fetch(`${BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      session_id: sessionId,
      require_sql_approval: requireSqlApproval,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function* streamQuery(
  query: string,
  sessionId: string
): AsyncGenerator<{
  chunk?: string;
  evidence?: Evidence[];
  done: boolean;
  error?: string;
}> {
  const res = await fetch(`${BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id: sessionId, stream: true }),
  });
  if (!res.ok || !res.body) {
    throw new Error(await res.text());
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          yield JSON.parse(line.slice(6));
        } catch {
          // skip malformed SSE lines
        }
      }
    }
  }
}

export async function approveSql(pendingId: string): Promise<QueryResponse> {
  const res = await fetch(`${BASE}/sql/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pending_id: pendingId }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function uploadPdf(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function clearMemory(sessionId: string): Promise<void> {
  await fetch(`${BASE}/memory/${sessionId}`, { method: "DELETE" });
}