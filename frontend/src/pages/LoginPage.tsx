import { useState } from "react";
import { useForm } from "@mantine/form";
import {
  Alert,
  Anchor,
  Button,
  Center,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import {
  Link,
  useLocation,
  useNavigate,
  type Location,
} from "react-router-dom";
import { isAxiosError } from "axios";
import { useAuth } from "../features/auth/AuthContext";
import { resolveHomePath } from "../features/auth/navigation";
import { CONNECTION_ERROR } from "../lib/apiError";

// Same string the backend returns for every way a login can fail (see
// backend/app/api/routes/auth.py) — kept as a constant here too, rather than
// read off the response body, so a network failure that never reaches the
// backend still shows something sensible instead of an empty message.
const INVALID_CREDENTIALS = "Email o contraseña incorrectos";

interface LocationState {
  from?: Location;
}

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const form = useForm({
    initialValues: { email: "", password: "" },
    validate: {
      email: (value) =>
        /^\S+@\S+\.\S+$/.test(value) ? null : "Ingresá un email válido",
      password: (value) => (value.length > 0 ? null : "Ingresá tu contraseña"),
    },
  });

  const handleSubmit = form.onSubmit(async ({ email, password }) => {
    setSubmitError(null);
    setSubmitting(true);
    try {
      const account = await login(email, password);
      const state = location.state as LocationState | null;
      const destination = state?.from?.pathname ?? resolveHomePath(account);
      navigate(destination, { replace: true });
    } catch (error) {
      if (isAxiosError(error) && error.response?.status === 401) {
        setSubmitError(INVALID_CREDENTIALS);
      } else {
        setSubmitError(CONNECTION_ERROR);
      }
    } finally {
      setSubmitting(false);
    }
  });

  return (
    <Center mih="100vh" px="md">
      <Paper withBorder shadow="sm" radius="md" p="xl" w={380} maw="100%">
        <Stack gap="lg">
          <div>
            <Title order={2} ta="center">
              Warchitecture
            </Title>
            <Text ta="center" c="dimmed" size="sm">
              Iniciá sesión para ver tus obras
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
                label="Email"
                placeholder="tu@estudio.com"
                autoComplete="email"
                {...form.getInputProps("email")}
              />

              <PasswordInput
                label="Contraseña"
                placeholder="Tu contraseña"
                autoComplete="current-password"
                {...form.getInputProps("password")}
              />

              <Button type="submit" fullWidth loading={submitting}>
                Iniciar sesión
              </Button>
            </Stack>
          </form>

          <Anchor
            component={Link}
            to="/forgot-password"
            size="sm"
            c="dimmed"
            ta="center"
          >
            ¿Olvidaste tu contraseña?
          </Anchor>
        </Stack>
      </Paper>
    </Center>
  );
}
