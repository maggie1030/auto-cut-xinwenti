#!/usr/bin/env node
/**
 * 环境自检：Node/ffmpeg/jq/python、字体、可选 faster-whisper；生成 1s 测试片验证 ffmpeg。
 */
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

function run(cmd, args, opts = {}) {
  return spawnSync(cmd, args, { encoding: "utf8", ...opts });
}

function line(msg) {
  console.log(msg);
}

function main() {
  const ok = [];
  const manual = [];
  const optional = [];

  line("=== 短视频流水线环境自检 ===\n");

  const plat = process.platform;
  line(`系统: ${plat} (${plat === "darwin" ? "macOS" : plat})`);

  const nodeV = process.version;
  ok.push(`Node.js ${nodeV}`);

  const n = run("npm", ["-v"]);
  if (n.status === 0) ok.push(`npm ${n.stdout.trim()}`);
  else manual.push("npm 不可用，请检查 Node 安装");

  const ff = run("ffmpeg", ["-version"]);
  if (ff.status === 0) ok.push(ff.stdout.split("\n")[0] || "ffmpeg 可用");
  else manual.push("未检测到 ffmpeg，请安装（macOS: brew install ffmpeg）");

  const jq = run("jq", ["--version"]);
  if (jq.status === 0) ok.push(`jq ${jq.stdout.trim()}`);
  else manual.push("未检测到 jq，请安装（macOS: brew install jq）");

  const py = run("python3", ["--version"]);
  if (py.status === 0) ok.push(`python3 ${py.stdout.trim()}`);
  else optional.push("python3 未找到（可选：自动字幕 faster-whisper）");

  const pip = run("pip3", ["show", "faster-whisper"]);
  if (pip.status === 0) ok.push("pip 包 faster-whisper 已安装（可选增强）");
  else optional.push("未检测到 faster-whisper（可选：pip install -r requirements-whisper.txt）");

  const pil = run("pip3", ["show", "Pillow"]);
  if (pil.status === 0) ok.push("Pillow 已安装（字幕 PNG 烧录）");
  else manual.push("未检测到 Pillow：请 pip install -r requirements-bake.txt（出片必需）");

  const fc = run("fc-list", []);
  if (fc.status === 0 && /Noto.*CJK/i.test(fc.stdout)) {
    ok.push("已检测到 Noto CJK 字体（fc-list）");
  } else if (fc.status !== 0) {
    optional.push("fc-list 不可用；macOS 可在「字体册」搜索 Noto Sans CJK SC 确认");
  } else {
    manual.push("未在 fc-list 中发现 Noto CJK；建议安装 font-noto-sans-cjk-sc（brew --cask）");
  }

  const outDir = join(root, "out", "_selfcheck");
  mkdirSync(outDir, { recursive: true });
  const testMp4 = join(outDir, "ffmpeg-smoke.mp4");
  const lavfi = "testsrc=duration=1:size=720x1280:rate=30,format=yuv420p";
  const r = run("ffmpeg", ["-y", "-f", "lavfi", "-i", lavfi, "-c:v", "libx264", "-t", "1", testMp4]);
  if (r.status === 0 && existsSync(testMp4)) {
    ok.push(`ffmpeg 冒烟成功: ${testMp4}`);
  } else {
    manual.push("ffmpeg 生成测试片失败，请查看终端权限或编码器配置");
  }

  line("\n【已成功 / 可用】");
  ok.forEach((x) => line(` - ${x}`));

  if (optional.length) {
    line("\n【可选 / 未装】");
    optional.forEach((x) => line(` - ${x}`));
  }

  if (manual.length) {
    line("\n【需你手动处理】");
    manual.forEach((x) => line(` - ${x}`));
  }

  line("\n【成片能力】");
  if (manual.some((m) => m.includes("ffmpeg")) || manual.some((m) => m.includes("Pillow"))) {
    line(" - 尚不能保证一键出片：请先修复 ffmpeg 与 Pillow。");
  } else {
    line(" - 将素材放入 assets/video 与 assets/audio，编辑 copy 后执行 npm run render:example（需与 JSON 内文件名一致）。");
    line(" - 或先 npm run bootstrap-demo && npm run render:demo 验证整条链路。");
  }

  line("\n说明：主路径为 ffmpeg + 脚本，不需要 Chrome/Chromium；若改用 Remotion 再安装浏览器依赖。");
}

main();
