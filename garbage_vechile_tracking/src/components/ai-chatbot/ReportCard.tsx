import { ReportResult } from '@/services/aiChatbotService';
import { Sparkles } from 'lucide-react';

function toHeaderLabel(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function ReportCard({ report }: { report: ReportResult }) {
  const columns = report.items.length > 0 ? Object.keys(report.items[0]) : [];

  return (
    <div className="mt-2 space-y-3 rounded-lg border border-border/60 bg-card/60 p-3">
      {report.metrics.length > 0 && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {report.metrics.map((metric) => (
            <div key={metric.label} className="rounded-lg bg-muted/50 p-2.5">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground truncate">{metric.label}</p>
              <p className="text-lg font-semibold text-foreground">{metric.value}</p>
              {metric.hint && <p className="text-[11px] text-muted-foreground/80 truncate">{metric.hint}</p>}
            </div>
          ))}
        </div>
      )}

      {columns.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border/60">
          <table className="w-full text-left text-xs">
            <thead className="bg-muted/50 text-muted-foreground">
              <tr>
                {columns.map((col) => (
                  <th key={col} className="whitespace-nowrap px-3 py-2 font-medium">{toHeaderLabel(col)}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {report.items.map((row, idx) => (
                <tr key={idx} className="hover:bg-muted/30">
                  {columns.map((col) => (
                    <td key={col} className="whitespace-nowrap px-3 py-2 text-foreground">{String(row[col] ?? '—')}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {report.insights.length > 0 && (
        <div className="space-y-1.5">
          <p className="flex items-center gap-1.5 text-xs font-medium text-primary">
            <Sparkles className="h-3.5 w-3.5" /> Key insights
          </p>
          <ul className="space-y-1 pl-1">
            {report.insights.map((insight, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-muted-foreground">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary/60" />
                <span>{insight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
