import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import type {
  PortfolioDashboard,
  PositionCreate,
  PositionUpdate,
  Position,
  IBStatus,
} from "../types";

const api = axios.create({ baseURL: "/api/v1" });

// ─── Portfolio dashboard ─────────────────────────────────────────────────────

export function usePortfolioDashboard(portfolioValue?: number, cashBalance?: number) {
  const [data, setData] = useState<PortfolioDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, number> = {};
      if (portfolioValue !== undefined) params.portfolio_value = portfolioValue;
      if (cashBalance !== undefined) params.cash_balance = cashBalance;
      const res = await api.get<PortfolioDashboard>("/portfolio/dashboard", { params });
      setData(res.data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to fetch portfolio");
    } finally {
      setLoading(false);
    }
  }, [portfolioValue, cashBalance]);

  useEffect(() => { void fetch(); }, [fetch]);

  return { data, loading, error, refetch: fetch };
}

// ─── Positions CRUD ──────────────────────────────────────────────────────────

export function usePositions() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPositions = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<Position[]>("/portfolio/positions");
      setPositions(res.data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void fetchPositions(); }, [fetchPositions]);

  const createPosition = useCallback(async (payload: PositionCreate): Promise<Position> => {
    const res = await api.post<Position>("/portfolio/positions", payload);
    await fetchPositions();
    return res.data;
  }, [fetchPositions]);

  const updatePosition = useCallback(async (id: number, payload: PositionUpdate): Promise<Position> => {
    const res = await api.patch<Position>(`/portfolio/positions/${id}`, payload);
    await fetchPositions();
    return res.data;
  }, [fetchPositions]);

  const deletePosition = useCallback(async (id: number): Promise<void> => {
    await api.delete(`/portfolio/positions/${id}`);
    await fetchPositions();
  }, [fetchPositions]);

  return { positions, loading, refetch: fetchPositions, createPosition, updatePosition, deletePosition };
}

// ─── IB connection ───────────────────────────────────────────────────────────

export function useIBConnection() {
  const [status, setStatus] = useState<IBStatus | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await api.get<IBStatus>("/portfolio/ib/status");
      setStatus(res.data);
    } catch {
      setStatus({ connected: false, host: "", port: 0, message: "Backend unreachable" });
    }
  }, []);

  useEffect(() => { void fetchStatus(); }, [fetchStatus]);

  const connect = useCallback(async () => {
    const res = await api.post<IBStatus>("/portfolio/ib/connect");
    setStatus(res.data);
    return res.data;
  }, []);

  const disconnect = useCallback(async () => {
    const res = await api.post<IBStatus>("/portfolio/ib/disconnect");
    setStatus(res.data);
    return res.data;
  }, []);

  const sync = useCallback(async () => {
    const res = await api.post<{ synced_count: number }>("/portfolio/ib/sync");
    return res.data;
  }, []);

  const refreshPrices = useCallback(async () => {
    const res = await api.post<{ updated: number }>("/portfolio/refresh-prices");
    return res.data;
  }, []);

  return { status, fetchStatus, connect, disconnect, sync, refreshPrices };
}
