import { PageHeader } from "../components/ui";
import MapView from "../features/heat-risk-map/MapView";

export default function HeatMapPage() {
  return (
    <div>
      <PageHeader eyebrow="Geospatial analytics" title="Heat-risk map"
        subtitle="Explore observed heat conditions and the HEATVERSE risk score across Indian cities, day by day from 2000 to 2024." />
      <MapView />
    </div>
  );
}
