import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, CheckCircle2, Clock3, Lock, MapPinned, Mail, Route, ShieldCheck, Truck } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { ApiError } from '@/services/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

function FleetBackdrop() {
  return (
    <div className="absolute inset-0 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,hsl(var(--primary)/0.18),transparent_32%),radial-gradient(circle_at_85%_15%,hsl(var(--secondary)/0.14),transparent_26%),linear-gradient(180deg,hsl(var(--background))_0%,hsl(var(--muted)/0.62)_100%)]" />

      <div className="absolute inset-0 opacity-[0.28] [background-image:linear-gradient(hsl(var(--foreground)/0.08)_1px,transparent_1px),linear-gradient(90deg,hsl(var(--foreground)/0.08)_1px,transparent_1px)] [background-size:72px_72px]" />

      <svg
        className="absolute left-[52%] top-[50%] h-[48rem] w-[48rem] -translate-x-1/2 -translate-y-1/2 opacity-55"
        viewBox="0 0 960 960"
        fill="none"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="fleet-route" x1="160" y1="180" x2="820" y2="780" gradientUnits="userSpaceOnUse">
            <stop stopColor="hsl(var(--primary))" stopOpacity="0.95" />
            <stop offset="1" stopColor="hsl(var(--secondary))" stopOpacity="0.9" />
          </linearGradient>
          <linearGradient id="fleet-halo" x1="0" y1="0" x2="1" y2="1">
            <stop stopColor="hsl(var(--primary))" stopOpacity="0.34" />
            <stop offset="1" stopColor="hsl(var(--secondary))" stopOpacity="0.06" />
          </linearGradient>
        </defs>

        <circle cx="480" cy="480" r="250" stroke="url(#fleet-halo)" strokeWidth="42" />
        <circle cx="480" cy="480" r="168" stroke="hsl(var(--foreground)/0.08)" strokeWidth="1" />
        <circle cx="480" cy="480" r="270" stroke="hsl(var(--foreground)/0.05)" strokeWidth="1" strokeDasharray="6 10" />

        <path
          d="M165 266C278 194 380 205 463 280C547 356 636 385 772 330"
          stroke="url(#fleet-route)"
          strokeWidth="14"
          strokeLinecap="round"
        />
        <path
          d="M186 622C295 558 386 543 482 602C579 662 659 684 796 638"
          stroke="hsl(var(--foreground)/0.15)"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray="8 14"
        />
        <path
          d="M250 356C330 322 414 330 492 385C560 433 645 455 724 438"
          stroke="hsl(var(--primary)/0.24)"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray="4 10"
        />

        <circle cx="165" cy="266" r="18" fill="hsl(var(--background))" stroke="hsl(var(--primary))" strokeWidth="6" />
        <circle cx="463" cy="280" r="16" fill="hsl(var(--background))" stroke="hsl(var(--secondary))" strokeWidth="6" />
        <circle cx="772" cy="330" r="18" fill="hsl(var(--background))" stroke="hsl(var(--primary))" strokeWidth="6" />
        <circle cx="186" cy="622" r="16" fill="hsl(var(--background))" stroke="hsl(var(--secondary))" strokeWidth="6" />
        <circle cx="482" cy="602" r="16" fill="hsl(var(--background))" stroke="hsl(var(--primary))" strokeWidth="6" />
        <circle cx="796" cy="638" r="18" fill="hsl(var(--background))" stroke="hsl(var(--secondary))" strokeWidth="6" />

        <rect x="336" y="402" width="288" height="164" rx="28" fill="hsl(var(--card)/0.72)" stroke="hsl(var(--foreground)/0.08)" />
        <rect x="366" y="430" width="108" height="18" rx="9" fill="hsl(var(--foreground)/0.12)" />
        <rect x="366" y="462" width="126" height="16" rx="8" fill="hsl(var(--foreground)/0.08)" />
        <rect x="366" y="498" width="94" height="16" rx="8" fill="hsl(var(--foreground)/0.08)" />
        <rect x="522" y="430" width="70" height="70" rx="20" fill="hsl(var(--primary)/0.8)" />
        <rect x="522" y="514" width="70" height="18" rx="9" fill="hsl(var(--secondary)/0.65)" />
        <circle cx="476" cy="530" r="18" fill="hsl(var(--foreground)/0.75)" />
        <circle cx="574" cy="530" r="18" fill="hsl(var(--foreground)/0.75)" />

        <path d="M364 552h222" stroke="hsl(var(--foreground)/0.08)" strokeWidth="2" />
        <path d="M364 573h126" stroke="hsl(var(--foreground)/0.08)" strokeWidth="2" />

        <g opacity="0.55">
          <path d="M74 188h102" stroke="hsl(var(--foreground)/0.12)" strokeWidth="2" />
          <path d="M74 188v102" stroke="hsl(var(--foreground)/0.12)" strokeWidth="2" />
          <path d="M884 770h-102" stroke="hsl(var(--foreground)/0.12)" strokeWidth="2" />
          <path d="M884 770v-102" stroke="hsl(var(--foreground)/0.12)" strokeWidth="2" />
        </g>
      </svg>

      <div className="absolute left-[7%] top-[12%] hidden h-52 w-52 rounded-full border border-primary/15 bg-primary/5 blur-[2px] md:block" />
      <div className="absolute right-[10%] top-[20%] hidden h-36 w-36 rounded-full border border-secondary/20 bg-secondary/10 blur-[1px] md:block" />
      <div className="absolute bottom-[10%] left-[14%] hidden h-32 w-32 rounded-full border border-success/20 bg-success/10 blur-[1px] md:block" />
    </div>
  );
}

export default function Auth() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorOpen, setErrorOpen] = useState(false);
  const [errorTitle, setErrorTitle] = useState('Login failed');
  const [errorMessage, setErrorMessage] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const showLoginError = (title: string, message: string) => {
    setErrorTitle(title);
    setErrorMessage(message);
    setErrorOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedUsername = username.trim();
    const trimmedPassword = password.trim();
    if (!trimmedUsername || !trimmedPassword) {
      showLoginError('Missing details', 'Please enter both username and password.');
      return;
    }

    setIsLoading(true);

    try {
      await login(trimmedUsername, trimmedPassword, 'user');
      navigate('/');
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 401) {
          showLoginError('Invalid credentials', 'The username or password is incorrect. Please try again.');
        } else if (error.status === 422) {
          showLoginError('Validation error', error.message || 'Please check your login details and try again.');
        } else {
          showLoginError('Login failed', error.message || 'Unable to sign in right now. Please try again.');
        }
      } else if (error instanceof Error) {
        showLoginError('Login failed', error.message || 'Unable to sign in right now. Please try again.');
      } else {
        showLoginError('Login failed', 'Unable to sign in right now. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <Dialog open={errorOpen} onOpenChange={setErrorOpen}>
        <DialogContent className="overflow-hidden border-border/70 bg-card/95 p-0 shadow-[0_30px_90px_-24px_hsl(var(--foreground)/0.55)] sm:max-w-md">
          <div className="h-1 bg-gradient-to-r from-destructive via-warning to-primary" />
          <div className="grid gap-5 p-6">
            <DialogHeader className="text-left">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-destructive/10 text-destructive ring-1 ring-destructive/15">
                  <AlertCircle className="h-6 w-6" />
                </div>
                <div className="space-y-1">
                  <DialogTitle className="text-xl">{errorTitle}</DialogTitle>
                  <DialogDescription className="text-sm leading-6 text-muted-foreground">
                    {errorMessage}
                  </DialogDescription>
                </div>
              </div>
            </DialogHeader>

            <div className="grid gap-3 rounded-xl border border-border/70 bg-muted/40 p-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-2 text-foreground">
                <ShieldCheck className="h-4 w-4 text-success" />
                Check your username and password carefully.
              </div>
              <div className="flex items-center gap-2">
                <Clock3 className="h-4 w-4 text-primary" />
                If the issue continues, confirm the account is active.
              </div>
            </div>

            <DialogFooter className="sm:justify-end">
              <Button type="button" onClick={() => setErrorOpen(false)} className="sm:min-w-24">
                OK
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>

      <div className="relative min-h-screen overflow-hidden">
        <FleetBackdrop />

        <main className="relative z-10 grid min-h-screen items-center px-4 py-8 md:px-8 lg:grid-cols-[1.1fr_0.9fr] lg:px-12">
          <section className="hidden max-w-2xl flex-col gap-8 lg:flex">
            <div className="inline-flex w-fit items-center gap-2 rounded-full border border-border/70 bg-card/80 px-4 py-2 text-sm text-muted-foreground shadow-sm backdrop-blur">
              <Route className="h-4 w-4 text-primary" />
              Fleet operations command center
            </div>

            <div className="space-y-5">
              <h1 className="max-w-xl text-5xl font-semibold tracking-tight text-foreground">
                Command every truck from a single control point.
              </h1>
              <p className="max-w-lg text-base leading-7 text-muted-foreground">
                Sign in to monitor active, idle, and moving vehicles, review zone and ward coverage, and follow live GPS movement as it happens.
              </p>
            </div>

            <div className="grid max-w-xl grid-cols-3 gap-4">
              <div className="rounded-2xl border border-border/70 bg-card/85 p-4 shadow-sm backdrop-blur">
                <Truck className="mb-3 h-5 w-5 text-primary" />
                <div className="text-sm font-medium">Fleet status</div>
                <div className="mt-1 text-xs text-muted-foreground">Active, inactive, and idle counts at a glance.</div>
              </div>
              <div className="rounded-2xl border border-border/70 bg-card/85 p-4 shadow-sm backdrop-blur">
                <MapPinned className="mb-3 h-5 w-5 text-secondary" />
                <div className="text-sm font-medium">Geo context</div>
                <div className="mt-1 text-xs text-muted-foreground">Zones, wards, routes, and coordinates together.</div>
              </div>
              <div className="rounded-2xl border border-border/70 bg-card/85 p-4 shadow-sm backdrop-blur">
                <CheckCircle2 className="mb-3 h-5 w-5 text-success" />
                <div className="text-sm font-medium">Live updates</div>
                <div className="mt-1 text-xs text-muted-foreground">Current positions and movement snapshots in realtime.</div>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <div className="rounded-full border border-border/70 bg-card/80 px-4 py-2 text-sm text-muted-foreground backdrop-blur">
                Route visibility
              </div>
              <div className="rounded-full border border-border/70 bg-card/80 px-4 py-2 text-sm text-muted-foreground backdrop-blur">
                Ward coverage
              </div>
              <div className="rounded-full border border-border/70 bg-card/80 px-4 py-2 text-sm text-muted-foreground backdrop-blur">
                Device assignment
              </div>
            </div>
          </section>

          <section className="mx-auto w-full max-w-md lg:justify-self-end">
            <Card className="overflow-hidden border-border/70 bg-card/90 shadow-[0_24px_80px_-28px_hsl(var(--foreground)/0.5)] backdrop-blur-xl">
              <div className="h-1 bg-gradient-to-r from-primary via-secondary to-success" />
              <CardHeader className="space-y-3 pt-8 text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/15">
                  <Truck className="h-8 w-8 text-primary" />
                </div>
                <CardTitle className="text-2xl">Fleet Tracking System</CardTitle>
                <CardDescription className="leading-6">
                  Municipal garbage truck GPS tracking and live fleet visibility.
                </CardDescription>
              </CardHeader>
              <CardContent className="pb-8">
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="username">Username</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="username"
                        type="text"
                        placeholder="admin"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        className="pl-10"
                        autoComplete="username"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="password"
                        type="password"
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="pl-10"
                        autoComplete="current-password"
                        required
                      />
                    </div>
                  </div>

                  <Button type="submit" className="w-full shadow-sm" disabled={isLoading}>
                    {isLoading ? 'Signing in...' : 'Sign In'}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </section>
        </main>

        <div className="pointer-events-none absolute inset-x-0 bottom-0 z-[2] h-24 bg-gradient-to-t from-background via-background/70 to-transparent" />
      </div>
    </>
  );
}
