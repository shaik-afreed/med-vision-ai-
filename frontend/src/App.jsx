import { Routes, Route, Navigate } from "react-router-dom";
import "./App.css";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Patients from "./pages/Patients";
import XRayAnalysis from "./pages/XRayAnalysis";
import MedicalReports from "./pages/MedicalReports";
import DocumentAnalysis from "./pages/DocumentAnalysis";
import AiDoctor from "./pages/AiDoctor";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";

function LoginRoute() {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <Navigate to="/" replace /> : <Login />;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginRoute />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/patients" element={<Patients />} />
          <Route path="/xray" element={<XRayAnalysis />} />
          <Route path="/documents" element={<DocumentAnalysis />} />
          <Route path="/reports" element={<MedicalReports />} />
          <Route path="/ai-doctor" element={<AiDoctor />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
