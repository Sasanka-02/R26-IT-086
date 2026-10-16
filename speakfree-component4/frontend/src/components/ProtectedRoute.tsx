import { Navigate } from "react-router-dom";
import { ReactNode } from "react";
import { homePathFor, useAuth, UserRole } from "../context/AuthContext";
import AgeGate from "./AgeGate";

export default function ProtectedRoute({
  children,
  role = "student",
}: {
  children: ReactNode;
  role?: UserRole;
}) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== role) return <Navigate to={homePathFor(user.role)} replace />;
  // Students need an age group (it decides their exercises) before the app opens.
  if (user.role === "student" && !user.age_group) return <AgeGate />;
  return <>{children}</>;
}
