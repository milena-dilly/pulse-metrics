/**
 * hooks/useApi.js — Generic data-fetching hook
 * ─────────────────────────────────────────────
 * Wraps any API call with loading / error / data states.
 * Re-fetches when dependencies change (like useEffect).
 *
 * Usage:
 *   const { data, loading, error, refetch } = useApi(fetchKPIs, [month], month);
 */

import { useState, useEffect, useCallback, useRef } from "react";

/**
 * @param {Function} fetcher     - async function that returns data
 * @param {Array}    args        - arguments passed to fetcher
 * @param {Array}    deps        - useEffect dependency array (defaults to args)
 */
export function useApi(fetcher, args = [], deps = args) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  // Track whether component is still mounted
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher(...args);
      if (mountedRef.current) setData(result);
    } catch (err) {
      if (mountedRef.current) setError(err);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => { load(); }, [load]);

  return { data, loading, error, refetch: load };
}

/**
 * Convenience hook that loads multiple API calls in parallel.
 *
 * Usage:
 *   const { results, loading, error } = useApiBatch({
 *     kpis:     () => fetchKPIs(),
 *     revenue:  () => fetchRevenueTrend(from, to),
 *   }, [from, to]);
 */
export function useApiBatch(fetcherMap, deps = []) {
  const [results, setResults] = useState({});
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const entries = Object.entries(fetcherMap);
      const values  = await Promise.all(entries.map(([, fn]) => fn()));
      const mapped  = Object.fromEntries(entries.map(([k], i) => [k, values[i]]));
      setResults(mapped);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => { load(); }, [load]);

  return { results, loading, error, refetch: load };
}
