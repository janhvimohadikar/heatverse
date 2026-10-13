import { useEffect } from "react";
import type { GeoJsonObject, Feature } from "geojson";
import { CircleMarker, GeoJSON, MapContainer, Rectangle, TileLayer, Tooltip, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { LayerInfo, MapFeature, SurfaceResponse } from "../../types";
import { NO_DATA, continuousColor, featureColor, formatLayerValue, geoStateName } from "./colors";

export const INDIA_BOUNDS: [[number, number], [number, number]] = [[6.5, 68.0], [35.5, 97.5]];

function Controller({ resetSignal, selected }: { resetSignal: number; selected: MapFeature | null }) {
  const map = useMap();
  useEffect(() => { map.fitBounds(INDIA_BOUNDS); }, [resetSignal, map]);
  useEffect(() => { if (selected) map.panTo([selected.latitude, selected.longitude]); }, [selected, map]);
  // Leaflet must recompute its size when the container changes (e.g. full-screen toggle)
  useEffect(() => {
    const el = map.getContainer();
    const ro = new ResizeObserver(() => map.invalidateSize());
    ro.observe(el);
    return () => ro.disconnect();
  }, [map]);
  return null;
}

interface Props {
  features: MapFeature[];
  layer: LayerInfo;
  selectedId: number | null;
  onSelect: (id: number) => void;
  surface: SurfaceResponse | null;
  boundaries: GeoJsonObject | null;
  stateColors: Record<string, string>;
  showBoundaries: boolean;
  resetSignal: number;
}

export default function MapCanvas({ features, layer, selectedId, onSelect, surface, boundaries, stateColors, showBoundaries, resetSignal }: Props) {
  const selected = features.find((f) => f.city_id === selectedId) ?? null;
  const half = (surface?.cell_size_deg ?? 0.75) / 2;

  return (
    <MapContainer bounds={INDIA_BOUNDS} minZoom={4} maxZoom={10} preferCanvas scrollWheelZoom
      style={{ height: "100%", width: "100%", minHeight: 380 }} aria-label="Map of India showing heat-risk by city">
      <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <Controller resetSignal={resetSignal} selected={selected} />

      {showBoundaries && boundaries && (
        <GeoJSON key={JSON.stringify(stateColors)} data={boundaries}
          style={(feat?: Feature) => {
            const color = stateColors[geoStateName(feat?.properties as Record<string, unknown> | undefined)];
            return { color: "#475569", weight: 0.8, fillColor: color ?? "transparent", fillOpacity: color ? 0.45 : 0 };
          }} />
      )}

      {surface?.available && surface.cells.map((c, i) => (
        <Rectangle key={i} bounds={[[c.lat - half, c.lon - half], [c.lat + half, c.lon + half]]}
          pathOptions={{ stroke: false, fillColor: continuousColor(layer, c.value), fillOpacity: 0.4 }} interactive={false} />
      ))}

      {features.map((f) => {
        const isSel = f.city_id === selectedId;
        return (
          <CircleMarker key={f.city_id} center={[f.latitude, f.longitude]} radius={isSel ? 15 : 11}
            pathOptions={{ color: isSel ? "#0B1F3A" : "#ffffff", weight: isSel ? 3 : 1.5, fillColor: featureColor(layer, f) || NO_DATA, fillOpacity: 0.92 }}
            eventHandlers={{ click: () => onSelect(f.city_id) }}>
            <Tooltip direction="top" offset={[0, -8]}>
              <strong>{f.name}</strong>{f.state ? `, ${f.state}` : ""}<br />
              {layer.label}: {formatLayerValue(layer, f)}
            </Tooltip>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
