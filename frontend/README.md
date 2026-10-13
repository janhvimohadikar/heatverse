# HEATVERSE frontend

React 18 + TypeScript + Vite + Tailwind CSS + Recharts + Leaflet (react-leaflet).

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api to http://127.0.0.1:8000)
npm run build      # production build in dist/
npm run typecheck  # optional strict TypeScript check
```

`VITE_API_BASE_URL` is only needed when the backend is hosted on a different address (see `.env.example`).
The first `npm install` creates `package-lock.json` — commit it.
Map code: `src/features/heat-risk-map/`.
