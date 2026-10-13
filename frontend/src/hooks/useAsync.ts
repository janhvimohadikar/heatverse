import { useCallback, useEffect, useState } from "react";

interface State<T> { data: T | null; loading: boolean; error: string | null; }

/** Run an async function when `deps` change. Ignores results from outdated calls. */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[], enabled = true) {
  const [state, setState] = useState<State<T>>({ data: null, loading: enabled, error: null });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!enabled) {
      setState({ data: null, loading: false, error: null });
      return;
    }
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));
    fn()
      .then((data) => { if (!cancelled) setState({ data, loading: false, error: null }); })
      .catch((e: unknown) => {
        if (cancelled) return;
        if (e instanceof DOMException && e.name === "AbortError") return;
        setState({ data: null, loading: false, error: e instanceof Error ? e.message : String(e) });
      });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick, enabled]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}
