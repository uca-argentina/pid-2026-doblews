import { type FormEvent, useState } from "react";
import {
  Alert,
  Button,
  Group,
  Loader,
  Modal,
  NumberInput,
  Select,
  Stack,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { formatMoney, formatQuantity } from "../../lib/format";
import {
  useMaterialComparison,
  useProjectPurchasing,
} from "../purchasing/usePurchasing";
import { orderNumber } from "./orderDisplay";
import type { PurchaseOrderLineOut, PurchaseOrderOut } from "./types";
import {
  useAddLine,
  useChangeLineSupplier,
  useDiscardOrder,
  useUpdateLine,
} from "./usePurchaseOrders";

/** The four edits of a draft (HU-20), each its own modal. Every one is
 * mounted per opening, so it starts from the line as it is now. */

function Actions({
  pending,
  onCancel,
  submitLabel,
  color,
}: {
  pending: boolean;
  onCancel: () => void;
  submitLabel: string;
  color?: string;
}) {
  return (
    <Group justify="flex-end" gap="sm">
      <Button variant="subtle" onClick={onCancel} disabled={pending}>
        Cancelar
      </Button>
      <Button type="submit" loading={pending} color={color}>
        {submitLabel}
      </Button>
    </Group>
  );
}

/** A NumberInput's value as the decimal string the API takes, or null. */
function quantityString(value: number | string): string | null {
  return typeof value === "number" && value > 0 ? String(value) : null;
}

function QuantityField({
  value,
  onChange,
  unit,
}: {
  value: number | string;
  onChange: (value: number | string) => void;
  unit: string;
}) {
  return (
    <NumberInput
      label="Cantidad"
      description={`En ${unit}`}
      value={value}
      onChange={onChange}
      min={0}
      decimalScale={3}
      decimalSeparator=","
      thousandSeparator="."
      allowNegative={false}
      hideControls
      inputMode="decimal"
      data-autofocus
    />
  );
}

// --- quantity -------------------------------------------------------------

export function LineQuantityModal({
  firmId,
  order,
  line,
  onClose,
}: {
  firmId: number;
  order: PurchaseOrderOut;
  line: PurchaseOrderLineOut | null;
  onClose: () => void;
}) {
  return (
    <Modal
      opened={line !== null}
      onClose={onClose}
      title="Cambiar cantidad"
      centered
    >
      {line && (
        <QuantityForm
          firmId={firmId}
          order={order}
          line={line}
          onClose={onClose}
        />
      )}
    </Modal>
  );
}

function QuantityForm({
  firmId,
  order,
  line,
  onClose,
}: {
  firmId: number;
  order: PurchaseOrderOut;
  line: PurchaseOrderLineOut;
  onClose: () => void;
}) {
  const update = useUpdateLine(firmId, order.id);
  const [value, setValue] = useState<number | string>(Number(line.quantity));
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const quantity = quantityString(value);
    if (!quantity) {
      setError("Ingresá una cantidad mayor a cero.");
      return;
    }
    setError(null);
    try {
      await update.mutateAsync({ lineId: line.id, quantity });
      onClose();
    } catch (caught) {
      setError(apiErrorMessage(caught, "No pudimos cambiar la cantidad."));
    }
  };

  return (
    <form onSubmit={submit} noValidate>
      <Stack gap="md">
        {error && (
          <Alert color="red" variant="light" role="alert">
            {error}
          </Alert>
        )}
        <Text fw={600}>{line.resource.name}</Text>
        <QuantityField
          value={value}
          onChange={setValue}
          unit={line.unit.abbreviation}
        />
        <Text size="xs" c="dimmed">
          El precio no cambia: es el que tenía el proveedor al generar la orden.
        </Text>
        <Actions
          pending={update.isPending}
          onCancel={onClose}
          submitLabel="Guardar"
        />
      </Stack>
    </form>
  );
}

// --- supplier -------------------------------------------------------------

export function LineSupplierModal({
  firmId,
  order,
  line,
  onClose,
}: {
  firmId: number;
  order: PurchaseOrderOut;
  line: PurchaseOrderLineOut | null;
  onClose: () => void;
}) {
  return (
    <Modal
      opened={line !== null}
      onClose={onClose}
      title="Cambiar proveedor"
      centered
    >
      {line && (
        <SupplierForm
          firmId={firmId}
          order={order}
          line={line}
          onClose={onClose}
        />
      )}
    </Modal>
  );
}

/** Lists every supplier that offers the material, ranked for the line's
 * quantity by HU-18's own comparison, so the choice is made with the same
 * numbers the screen showed when the draft was generated. */
function SupplierForm({
  firmId,
  order,
  line,
  onClose,
}: {
  firmId: number;
  order: PurchaseOrderOut;
  line: PurchaseOrderLineOut;
  onClose: () => void;
}) {
  const comparison = useMaterialComparison(
    firmId,
    line.resource.id,
    String(Number(line.quantity)),
  );
  const change = useChangeLineSupplier(firmId, order.id);
  const [supplierId, setSupplierId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const options = (comparison.data?.offers ?? [])
    .filter((offer) => offer.supplier_id !== order.supplier.id)
    .map((offer) => ({
      value: String(offer.supplier_id),
      label: `${offer.supplier_name} — ${formatMoney(offer.total, order.currency)}${offer.cheapest ? " (más económico)" : ""}`,
    }));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!supplierId) {
      setError("Elegí un proveedor.");
      return;
    }
    setError(null);
    try {
      const target = await change.mutateAsync({
        lineId: line.id,
        supplierId: Number(supplierId),
      });
      notifications.show({
        title: "Renglón movido",
        message: `${line.resource.name} pasó a ${orderNumber(target.number)} (${target.supplier.name}).`,
        color: "obra",
      });
      onClose();
    } catch (caught) {
      setError(apiErrorMessage(caught, "No pudimos cambiar el proveedor."));
    }
  };

  return (
    <form onSubmit={submit} noValidate>
      <Stack gap="md">
        {error && (
          <Alert color="red" variant="light" role="alert">
            {error}
          </Alert>
        )}
        <Text size="sm">
          {line.resource.name}: {formatQuantity(line.quantity)}{" "}
          {line.unit.abbreviation}. Pasa al borrador de la obra para el
          proveedor que elijas, con su precio de hoy.
        </Text>
        {comparison.isLoading ? (
          <Loader size="sm" />
        ) : options.length === 0 ? (
          <Text size="sm" c="dimmed">
            Ningún otro proveedor del estudio ofrece este material.
          </Text>
        ) : (
          <Select
            label="Proveedor"
            placeholder="Elegí un proveedor"
            data={options}
            value={supplierId}
            onChange={setSupplierId}
            data-autofocus
          />
        )}
        <Actions
          pending={change.isPending}
          onCancel={onClose}
          submitLabel="Mover"
        />
      </Stack>
    </form>
  );
}

// --- add a material -----------------------------------------------------------

export function AddLineModal({
  firmId,
  order,
  opened,
  onClose,
}: {
  firmId: number;
  order: PurchaseOrderOut;
  opened: boolean;
  onClose: () => void;
}) {
  return (
    <Modal opened={opened} onClose={onClose} title="Agregar material" centered>
      {opened && (
        <AddLineForm firmId={firmId} order={order} onClose={onClose} />
      )}
    </Modal>
  );
}

/** Offers the materials of the work's take-off that this order's supplier
 * sells and the order does not have yet, read from the work's comparison.
 * That read needs to see the work's costs: an architect who is not on the
 * work gets the notice instead, and can still edit what is there. */
function AddLineForm({
  firmId,
  order,
  onClose,
}: {
  firmId: number;
  order: PurchaseOrderOut;
  onClose: () => void;
}) {
  const purchasing = useProjectPurchasing(firmId, order.project.id);
  const add = useAddLine(firmId, order.id);
  const [resourceId, setResourceId] = useState<string | null>(null);
  const [value, setValue] = useState<number | string>("");
  const [error, setError] = useState<string | null>(null);

  const inOrder = new Set(order.lines.map((line) => line.resource.id));
  const candidates = (purchasing.data?.items ?? []).filter(
    (item) =>
      !inOrder.has(item.resource_id) &&
      item.offers.some((offer) => offer.supplier_id === order.supplier.id),
  );
  const chosen = candidates.find(
    (item) => String(item.resource_id) === resourceId,
  );

  const pick = (id: string | null) => {
    setResourceId(id);
    const item = candidates.find((c) => String(c.resource_id) === id);
    if (item) {
      // What the work still needs, as generating would propose.
      const pending = Number(item.quantity) - Number(item.ordered_quantity);
      setValue(pending > 0 ? Number(pending.toFixed(3)) : "");
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const quantity = quantityString(value);
    if (!resourceId || !quantity) {
      setError("Elegí un material y una cantidad mayor a cero.");
      return;
    }
    setError(null);
    try {
      await add.mutateAsync({ resource_id: Number(resourceId), quantity });
      onClose();
    } catch (caught) {
      setError(apiErrorMessage(caught, "No pudimos agregar el material."));
    }
  };

  return (
    <form onSubmit={submit} noValidate>
      <Stack gap="md">
        {error && (
          <Alert color="red" variant="light" role="alert">
            {error}
          </Alert>
        )}
        {purchasing.isLoading && <Loader size="sm" />}
        {purchasing.isError && (
          <Text size="sm" c="dimmed">
            Para agregar materiales necesitás ver los costos de la obra.
          </Text>
        )}
        {purchasing.data && candidates.length === 0 && (
          <Text size="sm" c="dimmed">
            {order.supplier.name} no ofrece otros materiales del cómputo de esta
            obra.
          </Text>
        )}
        {candidates.length > 0 && (
          <>
            <Select
              label="Material del cómputo"
              placeholder="Elegí un material"
              data={candidates.map((item) => ({
                value: String(item.resource_id),
                label: `${item.name} (${item.unit.abbreviation})`,
              }))}
              value={resourceId}
              onChange={pick}
              searchable
              data-autofocus
            />
            <QuantityField
              value={value}
              onChange={setValue}
              unit={chosen?.unit.abbreviation ?? "la unidad del material"}
            />
          </>
        )}
        <Actions
          pending={add.isPending}
          onCancel={onClose}
          submitLabel="Agregar"
        />
      </Stack>
    </form>
  );
}

// --- discard ------------------------------------------------------------------

export function DiscardOrderModal({
  firmId,
  order,
  opened,
  onClose,
  onDiscarded,
}: {
  firmId: number;
  order: PurchaseOrderOut;
  opened: boolean;
  onClose: () => void;
  onDiscarded: () => void;
}) {
  const discard = useDiscardOrder(firmId);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await discard.mutateAsync(order.id);
      notifications.show({
        title: "Borrador descartado",
        message: `${orderNumber(order.number)} ya no está en las compras de la obra.`,
        color: "obra",
      });
      onDiscarded();
    } catch (caught) {
      setError(apiErrorMessage(caught, "No pudimos descartar el borrador."));
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={`Descartar ${orderNumber(order.number)}`}
      centered
    >
      <form onSubmit={submit} noValidate>
        <Stack gap="md">
          {error && (
            <Alert color="red" variant="light" role="alert">
              {error}
            </Alert>
          )}
          <Text size="sm">
            El borrador deja de existir y sus cantidades vuelven a quedar sin
            pedir: las podés generar de nuevo desde Compras.
          </Text>
          <Actions
            pending={discard.isPending}
            onCancel={onClose}
            submitLabel="Descartar"
            color="red"
          />
        </Stack>
      </form>
    </Modal>
  );
}
