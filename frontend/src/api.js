export async function postRoute({ origin, destination, preference }) {
  const response = await fetch("/api/route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ origin, destination, preference }),
  });
  const data = await response.json();
  return { ok: response.ok, data };
}
