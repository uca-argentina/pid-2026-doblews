import { useState } from "react";
import { useForm } from "@mantine/form";
import {
  Alert,
  Button,
  Group,
  Modal,
  PasswordInput,
  Select,
  Stack,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useCurrentFirm } from "../firms/firmContext";
import {
  validateEmail,
  validateName,
  validatePassword,
} from "../../lib/accountFields";
import { apiErrorMessage } from "../../lib/apiError";
import { useAddMember, useMemberRoles } from "./useMembers";
import type { AssignableFirmRole } from "./types";

interface AddMemberModalProps {
  opened: boolean;
  onClose: () => void;
}

interface FormValues {
  name: string;
  email: string;
  role_code: AssignableFirmRole | null;
  password: string;
}

/** HU-2's add form, which is also how someone who left comes back.
 *
 * One form for both because the backend has one endpoint for both, and
 * deliberately answers them identically: it never reveals whether an address
 * already has an account on the platform. That is also why the notice about
 * existing accounts is fixed text shown to everyone, rather than something the
 * UI says only when it happens. */
export function AddMemberModal({ opened, onClose }: AddMemberModalProps) {
  const { firm } = useCurrentFirm();
  const roles = useMemberRoles(firm.id);
  const addMember = useAddMember(firm.id);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<FormValues>({
    initialValues: { name: "", email: "", role_code: null, password: "" },
    validate: {
      name: validateName,
      email: validateEmail,
      role_code: (value) => (value ? null : "Elegí un rol"),
      password: validatePassword,
    },
  });

  const close = () => {
    form.reset();
    setSubmitError(null);
    onClose();
  };

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitError(null);
    try {
      const member = await addMember.mutateAsync({
        name: values.name.trim(),
        email: values.email.trim(),
        // Never null here: validate() has already run.
        role_code: values.role_code as AssignableFirmRole,
        password: values.password,
      });
      notifications.show({
        title: "Miembro agregado",
        // The stored name, not the typed one: if the address already had an
        // account, that account keeps its own name and this is what the
        // listing is about to show.
        message: `${member.name} ya forma parte de ${firm.name}.`,
        color: "obra",
      });
      close();
    } catch (error) {
      // Stays open with the message above the fields: a 409 ("ya es miembro")
      // is something the owner can fix without retyping everything.
      setSubmitError(
        apiErrorMessage(error, "No pudimos agregar a esta persona."),
      );
    }
  });

  return (
    <Modal opened={opened} onClose={close} title="Agregar miembro" centered>
      <form onSubmit={handleSubmit} noValidate>
        <Stack gap="md">
          {submitError && (
            <Alert color="red" variant="light" role="alert">
              {submitError}
            </Alert>
          )}

          <Alert color="gray" variant="light">
            Si esta persona ya tiene cuenta en Warchitecture, se suma con su
            nombre y contraseña actuales; lo que escribas acá se ignora.
          </Alert>

          <TextInput
            label="Nombre"
            placeholder="Nombre y apellido"
            {...form.getInputProps("name")}
          />

          <TextInput
            label="Email"
            placeholder="persona@estudio.com"
            {...form.getInputProps("email")}
          />

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

          <PasswordInput
            label="Contraseña inicial"
            description="Se la pasás vos: la app no manda mails."
            {...form.getInputProps("password")}
          />

          <Group justify="flex-end" gap="sm">
            <Button
              variant="subtle"
              onClick={close}
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
    </Modal>
  );
}
