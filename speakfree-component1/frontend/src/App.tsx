import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import AuthFlow from "./components/AuthFlow";
import AppLayout from "./components/AppLayout";
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
import AdminAppointments from "./pages/admin/AdminAppointments";
import AdminPatients from "./pages/admin/AdminPatients";
import AppointmentsPage from "./pages/AppointmentsPage";
import ReportsPage from "./pages/ReportsPage";
import ResourcesPage from "./pages/ResourcesPage";
import SettingsPage from "./pages/SettingsPage";
import TherapyReport from "./pages/therapy/TherapyReport";
import ModelsPage from "./pages/admin/pipeline/ModelsPage";
import PipelineOverview from "./pages/admin/pipeline/PipelineOverview";
import PipelineSession from "./pages/admin/pipeline/PipelineSession";
import TherapyMonitor from "./pages/admin/pipeline/TherapyMonitor";
import AssistantPage from "./pages/therapy/AssistantPage";
import ExerciseSession from "./pages/therapy/ExerciseSession";
import TherapyPlan from "./pages/therapy/TherapyPlan";
import PrivacyPage from "./pages/therapy/PrivacyPage";
import RecordingsPage from "./pages/therapy/RecordingsPage";
import EvidencePage from "./pages/admin/pipeline/EvidencePage";
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

/** Patient-facing therapy pages: the admin uses the therapy monitor instead. */
function NotAdmin({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  return user?.role === "admin" ? <Navigate to="/admin/pipeline" replace /> : <>{children}</>;
}

/** Home: the admin starts in the patient directory, everyone else on their dashboard. */
function Home() {
  const { user } = useAuth();
  return user?.role === "admin" ? <Navigate to="/admin/pipeline" replace /> : <DashboardHome />;
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
      <Route path="/therapy/report" element={<Protected><TherapyReport /></Protected>} />
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
        <Route path="admin/patients/:patientId/therapy" element={<AdminOnly><TherapyMonitor /></AdminOnly>} />
        <Route path="admin/pipeline" element={<AdminOnly><PipelineOverview /></AdminOnly>} />
        <Route path="admin/pipeline/:sessionId" element={<AdminOnly><PipelineSession /></AdminOnly>} />
        <Route path="admin/models" element={<AdminOnly><ModelsPage /></AdminOnly>} />
        <Route path="admin/evidence" element={<AdminOnly><EvidencePage /></AdminOnly>} />
        <Route path="progress" element={<ProgressPage />} />
        <Route path="task-library" element={<TaskLibrary />} />
        <Route path="therapy-plan" element={<NotAdmin><TherapyPlan /></NotAdmin>} />
        <Route path="therapy/exercise/:exerciseId" element={<NotAdmin><ExerciseSession /></NotAdmin>} />
        <Route path="therapy/assistant" element={<NotAdmin><AssistantPage /></NotAdmin>} />
        <Route path="therapy/privacy" element={<NotAdmin><PrivacyPage /></NotAdmin>} />
        <Route path="therapy/recordings" element={<NotAdmin><RecordingsPage /></NotAdmin>} />
        <Route path="reports" element={<NotAdmin><ReportsPage /></NotAdmin>} />
        <Route path="resources" element={<ResourcesPage />} />
        <Route path="appointments" element={<NotAdmin><AppointmentsPage /></NotAdmin>} />
        <Route path="admin/appointments" element={<AdminOnly><AdminAppointments /></AdminOnly>} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
