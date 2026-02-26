import { useState } from "react";
import type { Position, PositionCreate, InstrumentType } from "../../types";
import axios from "axios";

const api = axios.create({ baseURL: "/api/v1" });

const INSTRUMENT_TYPES: InstrumentType[] = [
  "stock", "call_option", "put_option", "call_warrant", "put_warrant", "turbo_long", "turbo_short",
];

interface Props {
  position: Position | null; // null = create, non-null = edit
  onSubmit: () => Promise<void>;
  onCancel: () => void;
}

export default function PositionForm({ position, onSubmit, onCancel }: Props) {
  const isEdit = position !== null;
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [ticker, setTicker] = useState(position?.ticker ?? "");
  const [instrumentType, setInstrumentType] = useState<InstrumentType>(
    (position?.instrument_type as InstrumentType) ?? "stock"
  );
  const [quantity, setQuantity] = useState(String(position?.quantity ?? ""));
  const [avgCost, setAvgCost] = useState(position?.avg_cost != null ? String(position.avg_cost) : "");
  const [marketPrice, setMarketPrice] = useState(position?.market_price != null ? String(position.market_price) : "");
  const [currency, setCurrency] = useState(position?.currency ?? "USD");
  const [strike, setStrike] = useState(position?.strike != null ? String(position.strike) : "");
  const [expiry, setExpiry] = useState(position?.expiry ?? "");
  const [optionType, setOptionType] = useState(position?.option_type ?? "");
  const [sector, setSector] = useState(position?.sector ?? "");
  const [notes, setNotes] = useState(position?.notes ?? "");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!ticker.trim()) { setFormError("Ticker is required"); return; }
    if (!quantity || Number(quantity) === 0) { setFormError("Quantity is required"); return; }

    setSubmitting(true);
    try {
      if (isEdit) {
        await api.patch(`/portfolio/positions/${position.id}`, {
          quantity: Number(quantity),
          avg_cost: avgCost ? Number(avgCost) : undefined,
          market_price: marketPrice ? Number(marketPrice) : undefined,
          sector: sector || undefined,
          notes: notes || undefined,
        });
      } else {
        const payload: PositionCreate = {
          ticker: ticker.toUpperCase().trim(),
          instrument_type: instrumentType,
          quantity: Number(quantity),
          avg_cost: avgCost ? Number(avgCost) : undefined,
          market_price: marketPrice ? Number(marketPrice) : undefined,
          currency,
          strike: strike ? Number(strike) : undefined,
          expiry: expiry || undefined,
          option_type: optionType || undefined,
          sector: sector || undefined,
          notes: notes || undefined,
        };
        await api.post("/portfolio/positions", payload);
      }
      await onSubmit();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Failed to save position");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {formError && <div className="alert-danger">{formError}</div>}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <label className="label">Ticker *</label>
          <input className="input" value={ticker} onChange={(e) => setTicker(e.target.value)} disabled={isEdit} />
        </div>
        <div>
          <label className="label">Type *</label>
          <select className="input" value={instrumentType} onChange={(e) => setInstrumentType(e.target.value as InstrumentType)} disabled={isEdit}>
            {INSTRUMENT_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Quantity *</label>
          <input className="input" type="number" step="0.01" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
        </div>
        <div>
          <label className="label">Avg Cost</label>
          <input className="input" type="number" step="0.0001" value={avgCost} onChange={(e) => setAvgCost(e.target.value)} />
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <label className="label">Market Price</label>
          <input className="input" type="number" step="0.0001" value={marketPrice} onChange={(e) => setMarketPrice(e.target.value)} />
        </div>
        <div>
          <label className="label">Currency</label>
          <select className="input" value={currency} onChange={(e) => setCurrency(e.target.value)}>
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
          </select>
        </div>
        <div>
          <label className="label">Sector</label>
          <input className="input" value={sector} onChange={(e) => setSector(e.target.value)} placeholder="Technology" />
        </div>
        <div>
          <label className="label">Strike</label>
          <input className="input" type="number" step="0.01" value={strike} onChange={(e) => setStrike(e.target.value)} />
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <label className="label">Expiry</label>
          <input className="input" type="date" value={expiry} onChange={(e) => setExpiry(e.target.value)} />
        </div>
        <div>
          <label className="label">Option Type</label>
          <select className="input" value={optionType} onChange={(e) => setOptionType(e.target.value)}>
            <option value="">—</option>
            <option value="CALL">CALL</option>
            <option value="PUT">PUT</option>
          </select>
        </div>
        <div className="col-span-2">
          <label className="label">Notes</label>
          <input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>

      <div className="flex gap-3">
        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? "Saving..." : isEdit ? "Update Position" : "Add Position"}
        </button>
        <button type="button" className="btn-ghost" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}
