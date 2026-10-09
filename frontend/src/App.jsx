import { useState } from "react";
import RouteForm from "./components/RouteForm.jsx";
import RouteCard from "./components/RouteCard.jsx";
import MapView from "./components/MapView.jsx";
import { postRoute } from "./api.js";

export default function App() {
  const [status, setStatus] = useState("");
  const [explanation, setExplanation] = useState(null);
  const [routes, setRoutes] = useState([]);

  async function handleSubmit({ origin, destination, preference }) {
    setStatus("Finding routes and assessing hazards...");
    setRoutes([]);
    setExplanation(null);
    try {
      const { ok, data } = await postRoute({ origin, destination, preference });
      if (!ok) {
        setStatus(data.error || "Request failed");
        return;
      }
      setStatus("");
      if (data.explanation && data.explanation.generated) {
        setExplanation(data.explanation.text);
      }
      setRoutes(data.routes);
    } catch (error) {
      setStatus("Network error: " + error.message);
    }
  }

  return (
    <div>
      <header>
        <h1>SafeRoute AI</h1>
        <p>Safety-aware navigation - avoid potholes, cracks, waterlogging and rough roads.</p>
      </header>
      <main>
        <section className="panel">
          <RouteForm onSubmit={handleSubmit} />
          <p className="status" role="status">
            {status}
          </p>
        </section>
        <section className="panel">
          {explanation && <div className="explanation">{explanation}</div>}
          <div className="routes">
            {routes.map((route) => (
              <RouteCard key={route.id} route={route} />
            ))}
          </div>
        </section>
        <MapView routes={routes} apiKey={window.SAFEROUTE_MAPS_KEY} />
      </main>
    </div>
  );
}
