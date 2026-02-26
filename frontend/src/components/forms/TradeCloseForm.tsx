import { useState } from "react";
import type { Trade, TradeClose, ExitReason, EmotionalState } from "../../types";

const EXIT_REASONS: ExitReason[] = [
  "profit_target", "stop_loss", "time_stop", "thesis_invalidated",
  "trailing_stop", "manual", "expiry",
];
const EMOTIONAL_STATES: EmotionalState[] = ["calm", "anxious", "excited", "revenge", "fomo", "confident"];

interface Props {
  trade: Trade;
  onSubmit: (payload: TradeClose) => Promise<void>;
  onCancel: () => void;
}

export default function TradeCloseForm({ trade, onSubmit, onCancel }: Props) {
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [exitPrice, setExitPrice] = useState("");
  const [feesExit, setFeesExit] = useState("0");
  const [exitReason, setExitReason] = useState<ExitReason>("manual");
  const [emotionalStateExit, setEmotionalStateExit] = useState<EmotionalState>("calm");
  const [notesWorked, setNotesWorked] = useState("");
  const [notesFailed, setNotesFailed] = useState("");
  const [lessonsLearned, setLessonsLearned] = useState("");
  const [wouldTakeAgain, setWouldTakeAgain] = useState<boolean | undefined>(undefined);
  const [mfe, setMfe] = useState("");
  const [mae, setMae] = useState("");

  // Preview P&L
  const previewPnl = exitPrice
    ? (() => {
        const ep = Number(exitPrice);
        const isShort = ["turbo_short", "put_option", "put_warrant"].includes(trade.instrument_type);
        const dir = isShort ? -1 : 1;
        const gross = (ep - trade.entry_price) * trade.quantity * dir;
        const net = gross - (trade.fees_entry ?? 0) - Number(feesExit || 0);
        return { gross: gross.toFixed(2), net: net.toFixed(2), positive: net >= 0 };
      })()
    : null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);

    if (!exitPrice || Number(exitPrice) <= 0) { setFormError("Exit price is required"); return; }

    const payload: TradeClose = {
      exit_price: Number(exitPrice),
      fees_exit: Number(feesExit) || 0,
      exit_reason: exitReason,
      emotional_state_exit: emotionalStateExit,
      notes_what_worked: notesWorked || undefined,
      notes_what_didnt: notesFailed || undefined,
      lessons_learned: lessonsLearned || undefined,
      would_take_again: wouldTakeAgain,
      max_favorable_excursion: mfe ? Number(mfe) : undefined,
      max_adverse_excursion: mae ? Number(mae) : undefined,
    };

    setSubmitting(true);
    try {
      await onSubmit(payload);
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Failed to close trade");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {formError && <div className="alert-danger">{formError}</div>}

      {/* Trade summary */}
      <div className="text-sm text-muted space-y-1">
        <p>Entry: <span className="font-mono text-bright">{trade.entry_price}</span> x {trade.quantity} ({trade.currency})</p>
        {trade.profit_target_pct && <p>Target: +{String(trade.profit_target_pct)}%</p>}
        {trade.stop_loss_pct && <p>Stop: -{String(trade.stop_loss_pct)}%</p>}
      </div>

      {/* Exit price + P&L preview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <label className="label">Exit Price *</label>
          <input className="input" type="number" step="0.0001" value={exitPrice} onChange={(e) => setExitPrice(e.target.value)} required />
        </div>
        <div>
          <label className="label">Fees</label>
          <input className="input" type="number" step="0.01" value={feesExit} onChange={(e) => setFeesExit(e.target.value)} />
        </div>
        <div>
          <label className="label">Exit Reason *</label>
          <select className="input" value={exitReason} onChange={(e) => setExitReason(e.target.value as ExitReason)}>
            {EXIT_REASONS.map((r) => <option key={r} value={r}>{r.replace(/_/g, " ")}</option>)}
          </select>
        </div>
        {previewPnl && (
          <div className="flex flex-col justify-end">
            <span className="label">Est. Net P&L</span>
            <span className={`metric-value text-lg ${previewPnl.positive ? "text-profit" : "text-loss"}`}>
              €{previewPnl.net}
            </span>
          </div>
        )}
      </div>

      {/* Emotional state */}
      <div>
        <label className="label">Emotional State at Exit</label>
        <div className="flex gap-2 flex-wrap">
          {EMOTIONAL_STATES.map((state) => (
            <button
              key={state}
              type="button"
              className={`badge cursor-pointer transition-colors ${
                emotionalStateExit === state
                  ? "bg-info/30 text-info ring-1 ring-info"
                  : "bg-surface-2 text-muted hover:text-bright"
              }`}
              onClick={() => setEmotionalStateExit(state)}
            >
              {state}
            </button>
          ))}
        </div>
      </div>

      {/* Post-trade analysis */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="label">What worked?</label>
          <textarea className="input" rows={2} value={notesWorked} onChange={(e) => setNotesWorked(e.target.value)} />
        </div>
        <div>
          <label className="label">What didn't work?</label>
          <textarea className="input" rows={2} value={notesFailed} onChange={(e) => setNotesFailed(e.target.value)} />
        </div>
      </div>
      <div>
        <label className="label">Lessons Learned</label>
        <textarea className="input" rows={2} value={lessonsLearned} onChange={(e) => setLessonsLearned(e.target.value)} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <label className="label">Would Take Again?</label>
          <select
            className="input"
            value={wouldTakeAgain === undefined ? "" : wouldTakeAgain ? "yes" : "no"}
            onChange={(e) => setWouldTakeAgain(e.target.value === "" ? undefined : e.target.value === "yes")}
          >
            <option value="">—</option>
            <option value="yes">Yes</option>
            <option value="no">No</option>
          </select>
        </div>
        <div>
          <label className="label">Max Favorable Excursion</label>
          <input className="input" type="number" step="0.01" value={mfe} onChange={(e) => setMfe(e.target.value)} />
        </div>
        <div>
          <label className="label">Max Adverse Excursion</label>
          <input className="input" type="number" step="0.01" value={mae} onChange={(e) => setMae(e.target.value)} />
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? "Closing..." : "Close Trade"}
        </button>
        <button type="button" className="btn-ghost" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
