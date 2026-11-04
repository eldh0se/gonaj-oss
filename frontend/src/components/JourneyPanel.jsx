// Journey helper chat panel (004-journey-agent).
//
// Fills the dock slot reserved by the 005 map page. Talks only to
// the two versioned REST endpoints via api/journey.js — no model
// calls and no model key here. Every AI-assisted answer renders
// distinctly labelled unverified with inline /routes/:id evidence
// links; nothing is stored anywhere.
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { getConnectivity, listStops } from "../api/client.js";
import { postJourney, postTranscribe } from "../api/journey.js";
import { Pager } from "./ResultsList.jsx";

const WAV_SAMPLE_RATE = 24000;

function wavBlob(audioBuffer) {
  const channel = audioBuffer.getChannelData(0);
  const dataSize = channel.length * 2;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);
  const writeString = (offset, text) => {
    for (let i = 0; i < text.length; i += 1) {
      view.setUint8(offset + i, text.charCodeAt(i));
    }
  };
  writeString(0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, audioBuffer.sampleRate, true);
  view.setUint32(28, audioBuffer.sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, dataSize, true);
  for (let i = 0; i < channel.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, channel[i]));
    view.setInt16(
      44 + i * 2,
      sample < 0 ? sample * 0x8000 : sample * 0x7fff,
      true
    );
  }
  return new Blob([buffer], { type: "audio/wav" });
}

async function encodeToWav(blob) {
  const AudioContextClass =
    globalThis.AudioContext || globalThis.webkitAudioContext;
  if (!AudioContextClass || !globalThis.OfflineAudioContext) {
    throw new Error("webaudio-unavailable");
  }
  const sourceContext = new AudioContextClass();
  const raw = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error ?? new Error("read-failed"));
    reader.onload = () => resolve(reader.result);
    reader.readAsArrayBuffer(blob);
  });
  let decoded;
  try {
    decoded = await sourceContext.decodeAudioData(raw);
  } finally {
    if (sourceContext.close) await sourceContext.close().catch(() => {});
  }
  const length = Math.max(
    1,
    Math.ceil(decoded.duration * WAV_SAMPLE_RATE)
  );
  const offline = new globalThis.OfflineAudioContext(
    1,
    length,
    WAV_SAMPLE_RATE
  );
  const source = offline.createBufferSource();
  source.buffer = decoded;
  source.connect(offline.destination);
  source.start(0);
  const rendered = await offline.startRendering();
  return wavBlob(rendered);
}

const CANNOT_ANSWER_NOW =
  "The journey helper cannot answer right now. Please try again later.";

const NO_DIRECT = "I could not find a direct service between those stops.";

function StopPicker({ label, text, onTextChange, selected, onSelect, onClear, disabled }) {
  const [options, setOptions] = useState([]);
  const inputId = `gonaj-journey-${label.toLowerCase().replace(/\s+/g, "-")}`;

  useEffect(() => {
    const query = text.trim();
    if (selected || query.length < 2) {
      setOptions([]);
      return;
    }
    let live = true;
    const timer = setTimeout(async () => {
      try {
        const body = await listStops({ search: query, pageSize: 6 });
        if (live) setOptions(body.results ?? []);
      } catch {
        if (live) setOptions([]);
      }
    }, 300);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [text, selected]);

  return (
    <div className={`gonaj-stop-picker${selected ? " is-picked" : ""}`}>
      <label htmlFor={inputId}>{label}</label>
      <div className="gonaj-stop-field">
        <input
          id={inputId}
          type="text"
          value={text}
          onChange={(event) => onTextChange(event.target.value)}
          placeholder={`Type a stop name`}
          autoComplete="off"
          disabled={disabled}
        />
        {selected && (
          <button
            type="button"
            className="gonaj-stop-clear"
            onClick={onClear}
            aria-label={`Clear ${label}`}
          >
            ×
          </button>
        )}
      </div>
      {options.length > 0 && (
        <ul className="gonaj-journey-candidates gonaj-journey-menu">
          {options.map((stop) => (
            <li key={stop.id}>
              <button type="button" onClick={() => onSelect(stop)}>
                {stop.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function boundsFor(candidates, groups) {
  const points = [];
  for (const c of candidates ?? []) {
    if (typeof c?.lat === "number" && typeof c?.lon === "number") {
      points.push([c.lat, c.lon]);
    }
  }
  for (const g of groups ?? []) {
    const b = g?.bbox;
    if (
      b &&
      typeof b.min_lat === "number" &&
      typeof b.max_lat === "number" &&
      typeof b.min_lon === "number" &&
      typeof b.max_lon === "number"
    ) {
      points.push([b.min_lat, b.min_lon], [b.max_lat, b.max_lon]);
    }
  }
  if (points.length === 0) return null;
  return {
    south: Math.min(...points.map(([lat]) => lat)),
    west: Math.min(...points.map(([, lon]) => lon)),
    north: Math.max(...points.map(([lat]) => lat)),
    east: Math.max(...points.map(([, lon]) => lon)),
  };
}

function JourneyOptionCards({ options, filter, walkNote }) {
  const term = filter.trim().toLowerCase();
  function matches(option) {
    const haystack = [
      option?.route?.name,
      option?.boarding_stop?.name,
      option?.alighting_stop?.name,
      option?.operator,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(term);
  }
  const visible = term ? options.filter(matches) : options;
  if (visible.length === 0 && term) {
    return <p>No loaded options match this filter.</p>;
  }
  return (
    <ul className="gonaj-journey-options">
      {visible.map((option) => {
        const route = option.route ?? {};
        const from = option.boarding_stop ?? {};
        const to = option.alighting_stop ?? {};
        const notes = [
          option.boarding_hint,
          walkNote(
            from.name,
            option.also_nearby_boarding,
            option.overflow_nearby_boarding
          ),
          walkNote(
            to.name,
            option.also_nearby,
            option.overflow_nearby
          ),
        ].filter(Boolean);
        return (
          <li
            key={`${route.id}-${from.id}-${to.id}`}
            className="gonaj-journey-option"
          >
            <Link to={route.evidence}>{route.name}</Link>
            <p>
              {from.name} to {to.name}
            </p>
            <p>
              {option.operator}
              {option.network ? ` · ${option.network}` : ""}
            </p>
            {notes.map((note) => (
              <p key={note}>{note}</p>
            ))}
          </li>
        );
      })}
    </ul>
  );
}

const TAP_MS = 300;

export default function JourneyPanel({
  onShowCandidates,
  chooseRef,
  onReportIssue,
} = {}) {
  const [question, setQuestion] = useState("");
  const [state, setState] = useState({ status: "idle" });
  const [mapHelpDismissed, setMapHelpDismissed] = useState(false);
  const [recording, setRecording] = useState(false);
  const [tapHint, setTapHint] = useState(false);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const pressTimerRef = useRef(null);

  useEffect(
    () => () => {
      if (pressTimerRef.current) clearTimeout(pressTimerRef.current);
    },
    []
  );
  const askAbort = useRef(null);
  const directAbort = useRef(null);
  const questionInputRef = useRef(null);
  const [fromText, setFromText] = useState("");
  const [fromStop, setFromStop] = useState(null);
  const [toText, setToText] = useState("");
  const [toStop, setToStop] = useState(null);
  const [direct, setDirect] = useState({ status: "idle" });
  const [cards, setCards] = useState([]);
  const [paging, setPaging] = useState(null);
  const [filter, setFilter] = useState("");
  const [loadingMore, setLoadingMore] = useState(false);
  const lastAskRef = useRef(null);
  const pagingRef = useRef(null);

  function walkNote(endName, mates, overflow) {
    const list = mates ?? [];
    if (list.length === 0 && !overflow) return "";
    const bits = list
      .map((mate) => `${mate.name} (${mate.walk_m}m walk)`)
      .join(", ");
    const extra = overflow ? ` plus ${overflow} more within 150m` : "";
    return `Also near ${endName}: ${bits}${extra}.`;
  }

  async function startDictation() {
    if (
      !navigator.mediaDevices?.getUserMedia ||
      typeof MediaRecorder === "undefined"
    ) {
      setState({
        status: "error",
        message:
          "Voice input is not available on this device. Please type your question.",
      });
      return;
    }
    let stream = null;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setState({
        status: "error",
        message:
          "The microphone is not available. Please check permission and type your question instead.",
      });
      return;
    }
    chunksRef.current = [];
    const recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size) {
        chunksRef.current.push(event.data);
      }
    };
    recorder.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop());
      const blob = new Blob(chunksRef.current, {
        type: recorder.mimeType || "audio/webm",
      });
      if (!blob.size) {
        setState({
          status: "error",
          message: "We could not hear anything. Please try again.",
        });
        return;
      }
      setState({ status: "loading" });
      let wav;
      try {
        wav = await encodeToWav(blob);
      } catch {
        setState({
          status: "error",
          message: "We could not transcribe that audio. Please try again.",
        });
        if (questionInputRef.current) questionInputRef.current.focus();
        return;
      }
      try {
        const body = await postTranscribe(wav);
        setQuestion(body.transcript);
        clearDirectInputs();
        setState({ status: "idle" });
      } catch (err) {
        setState({
          status: "error",
          message: (err && err.detail) || CANNOT_ANSWER_NOW,
        });
      }
    };
    recorderRef.current = recorder;
    recorder.start();
    setRecording(true);
  }

  function stopDictation() {
    const recorder = recorderRef.current;
    recorderRef.current = null;
    setRecording(false);
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }
  }

  // Press-and-hold: capture starts only after a sustained hold. Releasing
  // before TAP_MS explains the gesture instead — never touching the mic.
  function handleDictateDown(event) {
    event.preventDefault?.();
    setTapHint(false);
    if (pressTimerRef.current) clearTimeout(pressTimerRef.current);
    pressTimerRef.current = setTimeout(() => {
      pressTimerRef.current = null;
      startDictation();
    }, TAP_MS);
  }

  function handleDictateUp() {
    if (pressTimerRef.current) {
      clearTimeout(pressTimerRef.current);
      pressTimerRef.current = null;
      setTapHint(true);
      return;
    }
    stopDictation();
  }

  const askLoading = state.status === "loading";

  function stopAsk() {
    askAbort.current?.abort();
    setState({ status: "idle" });
  }

  async function findDirectRoutes() {
    // Belt and braces with the disabled UI: never run alongside an ask.
    if (state.status === "loading") return;
    if (!fromStop || !toStop) {
      setDirect({
        status: "error",
        detail: "Pick a boarding and an alighting stop first.",
      });
      return;
    }
    // A real direct search starts: the ask side must go, not just abort.
    clearAskMode();
    askAbort.current?.abort();
    directAbort.current?.abort();
    const controller = new AbortController();
    directAbort.current = controller;
    setDirect({ status: "loading" });
    try {
      const body = await getConnectivity(fromStop.id, toStop.id, {
        signal: controller.signal,
      });
      const routes = body.results ?? [];
      setDirect({
        status: routes.length > 0 ? "ok" : "empty",
        routes,
      });
    } catch (err) {
      if (err && err.name === "AbortError") return;
      setDirect({
        status: "error",
        detail: (err && err.detail) || CANNOT_ANSWER_NOW,
      });
    }
  }

  const lastPayloadRef = useRef(null);
  if (chooseRef) {
    chooseRef.current = (candidate) => {
      if (lastPayloadRef.current) choose(candidate, lastPayloadRef.current);
    };
  }

  function showCandidates(payload) {
    lastPayloadRef.current = payload;
    if (mapHelpDismissed || !onShowCandidates) return;
    const candidates = payload.candidates ?? [];
    const bounds = boundsFor(candidates, payload.groups);
    if (!bounds) return;
    onShowCandidates(
      {
        bounds,
        stops: candidates.map((c) => ({
          id: c.id,
          name: c.name,
          lat: c.lat,
          lon: c.lon,
          detail: c.detail,
        })),
      },
      payload
    );
  }

  function hideCandidates() {
    lastPayloadRef.current = null;
    onShowCandidates?.(null);
  }

  // Mutual clear (016 FR-006): each mode owns the panel; starting one resets
  // the other, including half-made selections.
  function clearDirectInputs() {
    setFromText("");
    setFromStop(null);
    setToText("");
    setToStop(null);
    setDirect({ status: "idle" });
  }

  function clearAskMode() {
    setQuestion("");
    setState({ status: "idle" });
    setCards([]);
    setPaging(null);
    pagingRef.current = null;
    setFilter("");
    setLoadingMore(false);
    hideCandidates();
  }

  function noneOfThese() {
    // Guided retry: forget the stale candidates and re-ask fresh.
    hideCandidates();
    ask(question, {}, []);
  }

  function dismissMapHelp() {
    setMapHelpDismissed(true);
    onShowCandidates?.(null);
  }

  async function ask(text, context, history) {
    const wording = (text ?? question).trim();
    if (!wording) {
      clearDirectInputs();
      setState({
        status: "refuse",
        message:
          "Please ask me a journey question, for example " +
          "'How do I get from Ernakulam South to Fort Kochi?'",
      });
      return;
    }
    askAbort.current?.abort();
    directAbort.current?.abort();
    clearDirectInputs();
    setMapHelpDismissed(false);
    setCards([]);
    setPaging(null);
    pagingRef.current = null;
    setFilter("");
    setLoadingMore(false);
    lastAskRef.current = {
      wording,
      history: history ?? [],
      context: context ?? {},
    };
    const controller = new AbortController();
    askAbort.current = controller;
    setState({ status: "loading" });
    try {
      const body = await postJourney(
        {
          question: wording,
          history: history ?? [],
          context: context ?? {},
        },
        { signal: controller.signal }
      );
      if (body.status === "ok") {
        hideCandidates();
        const opts = Array.isArray(body.options) ? body.options : [];
        setCards(opts);
        const info = Array.isArray(body.options)
          ? {
              page: body.page ?? 1,
              total_pages: body.total_pages ?? 1,
              page_size: body.page_size ?? opts.length,
              total_options: body.total_options ?? opts.length,
            }
          : null;
        setPaging(info);
        pagingRef.current = info;
        setState({ status: "ok", payload: body });
      } else if (body.status === "disambiguate") {
        setState({ status: "disambiguate", payload: body });
        showCandidates(body);
      } else {
        hideCandidates();
        setState({ status: "refuse", message: body.message });
      }
    } catch (err) {
      if (err && err.name === "AbortError") return;
      if (err && err.status === 0) {
        setState({ status: "error", message: CANNOT_ANSWER_NOW });
      } else {
        setState({
          status: "error",
          message: (err && err.detail) || CANNOT_ANSWER_NOW,
        });
      }
    }
  }

  async function goPage(page) {
    const last = lastAskRef.current;
    const info = pagingRef.current;
    if (!last || !info || loadingMore) return;
    if (page < 1 || page > info.total_pages || page === info.page) return;
    const controller = new AbortController();
    askAbort.current = controller;
    setLoadingMore(true);
    try {
      const body = await postJourney(
        {
          question: last.wording,
          history: last.history,
          context: last.context,
        },
        {
          signal: controller.signal,
          page,
          page_size: info.page_size,
        }
      );
      if (body.status === "ok" && Array.isArray(body.options)) {
        setCards(body.options);
        setFilter("");
        const next = {
          page: body.page ?? page,
          total_pages: body.total_pages ?? info.total_pages,
          page_size: body.page_size ?? info.page_size,
          total_options: body.total_options ?? info.total_options,
        };
        setPaging(next);
        pagingRef.current = next;
      }
    } catch (err) {
      if (err && err.name === "AbortError") return;
    } finally {
      setLoadingMore(false);
    }
  }

  function choose(candidate, payload) {
    const candidates = payload.candidates ?? [];
    // The input still holds the passenger's original question here:
    // capture it so the follow-up preserves history for the second end.
    const original = question;
    setQuestion(candidate.name);
    ask(
      candidate.name,
      {
        candidate_stop_ids: candidates.map((c) => c.id),
        selected_stop_id: candidate.id,
        slot: payload.slot,
        resolved: payload.resolved,
        slots: payload.slots,
        surviving_context: payload.surviving_context,
      },
      original ? [{ role: "user", content: original }] : []
    );
  }

  return (
    <section aria-label="Journey helper" className="gonaj-journey">
      <h2>Journey helper</h2>
      <p>Plain-language answers about direct services, with evidence.</p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          ask();
        }}
      >
        <label htmlFor="gonaj-journey-question">Your journey question</label>
        <input
          id="gonaj-journey-question"
          type="text"
          role="textbox"
          ref={questionInputRef}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="How do I get from Ernakulam South to Fort Kochi?"
        />
        <button type="submit" disabled={recording}>
          Ask
        </button>
        <button
          type="button"
          aria-label="Dictate your question"
          title="Press and hold to record"
          onPointerDown={handleDictateDown}
          onPointerUp={handleDictateUp}
          onPointerLeave={handleDictateUp}
        >
          Dictate
        </button>
      </form>
      <p className="gonaj-dictate-hint">Press and hold to record</p>
      {tapHint && !recording && (
        <p role="status">
          Quick tap detected — press and hold the Dictate button to record.
        </p>
      )}
      {recording && (
        <p role="status">
          <span className="gonaj-rec-dot" aria-hidden="true" />
          Listening… release to send.
        </p>
      )}

      <div className="gonaj-journey-or" role="separator">
        <span>OR</span>
      </div>

      <div className="gonaj-journey-stops">
      <StopPicker
        label="From stop"
        text={fromText}
        onTextChange={(value) => {
          setFromText(value);
          setFromStop(null);
          clearAskMode();
        }}
        selected={fromStop}
        onSelect={(stop) => {
          setFromStop(stop);
          setFromText(stop.name);
          clearAskMode();
        }}
        onClear={() => {
          setFromStop(null);
          setFromText("");
        }}
        disabled={askLoading}
      />
      <StopPicker
        label="To stop"
        text={toText}
        onTextChange={(value) => {
          setToText(value);
          setToStop(null);
          clearAskMode();
        }}
        selected={toStop}
        onSelect={(stop) => {
          setToStop(stop);
          setToText(stop.name);
          clearAskMode();
        }}
        onClear={() => {
          setToStop(null);
          setToText("");
        }}
        disabled={askLoading}
      />
      </div>
      <button type="button" onClick={findDirectRoutes} disabled={askLoading}>
        Find direct routes
      </button>

      <div className="gonaj-journey-results">
        {direct.status === "loading" && (
          <p role="status">Finding direct routes…</p>
        )}

        {direct.status === "ok" && (
          <ul className="gonaj-journey-routes">
            {(direct.routes ?? []).map((route) => (
              <li key={route.id}>
                <Link to={`/routes/${route.id}`}>
                  {route.name ?? `Route ${route.id}`}
                </Link>
              </li>
            ))}
          </ul>
        )}

        {(direct.status === "empty" || direct.status === "error") && (
          <p role="status">
            {direct.status === "empty" ? NO_DIRECT : direct.detail}
          </p>
        )}

        {state.status === "loading" && (
          <>
            <p role="status">Finding a direct service…</p>
            <button type="button" onClick={stopAsk}>
              Stop
            </button>
          </>
        )}

        {state.status === "ok" && (
          <article aria-label="Journey answer">
            <p className="gonaj-unverified">
              Journey agent can make mistakes, Check important info
            </p>
            {state.payload.meta?.model &&
              state.payload.meta.model !== "none" && (
                <p>Answer generated using {state.payload.meta.model}.</p>
              )}
            <p>{state.payload.answer}</p>
            {onReportIssue && (
              <button
                type="button"
                className="gonaj-journey-report"
                onClick={() =>
                  onReportIssue({
                    journey: {
                      question,
                      from_name: fromStop?.name,
                      to_name: toStop?.name,
                    },
                  })
                }
              >
                Report issue
              </button>
            )}
            {Array.isArray(state.payload.options) ? (
              <>
                <div className="gonaj-journey-filter">
                  <label htmlFor="gonaj-journey-filter">Filter options</label>
                  <input
                    id="gonaj-journey-filter"
                    type="text"
                    value={filter}
                    onChange={(event) => setFilter(event.target.value)}
                    placeholder="Stop, service, or operator"
                    autoComplete="off"
                  />
                </div>
                <JourneyOptionCards
                  options={cards}
                  filter={filter}
                  walkNote={walkNote}
                />
                {paging && paging.total_pages > 1 && (
                  <Pager
                    kind="options"
                    list={{
                      page: paging.page,
                      totalPages: paging.total_pages,
                      count: paging.total_options,
                    }}
                    onPage={goPage}
                  />
                )}
              </>
            ) : (
              <ul className="gonaj-journey-routes">
                {(state.payload.routes ?? []).map((route) => (
                  <li key={route.id}>
                    <Link to={route.evidence}>{route.name}</Link>
                  </li>
                ))}
              </ul>
            )}
          </article>
        )}

        {state.status === "disambiguate" && (
          <div aria-label="Choose a stop">
            <p className="gonaj-unverified">Journey agent can make mistakes, Check important info</p>
            <p>{state.payload.message}</p>
            {!mapHelpDismissed && (
              <p className="gonaj-journey-map-hint">
                The map is fitted to these stops — pick a highlighted pin
                or choose from the list.
              </p>
            )}
            <ul className="gonaj-journey-candidates">
              {(state.payload.candidates ?? []).map((candidate) => (
                <li key={candidate.id}>
                  <button
                    type="button"
                    onClick={() => choose(candidate, state.payload)}
                  >
                    {candidate.name}
                    {candidate.detail ? ` — ${candidate.detail}` : ""}
                  </button>
                </li>
              ))}
            </ul>
            <button type="button" onClick={noneOfThese}>
              None of these
            </button>
            <p className="gonaj-journey-rephrase">
              Not these? Answer none of these and try rephrasing with a
              nearby landmark.
            </p>
            {!mapHelpDismissed && onShowCandidates && (
              <button type="button" onClick={dismissMapHelp}>
                Hide map
              </button>
            )}
          </div>
        )}

        {(state.status === "refuse" || state.status === "error") && (
          <div aria-label="Journey helper notice">
            <p className="gonaj-unverified">Journey agent can make mistakes, Check important info</p>
            <p role="status">{state.message}</p>
          </div>
        )}
      </div>
    </section>
  );
}
