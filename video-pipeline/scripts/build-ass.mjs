#!/usr/bin/env node
/**
 * 用法: node scripts/build-ass.mjs <episode.json> <durationSeconds> <out.ass>
 * 从 episode 的 slots + timing_mode 生成 ASS（竖屏大字幕，按槽位分时）。
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

function hexToAssBgr(hex) {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `&H00${b.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${r
    .toString(16)
    .padStart(2, "0")}`;
}

function assEscape(text) {
  return String(text)
    .replaceAll("\\", "\\\\")
    .replaceAll("{", "\\{")
    .replaceAll("}", "\\}")
    .replaceAll("\n", "\\N");
}

function secToAssTime(t) {
  const cs = Math.round(t * 100);
  const h = Math.floor(cs / 360000);
  const m = Math.floor((cs % 360000) / 6000);
  const s = Math.floor((cs % 6000) / 100);
  const csRem = cs % 100;
  return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}.${String(csRem).padStart(2, "0")}`;
}

function loadJson(p) {
  return JSON.parse(readFileSync(p, "utf8"));
}

function slotOrder() {
  return ["hook", "benefit", "pivot", "close"];
}

function computeDurations(total, episode) {
  const order = slotOrder();
  const texts = order.map((k) => episode.slots[k] || "");
  const mode = episode.timing_mode || "equal_by_slot";
  if (mode === "equal_by_slot") {
    const n = order.length;
    const each = total / n;
    return order.map(() => each);
  }
  if (mode === "by_char_weight") {
    const weights = texts.map((t) => Math.max(1, [...t].length));
    const sum = weights.reduce((a, b) => a + b, 0);
    return weights.map((w) => (w / sum) * total);
  }
  throw new Error(`未知 timing_mode: ${mode}`);
}

function buildStyleLine(preset) {
  const primary = hexToAssBgr(preset.primary || "#FFFFFF");
  const outline = hexToAssBgr(preset.outline || "#000000");
  const back = preset.box
    ? hexToAssBgr(preset.boxColor?.slice(0, 7) || "#000000")
    : "&H80000000";
  const borderStyle = preset.box ? 3 : 1;
  const outlineW = Number(preset.outlineWidth ?? 3);
  const shadow = Number(preset.shadow ?? 2);
  const font = preset.fontName || "Noto Sans CJK SC Medium";
  const size = Number(preset.fontSize || 44);
  const align = Number(preset.alignment ?? 2);
  const marginV = Number(preset.marginV ?? 120);
  const bold = /bold/i.test(font) ? -1 : 0;
  return `Style: Default,${font},${size},${primary},&H000000FF,${outline},${back},${bold},0,0,0,100,100,0,0,${borderStyle},${outlineW},${shadow},${align},40,40,${marginV},1`;
}

function main() {
  const [, , epPath, durRaw, outPath] = process.argv;
  if (!epPath || !durRaw || !outPath) {
    console.error("用法: node scripts/build-ass.mjs <episode.json> <durationSeconds> <out.ass>");
    process.exit(2);
  }
  const total = Number(durRaw);
  if (!Number.isFinite(total) || total <= 0) {
    console.error("durationSeconds 无效:", durRaw);
    process.exit(2);
  }

  const episode = loadJson(epPath);
  const presets = loadJson(join(root, "copy", "presets.json"));
  const presetName = episode.style_preset || "default";
  const preset = presets[presetName];
  if (!preset || typeof preset !== "object") {
    console.error("找不到 style_preset:", presetName);
    process.exit(1);
  }

  const order = slotOrder();
  const lengths = computeDurations(total, episode);
  let t = 0;
  const dialogues = [];
  for (let i = 0; i < order.length; i++) {
    const key = order[i];
    const text = assEscape(episode.slots[key] || "");
    const start = t;
    const end = t + lengths[i];
    t = end;
    dialogues.push(
      `Dialogue: 0,${secToAssTime(start)},${secToAssTime(end)},Default,,0,0,0,,${text}`
    );
  }

  const header = `[Script Info]
Title: ${episode.id || "episode"}
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
${buildStyleLine(preset)}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
`;

  writeFileSync(outPath, `\ufeff${header}${dialogues.join("\n")}\n`, "utf8");
}

main();
