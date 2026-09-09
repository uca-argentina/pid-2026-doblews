import { Navigate, Route, Routes } from "react-router-dom";
import { AppShellLayout } from "./layout/AppShellLayout";
import { FirmPickerPage } from "./pages/FirmPickerPage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { HomeRedirect } from "./pages/HomeRedirect";
import { LoginPage } from "./pages/LoginPage";
import { NoFirmPage } from "./pages/NoFirmPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { ProtectedRoute } from "./routes/ProtectedRoute";
import { PublicOnlyRoute } from "./routes/PublicOnlyRoute";

function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicOnlyRoute>
            <LoginPage />
          </PublicOnlyRoute>
        }
      />

      {/* Public, and deliberately not behind PublicOnlyRoute: it explains a
          policy rather than starting a session, so it stays readable whether or
          not someone is logged in. */}
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShellLayout />}>
          <Route path="/" element={<HomeRedirect />} />
          <Route path="/firms" element={<FirmPickerPage />} />
          <Route path="/no-firm" element={<NoFirmPage />} />
          <Route path="/firms/:firmId/projects" element={<ProjectsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
