import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Numbered pixel-style pins. (Leaflet's default image pins often break
// when bundled with Vite, and these fit the theme better anyway.)
function numberIcon(n) {
  return L.divIcon({
    className: "pin",
    html: `<span>${n}</span>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -14],
  });
}

// Zooms the map so every stop is visible.
function FitBounds({ stops }) {
  const map = useMap();
  useEffect(() => {
    if (stops.length === 1) {
      map.setView([stops[0].lat, stops[0].lon], 16);
    } else {
      map.fitBounds(
        stops.map((s) => [s.lat, s.lon]),
        { padding: [40, 40] }
      );
    }
  }, [stops, map]);
  return null;
}

export default function ResultMap({ stops }) {
  return (
    <MapContainer
      key={stops.map((s) => s.name).join("|")}
      className="map"
      center={[stops[0].lat, stops[0].lon]}
      zoom={15}
      scrollWheelZoom={false}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitBounds stops={stops} />
      {stops.map((s, i) => (
        <Marker key={s.name} position={[s.lat, s.lon]} icon={numberIcon(i + 1)}>
          <Popup>{s.name}</Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}