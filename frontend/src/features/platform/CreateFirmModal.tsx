import { useState } from "react";
import { useForm } from "@mantine/form";
import {
  Alert,
  Button,
  Divider,
  Group,
  Modal,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  useMantineTheme,
} from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import {
  validateEmail,
  validateName,
  validatePassword,
} from "../../lib/accountFields";
import { apiErrorMessage } from "../../lib/apiError";
import { useCreateFirm } from "./usePlatform";

// firm.phone is String(30) on the backend.
const MAX_PHONE = 30;

interface CreateFirmModalProps {
  opened: boolean;
  onClose: () => void;
}

interface FormValues {
  name: string;
  contactEmail: string;
  phone: string;
  ownerName: string;
  ownerEmail: string;
  ownerPassword: string;
}

const INITIAL_VALUES: FormValues = {
  name: "",
  contactEmail: "",
  phone: "",
  ownerName: "",
  ownerEmail: "",
  ownerPassword: "",
};

/** HU-7's firm creation: the firm and its owner, in one form and one request.
 *
 * One form and not two steps because ADR-002 section 10 does not allow a firm
 * without an owner, and a wizard that created the firm first would be exactly
 * that between its two steps.
 *
 * The notice about existing accounts is fixed text, as in AddMemberModal.
 * Unlike there, the outcome is also said afterwards: the backend answers with
 * owner.account_existed, since support is trusted to know whether the address
 * already had an account (ADR-002 section 10.2).
 *
 * Full screen on a phone, like AddLineModal: six fields and a keyboard do not
 * fit in a centered modal at 375px. */
export function CreateFirmModal({ opened, onClose }: CreateFirmModalProps) {
  const theme = useMantineTheme();
  const isPhone = useMediaQuery(`(max-width: ${theme.breakpoints.sm})`);
  const createFirm = useCreateFirm();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<FormValues>({
    initialValues: INITIAL_VALUES,
    validate: {
      name: (value) =>
        value.trim() ? validateName(value) : "Ingresá el nombre del estudio",
      contactEmail: validateEmail,
      phone: (value) =>
        value.trim().length <= MAX_PHONE
          ? null
          : `Como máximo ${MAX_PHONE} caracteres`,
      ownerName: validateName,
      ownerEmail: validateEmail,
      ownerPassword: validatePassword,
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
      const firm = await createFirm.mutateAsync({
        name: values.name.trim(),
        contact_email: values.contactEmail.trim(),
        phone: values.phone.trim(),
        owner: {
          name: values.ownerName.trim(),
          email: values.ownerEmail.trim(),
          password: values.ownerPassword,
        },
      });
      // Asked of the backend's flag, never guessed by comparing names: that
      // comparison is wrong exactly when support typed the person's real name,
      // and the typed password was ignored all the same.
      const { owner } = firm;
      notifications.show({
        title: "Estudio creado",
        message: owner.account_existed
          ? `${owner.email} ya tenía cuenta: quedó como propietario de ${firm.name} con su nombre (${owner.name}) y su contraseña de siempre. La que escribiste no se usó.`
          : `${firm.name} ya está en la plataforma, con ${owner.name} como propietario.`,
        color: "obra",
        // Stays until closed when it carries something support must act on:
        // not handing over a password that does not work.
        autoClose: owner.account_existed ? false : undefined,
      });
      close();
    } catch (error) {
      // Stays open with the message above the fields: a 409 (a support or a
      // deactivated account as owner) is fixed by changing one email, not by
      // retyping everything.
      setSubmitError(apiErrorMessage(error, "No pudimos crear el estudio."));
    }
  });

  return (
    <Modal
      opened={opened}
      onClose={close}
      title="Nuevo estudio"
      fullScreen={isPhone}
      size="lg"
      centered
    >
      <form onSubmit={handleSubmit} noValidate>
        <Stack gap="md">
          {submitError && (
            <Alert color="red" variant="light" role="alert">
              {submitError}
            </Alert>
          )}

          <TextInput
            label="Nombre del estudio"
            placeholder="Estudio Oeste"
            {...form.getInputProps("name")}
          />
          <TextInput
            label="Email de contacto"
            placeholder="contacto@estudio.com"
            {...form.getInputProps("contactEmail")}
          />
          <TextInput
            label="Teléfono"
            description="Opcional"
            placeholder="351 555-0000"
            {...form.getInputProps("phone")}
          />

          <Divider
            label="Propietario"
            labelPosition="left"
            mt="xs"
            styles={{ label: { fontSize: theme.fontSizes.sm } }}
          />
          <Text size="sm" c="dimmed">
            Un estudio no puede quedar sin propietario: se crean juntos.
          </Text>

          <Alert color="gray" variant="light">
            Si esta persona ya tiene cuenta en Warchitecture, queda como
            propietaria con su nombre y contraseña actuales; lo que escribas acá
            se ignora.
          </Alert>

          <TextInput
            label="Nombre"
            placeholder="Nombre y apellido"
            {...form.getInputProps("ownerName")}
          />
          <TextInput
            label="Email"
            placeholder="persona@estudio.com"
            {...form.getInputProps("ownerEmail")}
          />
          <PasswordInput
            label="Contraseña inicial"
            description="Se la pasás vos: la app no manda mails."
            {...form.getInputProps("ownerPassword")}
          />

          <Group justify="flex-end" gap="sm">
            <Button
              variant="subtle"
              onClick={close}
              disabled={createFirm.isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" loading={createFirm.isPending}>
              Crear estudio
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
