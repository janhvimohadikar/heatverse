import { Link } from "react-router-dom";
import { Logo, ThemeToggle } from "../components/Layout";
import { useAuth } from "../hooks/useAuth";

const FEATURES = [
  { title: "Interactive heat-risk map", text: "City markers, optional state boundaries, an interpolated heat surface and a historical timeline from 2000 to 2024." },
  { title: "Risk score & explanations", text: "A documented 0–100 severity score. Every number can be traced back to the observation that produced it." },
  { title: "Climate trends", text: "Annual, monthly and seasonal analysis, city comparison and heatwave-event detection computed in the database." },
  { title: "Safety guidance", text: "Heat-illness warning signs, hydration tips and nearby hospitals from OpenStreetMap when you allow location access." },
];

export default function LandingPage() {
  const { user } = useAuth();
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between p-4">
        <Logo />
        <div className="flex items-center gap-2">
          <ThemeToggle />
          {user ? <Link to="/dashboard" className="btn-primary">Open dashboard</Link> : (<>
            <Link to="/login" className="btn-secondary">Log in</Link>
            <Link to="/signup" className="btn-primary">Sign up</Link>
          </>)}
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-4 py-14 sm:py-20">
        <p className="text-xs font-semibold uppercase tracking-widest text-heat-orange">Climate &amp; health</p>
        <h1 className="mt-2 max-w-3xl text-4xl font-bold leading-tight sm:text-5xl">Know the heat. <span className="text-heat-orange">Protect yourself.</span></h1>
        <p className="mt-4 max-w-2xl text-lg text-slate-600 dark:text-slate-300">
          HEATVERSE turns 25 years of daily weather for ten Indian cities into a heat-risk map, trend analysis and personalised safety guidance.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link to="/map" className="btn-primary">Explore the heat-risk map</Link>
          <Link to="/trends" className="btn-secondary">View climate trends</Link>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-4 px-4 pb-12 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map((f) => (
          <div key={f.title} className="card">
            <h2 className="text-base font-semibold">{f.title}</h2>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{f.text}</p>
          </div>
        ))}
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-16">
        <div className="card text-sm text-slate-600 dark:text-slate-400">
          <h2 className="mb-1 text-base font-semibold text-navy-900 dark:text-white">Important</h2>
          <p>
            HEATVERSE is a college DBMS project. Its risk score is an informational project metric and is <strong>not</strong> an official government heat warning.
            Predictions are labelled <strong>DEMO</strong> unless a trained model has been connected. Safety guidance is educational and is not medical advice.
          </p>
        </div>
      </section>
    </div>
  );
}
