import { API_BASE_URL } from '@/config/api';
import { clearAuthTokens, getAccessToken, getRefreshToken, saveAuthTokens } from '@/lib/authStorage';

export type ChatRole = 'user' | 'assistant';

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ReportMetric {
  label: string;
  value: string;
  hint?: string | null;
}

export interface ReportResult {
  summary: string;
  metrics: ReportMetric[];
  insights: string[];
  items: Record<string, unknown>[];
  generated_at: string;
}

const AI_CHATBOT_BASE = `${API_BASE_URL}/ai-chatbot`;

function authHeaders(token?: string | null): HeadersInit {
  const accessToken = token ?? getAccessToken();
  return {
    'Content-Type': 'application/json',
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
  };
}

/** Access tokens expire after 30 minutes - refresh once and retry instead of failing the chat. */
async function tryRefreshToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  try {
    const response = await fetch(`${API_BASE_URL}/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) {
      clearAuthTokens();
      return null;
    }
    const payload = await response.json();
    const accessToken = String(payload?.access_token || '');
    const nextRefreshToken = String(payload?.refresh_token || '');
    if (!accessToken || !nextRefreshToken) {
      clearAuthTokens();
      return null;
    }
    saveAuthTokens(accessToken, nextRefreshToken);
    return accessToken;
  } catch {
    return null;
  }
}

/**
 * Mode 1 — streaming conversation.
 * Reads a Server-Sent-Events response token-by-token and reports each chunk via onToken.
 */
export async function streamChat(
  messages: ChatMessage[],
  handlers: {
    onToken: (token: string) => void;
    onDone: () => void;
    onError: (message: string) => void;
  },
  signal?: AbortSignal,
): Promise<void> {
  try {
    let response = await fetch(`${AI_CHATBOT_BASE}/chat/stream`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ messages }),
      signal,
    });

    if (response.status === 401) {
      const nextToken = await tryRefreshToken();
      if (nextToken) {
        response = await fetch(`${AI_CHATBOT_BASE}/chat/stream`, {
          method: 'POST',
          headers: authHeaders(nextToken),
          body: JSON.stringify({ messages }),
          signal,
        });
      }
    }

    if (!response.ok || !response.body) {
      const text = await response.text().catch(() => '');
      throw new Error(text || `Request failed with status ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() ?? '';

      for (const rawEvent of events) {
        const line = rawEvent.trim();
        if (!line.startsWith('data:')) continue;
        const jsonStr = line.slice(5).trim();
        if (!jsonStr) continue;

        const payload = JSON.parse(jsonStr) as { token?: string; done?: boolean; error?: string };
        if (payload.error) {
          handlers.onError(payload.error);
          return;
        }
        if (payload.token) {
          handlers.onToken(payload.token);
        }
        if (payload.done) {
          handlers.onDone();
          return;
        }
      }
    }
    handlers.onDone();
  } catch (err) {
    if ((err as Error).name === 'AbortError') return;
    handlers.onError((err as Error).message || 'Streaming failed');
  }
}

/**
 * Mode 2 — structured report grounded in live operations data.
 * `history` carries prior Data Reports turns so follow-up questions keep context.
 */
export async function fetchReport(question: string, history: ChatMessage[] = []): Promise<ReportResult> {
  let response = await fetch(`${AI_CHATBOT_BASE}/report`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ question, history }),
  });

  if (response.status === 401) {
    const nextToken = await tryRefreshToken();
    if (nextToken) {
      response = await fetch(`${AI_CHATBOT_BASE}/report`, {
        method: 'POST',
        headers: authHeaders(nextToken),
        body: JSON.stringify({ question, history }),
      });
    }
  }

  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(text || `Request failed with status ${response.status}`);
  }

  return response.json();
}
