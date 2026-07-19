#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const width = 2560;
const height = 1600;

const outPath = process.argv[2] || "wallpapers/source/ducktop-hud-native.svg";
const outDir = path.dirname(outPath);

const c = {
  black: "#080a0c",
  graphite: "#101418",
  panel: "#161b20",
  panelHigh: "#20262c",
  text: "#e4e8e6",
  muted: "#8b949b",
  amber: "#ffb000",
  amberDim: "#9c6d00",
  cyan: "#00d7ff",
  cyanDim: "#007d96",
  red: "#ff4d4f"
};

function attrs(values = {}) {
  return Object.entries(values)
    .filter(([, value]) => value !== undefined && value !== null && value !== false)
    .map(([key, value]) => `${key}="${String(value)}"`)
    .join(" ");
}

function tag(name, values = {}, body = "") {
  const a = attrs(values);
  if (body === "") return `<${name}${a ? ` ${a}` : ""}/>`;
  return `<${name}${a ? ` ${a}` : ""}>${body}</${name}>`;
}

function line(x1, y1, x2, y2, values = {}) {
  return tag("line", { x1, y1, x2, y2, ...values });
}

function rect(x, y, w, h, values = {}) {
  return tag("rect", { x, y, width: w, height: h, ...values });
}

function circle(cx, cy, r, values = {}) {
  return tag("circle", { cx, cy, r, ...values });
}

function poly(points, values = {}) {
  return tag("polyline", { points: points.map(([x, y]) => `${x},${y}`).join(" "), ...values });
}

function pathEl(d, values = {}) {
  return tag("path", { d, ...values });
}

function panelPath(x, y, w, h, cuts = {}) {
  const tl = cuts.tl ?? 32;
  const tr = cuts.tr ?? 32;
  const br = cuts.br ?? 32;
  const bl = cuts.bl ?? 32;
  return [
    `M ${x + tl} ${y}`,
    `H ${x + w - tr}`,
    `L ${x + w} ${y + tr}`,
    `V ${y + h - br}`,
    `L ${x + w - br} ${y + h}`,
    `H ${x + bl}`,
    `L ${x} ${y + h - bl}`,
    `V ${y + tl}`,
    "Z"
  ].join(" ");
}

function panel(x, y, w, h, cuts = {}, values = {}) {
  return pathEl(panelPath(x, y, w, h, cuts), {
    fill: "none",
    stroke: c.amberDim,
    "stroke-width": 2,
    "vector-effect": "non-scaling-stroke",
    ...values
  });
}

function filledPanel(x, y, w, h, cuts = {}, values = {}) {
  return pathEl(panelPath(x, y, w, h, cuts), {
    fill: c.panel,
    "fill-opacity": 0.24,
    stroke: c.panelHigh,
    "stroke-width": 1,
    "vector-effect": "non-scaling-stroke",
    ...values
  });
}

function tickGroup(x, y, count, step, len, vertical = false, stroke = c.amber, opacity = 0.85) {
  const out = [];
  for (let i = 0; i < count; i += 1) {
    const dx = vertical ? 0 : i * step;
    const dy = vertical ? i * step : 0;
    out.push(line(x + dx, y + dy, x + dx + (vertical ? 0 : len), y + dy + (vertical ? len : 0), {
      stroke,
      "stroke-width": 3,
      "stroke-linecap": "round",
      opacity
    }));
  }
  return out.join("\n");
}

function dotRow(x, y, count, step, fill = c.cyan, opacity = 0.8) {
  const out = [];
  for (let i = 0; i < count; i += 1) {
    out.push(rect(x + i * step, y, 4, 4, { fill, opacity }));
  }
  return out.join("\n");
}

function grid(x, y, w, h, step, stroke = c.cyanDim, opacity = 0.16) {
  const out = [rect(x, y, w, h, { fill: "url(#panelGrid)", opacity: 0.5 })];
  for (let gx = x; gx <= x + w; gx += step) {
    out.push(line(gx, y, gx, y + h, { stroke, "stroke-width": 1, opacity }));
  }
  for (let gy = y; gy <= y + h; gy += step) {
    out.push(line(x, gy, x + w, gy, { stroke, "stroke-width": 1, opacity }));
  }
  return out.join("\n");
}

function cornerBrackets(x, y, w, h, size = 44, stroke = c.cyan, opacity = 0.92) {
  return [
    line(x, y + size, x, y, { stroke, "stroke-width": 3, opacity }),
    line(x, y, x + size, y, { stroke, "stroke-width": 3, opacity }),
    line(x + w - size, y, x + w, y, { stroke, "stroke-width": 3, opacity }),
    line(x + w, y, x + w, y + size, { stroke, "stroke-width": 3, opacity }),
    line(x, y + h - size, x, y + h, { stroke, "stroke-width": 3, opacity }),
    line(x, y + h, x + size, y + h, { stroke, "stroke-width": 3, opacity }),
    line(x + w - size, y + h, x + w, y + h, { stroke, "stroke-width": 3, opacity }),
    line(x + w, y + h - size, x + w, y + h, { stroke, "stroke-width": 3, opacity })
  ].join("\n");
}

const g = [];

g.push(`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" shape-rendering="geometricPrecision">`);
g.push(`<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="${c.black}"/>
    <stop offset="0.45" stop-color="${c.graphite}"/>
    <stop offset="1" stop-color="${c.black}"/>
  </linearGradient>
  <radialGradient id="rightGlow" cx="82%" cy="48%" r="46%">
    <stop offset="0" stop-color="${c.cyan}" stop-opacity="0.08"/>
    <stop offset="0.55" stop-color="${c.amber}" stop-opacity="0.045"/>
    <stop offset="1" stop-color="${c.black}" stop-opacity="0"/>
  </radialGradient>
  <pattern id="microDots" width="10" height="10" patternUnits="userSpaceOnUse">
    <rect width="10" height="10" fill="none"/>
    <rect x="1" y="1" width="1" height="1" fill="#ffffff" opacity="0.07"/>
  </pattern>
  <pattern id="panelGrid" width="28" height="28" patternUnits="userSpaceOnUse">
    <path d="M 28 0 H 0 V 28" fill="none" stroke="${c.cyanDim}" stroke-width="1" opacity="0.16"/>
  </pattern>
</defs>`);

g.push(rect(0, 0, width, height, { fill: "url(#bg)" }));
g.push(rect(0, 0, width, height, { fill: "url(#microDots)", opacity: 0.55 }));
g.push(rect(0, 0, width, height, { fill: "url(#rightGlow)" }));

g.push(`<g id="subtle-background" fill="none" stroke-linecap="round" stroke-linejoin="round">`);
g.push(line(240, 220, 1260, 220, { stroke: c.panelHigh, "stroke-width": 2, opacity: 0.38 }));
g.push(line(1260, 220, 1330, 174, { stroke: c.panelHigh, "stroke-width": 2, opacity: 0.28 }));
g.push(line(312, 1306, 1704, 1306, { stroke: c.panelHigh, "stroke-width": 2, opacity: 0.42 }));
g.push(line(1038, 112, 1458, 112, { stroke: c.panelHigh, "stroke-width": 2, opacity: 0.33 }));
g.push(line(1478, 112, 1544, 70, { stroke: c.panelHigh, "stroke-width": 2, opacity: 0.28 }));
g.push(line(1760, 76, 2400, 76, { stroke: c.panelHigh, "stroke-width": 2, opacity: 0.36 }));
g.push(line(1800, 1422, 2460, 1422, { stroke: c.panelHigh, "stroke-width": 2, opacity: 0.36 }));
g.push(pathEl("M 640 832 C 742 780 842 902 958 846 C 1038 808 1098 846 1184 806", {
  stroke: c.panelHigh,
  "stroke-width": 1,
  opacity: 0.18
}));
g.push(`</g>`);

g.push(`<g id="main-left-frame" fill="none" stroke-linecap="round" stroke-linejoin="round">`);
g.push(pathEl([
  "M 72 488",
  "V 188",
  "L 142 118",
  "H 274",
  "M 392 118 H 1120",
  "L 1164 88",
  "H 1552",
  "L 1594 118",
  "H 1672",
  "M 1672 118 V 1410",
  "L 1630 1452",
  "H 732",
  "L 678 1416",
  "H 358",
  "L 306 1452",
  "H 82",
  "V 616"
].join(" "), {
  stroke: c.panelHigh,
  "stroke-width": 3,
  opacity: 0.62
}));
g.push(pathEl([
  "M 44 514",
  "V 166",
  "L 126 84",
  "H 274",
  "M 348 84 H 1122",
  "L 1168 54",
  "H 1586",
  "L 1640 92",
  "H 1720",
  "M 1720 92 V 1436",
  "L 1666 1490",
  "H 728",
  "L 668 1450",
  "H 372",
  "L 320 1490",
  "H 44",
  "V 648"
].join(" "), {
  stroke: c.amberDim,
  "stroke-width": 2,
  opacity: 0.92
}));
g.push(pathEl("M 48 156 L 132 72 H 268", { stroke: c.amber, "stroke-width": 3, opacity: 0.95 }));
g.push(pathEl("M 374 1460 H 660 L 716 1496 H 1420", { stroke: c.cyan, "stroke-width": 3, opacity: 0.8 }));
g.push(tickGroup(174, 1384, 4, 18, 7, false, c.amber, 0.9));
g.push(tickGroup(54, 1004, 4, 18, 7, true, c.amber, 0.86));
g.push(tickGroup(66, 442, 2, 120, 28, true, c.cyan, 0.8));
g.push(circle(64, 1260, 12, { stroke: c.amberDim, "stroke-width": 2, fill: "none", opacity: 0.7 }));
g.push(circle(64, 1260, 4, { fill: c.amber, opacity: 0.8 }));
g.push(`</g>`);

g.push(`<g id="right-panels" fill="none" stroke-linecap="round" stroke-linejoin="round">`);
g.push(filledPanel(1788, 98, 676, 506, { tl: 64, tr: 18, br: 70, bl: 44 }, { opacity: 0.72 }));
g.push(panel(1846, 176, 552, 336, { tl: 28, tr: 16, br: 28, bl: 40 }, { stroke: c.amber, opacity: 0.82 }));
g.push(grid(1876, 212, 492, 264, 28, c.cyanDim, 0.11));
g.push(cornerBrackets(1846, 176, 552, 336, 34, c.amber, 0.55));
g.push(tickGroup(2268, 118, 5, 18, 6, false, c.cyan, 0.88));
g.push(tickGroup(1816, 372, 3, 16, 5, true, c.amber, 0.85));
g.push(pathEl("M 1838 122 L 1890 70 H 1964", { stroke: c.amber, "stroke-width": 3, opacity: 0.86 }));

g.push(filledPanel(1728, 660, 352, 316, { tl: 24, tr: 8, br: 36, bl: 16 }, { opacity: 0.76 }));
g.push(panel(1764, 700, 272, 206, { tl: 16, tr: 4, br: 22, bl: 22 }, { stroke: c.amber, opacity: 0.75 }));
g.push(rect(1798, 728, 200, 92, { fill: "url(#microDots)", opacity: 0.5 }));
g.push(cornerBrackets(1764, 700, 272, 206, 26, c.amber, 0.4));

g.push(filledPanel(2110, 666, 304, 312, { tl: 16, tr: 18, br: 22, bl: 16 }, { opacity: 0.76 }));
g.push(panel(2134, 704, 242, 224, { tl: 16, tr: 16, br: 16, bl: 16 }, { stroke: c.cyan, opacity: 0.72 }));
g.push(grid(2158, 728, 194, 176, 22, c.cyanDim, 0.18));
g.push(cornerBrackets(2134, 704, 242, 224, 28, c.cyan, 0.75));

g.push(filledPanel(1694, 1022, 780, 350, { tl: 22, tr: 34, br: 16, bl: 40 }, { opacity: 0.78 }));
g.push(panel(1744, 1070, 652, 214, { tl: 20, tr: 28, br: 18, bl: 18 }, { stroke: c.amberDim, opacity: 0.75 }));
g.push(line(1760, 1328, 2336, 1328, { stroke: c.amber, "stroke-width": 3, opacity: 0.72 }));
g.push(line(2044, 1350, 2268, 1350, { stroke: c.cyan, "stroke-width": 2, opacity: 0.72 }));
g.push(tickGroup(2450, 1150, 4, 22, 34, true, c.amber, 0.86));
g.push(tickGroup(2428, 1474, 3, 26, 16, false, c.cyan, 0.8));
g.push(`</g>`);

g.push(`<g id="bottom-bus" fill="none" stroke-linecap="round" stroke-linejoin="round">`);
g.push(pathEl("M 366 1516 H 734 L 780 1550 H 1182 L 1230 1516 H 1634 L 1670 1548 H 2056", {
  stroke: c.amberDim,
  "stroke-width": 2,
  opacity: 0.8
}));
g.push(pathEl("M 872 1482 H 1168 L 1212 1454 H 1510", {
  stroke: c.panelHigh,
  "stroke-width": 8,
  opacity: 0.34
}));
g.push(line(1112, 1528, 1420, 1528, { stroke: c.cyan, "stroke-width": 4, opacity: 0.86 }));
g.push(line(1346, 1502, 1498, 1502, { stroke: c.amber, "stroke-width": 3, opacity: 0.76 }));
g.push(dotRow(894, 1494, 4, 16, c.cyan, 0.9));
g.push(dotRow(1168, 1494, 5, 14, c.amber, 0.86));
g.push(tickGroup(298, 1508, 5, 16, 24, false, c.amber, 0.6));
g.push(`</g>`);

g.push(`<g id="cyan-accents" fill="none" stroke-linecap="round" stroke-linejoin="round">`);
g.push(pathEl("M 106 204 V 158 H 154", { stroke: c.cyan, "stroke-width": 3, opacity: 0.8 }));
g.push(line(648, 116, 710, 116, { stroke: c.cyan, "stroke-width": 4, opacity: 0.85 }));
g.push(line(742, 116, 756, 116, { stroke: c.cyan, "stroke-width": 4, opacity: 0.85 }));
g.push(line(782, 116, 794, 116, { stroke: c.cyan, "stroke-width": 4, opacity: 0.85 }));
g.push(line(1060, 86, 1078, 86, { stroke: c.cyan, "stroke-width": 4, opacity: 0.92 }));
g.push(pathEl("M 2210 622 H 2242 L 2258 606 H 2288", { stroke: c.cyan, "stroke-width": 3, opacity: 0.66 }));
g.push(pathEl("M 1908 990 L 1876 1022 H 1838", { stroke: c.cyan, "stroke-width": 3, opacity: 0.72 }));
g.push(pathEl("M 2408 618 V 582", { stroke: c.cyan, "stroke-width": 4, opacity: 0.85 }));
g.push(`</g>`);

g.push(`<g id="deck-mark">`);
g.push(tag("text", {
  x: 134,
  y: 1398,
  fill: c.amber,
  "font-family": "JetBrains Mono, Fira Code, Menlo, Consolas, monospace",
  "font-size": 38,
  "font-weight": 800,
  "letter-spacing": 0
}, "DUCKTOP2"));
g.push(rect(134, 1418, 238, 4, { fill: c.amberDim, opacity: 0.82 }));
g.push(rect(388, 1418, 54, 4, { fill: c.cyan, opacity: 0.82 }));
g.push(`</g>`);

g.push(`<g id="tiny-edge-marks" fill="${c.amber}" opacity="0.72">`);
for (const [x, y] of [[30, 1320], [30, 1334], [30, 1348], [2140, 72], [2154, 72], [2168, 72], [2468, 1088], [2468, 1102], [2468, 1116]]) {
  g.push(rect(x, y, 4, 4));
}
g.push(`</g>`);

g.push("</svg>");

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(outPath, `${g.join("\n")}\n`, "utf8");
console.log(`Wrote ${outPath} (${width}x${height})`);
