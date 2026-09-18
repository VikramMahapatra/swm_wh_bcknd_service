import { DisplayMessage } from '@/hooks/useAiChat';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Bot, User, AlertTriangle } from 'lucide-react';
import { TypingDots } from './TypingDots';
import { ReportCard } from './ReportCard';
import { MarkdownContent } from './MarkdownContent';
import { cn } from '@/lib/utils';

export function ChatMessageBubble({ message }: { message: DisplayMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={cn('flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}>
      <Avatar className="h-8 w-8 shrink-0 ring-1 ring-border/60">
        <AvatarFallback className={isUser ? 'bg-primary/15 text-primary' : 'bg-secondary/15 text-secondary'}>
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>

      <div className={cn('max-w-[80%] rounded-2xl px-4 py-2.5 text-sm shadow-sm', isUser
        ? 'rounded-tr-sm bg-gradient-to-br from-primary to-secondary text-primary-foreground'
        : 'rounded-tl-sm border border-border/60 bg-card text-card-foreground')}
      >
        {message.error ? (
          <div className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{message.error}</span>
          </div>
        ) : isUser ? (
          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        ) : (
          <>
            {message.isStreaming && !message.content ? (
              <TypingDots />
            ) : (
              <MarkdownContent content={message.content} />
            )}
            {message.isStreaming && message.content && (
              <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-current align-middle" />
            )}
            {message.report && <ReportCard report={message.report} />}
          </>
        )}
      </div>
    </div>
  );
}
