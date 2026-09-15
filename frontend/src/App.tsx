import { Navigate, Route, Routes } from "react-router-dom";
import { AppShellLayout } from "./layout/AppShellLayout";
import { CatalogPage } from "./pages/CatalogPage";
import { FirmLayout } from "./layout/FirmLayout";
import { ProjectLayout } from "./layout/ProjectLayout";
import { FirmPickerPage } from "./pages/FirmPickerPage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { HomeRedirect } from "./pages/HomeRedirect";
import { LoginPage } from "./pages/LoginPage";
import { MembersPage } from "./pages/MembersPage";
import { ProjectDetailPage } from "./pages/ProjectDetailPage";
import { ProjectTakeoffPage } from "./pages/ProjectTakeoffPage";
import { NoFirmPage } from "./pages/NoFirmPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { PlatformLayout } from "./layout/PlatformLayout";
import { PasswordResetPage } from "./pages/PasswordResetPage";
import { PlatformFirmsPage } from "./pages/PlatformFirmsPage";
import { PlatformMaterialsPage } from "./pages/PlatformMaterialsPage";
import { PlatformRecipesPage } from "./pages/PlatformRecipesPage";
import { ProtectedRoute } from "./routes/ProtectedRoute";
import { RequirePermission } from "./routes/RequirePermission";
import { RequirePlatformPermission } from "./routes/RequirePlatformPermission";
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
        </Route>

        {/* Support's screens (HU-7). Outside /firms/:firmId on purpose:
            support belongs to no firm, and FirmLayout would answer "not found".
            Each screen demands its own platform permission, the same one its
            endpoint does. */}
        <Route path="/platform" element={<PlatformLayout />}>
          <Route index element={<Navigate to="firms" replace />} />
          <Route
            path="firms"
            element={
              <RequirePlatformPermission code="firm.view">
                <PlatformFirmsPage />
              </RequirePlatformPermission>
            }
          />
          <Route
            path="password-reset"
            element={
              <RequirePlatformPermission code="account.reset_password">
                <PasswordResetPage />
              </RequirePlatformPermission>
            }
          />
          {/* HU-8: two screens, not one with a toggle, same split as
              "firms"/"password-reset" above. Both guarded by the same
              permission — the catalogue has one, not one per action
              (ADR-005 section 2). */}
          <Route
            path="catalog/materials"
            element={
              <RequirePlatformPermission code="catalog.manage">
                <PlatformMaterialsPage />
              </RequirePlatformPermission>
            }
          />
          <Route
            path="catalog/recipes"
            element={
              <RequirePlatformPermission code="catalog.manage">
                <PlatformRecipesPage />
              </RequirePlatformPermission>
            }
          />
        </Route>

        {/* Inside a firm the shell gains a sidebar, so FirmLayout renders its
            own AppShellLayout instead of nesting in the one above. */}
        <Route path="/firms/:firmId" element={<FirmLayout />}>
          <Route index element={<Navigate to="projects" replace />} />
          <Route path="projects" element={<ProjectsPage />} />
          {/* One work, with its name as the context of everything inside it
              (HU-3). Each tab of the work is a child route: the index is its
              data, "takeoff" is HU-5's take-off, and HU-6's team joins them
              the same way. */}
          <Route path="projects/:projectId" element={<ProjectLayout />}>
            <Route index element={<ProjectDetailPage />} />
            <Route path="takeoff" element={<ProjectTakeoffPage />} />
          </Route>
          {/* Every firm role holds catalog.view today, so the gate is for the
              role that someday will not, not for anyone who exists now. */}
          <Route
            path="catalog"
            element={
              <RequirePermission
                code="catalog.view"
                message="Tu rol en este estudio no incluye ver el catálogo."
              >
                <CatalogPage />
              </RequirePermission>
            }
          />
          <Route
            path="members"
            element={
              <RequirePermission code="member.add">
                <MembersPage />
              </RequirePermission>
            }
          />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
