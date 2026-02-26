import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import type { Trade, TradeCreate, TradeClose, DashboardData, RuleChecklistItem } from "../types";

const api = axios.create({ baseURL: "/api/v1" });

// ─── Trades ───────────────────────────────────────────────────────────────────

export function useTrades(filters?: {
  status?: string;
  ticker?: string;
  limit?: number;
}) {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTrades = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number> = {};
      if (filters?.status) params.status = filters.status;
      if (filters?.ticker) params.ticker = filters.ticker;
      if (filters?.limit) params.limit = filters.limit;
      const res = await api.get<Trade[]>("/trades", { params });
      setTrades(res.data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to fetch trades");
    } finally {
      setLoading(false);
    }
  }, [filters?.status, filters?.ticker, filters?.limit]);

  useEffect(() => { void fetchTrades(); }, [fetchTrades]);

  const createTrade = useCallback(async (payload: TradeCreate): Promise<Trade> => {
    const res = await api.post<Trade>("/trades", payload);
    await fetchTrades();
    return res.data;
  }, [fetchTrades]);

  const closeTrade = useCallback(async (id: number, payload: TradeClose): Promise<Trade> => {
    const res = await api.post<Trade>(`/trades/${id}/close`, payload);
    await fetchTrades();
    return res.data;
  }, [fetchTrades]);

  const deleteTrade = useCallback(async (id: number): Promise<void> => {
    await api.delete(`/trades/${id}`);
    await fetchTrades();
  }, [fetchTrades]);

  return { trades, loading, error, refetch: fetchTrades, createTrade, closeTrade, deleteTrade };
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export function useDashboard(portfolioValue?: number, cashBalance?: number) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, number> = {};
      if (portfolioValue !== undefined) params.portfolio_value = portfolioValue;
      if (cashBalance !== undefined) params.cash_balance = cashBalance;
      const res = await api.get<DashboardData>("/dashboard", { params });
      setData(res.data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to fetch dashboard");
    } finally {
      setLoading(false);
    }
  }, [portfolioValue, cashBalance]);

  useEffect(() => { void fetch(); }, [fetch]);

  return { data, loading, error, refetch: fetch };
}

// ─── Rule checklist ───────────────────────────────────────────────────────────

export function useRuleChecklist() {
  const [checklist, setChecklist] = useState<RuleChecklistItem[]>([]);

  useEffect(() => {
    api.get<{ checklist: RuleChecklistItem[] }>("/dashboard/rule-checklist")
      .then(res => setChecklist(res.data.checklist))
      .catch(() => {});
  }, []);

  return checklist;
}
