import { useEffect, useRef } from 'react';
import { PageHeader } from '@/components/PageHeader';
import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Bot, Sparkles, RotateCcw } from 'lucide-react';
import { useAiChat } from '@/hooks/useAiChat';
import { ChatModeToggle } from '@/components/ai-chatbot/ChatModeToggle';
import { ChatComposer } from '@/components/ai-chatbot/ChatComposer';
import { ChatMessageBubble } from '@/components/ai-chatbot/ChatMessageBubble';

const SUGGESTIONS: Record<'chat' | 'report', string[]> = {
  chat: ['What can you help me with?', 'Explain what "route efficiency" means.'],
  report: ['How many trucks are active right now?', 'Summarize the current active alerts.'],
};

export default function AiChatbot() {
  const { messages, mode, setMode, isBusy, sendMessage, stopStreaming, clearMessages } = useAiChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex h-full flex-col gap-4 p-4 sm:p-6">
      <PageHeader
        icon={Bot}
        category="assistant"
        title="AI Chat Bot"
        description="Ask questions in real time or get answers grounded in live fleet data"
        actions={
          <Button variant="outline" size="sm" onClick={clearMessages} className="gap-1.5" title="Clear this tab's conversation and start over">
            <RotateCcw className="h-3.5 w-3.5" /> New Session
          </Button>
        }
      />

      <Card className="flex flex-1 flex-col overflow-hidden border-border/60 shadow-sm">
        <div className="flex items-center justify-between gap-3 border-b border-border/60 bg-gradient-to-r from-emerald-50/60 via-card to-amber-50/40 px-4 py-3">
          <ChatModeToggle value={mode} onChange={setMode} />
          <span className="hidden items-center gap-1.5 text-xs text-muted-foreground sm:flex">
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            Powered by OpenAI
          </span>
        </div>

        <CardContent className="flex flex-1 flex-col gap-4 overflow-hidden p-0">
          <ScrollArea className="flex-1 px-4 py-4">
            {messages.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center gap-3 py-16 text-center">
                <div className="rounded-full bg-primary/10 p-4 ring-1 ring-primary/15">
                  <Bot className="h-8 w-8 text-primary" />
                </div>
                <p className="text-sm font-medium text-foreground">Start a conversation</p>
                <p className="max-w-sm text-xs text-muted-foreground">
                  Each tab keeps its own session - switch between Data Reports and Live Chat any time.
                </p>
                <div className="mt-2 flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS[mode].map((s) => (
                    <button
                      key={s}
                      onClick={() => sendMessage(s)}
                      className="rounded-full border border-border/60 bg-muted/40 px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {messages.map((message) => (
                  <ChatMessageBubble key={message.id} message={message} />
                ))}
                <div ref={bottomRef} />
              </div>
            )}
          </ScrollArea>

          <div className="border-t border-border/60 p-4">
            <ChatComposer mode={mode} isBusy={isBusy} onSend={sendMessage} onStop={stopStreaming} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
