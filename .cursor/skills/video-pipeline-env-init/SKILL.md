---
name: video-pipeline-env-init
description: >-
  Bootstraps the workspace video-pipeline: OS-aware dependency hints (ffmpeg, jq, Node, Python,
  Noto CJK, optional Chromium), npm run setup/check, pip requirements-bake/whisper, first-render
  smoke via bootstrap-demo + render:demo. Use when cloning the repo, new machine setup,
  环境安装, 初始化 video-pipeline, npm run check fails, or before first export from assets/.
---

# video-pipeline 剪辑环境安装与初始化

## 目标

在工作区根目录下的 **`video-pipeline/`** 内，把 **P0（素材进目录 → 一条命令出片）** 所需依赖装齐并跑通自检；**不无故覆盖**用户已放入 `assets/video/`、`assets/audio/` 的素材（`npm run bootstrap-demo` 仅写演示用路径，执行前确认 README 说明）。

权威文档以仓库内 **`video-pipeline/README.md`** 为准；本 skill 是 Agent 执行顺序与易错点摘要。

## 与另一条 skill 的分工

- **本 skill**：全工程依赖、`npm run setup` / `npm run check`、槽位 JSON 主路径（`npm run render`）。
- **`vertical-montage-dt-fit`**：仅针对 `scripts/render_fixed_fullscreen_overlay.py` 的竖屏多段 + 口播 **D/T** 整条 `setpts` 成片（与 `copy/` JSON 主渲染可并存，用途不同）。

## 推荐执行顺序（Agent 应按序做）

1. **确认路径**：工作区根目录下存在 `video-pipeline/`（若不存在则按 README 结构创建目录骨架，**勿删**已有 `assets/` 内容）。
2. **`cd video-pipeline`**；后续命令均在此目录执行。
3. **Node**：若 `node -v` 失败，安装 **Node LTS**（README 写 Node 22 已验证）；推荐 nvm 或官网 pkg。然后执行 **`npm install`**（安装 npm 本地元数据；`package.json` 可无 runtime 依赖，仍建议执行）。
4. **系统工具与中文字体**：
   - 运行 **`npm run setup`**（调用 `scripts/setup-env.sh`：macOS 可尝试 `brew install ffmpeg jq` 与 Noto CJK cask；Debian/RHEL 仅打印建议的 `apt`/`dnf` 命令，需用户 sudo）。
   - 若无法自动安装，按 **[reference.md](reference.md)** 的手动命令表安装 **ffmpeg、ffprobe、jq** 与 **Noto CJK**（或设置 `FONT_DIR` 指向含 `NotoSansCJKsc-*.otf` 的目录）。
5. **Python（主路径出片必需）**：
   - **`pip3 install -r requirements-bake.txt`**（Pillow，字幕 PNG 烧录）。
   - **可选 P2**：`pip3 install -r requirements-whisper.txt`（faster-whisper）；或建 venv 再装，避免污染系统 Python。
6. **自检**：**`npm run check`**。通读输出中的「已成功」「需你手动处理」「成片能力」三节。
7. **验收第一条成片（任选其一）**：
   - **演示链**：`npm run bootstrap-demo` → `npm run render:demo`（生成 `out/episode-demo-generated.mp4`）；**会生成/覆盖演示用素材与配置**，仅用于验证环境。
   - **自有素材**：把文件放入 `assets/video/`、`assets/audio/`，复制 `copy/examples/episode-001.json` 改 `assets` 与 `slots`，再 **`npm run validate -- copy/你的.json`** 后 **`npm run render -- copy/你的.json`**。

## 明确可选 / 通常不需要

- **Chrome / Chromium**：本仓库 **ffmpeg 主路径不需要**浏览器；仅当改用 Remotion 等方案时再装。
- **Remotion**：README 中标注为对比方案；**当前一键出片不依赖** Remotion。

## 跑完后用通俗中文汇报（给用户）

汇总四块即可：

1. **已成功**：例如 Node、ffmpeg、jq、Pillow、字体探测、冒烟 mp4。
2. **需用户手动**：例如无 brew、需 sudo 的 apt/dnf、字体未进 fc-list、权限问题。
3. **现在能否出第一条成片**：若 `npm run check` 无阻塞项，说明可 `render:example` / 自有 JSON；否则列出缺什么。
4. **文案与配置在哪改**：`copy/` 下单集 JSON、`copy/presets.json`、`copy/constraints.json`；详见 README「单集 JSON 字段」节。

## 禁止与注意

- **不要**在未说明的情况下删除或覆盖用户 `assets/` 下已有成片素材。
- **`npm run setup`** 里的 `pip3 install` 可能同时尝试 `requirements-whisper.txt`；Whisper 失败可忽略（可选），但 **Pillow（bake）失败不可忽略**。
- 无 GUI 服务器上字体验证：README 已说明可用 `fc-list | grep -i noto` 或拷成片到本机预览。

## 延伸阅读

- 各发行版包名、排错与 venv 建议：**[reference.md](reference.md)**
- 目录与 JSON 字段全文：**`video-pipeline/README.md`**
