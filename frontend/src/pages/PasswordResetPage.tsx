import { useState } from "react";
import { useForm } from "@mantine/form";
import {
  Alert,
  Button,
  Group,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { isAxiosError } from "axios";
import { validateEmail, validatePassword } from "../lib/accountFields";
import { apiErrorMessage } from "../lib/apiError";
import { useResetPassword } from "../features/platform/usePlatform";

interface FormValues {
  email: string;
  password: string;
}

// The backend answers 404 both for an unknown address and for a staff account,
// which support may not reset (ADR-002 section 10.2). One message for both, as
// the API gives one answer for both.
const ACCOUNT_NOT_FOUND = "No hay una cuenta con ese email.";

/** HU-7: "Puedo resetear la contraseña de un usuario".
 *
 * A screen of its own rather than an action on a firm row: support starts from
 * the address the person gives, and the account may belong to several firms or
 * to none. The new password is typed here and handed over in person, as every
 * first password is in this application: there is no recovery email.
 *
 * A form on a page, not a modal, so it is reachable from the sidebar and fits a
 * phone without a full-screen dialog. It stays on the screen after a reset,
 * emptied, since resetting several accounts in a row is the likely case. */
export function PasswordResetPage() {
  const resetPassword = useResetPassword();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<FormValues>({
    initialValues: { email: "", password: "" },
    validate: { email: validateEmail, password: validatePassword },
  });

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitError(null);
    const email = values.email.trim();
    try {
      await resetPassword.mutateAsync({ email, password: values.password });
      notifications.show({
        title: "Contraseña cambiada",
        message: `${email} ya puede entrar con la contraseña nueva.`,
        color: "obra",
      });
      form.reset();
    } catch (error) {
      // A 404 is the one refusal support can act on here — a mistyped address
      // — so it gets its own message. apiErrorMessage only passes 409s through.
      setSubmitError(
        isAxiosError(error) && error.response?.status === 404
          ? ACCOUNT_NOT_FOUND
          : apiErrorMessage(error, "No pudimos cambiar la contraseña."),
      );
    }
  });

  return (
    <Stack gap="md" maw={480}>
      <div>
        <Title order={3}>Resetear contraseña</Title>
        <Text c="dimmed" size="sm">
          Le das una contraseña nueva a una cuenta. Se la pasás vos: la app no
          manda mails.
        </Text>
      </div>

      <form onSubmit={handleSubmit} noValidate>
        <Stack gap="md">
          {submitError && (
            <Alert color="red" variant="light" role="alert">
              {submitError}
            </Alert>
          )}

          <TextInput
            label="Email de la cuenta"
            placeholder="persona@estudio.com"
            {...form.getInputProps("email")}
          />
          <PasswordInput
            label="Contraseña nueva"
            description="Reemplaza la actual. La sesión que ya tenga abierta sigue abierta."
            {...form.getInputProps("password")}
          />

          <Group justify="flex-end">
            <Button type="submit" loading={resetPassword.isPending}>
              Cambiar contraseña
            </Button>
          </Group>
        </Stack>
      </form>
    </Stack>
  );
}
