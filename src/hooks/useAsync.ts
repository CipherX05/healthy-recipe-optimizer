import { useEffect, useState } from 'react';

interface Settled<T> {
  run: unknown;
  data: T | null;
  error: string | null;
}

/**
 * Runs `run` whenever its identity changes (wrap it in useCallback); pass null
 * to stay idle. Older requests are aborted. The last data stays available while
 * the next request loads, so the page does not jump.
 */
export function useAsync<T>(run: ((signal: AbortSignal) => Promise<T>) | null) {
  const [state, setState] = useState<Settled<T>>({ run: null, data: null, error: null });

  useEffect(() => {
    if (!run) return;
    const controller = new AbortController();
    run(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) setState({ run, data, error: null });
      },
      (error: unknown) => {
        if (!controller.signal.aborted) {
          setState({ run, data: null, error: error instanceof Error ? error.message : String(error) });
        }
      },
    );
    return () => controller.abort();
  }, [run]);

  const current = state.run === run;
  return {
    data: run ? state.data : null,
    error: run && current ? state.error : null,
    loading: run !== null && !current,
  };
}
