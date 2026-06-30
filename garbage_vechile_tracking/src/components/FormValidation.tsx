import { ReactNode } from 'react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

export type FormErrors = Record<string, string>;

export const errorClass = (errors: FormErrors, field: string) =>
  errors[field] ? 'border-destructive ring-1 ring-destructive focus-visible:ring-destructive' : '';

export function RequiredMark() {
  return <span className='text-destructive'>*</span>;
}

export function FieldError({ errors, field }: { errors: FormErrors; field: string }) {
  return errors[field] ? <p className='text-xs font-medium text-destructive'>{errors[field]}</p> : null;
}

export function ValidationAlert({
  open,
  onOpenChange,
  title = 'Validation Error',
  description = 'Please fix the highlighted fields before saving.',
  messages,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  description?: ReactNode;
  messages: string[];
}) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className='space-y-2'>
              <p>{description}</p>
              {messages.length > 0 ? (
                <ul className='list-disc space-y-1 pl-5'>
                  {messages.map((message) => (
                    <li key={message}>{message}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogAction>OK</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
