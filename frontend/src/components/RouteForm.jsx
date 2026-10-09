import { useState } from "react";

export default function RouteForm({ onSubmit }) {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [preference, setPreference] = useState("");

  function handleSubmit(event) {
    event.preventDefault();
    if (!origin.trim() || !destination.trim()) return;
    onSubmit({ origin: origin.trim(), destination: destination.trim(), preference: preference.trim() });
  }

  return (
    <form onSubmit={handleSubmit}>
      <label>
        Origin
        <input
          type="text"
          placeholder="e.g. Moodbidri"
          value={origin}
          onChange={(event) => setOrigin(event.target.value)}
          required
        />
      </label>
      <label>
        Destination
        <input
          type="text"
          placeholder="e.g. Mangalore Central"
          value={destination}
          onChange={(event) => setDestination(event.target.value)}
          required
        />
      </label>
      <label>
        Preference (optional)
        <input
          type="text"
          placeholder="avoid potholes, take the safest route"
          value={preference}
          onChange={(event) => setPreference(event.target.value)}
        />
      </label>
      <button type="submit">Find safest route</button>
    </form>
  );
}
