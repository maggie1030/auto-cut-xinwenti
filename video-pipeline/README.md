# 短视频素材剪辑与批量成片流水线（最小可用）

工作区根目录下的 `video-pipeline/`：把画面与口播音频放进约定目录，**一条命令**完成拼接、替换音轨、按槽位烧录大字幕并导出到 `out/`。文案与样式通过 `copy/` 下的 JSON **参数化**，便于批量生成「结构相同、表层不同」的引流成片。

## 目录约定

| 路径 | 用途 |
|------|------|
| `assets/video/` | 画面素材（你在 JSON 里写**相对此目录**的文件名） |
| `assets/audio/` | 口播/配音素材（**支持** `.wav` / `.m4a` / `.mp3` 等；也支持 **`.mp4` / `.mov` 等带画面的视频**，成片时**只抽取第一条音轨 `a:0`**，不会把该文件的画面拼进成片） |
| `out/` | 成片与中间文件（`out/_work/<id>/` 为中间过程，可删） |
| `copy/` | 文案槽位、样式 preset、约束（必选词/禁用词/字数上限） |
| `copy/examples/` | 示例单集配置 |
| `scripts/` | `render.sh`、校验、字幕烧录、可选 Whisper |

**一键出片（示例）**

```bash
cd video-pipeline
npm run check              # 环境自检
npm run bootstrap-demo     # 可选：生成占位竖屏画面+演示音频
npm run render:demo        # 导出 out/episode-demo-generated.mp4
```

使用自有素材时：

1. 将视频文件放入 `assets/video/`，音频放入 `assets/audio/`。
2. 复制 `copy/examples/episode-001.json` 为新文件，修改其中 `assets` 与 `slots`。
3. 执行：`npm run render -- copy/你的配置.json`（或 `bash scripts/render.sh copy/你的配置.json`）。

## 方案说明：ffmpeg 主路径 vs Remotion

| 维度 |本仓库主路径（ffmpeg + 脚本） | Remotion |
|------|-------------------------------|----------|
| 依赖 | `ffmpeg`、`jq`、Node（校验）、Python3 + **Pillow**（字幕 PNG） | Node + 浏览器（Chromium）+ Remotion 生态 |
| 本地素材 | 直接拼接 MP4/MOV + WAV等，适合「素材进目录」 | 也可接入，但需 Composition 与静态文件路径设计 |
| 字幕/样式 | 槽位文案 →全帧透明 PNG + `overlay`（**不依赖** `subtitles`/`drawtext` 滤镜） | React 组件任意排版，适合强动效 |
| 适用 | **P0 快速跑通、批量、服务器无头环境** | 强 UI 动画、可编程模板 |

**Chrome / Chromium**：本主路径**不需要**浏览器渲染；若你改用 Remotion，再安装 Chromium 或使用 Remotion 官方渲染指引。

**说明（重要）**：你本机 Homebrew 的 `ffmpeg` 可能**未**编译 `libass`/`libfreetype`，因此没有 `subtitles`/`drawtext` 滤镜。本工程已自动改为 **Pillow生成 PNG + overlay**，避免为此重装 ffmpeg。若你自行安装了带 `drawtext` 的 ffmpeg，仍可使用当前脚本（无需改命令）。

## 单集 JSON 字段（机器可读）

示例见 `copy/examples/episode-001.json`。核心字段：

- `id` / `version`：成片标识与版本。
- `seed`：**预留**。便于你在批量脚本或 LLM 采样时记录随机种子；当前渲染逻辑不依赖随机，但建议你写入以便复现「同一批文案/素材组合」。
- `style_preset`：对应 `copy/presets.json` 中的 key（如 `default`、`yellow_bar`、`high_contrast`）。
- `assets.video`：字符串数组，按顺序拼接；路径相对 `assets/video/`。
- `assets.audio`：单条口播文件，路径相对 `assets/audio/`。可为纯音频，或 **MP4/MOV 等视频文件**（仅使用其中 **第一条音频流**，与 `assets.video` 拼接出的画面合成；多音轨时默认取 `a:0`）。
- `slots`：四类叙事槽位（与竖屏营销口播层次一致）  
  - `hook`：主钩子（强情绪/场景切入）  
  - `benefit`：能力或利益点（可落地结果）  
  - `pivot`：认知转折或降门槛（带练、易上手等）  
  - `close`：证言/对比/收尾（**合规**：避免虚构可核验身份评价；「网友」类话术需符合平台规范，建议学员自述体或明确为个人体验）
- `timing_mode`：  
  - `equal_by_slot`：总时长在四个槽位间**均分**（字幕切换节奏固定）  
  - `by_char_weight`：按各槽位**字数比例**分配时间（口播密度高的一段略长）
- `output.filename`：导出到 `out/` 的文件名。

### 样式 preset（`copy/presets.json`）

可增删 key，并在单集 JSON 里引用。字段含义与 `scripts/bake_overlay_subtitles.py` 中绘制逻辑一致（字号、描边、黄底条 `box` / `boxColor` / `boxBorderW`、下边距 `marginV` 等）。

### 引流约束与校验（`copy/constraints.json`）

由你后续填入真实业务规则：

- `required_keywords`：整段口播层文案（四个槽位拼接）**必须**包含的词。
- `banned_words`：**禁止**出现的词。
- `max_chars_per_slot`：每槽最大字数（适配大字幕换行）。

校验命令：

```bash
npm run validate -- copy/examples/episode-001.json
```

占位符仍含 `REPLACE_*` 时，脚本会**跳过**必选/禁用词强校验（仅警告），避免一开始就无法渲染。

## 如何降低「每条都一样」的重复感

1. **文案**：轮换槽位具体内容；可从词库 JSON 数组里按 `seed` 或按序号取模组合（建议在外层用脚本或 LLM 批量写多个 episode JSON）。
2. **画面**：在 `assets.video/` 维护多段 B-roll，`assets.video` 列表换顺序或换文件。
3. **样式**：轮换 `style_preset`，或复制 preset 微调颜色/描边/黄底条透明度。
4. **复现**：固定 `seed` + 固定词库与素材列表，便于复打同一组合；更换 `seed` 或词库切片即可得新组合。

## 接入 LLM 批量生成（建议）

1. 让模型输出**严格 JSON**（单文件一集），字段与上表一致。  
2. 批量写入 `copy/batch/*.json`。  
3. Shell 循环：`for f in copy/batch/*.json; do npm run render -- "$f"; done`  
4. 渲染前用同一校验脚本做 CI 式检查（禁用词、必选词、字数）。

若你更习惯 **CSV**：可维护表头 `id,hook,benefit,...`，用 `python3`/`jq` 模板化为 JSON再渲染（本仓库以 JSON 为唯一一等公民，避免双格式漂移）。

## 可选：faster-whisper 自动字幕

用于从人声生成 **SRT** 与时间轴，辅助你对齐画面或反向校验口播（**不**自动写入本流水线的主渲染路径）。

```bash
pip install -r requirements-whisper.txt
python3 scripts/transcribe_whisper.py assets/audio/你的口播.wav out/你的字幕.srt
```

## 环境安装与自检

- **自动辅助**：`npm run setup`（macOS 会尝试 `brew install ffmpeg jq` 与 Noto 字体 cask；Debian/RHEL 打印建议的 `apt`/`dnf` 命令）。
- **自检**：`npm run check`（Node、ffmpeg、jq、Python、Pillow、字体探测、ffmpeg 冒烟）。

### 各系统说明

- **macOS**：优先 Homebrew；中文字体推荐 `font-noto-sans-cjk-sc`。无 GUI 服务器时，可用 `fc-list | grep -i noto` 或复制一份成片到本机预览字幕。
- **Debian/Ubuntu**：`apt install ffmpeg jq fonts-noto-cjk python3-pip`。
- **Fedora/RHEL 系**：`dnf install ffmpeg jq google-noto-sans-cjk-sc-fonts`（包名以发行版为准）。
- **无法唯一判断**：脚本会回退为打印通用依赖列表，由你手动安装。

### Node.js

若缺失 Node，建议使用 **nvm** 或官网安装 **LTS**；本工程脚本为 `npm run *` 薄封装，已在 Node 22 验证。

## 故障排查

- **缺少 Pillow**：`pip install -r requirements-bake.txt`
- **找不到字体**：安装 Noto CJK，或 `export FONT_DIR=/path/to/fonts` 指向含 `NotoSansCJKsc-*.otf` 的目录。
- **画面拼接失败**：各段分辨率/像素格式差异过大时，可先统一转码为相同分辨率与 `yuv420p` 再拼接（当前脚本已对 concat 输出统一重编码）。
- **音画时长不一致**：导出使用 `-shortest`，以**较短**的流为准；请保证口播与画面大致匹配，或预先裁切音频。

## npm 脚本一览

| 命令 | 作用 |
|------|------|
| `npm run setup` | 按平台辅助安装依赖 |
| `npm run check` | 环境自检 |
| `npm run validate` | 校验 JSON（默认示例路径见 package.json） |
| `npm run bootstrap-demo` | 生成 `assets/**/_demo` 演示素材 |
| `npm run render` | 默认渲染 `copy/examples/episode-001.json` |
| `npm run render:example` | 同上 |
| `npm run render:demo` | 渲染演示配置（需先 bootstrap-demo） |

---

**P0**：素材进目录 +一条命令出片 — 已实现。  
**P1**：槽位化 JSON + preset + 约束占位 — 已实现。  
**P2**：Whisper 转写 — 可选脚本已提供。
