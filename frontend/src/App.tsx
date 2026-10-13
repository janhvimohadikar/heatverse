import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminPage from "./pages/AdminPage";
import DashboardPage from "./pages/DashboardPage";
import HeatMapPage from "./pages/HeatMapPage";
import LandingPage from "./pages/LandingPage";
import { LoginPage, SignupPage } from "./pages/AuthPages";
import NotFoundPage from "./pages/NotFoundPage";
import PredictionsPage from "./pages/PredictionsPage";
import ProfilePage from "./pages/ProfilePage";
import SafetyPage from "./pages/SafetyPage";
import TrendsPage from "./pages/TrendsPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route element={<Layout />}>
        {/* Public: the map, historical trends and safety guidance can be explored without an account */}
        <Route path="/map" element={<HeatMapPage />} />
        <Route path="/trends" element={<TrendsPage />} />
        <Route path="/safety" element={<SafetyPage />} />
        {/* Signed-in users */}
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/predictions" element={<ProtectedRoute><PredictionsPage /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
        {/* Administrators (also enforced by the backend) */}
        <Route path="/admin" element={<ProtectedRoute adminOnly><AdminPage /></ProtectedRoute>} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
