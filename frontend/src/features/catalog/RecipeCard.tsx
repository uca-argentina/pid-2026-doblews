import type { ReactNode } from "react";
import {
  Badge,
  Button,
  Card,
  Collapse,
  Group,
  Stack,
  Text,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { formatMoney, formatQuantity } from "../../lib/format";
import type { RecipeOut } from "./types";

interface RecipeCardProps {
  recipe: RecipeOut;
  /** Something to do with this recipe, shown at the foot of the card. HU-5's
   * picker puts its "Agregar" button here; HU-9's catalogue, the edit and
   * deactivate menu of the firm's own recipes. */
  action?: ReactNode;
  /** Whether to badge where the recipe comes from (HU-9). On by default: a
   * firm's catalogue and HU-5's picker mix both origins. */
  showOrigin?: boolean;
}

const ORIGIN_LABEL = { general: "General", firm: "Del estudio" } as const;

/** One recipe: what it is, what it is measured in, and — on demand — what one
 * unit of it takes.
 *
 * A card at every width, not a table row, because a recipe is two levels deep
 * and a table has one. The lines start folded: with the list open the
 * catalogue is a wall of numbers, and the name and description are usually
 * enough to tell recipes apart. Unfolding is what someone does to compare two
 * similar ones before choosing. */
export function RecipeCard({
  recipe,
  action,
  showOrigin = true,
}: RecipeCardProps) {
  const [opened, lines] = useDisclosure(false);

  return (
    <Card withBorder padding="md" radius="md">
      <Stack gap="xs">
        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <Text fw={600}>{recipe.name}</Text>
          {/* The unit a quantity of this recipe is typed in — what HU-5 asks
              for right after choosing it. */}
          <Badge variant="light" style={{ flexShrink: 0 }}>
            por {recipe.unit.abbreviation}
          </Badge>
        </Group>

        {showOrigin && (
          // In a Group so the badge keeps its own width: Stack stretches its
          // children. Filled for the firm's own, so they stand out among the
          // general ones they share the list with.
          <Group>
            <Badge
              size="sm"
              variant={recipe.origin === "firm" ? "filled" : "outline"}
              color={recipe.origin === "firm" ? "obra" : "gray"}
            >
              {ORIGIN_LABEL[recipe.origin]}
            </Badge>
          </Group>
        )}

        {recipe.description && (
          <Text size="sm" c="dimmed" lineClamp={opened ? undefined : 2}>
            {recipe.description}
          </Text>
        )}

        <Group justify="space-between" gap="xs">
          <Button
            variant="subtle"
            size="compact-sm"
            px={0}
            onClick={lines.toggle}
            aria-expanded={opened}
          >
            {opened
              ? "Ocultar materiales"
              : `Ver materiales (${recipe.lines.length})`}
          </Button>
          {action}
        </Group>

        <Collapse expanded={opened}>
          <Stack gap={6}>
            {recipe.lines.map((line) => (
              // Quantity first, because it is what the line says: "60 u of
              // brick per m2". The price is the material's, per its own unit.
              <Group
                key={line.resource_id}
                justify="space-between"
                gap="xs"
                wrap="nowrap"
              >
                <Text size="sm">
                  <Text span fw={500}>
                    {formatQuantity(line.quantity_per_unit)}{" "}
                    {line.unit.abbreviation}
                  </Text>{" "}
                  {line.name}
                </Text>
                <Text size="sm" c="dimmed" style={{ whiteSpace: "nowrap" }}>
                  {formatMoney(line.reference_price, line.currency)}/
                  {line.unit.abbreviation}
                </Text>
              </Group>
            ))}
          </Stack>
        </Collapse>
      </Stack>
    </Card>
  );
}
