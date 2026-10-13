import type { LayerInfo } from "../../types";
import { CATEGORIES, CATEGORY_RANGES, NO_DATA, RISK_COLORS, gradientCss } from "./colors";

export default function Legend({ layer, interpolated }: { layer: LayerInfo; interpolated: boolean }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3 text-xs dark:border-navy-700 dark:bg-navy-900" aria-label="Map legend">
      <p className="mb-2 font-semibold">{layer.label}{layer.unit && layer.unit !== "category" ? ` (${layer.unit})` : ""}</p>
      {layer.key === "risk" ? (
        <ul className="space-y-1">
          {CATEGORIES.map((c) => (
            <li key={c} className="flex items-center gap-2">
              <span className="h-3 w-5 rounded-sm" style={{ backgroundColor: RISK_COLORS[c] }} />
              <span className="font-medium">{c}</span><span className="text-slate-500">score {CATEGORY_RANGES[c]}</span>
            </li>
          ))}
        </ul>
      ) : (
        <div>
          <div className="h-3 w-full rounded-sm" style={{ background: gradientCss(layer) }} />
          <div className="mt-1 flex justify-between text-slate-500"><span>{layer.domain[0]}</span><span>{layer.domain[1]}</span></div>
        </div>
      )}
      <p className="mt-2 flex items-center gap-2"><span className="h-3 w-5 rounded-sm" style={{ backgroundColor: NO_DATA }} /> No data</p>
      {interpolated && <p className="mt-2 text-purple-700 dark:text-purple-300">Faded background = interpolated estimate, not measurements.</p>}
      <p className="mt-2 text-slate-500">Risk categories apply to the HEATVERSE score (0–100), not to raw temperature.</p>
    </div>
  );
}
