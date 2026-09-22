import { useState } from "react";
import { useForm } from "@mantine/form";
import { Alert, Button, Group, Modal, Select, Stack } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useCurrentFirm } from "../firms/firmContext";
import { apiErrorMessage } from "../../lib/apiError";
import { useChangeMemberRole, useMemberRoles } from "./useMembers";
import type { AssignableFirmRole, MemberOut } from "./types";

interface ChangeRoleModalProps {
  /** The member being edited, or null when the modal is closed. */
  member: MemberOut | null;
  onClose: () => void;
}

/** HU-2's edit: the role, and nothing else. The email is the person's global
 * identity and the name belongs to their account, so neither is offered here.
 *
 * The form lives in a child component so that it mounts fresh for each member:
 * its initial value is that member's current role, and a component that stayed
 * mounted between openings would need an effect to keep up. */
export function ChangeRoleModal({ member, onClose }: ChangeRoleModalProps) {
  return (
    <Modal
      opened={member !== null}
      onClose={onClose}
      title={member ? `Cambiar rol de ${member.name}` : ""}
      centered
    >
      {member && <ChangeRoleForm member={member} onClose={onClose} />}
    </Modal>
  );
}

function ChangeRoleForm({
  member,
  onClose,
}: {
  member: MemberOut;
  onClose: () => void;
}) {
  const { firm } = useCurrentFirm();
  const roles = useMemberRoles(firm.id);
  const changeRole = useChangeMemberRole(firm.id);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<{ role_code: string | null }>({
    // The role they hold now, so the select opens on the current answer and
    // the owner only has to change what they came to change.
    initialValues: { role_code: member.role.code },
    validate: { role_code: (value) => (value ? null : "Elegí un rol") },
  });

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitError(null);
    try {
      const updated = await changeRole.mutateAsync({
        accountId: member.account_id,
        roleCode: values.role_code as AssignableFirmRole,
      });
      // Pulled out so the message below fits on one line: prettier 3.1.0, the
      // version the pre-commit hook pins, breaks a longer template literal
      // across lines and the local 3.9.6 joins it back, so the two rewrite
      // each other on every commit.
      const role = updated.role.name.toLowerCase();
      notifications.show({
        title: "Rol actualizado",
        message: `${updated.name} ahora es ${role} en ${firm.name}.`,
        color: "obra",
      });
      onClose();
    } catch (error) {
      // The 409 here is a rule worth reading: a lead cannot become a client
      // until they are off that project. The backend's own wording says so.
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
          label="Rol en el estudio"
          placeholder={roles.isLoading ? "Cargando…" : "Elegí un rol"}
          data={(roles.data ?? []).map((role) => ({
            value: role.code,
            label: role.name,
          }))}
          disabled={roles.isLoading || roles.isError}
          error={roles.isError ? "No pudimos cargar los roles" : undefined}
          {...form.getInputProps("role_code")}
        />

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
