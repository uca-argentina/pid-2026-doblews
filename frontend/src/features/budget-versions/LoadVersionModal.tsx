import { useState } from "react";
import { Alert, Button, Group, List, Modal, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { useCurrentFirm } from "../firms/firmContext";
import { useCurrentProject } from "../projects/projectContext";
import { useLoadVersion } from "./useBudgetVersions";
import type { BudgetVersionSummary } from "./types";

interface LoadVersionModalProps {
  /** The version being loaded, or null when the modal is closed. */
  version: Pick<BudgetVersionSummary, "id" | "version_number"> | null;
  onClose: () => void;
  onLoaded: () => void;
}

/** Confirmation for replacing the draft with a saved version's lines.
 *
 * It says the two things that are easy to get wrong, because both are
 * deliberate and both look like bugs otherwise. The current lines are not
 * deleted — they are deactivated, and the work keeps its history. And the
 * prices are not restored: the version's quantities come back and are costed at
 * today's catalogue, so the loaded draft may total something the version never
 * said (ADR-007, consequences).
 *
 * Recipes retired since the version was saved are reported after the fact
 * rather than predicted here: whether one is still available is the backend's
 * answer, and asking twice would let the two disagree. */
export function LoadVersionModal({
  version,
  onClose,
  onLoaded,
}: LoadVersionModalProps) {
  const { firm } = useCurrentFirm();
  const { project } = useCurrentProject();
  const load = useLoadVersion(firm.id, project.id);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [skipped, setSkipped] = useState<string[]>([]);

  const close = () => {
    setSubmitError(null);
    setSkipped([]);
    onClose();
  };

  const handleLoad = async () => {
    if (!version) return;

    setSubmitError(null);
    try {
      const outcome = await load.mutateAsync(version.id);
      if (outcome.skipped.length > 0) {
        // Not a notification: a list of lines that did not come back is
        // something to read and act on, and a toast disappears while you do.
        setSkipped(outcome.skipped);
        return;
      }
      notifications.show({
        title: `Cómputo cargado desde la v${version.version_number}`,
        message: "Se recalculó con los precios de hoy.",
        color: "obra",
      });
      onLoaded();
      close();
    } catch (error) {
      setSubmitError(apiErrorMessage(error, "No pudimos cargar la versión."));
    }
  };

  if (skipped.length > 0) {
    return (
      <Modal opened onClose={close} title="Cargado, con líneas afuera" centered>
        <Stack gap="md">
          <Text size="sm">
            El cómputo se cargó desde la v{version?.version_number}, pero estas
            recetas ya no están en el catálogo y sus líneas quedaron afuera:
          </Text>
          <List size="sm">
            {skipped.map((name) => (
              <List.Item key={name}>{name}</List.Item>
            ))}
          </List>
          <Text size="sm" c="dimmed">
            La versión guardada no cambió: sigue mostrando esas líneas.
          </Text>
          <Group justify="flex-end">
            <Button
              onClick={() => {
                onLoaded();
                close();
              }}
            >
              Entendido
            </Button>
          </Group>
        </Stack>
      </Modal>
    );
  }

  return (
    <Modal
      opened={version !== null}
      onClose={close}
      title={
        version ? `Cargar la v${version.version_number} en el cómputo` : ""
      }
      centered
    >
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        <Text size="sm">
          Reemplaza las líneas del cómputo actual por las de esta versión. Las
          de ahora se dan de baja, no se borran.
        </Text>

        <Alert color="obra" variant="light">
          <Text size="sm">
            Vuelven las <strong>cantidades</strong> de la versión, no sus
            precios: el cómputo se recalcula con los precios de hoy, así que el
            total puede no coincidir con el de la versión. La versión guardada
            queda intacta.
          </Text>
        </Alert>

        {/* HU-13: a version does not record which task each line was in, and
            the lines it loads are new ones (ADR-009, pending for HU-19). */}
        <Text size="sm">
          Las líneas cargadas quedan{" "}
          <strong>sin asignar a ninguna tarea</strong>: si la obra tiene
          planificación, vas a tener que volver a asignarlas.
        </Text>

        <Group justify="flex-end" gap="sm">
          <Button variant="subtle" onClick={close} disabled={load.isPending}>
            Cancelar
          </Button>
          <Button onClick={handleLoad} loading={load.isPending}>
            Cargar en el cómputo
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
