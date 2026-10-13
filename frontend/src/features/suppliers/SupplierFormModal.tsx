import { useState } from "react";
import { useForm } from "@mantine/form";
import { Alert, Button, Group, Modal, Stack, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { useCurrentFirm } from "../firms/firmContext";
import {
  emptySupplier,
  supplierPayload,
  supplierToValues,
  supplierValidation,
  type SupplierValues,
} from "./supplierForm";
import { useCreateSupplier, useUpdateSupplier } from "./useSuppliers";
import type { SupplierOut } from "./types";

interface SupplierFormModalProps {
  opened: boolean;
  /** The supplier being edited, or null to create one. */
  supplier: SupplierOut | null;
  onClose: () => void;
  /** Called with the saved supplier, e.g. to open its list after creating. */
  onSaved?: (supplier: SupplierOut) => void;
}

/** HU-17's create and edit form for a supplier: a name, and whatever else the
 * architect knows. Only the name is required; a supplier is usable the moment
 * it has one. */
export function SupplierFormModal({
  opened,
  supplier,
  onClose,
  onSaved,
}: SupplierFormModalProps) {
  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={supplier ? "Editar proveedor" : "Nuevo proveedor"}
      centered
    >
      {/* Mounted per opening, so every open starts from the right values
          instead of whatever the last one left in the form. */}
      {opened && (
        <SupplierForm supplier={supplier} onClose={onClose} onSaved={onSaved} />
      )}
    </Modal>
  );
}

function SupplierForm({
  supplier,
  onClose,
  onSaved,
}: Omit<SupplierFormModalProps, "opened">) {
  const { firm } = useCurrentFirm();
  const create = useCreateSupplier(firm.id);
  const update = useUpdateSupplier(firm.id);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const pending = create.isPending || update.isPending;

  const form = useForm<SupplierValues>({
    initialValues: supplier ? supplierToValues(supplier) : emptySupplier,
    validate: supplierValidation,
  });

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitError(null);
    const payload = supplierPayload(values);
    try {
      const saved = supplier
        ? await update.mutateAsync({ supplierId: supplier.id, payload })
        : await create.mutateAsync(payload);
      notifications.show({
        title: supplier ? "Proveedor actualizado" : "Proveedor creado",
        message: saved.name,
        color: "obra",
      });
      onSaved?.(saved);
      onClose();
    } catch (error) {
      // The 409 to expect is a name the firm already uses; its text is the
      // backend's, and the form stays open so it can be fixed in place.
      setSubmitError(
        apiErrorMessage(error, "No pudimos guardar el proveedor."),
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

        <TextInput
          label="Nombre"
          placeholder="Corralón Norte"
          data-autofocus
          {...form.getInputProps("name")}
        />
        <TextInput
          label="Persona de contacto"
          description="Opcional."
          {...form.getInputProps("contact_name")}
        />
        <TextInput
          label="Email"
          description="Opcional."
          placeholder="ventas@corralon.com"
          {...form.getInputProps("contact_email")}
        />
        <TextInput
          label="Teléfono"
          description="Opcional."
          inputMode="tel"
          {...form.getInputProps("phone")}
        />
        <TextInput
          label="Dirección"
          description="Opcional."
          {...form.getInputProps("address")}
        />

        <Group justify="flex-end" gap="sm">
          <Button variant="subtle" onClick={onClose} disabled={pending}>
            Cancelar
          </Button>
          <Button type="submit" loading={pending}>
            {supplier ? "Guardar" : "Crear"}
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
