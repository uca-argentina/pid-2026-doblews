import { type FormEvent, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Group,
  Modal,
  NumberInput,
  Stack,
  Text,
  Textarea,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import dayjs from "dayjs";
import { apiErrorMessage } from "../../lib/apiError";
import { formatMoney, formatQuantity } from "../../lib/format";
import { orderNumber } from "./orderDisplay";
import type {
  PurchaseOrderLineOut,
  PurchaseOrderOut,
  ReceiptLineIn,
} from "./types";
import { useRegisterReceipt } from "./usePurchaseOrders";

/** Registering what arrived of an order on a day (HU-22).
 *
 * Only the lines with something still owed are offered: a material already
 * complete has nothing left to receive, and showing it would invite a 409 the
 * form can avoid. Each quantity starts at what is pending, which is the common
 * case — the truck brought the rest — and the cost starts empty, because that
 * is the number the architect is reading off the remito.
 *
 * The freight is one field for the whole delivery, not one per material: that
 * is how a remito charges it (ADR-011 section 8).
 *
 * The calendar only opens on the days a delivery may claim — from the day the
 * order was placed to today — so the two rules the backend holds are visible in
 * the picker instead of arriving as a 409 after choosing. */

interface ReceiptModalProps {
  firmId: number;
  order: PurchaseOrderOut;
  opened: boolean;
  onClose: () => void;
}

/** What the form holds per line while it is being filled: both fields are
 * Mantine's "" for empty, so an untouched line is distinguishable from a zero. */
interface LineDraft {
  quantity: number | string;
  cost: number | string;
}

function pendingLines(order: PurchaseOrderOut): PurchaseOrderLineOut[] {
  return order.lines.filter((line) => Number(line.pending_quantity) > 0);
}

/** The day the order was issued, as the viewer's calendar reads it: the floor
 * of what a delivery may be dated. Taken from the history, which is where the
 * detail carries it, and undefined for an order with no issued event — which
 * cannot be received anyway, so the modal never opens on one. */
function issuedOn(order: PurchaseOrderOut): string | undefined {
  const issued = order.history.find((event) => event.kind === "issued");
  return issued ? dayjs(issued.at).format("YYYY-MM-DD") : undefined;
}

function initialDrafts(
  lines: PurchaseOrderLineOut[],
): Record<number, LineDraft> {
  return Object.fromEntries(
    lines.map((line) => [
      line.id,
      { quantity: Number(line.pending_quantity), cost: "" },
    ]),
  );
}

export function ReceiptModal({
  firmId,
  order,
  opened,
  onClose,
}: ReceiptModalProps) {
  const lines = pendingLines(order);
  const register = useRegisterReceipt(firmId, order.id);
  const today = dayjs().format("YYYY-MM-DD");
  const [receivedOn, setReceivedOn] = useState(today);
  const [note, setNote] = useState("");
  const [shipping, setShipping] = useState<number | string>("");
  const [drafts, setDrafts] = useState<Record<number, LineDraft>>(() =>
    initialDrafts(lines),
  );
  const [error, setError] = useState<string | null>(null);

  const close = () => {
    setError(null);
    onClose();
  };

  const edit = (lineId: number, change: Partial<LineDraft>) =>
    setDrafts((current) => ({
      ...current,
      [lineId]: { ...current[lineId], ...change },
    }));

  /** The rows the architect actually filled in, as the API takes them. */
  const filled: ReceiptLineIn[] = lines.flatMap((line) => {
    const draft = drafts[line.id];
    const quantity = Number(draft?.quantity);
    if (!draft || !quantity) return [];
    // A cost of zero is a real answer; an untouched field is "" and is what
    // `invalid` below refuses, so nothing empty reaches the API.
    return [
      {
        line_id: line.id,
        quantity: String(draft.quantity),
        actual_cost: String(draft.cost),
      },
    ];
  });

  /** The same two rules the backend holds, so the ordinary mistakes are caught
   * before a round trip. Everything else — the date, the ceiling across earlier
   * deliveries — comes back as a 409 with its own sentence. */
  const tooMuch = lines.filter(
    (line) =>
      Number(drafts[line.id]?.quantity ?? 0) > Number(line.pending_quantity),
  );
  const missingCost = filled.some((item) => {
    const draft = drafts[item.line_id];
    return draft?.cost === "";
  });
  const invalid = filled.length === 0 || tooMuch.length > 0 || missingCost;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await register.mutateAsync({
        received_on: receivedOn,
        note: note.trim() === "" ? null : note.trim(),
        shipping_cost: shipping === "" ? null : String(shipping),
        lines: filled,
      });
      notifications.show({
        title: "Recepción registrada",
        message: `Quedó registrado lo que llegó de ${orderNumber(order.number)}.`,
        color: "obra",
      });
      close();
    } catch (caught) {
      setError(apiErrorMessage(caught, "No pudimos registrar la recepción."));
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={close}
      title={`Registrar recepción de ${orderNumber(order.number)}`}
      centered
      size="lg"
    >
      <form onSubmit={submit} noValidate>
        <Stack gap="md">
          {error && (
            <Alert color="red" variant="light" role="alert">
              {error}
            </Alert>
          )}

          <DateInput
            label="Fecha de la entrega"
            description="El día que llegó la mercadería, según el remito."
            placeholder="DD/MM/AAAA"
            valueFormat="DD/MM/YYYY"
            value={receivedOn}
            onChange={(value) => setReceivedOn(value ?? "")}
            minDate={issuedOn(order)}
            maxDate={today}
            error={receivedOn ? undefined : "Elegí una fecha"}
            data-autofocus
          />

          <Stack gap="sm">
            <Text fw={600} size="sm">
              Qué llegó
            </Text>
            {lines.map((line) => (
              <Card key={line.id} withBorder padding="sm" radius="md">
                <Stack gap="xs">
                  <Group justify="space-between" align="baseline" wrap="nowrap">
                    <Text fw={600} size="sm">
                      {line.resource.name}
                    </Text>
                    <Text size="xs" c="dimmed">
                      Pendiente {formatQuantity(line.pending_quantity)}{" "}
                      {line.unit.abbreviation}
                    </Text>
                  </Group>
                  <Group grow align="flex-start" wrap="wrap">
                    <NumberInput
                      label="Cantidad recibida"
                      description={`En ${line.unit.abbreviation}`}
                      value={drafts[line.id]?.quantity ?? ""}
                      onChange={(value) => edit(line.id, { quantity: value })}
                      error={
                        Number(drafts[line.id]?.quantity ?? 0) >
                        Number(line.pending_quantity)
                          ? "Más de lo que falta recibir"
                          : undefined
                      }
                      min={0}
                      decimalScale={3}
                      decimalSeparator=","
                      thousandSeparator="."
                      allowNegative={false}
                      hideControls
                      inputMode="decimal"
                    />
                    <NumberInput
                      label="Costo real"
                      description={`Acordado: ${formatMoney(line.unit_price, order.currency)} por ${line.unit.abbreviation}`}
                      value={drafts[line.id]?.cost ?? ""}
                      onChange={(value) => edit(line.id, { cost: value })}
                      min={0}
                      decimalScale={2}
                      decimalSeparator=","
                      thousandSeparator="."
                      allowNegative={false}
                      hideControls
                      inputMode="decimal"
                    />
                  </Group>
                </Stack>
              </Card>
            ))}
            <Text size="xs" c="dimmed">
              El costo real es lo que facturaron por ese material en esta
              entrega, sin el envío. Lo que no llegó se deja en cero y se
              registra en otra recepción.
            </Text>
          </Stack>

          <NumberInput
            label="Envío de esta entrega"
            description="Opcional. Lo que cobraron por traerla, una sola vez para toda la entrega."
            value={shipping}
            onChange={setShipping}
            min={0}
            decimalScale={2}
            decimalSeparator=","
            thousandSeparator="."
            allowNegative={false}
            hideControls
            inputMode="decimal"
          />

          <Textarea
            label="Nota"
            description="Opcional. El número de remito, por ejemplo."
            maxLength={150}
            autosize
            minRows={1}
            value={note}
            onChange={(event) => setNote(event.currentTarget.value)}
          />

          <Group justify="flex-end" gap="sm">
            <Button
              variant="subtle"
              onClick={close}
              disabled={register.isPending}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              loading={register.isPending}
              disabled={invalid}
            >
              Registrar
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
