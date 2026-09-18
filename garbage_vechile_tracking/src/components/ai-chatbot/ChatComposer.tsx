import { useState, KeyboardEvent } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Send, Square } from 'lucide-react';
import { ChatMode } from '@/hooks/useAiChat';

const PLACEHOLDERS: Record<ChatMode, string> = {
  chat: 'Ask me anything… (Shift+Enter for a new line)',
  report: 'Ask about live fleet numbers, alerts, or zone performance…',
};

export function ChatComposer({
  mode,
  isBusy,
  onSend,
  onStop,
}: {
  mode: ChatMode;
  isBusy: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
}) {
  const [value, setValue] = useState('');

  const submit = () => {
    const text = value.trim();
    if (!text || isBusy) return;
    onSend(text);
    setValue('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="flex items-end gap-2 rounded-xl border border-border/60 bg-card/80 p-2 shadow-sm backdrop-blur">
      <Textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={PLACEHOLDERS[mode]}
        rows={1}
        className="max-h-32 min-h-[2.5rem] resize-none border-0 bg-transparent shadow-none focus-visible:ring-0"
      />
      {isBusy ? (
        <Button size="icon" variant="destructive" onClick={onStop} title="Stop">
          <Square className="h-4 w-4" />
        </Button>
      ) : (
        <Button size="icon" onClick={submit} disabled={!value.trim()} title="Send">
          <Send className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
