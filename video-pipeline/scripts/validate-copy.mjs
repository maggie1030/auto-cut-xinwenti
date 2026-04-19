#!/usr/bin/env node
/**
 * 校验 episode JSON：槽位字数、必选/禁用词（constraints.json）。
 * 用法: node scripts/validate-copy.mjs [episode.json]
 * 默认: copy/examples/episode-001.json
 */
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

const SLOT_KEYS = ["hook", "benefit", "pivot", "close"];

function loadJson(p) {
  return JSON.parse(readFileSync(p, "utf8"));
}

function isPlaceholderConstraints(c) {
  const req = c.required_keywords || [];
  const ban = c.banned_words || [];
  return (
    req.some((x) => String(x).includes("REPLACE")) || ban.some((x) => String(x).includes("REPLACE"))
  );
}

function main() {
  const epPath = process.argv[2] || join(root, "copy", "examples", "episode-001.json");
  const conPath = join(root, "copy", "constraints.json");

  if (!existsSync(epPath)) {
    console.error("找不到 episode文件:", epPath);
    process.exit(1);
  }

  const episode = loadJson(epPath);
  const errors = [];
  const warnings = [];

  for (const k of SLOT_KEYS) {
    if (typeof episode.slots?.[k] !== "string") {
      errors.push(`slots.${k} 必须是字符串`);
    }
  }

  let constraints = null;
  if (existsSync(conPath)) {
    constraints = loadJson(conPath);
  } else {
    warnings.push("未找到 copy/constraints.json，已跳过必选/禁用词校验");
  }

  if (constraints && !isPlaceholderConstraints(constraints)) {
    const maxMap = constraints.max_chars_per_slot || {};
    for (const k of SLOT_KEYS) {
      const text = episode.slots?.[k] || "";
      const max = maxMap[k];
      if (typeof max === "number" && [...text].length > max) {
        errors.push(`slots.${k} 超过 max_chars_per_slot（${[...text].length} > ${max}）`);
      }
    }

    const blob = SLOT_KEYS.map((k) => episode.slots[k] || "").join("\n");
    for (const w of constraints.banned_words || []) {
      if (!w || String(w).includes("REPLACE")) continue;
      if (blob.includes(w)) {
        errors.push(`文案命中禁用词: ${w}`);
      }
    }
    for (const w of constraints.required_keywords || []) {
      if (!w || String(w).includes("REPLACE")) continue;
      if (!blob.includes(w)) {
        errors.push(`文案缺少必选关键词: ${w}`);
      }
    }
  } else if (constraints) {
    warnings.push("constraints.json 仍为占位符（含 REPLACE_*），已跳过必选/禁用词强校验");
  }

  const presetPath = join(root, "copy", "presets.json");
  if (existsSync(presetPath)) {
    const presets = loadJson(presetPath);
    const name = episode.style_preset || "default";
    if (name.startsWith("_")) {
      errors.push(`style_preset 不能以 _ 开头（保留给元数据键）: ${name}`);
    } else if (!presets[name] || typeof presets[name] !== "object") {
      errors.push(`style_preset 不存在于 copy/presets.json: ${name}`);
    }
  }

  for (const w of warnings) console.warn("[warn]", w);
  if (errors.length) {
    console.error("校验失败:");
    for (const e of errors) console.error(" -", e);
    process.exit(1);
  }
  console.log("校验通过:", epPath);
}

main();
