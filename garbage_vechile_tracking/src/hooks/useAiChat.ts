import { useCallback, useMemo, useRef, useState } from 'react';
import { streamChat, fetchReport, ChatMessage, ReportResult } from '@/services/aiChatbotService';

export type ChatMode = 'chat' | 'report';

export interface DisplayMessage {
  id: string;
  role: 'user' | 'assistant';
  mode: ChatMode;
  content: string;
  report?: ReportResult;
  isStreaming?: boolean;
  error?: string;
}

function makeId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function useAiChat() {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [mode, setMode] = useState<ChatMode>('report');
  const [busyByMode, setBusyByMode] = useState<Record<ChatMode, boolean>>({ chat: false, report: false });
  const abortRef = useRef<AbortController | null>(null);

  const updateMessage = useCallback((id: string, patch: Partial<DisplayMessage>) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  }, []);

  const sendChatMessage = useCallback(async (text: string) => {
    const history: ChatMessage[] = [];
    setMessages((prev) => {
      history.push(...prev.filter((m) => m.mode === 'chat').map((m) => ({ role: m.role, content: m.content })));
      return prev;
    });

    const userMsg: DisplayMessage = { id: makeId(), role: 'user', mode: 'chat', content: text };
    const assistantId = makeId();
    const assistantMsg: DisplayMessage = { id: assistantId, role: 'assistant', mode: 'chat', content: '', isStreaming: true };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setBusyByMode((prev) => ({ ...prev, chat: true }));

    const controller = new AbortController();
    abortRef.current = controller;

    await streamChat(
      [...history, { role: 'user', content: text }],
      {
        onToken: (token) => {
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + token } : m)),
          );
        },
        onDone: () => {
          updateMessage(assistantId, { isStreaming: false });
          setBusyByMode((prev) => ({ ...prev, chat: false }));
        },
        onError: (message) => {
          updateMessage(assistantId, { isStreaming: false, error: message });
          setBusyByMode((prev) => ({ ...prev, chat: false }));
        },
      },
      controller.signal,
    );
  }, [updateMessage]);

  const sendReportQuestion = useCallback(async (text: string) => {
    const history: ChatMessage[] = [];
    setMessages((prev) => {
      history.push(...prev.filter((m) => m.mode === 'report' && !m.error).map((m) => ({ role: m.role, content: m.content })));
      return prev;
    });

    const userMsg: DisplayMessage = { id: makeId(), role: 'user', mode: 'report', content: text };
    const assistantId = makeId();
    const assistantMsg: DisplayMessage = { id: assistantId, role: 'assistant', mode: 'report', content: '', isStreaming: true };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setBusyByMode((prev) => ({ ...prev, report: true }));

    try {
      const report = await fetchReport(text, history);
      updateMessage(assistantId, { isStreaming: false, content: report.summary, report });
    } catch (err) {
      updateMessage(assistantId, { isStreaming: false, error: (err as Error).message });
    } finally {
      setBusyByMode((prev) => ({ ...prev, report: false }));
    }
  }, [updateMessage]);

  const sendMessage = useCallback(
    (text: string) => (mode === 'chat' ? sendChatMessage(text) : sendReportQuestion(text)),
    [mode, sendChatMessage, sendReportQuestion],
  );

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
    setBusyByMode((prev) => ({ ...prev, [mode]: false }));
  }, [mode]);

  const clearMessages = useCallback(() => {
    // Only wipe the session for the tab currently in view; the other mode's
    // conversation keeps running in the background so switching tabs restores it.
    abortRef.current?.abort();
    setBusyByMode((prev) => ({ ...prev, [mode]: false }));
    setMessages((prev) => prev.filter((m) => m.mode !== mode));
  }, [mode]);

  // Each tab (Live Chat / Data Reports) keeps its own independent session;
  // switching tabs just changes which slice of `messages` is shown.
  const sessionMessages = useMemo(() => messages.filter((m) => m.mode === mode), [messages, mode]);

  return { messages: sessionMessages, mode, setMode, isBusy: busyByMode[mode], sendMessage, stopStreaming, clearMessages };
}
