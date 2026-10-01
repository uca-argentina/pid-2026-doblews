import { useState } from "react";
import { Alert, Button, Group, Modal, Stack, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { useCurrentFirm } from "../firms/firmContext";
import { useCurrentProject } from "../projects/projectContext";
import { useSaveVersion } from "./useBudgetVersions";

interface SaveVersionModalProps {
  opened: boolean;
  onClose: () => void;
  onSaved: (versionNumber: number) => void;
}

/** "Guardar versión": freezes the budget on screen under an optional label.
 *
 * One field, because one field is all HU-12 asks for — and because everything
 * else about a version is computed by the server. A form that let someone type
 * a total would be a form that let them type the wrong one. */
export function SaveVersionModal({
  opened,
  onClose,
  onSaved,
}: SaveVersionModalProps) {
  const { firm } = useCurrentFirm();
  const { project } = useCurrentProject();
  const save = useSaveVersion(firm.id, project.id);
  const [note, setNote] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);

  const close = () => {
    setNote("");
    setSubmitError(null);
    onClose();
  };

  const handleSave = async () => {
    setSubmitError(null);
    try {
      const version = await save.mutateAsync({ note: note.trim() || null });
      notifications.show({
        title: `Versión v${version.version_number} guardada`,
        message: "Queda fija: ya no cambia aunque cambien los precios.",
        color: "obra",
      });
      onSaved(version.version_number);
      close();
    } catch (error) {
      // The 409 to expect: the take-off's last line was removed while this
      // modal was open, and there is nothing left to freeze.
      setSubmitError(
        apiErrorMessage(error, "No pudimos guardar la versión."),
      );
    }
  };

  return (
    <Modal opened={opened} onClose={close} title="Guardar versión" centered>
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        <Text size="sm">
          Guarda el presupuesto tal como está ahora. Queda fijo: si mañana
          cambia un precio del catálogo o editás el cómputo, esta versión sigue
          mostrando estos números.
        </Text>

        <TextInput
          label="Nombre o nota"
          description="Opcional. Para reconocerla después."
          placeholder="Presentado al cliente 20/10"
          value={note}
          onChange={(event) => setNote(event.currentTarget.value)}
          maxLength={150}
          data-autofocus
        />

        <Group justify="flex-end" gap="sm">
          <Button variant="subtle" onClick={close} disabled={save.isPending}>
            Cancelar
          </Button>
          <Button onClick={handleSave} loading={save.isPending}>
            Guardar versión
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
