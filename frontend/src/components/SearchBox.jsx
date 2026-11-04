import { useEffect, useRef, useState } from "react";

const DEBOUNCE_MS = 300;

// Text input over the application's own data only. Emits debounced
// query strings; makes no network calls itself. Uncontrolled by default;
// pass value + onValueChange to share one text across instances.
export default function SearchBox({ onQuery, value, onValueChange }) {
  const [inner, setInner] = useState("");
  const text = value !== undefined ? value : inner;
  const onQueryRef = useRef(onQuery);
  onQueryRef.current = onQuery;

  useEffect(() => {
    const timer = setTimeout(() => onQueryRef.current?.(text), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [text]);

  function handleChange(event) {
    if (onValueChange) onValueChange(event.target.value);
    else setInner(event.target.value);
  }

  return (
    <form
      role="search"
      className="gonaj-search"
      onSubmit={(event) => event.preventDefault()}
    >
      <label htmlFor="gonaj-search-input">Search routes and stops</label>
      <input
        id="gonaj-search-input"
        type="search"
        value={text}
        placeholder="Route, place, or stop name"
        onChange={handleChange}
      />
    </form>
  );
}
