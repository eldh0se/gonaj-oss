import { useEffect, useRef, useState } from "react";
import { postFeedback } from "../api/feedback.js";

const MAX_MESSAGE_CHARS = 2000;

// One shared report dialog for every entry point (017 FR-001…FR-005).
// Context arrives as chips; the map behind never changes. No new route,
// no tracking — submit returns a receipt-only reference.
function chipsFromContext(context = {}) {
  const chips = [];
  if (context.route) {
    chips.push({ kind: "route", id: context.route.id, name: context.route.name });
  }
  if (context.stop) {
    chips.push({ kind: "stop", id: context.stop.id, name: context.stop.name });
  }
  if (context.journey) {
    const { from_name, to_name, question } = context.journey;
    const ends = [from_name, to_name].filter(Boolean).join(" → ");
    chips.push({
      kind: "journey",
      name: ends ? `Journey: ${ends}` : "Journey",
      journey: { from_name, to_name, question },
    });
  }
  return chips;
}

function chipLabel(chip) {
  if (chip.kind === "route") return `Route: ${chip.name}`;
  if (chip.kind === "stop") return `Stop: ${chip.name}`;
  return chip.name;
}

export default function ReportDialog({ open, context, onClose }) {
  const [chips, setChips] = useState(() => chipsFromContext(context));
  const [category, setCategory] = useState("");
  const [message, setMessage] = useState("");
  const [formError, setFormError] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [pending, setPending] = useState(false);
  const [receipt, setReceipt] = useState(null);
  const dialogRef = useRef(null);
  const invokerRef = useRef(null);
  const pendingRef = useRef(false);

  // Reset per opening; remember the invoker for focus return.
  useEffect(() => {
    if (!open) return undefined;
    invokerRef.current = document.activeElement;
    setChips(chipsFromContext(context));
    setCategory("");
    setMessage("");
    setFormError("");
    setSubmitError("");
    setPending(false);
    pendingRef.current = false;
    setReceipt(null);
    const frame = requestAnimationFrame(() => dialogRef.current?.focus());
    return () => {
      cancelAnimationFrame(frame);
      invokerRef.current?.focus?.();
    };
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  // Esc closes unless a submit is in flight.
  useEffect(() => {
    if (!open) return undefined;
    function onKey(event) {
      if (event.key === "Escape" && !pendingRef.current) onClose?.();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  function removeChip(index) {
    setChips((current) => current.filter((_, i) => i !== index));
  }

  function receiptText(reference) {
    return (
      `Thanks — your report ${reference} is received. ` +
      "It is not verified yet. Reporting is anonymous with no tracking. " +
      "Please save your reference for your records; there is no lookup."
    );
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (pendingRef.current) return;
    const text = message.trim();
    if (!category) {
      setFormError("Please choose a category.");
      return;
    }
    if (text.length < 1) {
      setFormError("Please write a message describing the issue.");
      return;
    }
    if (text.length > MAX_MESSAGE_CHARS) {
      setFormError("Please keep the message to 2000 characters or fewer.");
      return;
    }
    setFormError("");
    setSubmitError("");
    pendingRef.current = true;
    setPending(true);
    const routeChip = chips.find((chip) => chip.kind === "route");
    const stopChip = chips.find((chip) => chip.kind === "stop");
    const journeyChip = chips.find((chip) => chip.kind === "journey");
    try {
      const data = await postFeedback({
        category,
        message: text,
        routeId: routeChip?.id,
        stopId: stopChip?.id,
        journey: journeyChip?.journey,
      });
      setReceipt({ reference: data.reference, text: data.receipt ?? receiptText(data.reference) });
    } catch (err) {
      setSubmitError(err?.detail ?? err?.message ?? "Your report could not be saved. Please try again later.");
    } finally {
      pendingRef.current = false;
      setPending(false);
    }
  }

  function handleBackdropClick(event) {
    if (event.target === event.currentTarget && !pendingRef.current) onClose?.();
  }

  return (
    <div
      className="gonaj-feedback-scrim"
      onClick={handleBackdropClick}
      data-testid="feedback-scrim"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Report an issue"
        tabIndex={-1}
        className="gonaj-feedback-dialog"
      >
        <h2>Report an issue</h2>
        {receipt ? (
          <div data-testid="feedback-receipt">
            <p role="status" className="gonaj-feedback-reference">
              {receipt.reference}
            </p>
            <p>{receipt.text}</p>
            <button type="button" onClick={onClose}>
              Close
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            {chips.length > 0 && (
              <ul className="gonaj-feedback-chips">
                {chips.map((chip, index) => (
                  <li key={`${chip.kind}-${chip.id ?? chip.name}`}>
                    <span>{chipLabel(chip)}</span>
                    <button
                      type="button"
                      aria-label={`Remove ${chipLabel(chip)}`}
                      onClick={() => removeChip(index)}
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <label htmlFor="gonaj-feedback-category">Category</label>
            <select
              id="gonaj-feedback-category"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              <option value="">Choose a category</option>
              <option value="incorrect">Incorrect</option>
              <option value="missing">Missing</option>
              <option value="outdated">Outdated</option>
              <option value="other">Other</option>
            </select>
            <label htmlFor="gonaj-feedback-message">Message</label>
            <textarea
              id="gonaj-feedback-message"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              rows={4}
              placeholder="Describe what is wrong"
            />
            <p className="gonaj-feedback-count" aria-hidden="true">
              {message.length}/{MAX_MESSAGE_CHARS}
            </p>
            {formError && <p role="alert">{formError}</p>}
            {submitError && (
              <p role="alert">
                {submitError}{" "}
                <button
                  type="submit"
                  disabled={pending}
                  data-testid="feedback-retry"
                >
                  Retry
                </button>
              </p>
            )}
            <div className="gonaj-feedback-actions">
              <button type="submit" disabled={pending}>
                {pending ? "Sending…" : "Send report"}
              </button>
              <button type="button" onClick={onClose} disabled={pending}>
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
