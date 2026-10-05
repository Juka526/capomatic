import { useEffect, useRef } from 'react';

/** Handle in-page state first; let the SDK close the mini app at the root. */
export function useTossBack(onBack: () => boolean) {
  const handler = useRef(onBack);
  useEffect(() => { handler.current = onBack; });

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_APP_TARGET !== 'toss') return;
    let disposed = false;
    let unsubscribe: (() => void) | undefined;
    void import('@apps-in-toss/web-framework').then(({ graniteEvent, closeView }) => {
      if (disposed) return;
      unsubscribe = graniteEvent.addEventListener('backEvent', {
        onEvent: () => {
          if (!handler.current()) void closeView().catch(console.error);
        },
        onError: (error) => console.error('Toss navigation failed:', error),
      });
    }).catch(console.error);
    return () => { disposed = true; unsubscribe?.(); };
  }, []);
}
