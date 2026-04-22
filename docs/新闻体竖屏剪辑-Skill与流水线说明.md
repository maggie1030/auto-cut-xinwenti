# 新闻体竖屏剪辑：Skill 功能与流水线使用说明

本文档依据仓库内 **Cursor 技能**（`.cursor/skills/`）与 **`video-pipeline/` 脚本源码**整理，描述「能做什么」与「怎么跑」，便于人类与 Agent 对照执行。

---

## 1. 这套能力解决什么问题

面向 **9:16 竖屏营销成片**，在典型输入下完成：

- **多段画面**按顺序整段使用、拼接；
- **一条口播**定成片时长，画面用 **D/T**（拼接总时长 D ÷ 口播有效时长 T）整体变速对齐，**默认不靠静音把口播垫长**；
- **固定五种转场**（推进、叠化、拉远、模糊放大、横移模糊）；
- **口播响度归一**（`loudnorm`，限峰防爆）；
- **新闻体四行固定叠字**（整片一张透明 PNG 覆盖，非逐句时间轴字幕）：商务/活泼 **颜色池** 分槽抽样、自动描边、字号随文案长度自适应。

---

## 2. 仓库与目录约定

| 路径 | 说明 |
|------|------|
| `.cursor/skills/` | Cursor 加载的项目技能：触发词、流程约定、自检清单 |
| `video-pipeline/` | 实际渲染脚本、`assets/`、`out/`、`copy/` |
| `video-pipeline/assets/video/` | 画面素材 |
| `video-pipeline/assets/audio/` | 口播（可为纯音频或带画面的 `.mp4` / `.mov`，成片**只用 `a:0`**） |
| `video-pipeline/out/` | 输出成片；`out/_work/<任务名>/` 为中间文件 |
| `video-pipeline/copy/final-jobs/` | 一站式任务 JSON 模板（见第 7 节） |
| `video-pipeline/copy/caption-jobs/` | 仅叠字任务 JSON 模板 |

**重要**：所有示例命令默认在 **`video-pipeline/`** 目录下执行，相对路径均相对该目录。

---

## 3. Cursor 技能一览（何时读哪个）

| 技能 ID | 文件 | 适用场景 |
|---------|------|----------|
| `vertical-montage-dt-fit` | `.cursor/skills/vertical-montage-dt-fit/SKILL.md` | 只要 **拼接 + D/T + 转场 + 最大音量**；画面字默认 **不要**（除非用户明确要求脚本内 `--overlay`） |
| `news-caption-overlay` | `.cursor/skills/news-caption-overlay/SKILL.md` | **已有竖屏成片**，只加 **四行新闻体叠字** |
| `final-news-video` | `.cursor/skills/final-news-video/SKILL.md` | 用户给 **视频列表 + 口播 + 四行文案**，要 **一条流程出 `*-final.mp4`**（Agent 按步骤串联脚本） |
| `video-pipeline-env-init` | `.cursor/skills/video-pipeline-env-init/SKILL.md` | 新机器、`npm run check` 失败、首次导出前环境自检 |

技能正文里有更细的「与用户沟通的承诺」「异常处理」，Agent 执行任务时应 **先 Read 对应 SKILL.md**。

---

## 4. 环境与依赖（最短清单）

在 `video-pipeline/` 下：

```bash
npm run check
```

常用硬依赖：

- **ffmpeg**、**ffprobe**（含 `libx264`；转场链路会用到 `xfade` 等）
- **python3**
- **叠字**：`pip install -r requirements-bake.txt`（Pillow）；中文字体见技能（`XINQING_FONT` / `FONT_DIR`、Noto CJK）

---

## 5. 推荐：一键脚本（转场 + 最大音量 + 可选叠字）

脚本：`video-pipeline/scripts/render_fixed_transitions_maxvol.sh`

内部顺序（与源码一致）：

1. `python3 scripts/render_fixed_fullscreen_overlay.py` — 基础 D/T 对齐成片（中间件写入 `workdir`）
2. 内嵌 Python 调 **ffmpeg** — 段间 **xfade**（仅五种转场轮换），再对整条视频轨 **setpts** 与口播 T 对齐
3. **ffmpeg loudnorm** — 音频 `I=-14:LRA=7:TP=-1.0`，视频 copy
4. 若配置了叠字任务 — `python3 scripts/burn_news_style_caption_overlay.py`（需 Pillow）

**参数约定**（见脚本 `usage`）：

- **`--name`**：任务名，用于 `out/<name>-final.mp4` 或 `out/<name>-maxvol.mp4`
- **`--audio`**：口播媒体路径
- **`--videos`**：至少 **2 段** 视频（脚本内校验 `len(videos) < 2` 会退出）
- **`--workdir`**：可选；默认 `out/_work/<name>/`
- **`--caption-job`**：可选；指向 `copy/caption-jobs/...json`。若省略且存在 **`copy/caption-jobs/caption-<name>-final.json`**，会自动用于烧录

**产物约定**（与脚本一致）：

- `out/` **只保留最后一步一个交付文件**：有叠字时为 **`out/<name>-final.mp4`**；无叠字时为 **`out/<name>-maxvol.mp4`**
- 中间文件在 **`out/_work/<name>/`**（如 `base.mp4`、`transition-fixed.mp4`、`maxvol.mp4` 等）

示例：

```bash
cd video-pipeline

./scripts/render_fixed_transitions_maxvol.sh \
  --name 003 \
  --audio assets/audio/voiceover.MP4 \
  --videos assets/video/A.MOV assets/video/B.MOV assets/video/C.MOV
```

带显式叠字任务：

```bash
./scripts/render_fixed_transitions_maxvol.sh \
  --name 003 \
  --audio assets/audio/voiceover.MP4 \
  --videos assets/video/A.MOV assets/video/B.MOV \
  --caption-job copy/caption-jobs/caption-003-final.json
```

一键脚本在调用叠字脚本时会 **同时传入** `--job`、`--in`（maxvol 中间件）、`--out`（最终路径）；其中 **`--in` / `--out` 优先于 job 文件里的 `in` / `out`**（与 `burn_news_style_caption_overlay.py` 参数解析逻辑一致）。

---

## 6. 分步核心脚本（自定义时用）

### 6.1 竖屏拼接 + D/T：`render_fixed_fullscreen_overlay.py`

- **用途**：规范化每段（旋转矩阵、`scale`+`pad` 到目标分辨率，默认 1080×1920）、concat、整条 **`setpts=PTS/(D/T)`**（省略 `--video-speed` 时）、去输出 Display Matrix（`yuv4mpegpipe` 重封装视频轨等，见脚本内注释）
- **常用参数**：`--videos`（多段）、`--audio`、`--out`、`--workdir`、`--w`、`--h`、`--video-speed`（固定倍速时与「自动 D/T」二选一）、`--audio-speed`、`--overlay`（脚本内置全屏 PNG 文案，**默认不建议**，营销新闻体更推荐独立 `burn_...`）

工作目录仍为 **`video-pipeline/`**。

### 6.2 仅叠字：`burn_news_style_caption_overlay.py`

- **用途**：读 job 或 CLI，用 Pillow 生成 **单张** `overlay_news.png`，再 ffmpeg 叠加；**有音轨则 audio copy**
- **推荐**：`--job copy/caption-jobs/你的任务.json`
- **CLI 覆盖**：同一字段 **CLI 优先于 job**（便于临时改一条试效果）
- **配色**：`tone` 为 `business` | `playful` | `random`；`random_seed` 可固定抽样结果

模板：`copy/caption-jobs/caption-job.example.json`。

---

## 7. 一站式任务 JSON（`final-news-video`）

模板：`video-pipeline/copy/final-jobs/final-job.example.json`。

Agent 或人工按技能 `final-news-video` 的顺序：**写 final job → 跑拼接 → loudnorm → 写 caption job（`in` 指向 maxvol，`out` 指向 final）→ burn**。

| 字段 | 必填 | 说明 |
|------|------|------|
| `job_name` | 是 | 输出与中间目录命名根 |
| `videos` | 是 | 按镜头顺序的相对路径数组 |
| `audio` | 是 | 口播路径 |
| `line1`～`line3`、`bottom` | 是 | 四行文案 |
| `tone`、`random_seed` | 否 | 配色控制 |
| `font_scale`、`line1_y_pct` 等 | 否 | 与叠字脚本一致 |
| `keep_intermediate` | 否 | 是否保留中间文件（技能约定，执行脚本时按你的目录策略使用） |

**输出命名约定**（技能约定，与一键脚本命名可并存）：例如 `job_name` 为 `003` 时，`out/003.mp4` → `out/003-maxvol.mp4` → `out/003-final.mp4`。

---

## 8. 叠字专用任务 JSON（仅 `news-caption-overlay`）

模板：`video-pipeline/copy/caption-jobs/caption-job.example.json`。

| 字段 | 说明 |
|------|------|
| `in` / `out` | 输入成片、输出路径（相对 `video-pipeline/`） |
| `workdir` | 中间 PNG 等 |
| `line1`～`bottom` | 四行文案 |
| `line1_y_pct`、`bottom_center_y_pct`、`stroke_scale`、`font_scale`、`tone`、`random_seed` | 可选，含义见 `news-caption-overlay` 技能 |

---

## 9. 跑前 / 跑后自检（摘要）

**跑前**

- `command -v ffmpeg ffprobe python3`
- 叠字：`python3 -c "import PIL"`
- `test -f` 确认每条 `videos`、`audio`（或 job 的 `in`）存在

**跑后**

- 日志中出现 **`已导出:`**（叠字）；拼接脚本日志中关注 **`已去除 Display Matrix`** 等成功提示
- 可选：`ffprobe` 看分辨率、时长、旋转 side data 是否符合预期

---

## 10. 常见问题

| 现象 | 处理方向 |
|------|----------|
| 提示缺少画面/音频 | 是否已 `cd video-pipeline`；路径是否相对正确 |
| `ffmpeg` not found | 安装并加入 `PATH` |
| 叠字报 Pillow | `pip install -r requirements-bake.txt` |
| 中文方块字 | Noto CJK 或设置 `XINQING_FONT` / `FONT_DIR` |
| 一键脚本报 videos 至少 2 条 | 当前 `render_fixed_transitions_maxvol.sh` 限制；仅 1 段时需改用 `render_fixed_fullscreen_overlay.py` 直接渲染（不经过该 shell 的转场 Python 段） |

---

## 11. 与「npm 槽位成片」的关系

`video-pipeline/README.md` 描述的 **`npm run render`**、`copy/examples/episode-*.json`、`bake_overlay_subtitles.py` 路线是另一条 **按时间段切换槽位字幕** 的批量模板；本文档聚焦 **D/T 整段对齐 + 新闻体四行固定叠字** 技能链。两套可并存，勿混用同一 JSON 格式。

---

*文档生成自仓库脚本与 `.cursor/skills`；若行为与代码不一致，以源码为准。*
