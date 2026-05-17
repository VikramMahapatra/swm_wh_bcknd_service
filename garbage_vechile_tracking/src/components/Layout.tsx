import { ReactNode, useEffect, useRef, useState } from 'react';
import { SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar';
import { AppSidebar } from '@/components/AppSidebar';
import Header from '@/components/Header';
import { useScrollPreservation } from '@/hooks/useScrollPreservation';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const mainContentRef = useRef<HTMLElement>(null);
  const [isScrolled, setIsScrolled] = useState(false);
  useScrollPreservation(mainContentRef);

  useEffect(() => {
    const container = mainContentRef.current;
    if (!container) return;

    const handleScroll = () => {
      setIsScrolled(container.scrollTop > 0);
    };

    handleScroll();
    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <SidebarProvider>
      <div className="h-screen flex w-full bg-background">
        <AppSidebar />
        <div className="flex-1 flex flex-col w-full overflow-hidden">
          <div
            className={
              "sticky top-0 z-30 border-b border-border/40 bg-gradient-to-r from-emerald-50/70 via-background/80 to-amber-50/60 backdrop-blur transition-shadow supports-[backdrop-filter]:bg-background/60 " +
              (isScrolled ? "shadow-sm" : "shadow-none")
            }
          >
            <div className="flex h-14 items-center px-4 gap-4">
              <SidebarTrigger />
              <Header />
            </div>
          </div>
          <main 
            ref={mainContentRef}
            className="flex-1 overflow-auto app-surface"
            style={{ overflowAnchor: 'none' }}
          >
            {children}
          </main>
        </div>
      </div>
    </SidebarProvider>
  );
}
