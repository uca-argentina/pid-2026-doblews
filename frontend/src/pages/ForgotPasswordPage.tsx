import { Anchor, Center, Paper, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";

// TODO: replace with the real support address before anyone outside the team
// sees this. Today it is the one app/db/seed_dev.py creates.
const SUPPORT_EMAIL = "soporte@warchitecture.test";

/** There is no self-service password recovery, and that is a decision rather
 * than a gap: HU-1 and ADR-004 both put it out of scope, and the platform has
 * no public sign-up either — a studio's owner (HU-2) or support (HU-7) creates
 * every account. Only the `support` platform role holds `account.reset_password`
 * (ADR-002 section 7), so this screen points there and nowhere else.
 *
 * It is a public route on purpose: whoever needs it cannot log in. */
export function ForgotPasswordPage() {
  return (
    <Center mih="100vh" px="md">
      <Paper withBorder shadow="sm" radius="md" p="xl" w={380} maw="100%">
        <Stack gap="lg">
          <Title order={2} ta="center">
            ¿Perdiste el acceso?
          </Title>

          <Text size="sm">
            Las cuentas de Warchitecture las crea el estudio que te incorpora, así que por
            ahora no hay una recuperación automática.
          </Text>

          <Text size="sm">
            Escribinos a <Anchor href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</Anchor>{" "}
            desde la dirección con la que iniciás sesión y te generamos una contraseña nueva.
          </Text>

          <Anchor component={Link} to="/login" size="sm" ta="center">
            Volver al inicio de sesión
          </Anchor>
        </Stack>
      </Paper>
    </Center>
  );
}
