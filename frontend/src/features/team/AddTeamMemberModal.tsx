import { useState } from "react";
import {
  Alert,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Text,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { useAuth } from "../auth/AuthContext";
import { useCurrentFirm } from "../firms/firmContext";
import { useCurrentProject } from "../projects/projectContext";
import { useMembers } from "../members/useMembers";
import { useAddTeamMember, useTeam, useTeamRoles } from "./useTeam";
import { CLIENT, LEAD, type AssignableProjectRole } from "./types";

/** The firm role whose holders may only ever be the client of a work (ADR-002
 * section 11.2). The same string as the project role CLIENT and a different
 * thing: one is a seat in the studio, the other a seat in this work. Named
 * apart here for the same reason services/project.py names them apart. */
const FIRM_CLIENT = "client";

interface AddTeamMemberModalProps {
  opened: boolean;
  onClose: () => void;
}

/** HU-6's add: someone from this studio's roster, with a role on this work.
 *
 * The form lives in a child component so it mounts fresh every time the modal
 * opens, rather than keeping the last attempt's values around. */
export function AddTeamMemberModal({
  opened,
  onClose,
}: AddTeamMemberModalProps) {
  return (
    <Modal opened={opened} onClose={onClose} title="Agregar al equipo" centered>
      {opened && <AddTeamMemberForm onClose={onClose} />}
    </Modal>
  );
}

function AddTeamMemberForm({ onClose }: { onClose: () => void }) {
  const { account } = useAuth();
  const { firm } = useCurrentFirm();
  const { project } = useCurrentProject();
  const roster = useMembers(firm.id);
  const team = useTeam(firm.id, project.id);
  const roles = useTeamRoles(firm.id, project.id);
  const addMember = useAddTeamMember(firm.id, project.id);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<{ account_id: string | null; role_code: string | null }>(
    {
      initialValues: { account_id: null, role_code: null },
      validate: {
        account_id: (value) => (value ? null : "Elegí una persona"),
        role_code: (value) => (value ? null : "Elegí un rol"),
      },
    },
  );

  // The roster, never the global account table: HU-6 is explicit that the
  // picker "nunca muestra usuarios de otros estudios ni de la tabla global".
  // Minus the people already on the work, whom the backend would refuse, and
  // minus those who left the studio, whose seat would grant nothing.
  const assigned = new Set(
    (team.data ?? []).map((member) => member.account_id),
  );
  const candidates = (roster.data ?? []).filter(
    (member) => member.is_active && !assigned.has(member.account_id),
  );

  const candidate = candidates.find(
    (member) => String(member.account_id) === form.values.account_id,
  );
  const isFirmClient = candidate?.role.code === FIRM_CLIENT;

  // A client of the studio is offered nothing but "Cliente" — HU-6: "el
  // desplegable ni siquiera le ofrece los otros". The backend refuses it too,
  // so this is about not proposing something that would be rejected.
  const roleOptions = (roles.data ?? [])
    .filter((role) => !isFirmClient || role.code === CLIENT)
    .map((role) => ({ value: role.code, label: role.name }));

  const currentLead = (team.data ?? []).find(
    (member) => member.role.code === LEAD,
  );

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitError(null);
    try {
      const added = await addMember.mutateAsync({
        account_id: Number(values.account_id),
        role_code: values.role_code as AssignableProjectRole,
      });
      const role = added.role.name.toLowerCase();
      notifications.show({
        title: "Miembro agregado",
        message: `${added.name} ahora es ${role} en ${project.name}.`,
        color: "obra",
      });
      onClose();
    } catch (error) {
      // The 409s to expect are rules worth reading as written: the person left
      // the studio while the form was open, or the work already has a client.
      setSubmitError(
        apiErrorMessage(error, "No pudimos agregar a esta persona."),
      );
    }
  });

  if (roster.isSuccess && team.isSuccess && candidates.length === 0) {
    return (
      <Stack gap="md">
        <Text size="sm">
          Todas las personas activas del padrón de {firm.name} ya están en el
          equipo de esta obra. Sumá a alguien al padrón para poder asignarlo.
        </Text>
        <Group justify="flex-end">
          <Button variant="subtle" onClick={onClose}>
            Cerrar
          </Button>
        </Group>
      </Stack>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        <Select
          label="Persona"
          placeholder={roster.isLoading ? "Cargando…" : "Elegí del padrón"}
          searchable
          data={candidates.map((member) => ({
            value: String(member.account_id),
            label: `${member.name} · ${member.role.name}`,
          }))}
          disabled={roster.isLoading || roster.isError}
          error={roster.isError ? "No pudimos cargar el padrón" : undefined}
          {...form.getInputProps("account_id")}
          onChange={(value) => {
            form.setFieldValue("account_id", value);
            const picked = candidates.find(
              (member) => String(member.account_id) === value,
            );
            // Their only possible role, chosen for them rather than left as an
            // empty select with one option in it.
            if (picked?.role.code === FIRM_CLIENT) {
              form.setFieldValue("role_code", CLIENT);
            }
          }}
        />

        <Select
          label="Rol en la obra"
          placeholder={roles.isLoading ? "Cargando…" : "Elegí un rol"}
          data={roleOptions}
          disabled={roles.isLoading || roles.isError || isFirmClient}
          description={
            isFirmClient
              ? "Un cliente del estudio solo puede participar como cliente."
              : undefined
          }
          error={roles.isError ? "No pudimos cargar los roles" : undefined}
          {...form.getInputProps("role_code")}
        />

        {form.values.role_code === LEAD && currentLead && (
          <Alert color="yellow" variant="light">
            {currentLead.account_id === account?.id
              ? "El rol de responsable se transfiere: vas a quedar como colaborador de esta obra."
              : `El rol de responsable se transfiere: ${currentLead.name} queda como colaborador.`}
          </Alert>
        )}

        <Group justify="flex-end" gap="sm">
          <Button
            variant="subtle"
            onClick={onClose}
            disabled={addMember.isPending}
          >
            Cancelar
          </Button>
          <Button type="submit" loading={addMember.isPending}>
            Agregar
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
