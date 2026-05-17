import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';

// Store scroll positions per route
const scrollPositions = new Map<string, number>();

export function useScrollPreservation(scrollContainerRef: React.RefObject<HTMLElement>) {
  const location = useLocation();
  const previousPathRef = useRef<string>(location.pathname);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    // Save current scroll position before navigating away
    const handleBeforeUnload = () => {
      scrollPositions.set(previousPathRef.current, container.scrollTop);
    };

    // Restore scroll position when arriving at a route
    const savedPosition = scrollPositions.get(location.pathname);
    if (savedPosition !== undefined) {
      // Use requestAnimationFrame to ensure DOM is ready
      requestAnimationFrame(() => {
        container.scrollTop = savedPosition;
      });
    }

    // Update previous path
    previousPathRef.current = location.pathname;

    // Save scroll on scroll event
    const handleScroll = () => {
      scrollPositions.set(location.pathname, container.scrollTop);
    };

    container.addEventListener('scroll', handleScroll, { passive: true });

    return () => {
      container.removeEventListener('scroll', handleScroll);
      handleBeforeUnload();
    };
  }, [location.pathname, scrollContainerRef]);
}

// Hook to prevent scroll jumping on state updates
export function usePreventScrollJump() {
  useEffect(() => {
    // Add CSS to prevent scroll anchoring issues
    document.documentElement.style.scrollBehavior = 'auto';
    document.documentElement.style.overflowAnchor = 'none';
    
    return () => {
      document.documentElement.style.scrollBehavior = '';
      document.documentElement.style.overflowAnchor = '';
    };
  }, []);
}
