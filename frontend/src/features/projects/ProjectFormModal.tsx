import { useState } from "react";
import { useForm } from "@mantine/form";
import {
  Alert,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Textarea,
  TextInput,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { useCurrentFirm } from "../firms/firmContext";
import { useMembers } from "../members/useMembers";
import { apiErrorMessage } from "../../lib/apiError";
import { useCreateProject, useUpdateProject } from "./useProjects";
import type { ProjectOut, ProjectWrite } from "./types";

// The same limits the columns carry, so the usual mistakes are caught before a
// round trip. They are not the protection: the API validates every field again,
// and this only spares the architect a 422 whose English field errors would not
// help them.
const MAX_NAME = 150;
const MAX_ADDRESS = 255;

// The firm role whose holders may be the client of a work. HU-3 feeds this
// picker from "el padrón de mi estudio filtrado por rol client", and the
// backend refuses anyone else with a 409, so filtering here is what keeps the
// two agreeing rather than a convenience.
const FIRM_CLIENT = "client";

interface ProjectFormModalProps {
  opened: boolean;
  /** The work being edited, or null to create a new one. */
  project: ProjectOut | null;
  onClose: () => void;
}

interface FormValues {
  name: string;
  description: string;
  address: string;
  estimated_start_date: string | null;
  client_account_id: string | null;
}

/** HU-3's form, which is the same one for creating and for editing.
 *
 * One form because the backend has one shape for both: the edit is a PUT that
 * takes the whole work, so there is no field that only one of the two can
 * touch. Creating additionally puts the caller on the work as its lead, which
 * happens in the same transaction and needs nothing from here.
 *
 * The form lives in a child component so that it mounts fresh each time: its
 * initial values are that work's current ones, and a component that stayed
 * mounted between openings would need an effect to keep up. */
export function ProjectFormModal({
  opened,
  project,
  onClose,
}: ProjectFormModalProps) {
  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={project ? `Editar ${project.name}` : "Nueva obra"}
      centered
    >
      {opened && (
        <ProjectForm
          key={project?.id ?? "new"}
          project={project}
          onClose={onClose}
        />
      )}
    </Modal>
  );
}

function ProjectForm({
  project,
  onClose,
}: {
  project: ProjectOut | null;
  onClose: () => void;
}) {
  const { firm } = useCurrentFirm();
  // The roster of HU-2, which is where the clients of this firm already live.
  // No endpoint of its own: routes/members.py guards the listing with
  // member.view — a permission an architect holds — precisely so this picker
  // can be filled from it.
  const members = useMembers(firm.id);
  const createProject = useCreateProject(firm.id);
  const updateProject = useUpdateProject(firm.id);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const saving = createProject.isPending || updateProject.isPending;

  // Only active members, because someone who left the roster cannot be given a
  // role in a work: their assignment would be inert (ADR-002 section 11.3).
  const clients = (members.data ?? []).filter(
    (member) => member.is_active && member.role.code === FIRM_CLIENT,
  );
  const noClientsYet =
    !members.isLoading && !members.isError && clients.length === 0;

  const form = useForm<FormValues>({
    initialValues: {
      name: project?.name ?? "",
      description: project?.description ?? "",
      address: project?.address ?? "",
      estimated_start_date: project?.estimated_start_date ?? null,
      // Mantine's Select speaks strings; the payload turns it back into a
      // number below.
      client_account_id: project?.client?.account_id.toString() ?? null,
    },
    validate: {
      name: (value) => {
        const name = value.trim();
        if (name.length === 0) return "Ingresá el nombre de la obra";
        return name.length <= MAX_NAME
          ? null
          : `Como máximo ${MAX_NAME} caracteres`;
      },
      address: (value) =>
        value.trim().length <= MAX_ADDRESS
          ? null
          : `Como máximo ${MAX_ADDRESS} caracteres`,
    },
  });

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitError(null);

    // Empty means empty, in every field: the form sends the whole work, so a
    // cleared address is an address removed and not one left alone. That is
    // what makes the edit a PUT.
    const payload: ProjectWrite = {
      name: values.name.trim(),
      description: values.description.trim() || null,
      address: values.address.trim() || null,
      estimated_start_date: values.estimated_start_date,
      client_account_id: values.client_account_id
        ? Number(values.client_account_id)
        : null,
    };

    try {
      const saved = project
        ? await updateProject.mutateAsync({ projectId: project.id, payload })
        : await createProject.mutateAsync(payload);
      notifications.show({
        title: project ? "Obra actualizada" : "Obra creada",
        message: project
          ? `Guardamos los cambios de ${saved.name}.`
          : `${saved.name} ya forma parte de ${firm.name}.`,
        color: "obra",
      });
      onClose();
    } catch (error) {
      // Stays open with the message above the fields. The 409 to expect is
      // about the client — they left the roster, or they are not a client of
      // this firm — and its wording is the backend's, where the rule lives.
      setSubmitError(apiErrorMessage(error, "No pudimos guardar la obra."));
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

        <TextInput
          label="Nombre"
          placeholder="Casa Rodríguez"
          {...form.getInputProps("name")}
        />

        <TextInput
          label="Dirección"
          placeholder="Av. Siempreviva 742"
          {...form.getInputProps("address")}
        />

        {/* Its value is already a "YYYY-MM-DD" string in Mantine 9, the same
            shape the API uses, so nothing is converted in either direction.
            valueFormat only changes how it is displayed. */}
        <DateInput
          label="Inicio estimado"
          placeholder="DD/MM/AAAA"
          valueFormat="DD/MM/YYYY"
          clearable
          {...form.getInputProps("estimated_start_date")}
        />

        <Select
          label="Cliente"
          placeholder={
            members.isLoading
              ? "Cargando…"
              : noClientsYet
                ? "Todavía no hay clientes en el padrón"
                : "Elegí un cliente"
          }
          // HU-3: "El campo puede quedar vacío."
          clearable
          data={clients.map((member) => ({
            value: member.account_id.toString(),
            label: member.name,
          }))}
          disabled={members.isLoading || members.isError || noClientsYet}
          description={
            noClientsYet
              ? "Los clientes se dan de alta en el padrón del estudio."
              : undefined
          }
          error={members.isError ? "No pudimos cargar el padrón" : undefined}
          {...form.getInputProps("client_account_id")}
        />

        <Textarea
          label="Descripción"
          placeholder="Qué obra es, en pocas líneas."
          autosize
          minRows={2}
          maxRows={6}
          {...form.getInputProps("description")}
        />

        <Group justify="flex-end" gap="sm">
          <Button variant="subtle" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button type="submit" loading={saving}>
            {project ? "Guardar" : "Crear obra"}
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
