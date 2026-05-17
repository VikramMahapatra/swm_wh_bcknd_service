import { LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface PageHeaderProps {
  category?: string;
  title: string;
  description?: string;
  icon?: LucideIcon;
  badge?: {
    label: string;
    variant?: "default" | "secondary" | "destructive" | "outline";
    className?: string;
  };
  actions?: React.ReactNode;
}

export function PageHeader({
  category,
  title,
  description,
  icon: Icon,
  badge,
  actions,
}: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-4 rounded-xl border border-border/60 bg-card/80 p-4 shadow-sm backdrop-blur sm:flex-row sm:items-center sm:justify-between sm:p-5">
      <div className="space-y-1.5">
        <div className="flex items-center gap-3">
          {Icon && (
            <div className="rounded-lg bg-primary/10 p-2 ring-1 ring-primary/15">
              <Icon className="h-5 w-5 text-primary" />
            </div>
          )}
          <div className="flex items-center gap-2">
            {category && (
              <>
                <span className="rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-widest text-primary/80">
                  {category}
                </span>
                <span className="text-muted-foreground/40">→</span>
              </>
            )}
            <h1 className="text-2xl font-semibold tracking-tight text-transparent bg-gradient-to-r from-primary via-secondary to-emerald-500 bg-clip-text">
              {title}
            </h1>
            {badge && (
              <Badge
                variant={badge.variant || "default"}
                className={badge.className}
              >
                {badge.label}
              </Badge>
            )}
          </div>
        </div>
        {description && (
          <div className={`flex items-center gap-2 text-sm text-muted-foreground ${Icon ? "pl-11" : "pl-0"}`}>
            <span className="h-1.5 w-1.5 rounded-full bg-primary/40" />
            <span>{description}</span>
          </div>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
