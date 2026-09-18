import { MessageCircle, BarChart3 } from 'lucide-react';
import { ChatMode } from '@/hooks/useAiChat';
import { cn } from '@/lib/utils';

const OPTIONS: { mode: ChatMode; label: string; icon: typeof MessageCircle; hint: string }[] = [
  { mode: 'report', label: 'Data Reports', icon: BarChart3, hint: 'Grounded in live fleet data' },
  { mode: 'chat', label: 'Live Chat', icon: MessageCircle, hint: 'Streaming conversation' },
];

export function ChatModeToggle({ value, onChange }: { value: ChatMode; onChange: (mode: ChatMode) => void }) {
  return (
    <div className="flex rounded-lg border border-border/60 bg-muted/40 p-1">
      {OPTIONS.map(({ mode, label, icon: Icon, hint }) => (
        <button
          key={mode}
          type="button"
          title={hint}
          onClick={() => onChange(mode)}
          className={cn(
            'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all',
            value === mode
              ? 'bg-card text-primary shadow-sm ring-1 ring-primary/15'
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          <Icon className="h-3.5 w-3.5" />
          {label}
        </button>
      ))}
    </div>
  );
}
