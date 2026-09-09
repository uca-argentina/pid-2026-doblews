import {
  createTheme,
  type CSSVariablesResolver,
  type MantineColorsTuple,
} from "@mantine/core";

// "Verde obra", the palette chosen in the design review.
//
// Shade 6 is the approved accent: it is what Mantine paints on a filled Button
// and on focus rings, because theme.primaryShade defaults to 6 in the light
// scheme. Shade 7 is its hover. The rest of the ramp is built around those two
// at an even lightness step, keeping hue and chroma in the same family.
const obra: MantineColorsTuple = [
  "#eef2ec",
  "#d5e0d0",
  "#b5c7af",
  "#94ab8d",
  "#76906f",
  "#5a7455",
  "#3f5b3c",
  "#334c2f",
  "#293e26",
  "#1f301d",
];

// Warm neutrals to sit under the olive.
//
// This overrides Mantine's stock `gray`, which is a cool blue-grey: it is what
// paints every card border, input border, placeholder and dimmed label in the
// app, and against a bone background it reads cold and slightly lilac. Same
// scale positions, so nothing that reads gray.4 needs to know it changed.
const stone: MantineColorsTuple = [
  "#f7f7f3",
  "#f2f2ec",
  "#e6e7dd",
  "#e0e1d6",
  "#d3d6cb",
  "#a3a79a",
  "#6b7266",
  "#4a5147",
  "#343a31",
  "#242b23",
];

export const theme = createTheme({
  primaryColor: "obra",
  colors: { obra, gray: stone },
});

// Two tokens that are not part of a colour scale.
//
// The page background is deliberately NOT set here: --mantine-color-body is
// also what Paper falls back to, so setting it would turn every card the same
// colour as the page and flatten the login card into its own background. It
// lives in index.css as a plain body rule instead.
export const cssVariablesResolver: CSSVariablesResolver = () => ({
  variables: {},
  light: {
    "--mantine-color-text": "#1a2019",
    "--mantine-color-dimmed": "#6b7266",
  },
  dark: {},
});
