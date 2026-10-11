import { Navigate } from "react-router-dom";
import { ReactNode } from "react";
import { homePathFor, useAuth, UserRole } from "../context/AuthContext";

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
  return <>{children}</>;
}
