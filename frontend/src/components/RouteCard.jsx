function coverageBadge(route) {
  const pct = Math.round((route.imageryCoverage || 0) * 100);
  if (!route.assessed) return <span className="badge warn">Unassessed</span>;
  if (pct < 100) return <span className="badge">Partially assessed ({pct}%)</span>;
  return null;
}

function hazardSummary(route) {
  const counts = {};
  (route.hazards || []).forEach((hazard) => {
    counts[hazard.class] = (counts[hazard.class] || 0) + 1;
  });
  const entries = Object.entries(counts);
  if (!entries.length) return "No hazards detected";
  return entries.map(([cls, n]) => `${n} ${cls.replace("_", " ")}`).join(", ");
}

export default function RouteCard({ route }) {
  return (
    <div className={"route" + (route.recommended ? " recommended" : "")}>
      <div className="score">
        {route.safetyScore} / 100 {coverageBadge(route)}
      </div>
      <div className="meta">
        {(route.durationS / 60).toFixed(1)} min &middot; {(route.distanceM / 1000).toFixed(1)} km
        {route.recommended ? " \u00b7 Recommended" : ""}
      </div>
      <div className="hazards">{hazardSummary(route)}</div>
    </div>
  );
}
