import { useState } from "react";
import { useForm } from "@mantine/form";
import {
  Alert,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useCurrentFirm } from "../firms/firmContext";
import { apiErrorMessage } from "../../lib/apiError";
import { useAddMember, useMemberRoles } from "./useMembers";
import type { AssignableFirmRole, MemberOut } from "./types";

interface ReinstateMemberModalProps {
  /** The member being brought back, or null when the modal is closed. */
  member: MemberOut | null;
  onClose: () => void;
}

/** Thrown away the moment it is sent, and never used by anything.
 *
 * The add endpoint takes a password because it may have to create an account.
 * Here it never does: this person is on the roster, which means their account
 * exists, and accounts are never deleted — so the backend ignores whatever is
 * sent and their real password stays untouched. Asking the owner to invent one
 * would be asking for something that has no effect.
 *
 * Random rather than a constant so nothing can ever authenticate with it, in
 * the case this reasoning stops holding. */
function throwawayPassword(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join(
    "",
  );
}

/** Bringing back someone who left, which HU-2 resolves through the same add
 * endpoint: their roster row is reactivated and every project assignment they
 * had in this firm starts working again, untouched.
 *
 * Only the role is asked, because everything else is already known. */
export function ReinstateMemberModal({
  member,
  onClose,
}: ReinstateMemberModalProps) {
  return (
    <Modal
      opened={member !== null}
      onClose={onClose}
      title={member ? `Reincorporar a ${member.name}` : ""}
      centered
    >
      {member && <ReinstateForm member={member} onClose={onClose} />}
    </Modal>
  );
}

function ReinstateForm({
  member,
  onClose,
}: {
  member: MemberOut;
  onClose: () => void;
}) {
  const { firm } = useCurrentFirm();
  const roles = useMemberRoles(firm.id);
  const addMember = useAddMember(firm.id);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<{ role_code: string | null }>({
    // The role they had when they left: the likeliest answer, and still
    // changeable here.
    initialValues: { role_code: member.role.code },
    validate: { role_code: (value) => (value ? null : "Elegí un rol") },
  });

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitError(null);
    try {
      const restored = await addMember.mutateAsync({
        name: member.name,
        email: member.email,
        role_code: values.role_code as AssignableFirmRole,
        password: throwawayPassword(),
      });
      notifications.show({
        title: "Miembro reincorporado",
        message: `${restored.name} vuelve a formar parte de ${firm.name}.`,
        color: "obra",
      });
      onClose();
    } catch (error) {
      // The 409 to expect: coming back as a client while still holding a
      // non-client role in one of the firm's projects.
      setSubmitError(
        apiErrorMessage(error, "No pudimos reincorporar a esta persona."),
      );
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

        <Text size="sm">
          Vuelve a ver {firm.name} con su misma cuenta y su contraseña de
          siempre. Sus obras de este estudio vuelven como estaban.
        </Text>

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
            disabled={addMember.isPending}
          >
            Cancelar
          </Button>
          <Button type="submit" loading={addMember.isPending}>
            Reincorporar
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
