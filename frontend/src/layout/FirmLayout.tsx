import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Alert, Center, Loader } from "@mantine/core";
import { useParams } from "react-router-dom";
import { FirmContext, type CurrentFirm } from "../features/firms/firmContext";
import { fetchFirm } from "../features/firms/firmService";
import { AppShellLayout } from "./AppShellLayout";
import { FirmNavbar } from "./FirmNavbar";

/** Everything under /firms/:firmId: resolves the firm once, then hands it to
 * the sidebar and to every screen through useCurrentFirm().
 *
 * Fetching GET /firms/{firmId} here — instead of trusting the firm list
 * already in the account from /auth/me — is what turns a stale or foreign
 * firm id typed into the URL into the backend's 404, rather than rendering
 * with no data. It is also where the caller's permissions come from, so the
 * sidebar and the screens never ask for them separately.
 *
 * The query key is ["firm", firmId]: anything else under this firm hangs its
 * own keys below it, so they are easy to find and invalidate together. */
export function FirmLayout() {
  const { firmId: param = "" } = useParams<{ firmId: string }>();
  // Numeric from here down, so every key under this firm — ["firm", id],
  // ["firm", id, "members"] — shares one prefix. A URL like /firms/abc never
  // reaches the API: it is answered below exactly like a firm that is not
  // yours, which is what the backend would say anyway.
  const firmId = Number(param);
  const isValidId = Number.isInteger(firmId) && firmId > 0;

  const {
    data: firm,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["firm", firmId],
    queryFn: () => fetchFirm(firmId),
    enabled: isValidId,
    // A 404 means "not yours", and asking again will not change that.
    retry: false,
  });

  const current = useMemo<CurrentFirm | null>(() => {
    if (!firm) return null;
    const granted = new Set(firm.permissions);
    return { firm, can: (permission) => granted.has(permission) };
  }, [firm]);

  if (isValidId && isLoading) {
    return (
      <AppShellLayout>
        <Center>
          <Loader />
        </Center>
      </AppShellLayout>
    );
  }

  // No sidebar here: a firm that is not yours has no sections to offer.
  if (isError || !current) {
    return (
      <AppShellLayout>
        <Alert color="red" variant="light">
          No encontramos ese estudio, o no formás parte de él.
        </Alert>
      </AppShellLayout>
    );
  }

  return (
    <FirmContext.Provider value={current}>
      <AppShellLayout navbar={(close) => <FirmNavbar onNavigate={close} />} />
    </FirmContext.Provider>
  );
}
