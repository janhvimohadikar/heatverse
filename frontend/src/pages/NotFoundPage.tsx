import { Link } from "react-router-dom";
import { PageHeader } from "../components/ui";

export default function NotFoundPage() {
  return (
    <div>
      <PageHeader title="Page not found" subtitle="The page you are looking for does not exist." />
      <Link to="/dashboard" className="btn-primary">Go to dashboard</Link>
    </div>
  );
}
