import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import AuthFlow from "./components/AuthFlow";
import AppLayout, { PlaceholderPage } from "./components/AppLayout";
import AsrConfidenceDashboard from "./components/AsrConfidenceDashboard";
import { Spinner } from "./components/ui";
import ClinicalReport from "./pages/ClinicalReport";
import DashboardHome from "./pages/DashboardHome";
import Landing from "./pages/Landing";
import PatientResults from "./pages/PatientResults";
import ProgressPage from "./pages/ProgressPage";
import SessionDashboard from "./pages/SessionDashboard";
import TaskLibrary from "./pages/TaskLibrary";
import AdminPatientProfile from "./pages/admin/AdminPatientProfile";
import AdminPatients from "./pages/admin/AdminPatients";
import AssessmentOverview from "./pages/assessment/AssessmentOverview";
import AnalysePage from "./pages/assessment/AnalysePage";
import { PicturePage, QuestionsPage, ScenarioPage } from "./pages/assessment/TaskPages";

function Protected({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Spinner className="min-h-screen" />;
  return user ? <>{children}</> : <Navigate to="/welcome" replace />;
}

function PublicOnly({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  return user ? <Navigate to="/" replace /> : <>{children}</>;
}

/** Technical views (session analysis, word-level results, patient directory) are admin-only. */
function AdminOnly({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  return user?.role === "admin" ? <>{children}</> : <Navigate to="/" replace />;
}

/** Home: the admin starts in the patient directory, everyone else on their dashboard. */
function Home() {
  const { user } = useAuth();
  return user?.role === "admin" ? <Navigate to="/admin/patients" replace /> : <DashboardHome />;
}

/** Session results: admin → technical dashboard, everyone else → simple patient view. */
function SessionResults() {
  const { user } = useAuth();
  return user?.role === "admin" ? <SessionDashboard /> : <PatientResults />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/welcome" element={<Landing />} />
      <Route path="/login" element={<PublicOnly><AuthFlow mode="login" /></PublicOnly>} />
      <Route path="/signup" element={<PublicOnly><AuthFlow mode="signup" /></PublicOnly>} />
      <Route path="/sessions/:sessionId/report" element={<Protected><ClinicalReport /></Protected>} />
      <Route element={<Protected><AppLayout /></Protected>}>
        <Route index element={<Home />} />
        <Route path="assessment" element={<AssessmentOverview />} />
        <Route path="assessment/picture" element={<PicturePage />} />
        <Route path="assessment/scenario" element={<ScenarioPage />} />
        <Route path="assessment/questions" element={<QuestionsPage />} />
        <Route path="assessment/analyse" element={<AnalysePage />} />
        <Route path="sessions/:sessionId" element={<SessionResults />} />
        <Route path="results/:analysisId" element={<AdminOnly><AsrConfidenceDashboard /></AdminOnly>} />
        <Route path="admin/patients" element={<AdminOnly><AdminPatients /></AdminOnly>} />
        <Route path="admin/patients/:patientId" element={<AdminOnly><AdminPatientProfile /></AdminOnly>} />
        <Route path="admin/patients/:patientId/sessions/:sessionId" element={<AdminOnly><SessionDashboard /></AdminOnly>} />
        <Route path="progress" element={<ProgressPage />} />
        <Route path="task-library" element={<TaskLibrary />} />
        <Route path="therapy-plan" element={<PlaceholderPage title="Therapy Plan" owner="Feature 4 – AI Therapy Assistant" description="Your personalised therapy plan and daily exercises, built around your screening results, are coming soon." />} />
        <Route path="reports" element={<PlaceholderPage title="Reports" owner="Features 1–3" description="Combined screening, articulation and severity reports for clinicians." />} />
        <Route path="resources" element={<PlaceholderPage title="Resources" owner="SpeakFree team" description="Guides and practice materials for patients and families." />} />
        <Route path="appointments" element={<PlaceholderPage title="Appointments" owner="SpeakFree platform" description="Booking a session with a speech-language pathologist is coming soon. Until then, use Contact Support and we will help you." />} />
        <Route path="settings" element={<PlaceholderPage title="Settings" owner="SpeakFree platform" description="Account, privacy and notification settings." />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
