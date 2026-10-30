// Journey helper chat panel (004-journey-agent).
//
// Fills the dock slot reserved by the 005 map page. Talks only to
// the two versioned REST endpoints via api/journey.js — no model
// calls and no model key here. Every AI-assisted answer renders
// distinctly labelled unverified with inline /routes/:id evidence
// links; nothing is stored anywhere.
import { useEffect, useRef, useState } from "react";
import { getConnectivity, listStops } from "../api/client.js";
import { postJourney, postTranscribe } from "../api/journey.js";

const CANNOT_ANSWER_NOW =
  "The journey helper cannot answer right now. Please try again later.";

const NO_DIRECT = "I could not find a direct service between those stops.";

function StopPicker({ label, text, onTextChange, selected, onSelect, onClear }) {
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

export default function JourneyPanel() {
  const [question, setQuestion] = useState("");
  const [state, setState] = useState({ status: "idle" });
  const [recording, setRecording] = useState(false);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const askAbort = useRef(null);
  const directAbort = useRef(null);
  const [fromText, setFromText] = useState("");
  const [fromStop, setFromStop] = useState(null);
  const [toText, setToText] = useState("");
  const [toStop, setToStop] = useState(null);
  const [direct, setDirect] = useState({ status: "idle" });

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
      try {
        const body = await postTranscribe(blob);
        setQuestion(body.transcript);
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

  async function findDirectRoutes() {
    if (!fromStop || !toStop) {
      setDirect({
        status: "error",
        detail: "Pick a boarding and an alighting stop first.",
      });
      return;
    }
    askAbort.current?.abort();
    directAbort.current?.abort();
    setState({ status: "idle" });
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

  async function ask(text, context) {
    const wording = (text ?? question).trim();
    if (!wording) {
      setDirect({ status: "idle" });
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
    setDirect({ status: "idle" });
    const controller = new AbortController();
    askAbort.current = controller;
    setState({ status: "loading" });
    try {
      const body = await postJourney(
        {
          question: wording,
          history: [],
          context: context ?? {},
        },
        { signal: controller.signal }
      );
      if (body.status === "ok") {
        setState({ status: "ok", payload: body });
      } else if (body.status === "disambiguate") {
        setState({ status: "disambiguate", payload: body });
      } else {
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

  function choose(candidate, candidates) {
    setQuestion(candidate.name);
    ask(candidate.name, {
      candidate_stop_ids: candidates.map((c) => c.id),
    });
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
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="How do I get from Ernakulam South to Fort Kochi?"
        />
        <button type="submit">Ask</button>
        <button
          type="button"
          aria-label="Dictate your question"
          onPointerDown={startDictation}
          onPointerUp={stopDictation}
          onPointerLeave={stopDictation}
        >
          Dictate
        </button>
      </form>
      {recording && <p role="status">Listening… release to send.</p>}

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
        }}
        selected={fromStop}
        onSelect={(stop) => {
          setFromStop(stop);
          setFromText(stop.name);
        }}
        onClear={() => {
          setFromStop(null);
          setFromText("");
        }}
      />
      <StopPicker
        label="To stop"
        text={toText}
        onTextChange={(value) => {
          setToText(value);
          setToStop(null);
        }}
        selected={toStop}
        onSelect={(stop) => {
          setToStop(stop);
          setToText(stop.name);
        }}
        onClear={() => {
          setToStop(null);
          setToText("");
        }}
      />
      </div>
      <button type="button" onClick={findDirectRoutes}>
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
                <a href={`/routes/${route.id}`}>
                  {route.name ?? `Route ${route.id}`}
                </a>
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
          <p role="status">Finding a direct service…</p>
        )}

        {state.status === "ok" && (
          <article aria-label="Journey answer">
            <p className="gonaj-unverified">Unverified AI answer</p>
            <p>{state.payload.answer}</p>
            <ul className="gonaj-journey-routes">
              {(state.payload.routes ?? []).map((route) => (
                <li key={route.id}>
                  <a href={route.evidence}>{route.name}</a>
                </li>
              ))}
            </ul>
          </article>
        )}

        {state.status === "disambiguate" && (
          <div aria-label="Choose a stop">
            <p className="gonaj-unverified">Unverified AI answer</p>
            <p>{state.payload.message}</p>
            <ul className="gonaj-journey-candidates">
              {(state.payload.candidates ?? []).map((candidate) => (
                <li key={candidate.id}>
                  <button
                    type="button"
                    onClick={() => choose(candidate, state.payload.candidates)}
                  >
                    {candidate.name}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {(state.status === "refuse" || state.status === "error") && (
          <div aria-label="Journey helper notice">
            <p className="gonaj-unverified">Unverified AI answer</p>
            <p role="status">{state.message}</p>
          </div>
        )}
      </div>
    </section>
  );
}
