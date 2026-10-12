import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@mantine/core/styles.css";
// Each Mantine package ships its own stylesheet, and a component whose one is
// missing renders unstyled rather than failing: without this the calendar that
// drops out of the "inicio estimado" field has no layout at all.
import "@mantine/charts/styles.css";
import "@mantine/dates/styles.css";
import "@mantine/notifications/styles.css";
import "./index.css";
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "./features/auth/AuthContext";
import { cssVariablesResolver, theme } from "./theme";
import App from "./App.tsx";

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <MantineProvider
      theme={theme}
      cssVariablesResolver={cssVariablesResolver}
      // Explicit because the app is designed light-first and there is no dark
      // palette yet. Without it a viewer whose OS is dark gets Mantine's stock
      // dark scheme, which "verde obra" has no values for.
      defaultColorScheme="light"
    >
      {/* Mounted once, at the root: notifications.show() can then be called
          from anywhere — a modal that is closing included, which is exactly
          when the roster confirms what it just did. */}
      <Notifications />
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <App />
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </MantineProvider>
  </StrictMode>,
);
