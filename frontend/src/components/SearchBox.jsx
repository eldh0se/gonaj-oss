import { useEffect, useRef, useState } from "react";

const DEBOUNCE_MS = 300;

// Text input over the application's own data only. Emits debounced
// query strings; makes no network calls itself.
export default function SearchBox({ onQuery }) {
  const [value, setValue] = useState("");
  const onQueryRef = useRef(onQuery);
  onQueryRef.current = onQuery;

  useEffect(() => {
    const timer = setTimeout(() => onQueryRef.current?.(value), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [value]);

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
        value={value}
        placeholder="Route, place, or stop name"
        onChange={(event) => setValue(event.target.value)}
      />
    </form>
  );
}
