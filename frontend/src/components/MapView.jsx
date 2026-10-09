import { useEffect, useRef } from "react";

let mapsPromise = null;

function loadMaps(apiKey) {
  if (!apiKey) return Promise.resolve(null);
  if (window.google && window.google.maps) return Promise.resolve(window.google.maps);
  if (!mapsPromise) {
    mapsPromise = new Promise((resolve, reject) => {
      window.__safeRouteMapReady = () => resolve(window.google.maps);
      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=geometry&callback=__safeRouteMapReady`;
      script.onerror = () => reject(new Error("Failed to load Google Maps"));
      document.head.appendChild(script);
    });
  }
  return mapsPromise;
}

export default function MapView({ routes, apiKey }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const overlaysRef = useRef([]);

  useEffect(() => {
    let cancelled = false;
    if (!routes || routes.length === 0) return undefined;

    loadMaps(apiKey)
      .then((maps) => {
        if (cancelled || !maps || !containerRef.current) return;
        if (!mapRef.current) {
          mapRef.current = new maps.Map(containerRef.current, {
            center: { lat: 12.9141, lng: 74.856 },
            zoom: 11,
          });
        }
        const map = mapRef.current;
        overlaysRef.current.forEach((overlay) => overlay.setMap(null));
        overlaysRef.current = [];

        const bounds = new maps.LatLngBounds();
        routes.forEach((route) => {
          const path = maps.geometry.encoding.decodePath(route.polyline || "");
          if (!path.length) return;
          path.forEach((point) => bounds.extend(point));
          const line = new maps.Polyline({
            path,
            strokeColor: route.recommended ? "#29c47f" : "#5a6b7a",
            strokeWeight: route.recommended ? 6 : 3,
            strokeOpacity: route.recommended ? 1 : 0.6,
          });
          line.setMap(map);
          overlaysRef.current.push(line);

          if (route.recommended) {
            (route.hazards || []).forEach((hazard) => {
              const marker = new maps.Marker({
                position: { lat: hazard.lat, lng: hazard.lng },
                title: hazard.class,
                label: (hazard.severity || "?")[0].toUpperCase(),
              });
              marker.setMap(map);
              overlaysRef.current.push(marker);
            });
          }
        });
        if (!bounds.isEmpty()) map.fitBounds(bounds);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [routes, apiKey]);

  return (
    <div ref={containerRef} className="map">
      {!apiKey && (
        <p className="map-hint">Set window.SAFEROUTE_MAPS_KEY in index.html to display the map.</p>
      )}
    </div>
  );
}
