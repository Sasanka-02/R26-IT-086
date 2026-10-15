import { Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import DashboardPage from "./pages/DashboardPage";
import TherapyPage from "./pages/TherapyPage";
import ProtectedRoute from "./components/ProtectedRoute";
import TherapistPortalPage from "./therapist/TherapistPortalPage";
import TherapistStudentPage from "./therapist/TherapistStudentPage";
import EvidencePage from "./therapist/EvidencePage";
import ComparePage from "./therapist/ComparePage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/therapy"
        element={
          <ProtectedRoute>
            <TherapyPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/therapist"
        element={
          <ProtectedRoute role="therapist">
            <TherapistPortalPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/therapist/evidence"
        element={
          <ProtectedRoute role="therapist">
            <EvidencePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/therapist/compare"
        element={
          <ProtectedRoute role="therapist">
            <ComparePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/therapist/students/:email"
        element={
          <ProtectedRoute role="therapist">
            <TherapistStudentPage />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
