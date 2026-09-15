import { useState } from "react";
import { Alert, Button, Group, Modal, Select, Stack } from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { useAuth } from "../auth/AuthContext";
import { useCurrentFirm } from "../firms/firmContext";
import { useCurrentProject } from "../projects/projectContext";
import { useChangeTeamRole, useTeam, useTeamRoles } from "./useTeam";
import {
  LEAD,
  type AssignableProjectRole,
  type ProjectMemberOut,
} from "./types";

interface ChangeTeamRoleModalProps {
  /** The member being edited, or null when the modal is closed. */
  member: ProjectMemberOut | null;
  onClose: () => void;
}

/** HU-6's edit: the role on this work, and nothing else. The name and the
 * email belong to the person's account, so neither is offered here.
 *
 * The form lives in a child component so that it mounts fresh for each member:
 * its initial value is that member's current role, and a component that stayed
 * mounted between openings would need an effect to keep up. */
export function ChangeTeamRoleModal({
  member,
  onClose,
}: ChangeTeamRoleModalProps) {
  return (
    <Modal
      opened={member !== null}
      onClose={onClose}
      title={member ? `Cambiar el rol de ${member.name}` : ""}
      centered
    >
      {member && <ChangeTeamRoleForm member={member} onClose={onClose} />}
    </Modal>
  );
}

function ChangeTeamRoleForm({
  member,
  onClose,
}: {
  member: ProjectMemberOut;
  onClose: () => void;
}) {
  const { account } = useAuth();
  const { firm } = useCurrentFirm();
  const { project } = useCurrentProject();
  const team = useTeam(firm.id, project.id);
  const roles = useTeamRoles(firm.id, project.id);
  const changeRole = useChangeTeamRole(firm.id, project.id);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<{ role_code: string | null }>({
    // The role they hold now, so the select opens on the current answer and
    // the lead only has to change what they came to change.
    initialValues: { role_code: member.role.code },
    validate: { role_code: (value) => (value ? null : "Elegí un rol") },
  });

  const currentLead = (team.data ?? []).find(
    (other) => other.role.code === LEAD,
  );

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitError(null);
    try {
      const updated = await changeRole.mutateAsync({
        accountId: member.account_id,
        roleCode: values.role_code as AssignableProjectRole,
      });
      const role = updated.role.name.toLowerCase();
      notifications.show({
        title: "Rol actualizado",
        message: `${updated.name} ahora es ${role} en ${project.name}.`,
        color: "obra",
      });
      onClose();
    } catch (error) {
      // The 409 to expect: they became a client of the studio while this was
      // open, or the work already has a client. The backend's wording says so.
      setSubmitError(apiErrorMessage(error, "No pudimos cambiar el rol."));
    }
  });

  return (
    <form onSubmit={handleSubmit} noValidate>
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        <Select
          label="Rol en la obra"
          placeholder={roles.isLoading ? "Cargando…" : "Elegí un rol"}
          data={(roles.data ?? []).map((role) => ({
            value: role.code,
            label: role.name,
          }))}
          disabled={roles.isLoading || roles.isError}
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
            disabled={changeRole.isPending}
          >
            Cancelar
          </Button>
          <Button type="submit" loading={changeRole.isPending}>
            Guardar
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
