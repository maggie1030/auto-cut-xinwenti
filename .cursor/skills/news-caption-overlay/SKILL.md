---
name: news-caption-overlay
description: >-
  Burns 9:16 marketing-style four-line copy onto a vertical MP4 via
  video-pipeline/scripts/burn_news_style_caption_overlay.py (Pillow PNG + ffmpeg).
  Colors always come from built-in business/playful slot pools with auto stroke; optional tone and
  random_seed. Use for 新闻体叠字、四行标题、烧录固定文案、burn_news_style_caption_overlay、
  caption job JSON、或成片上加营销字幕（非逐句时间轴字幕）。
---

# 竖屏成片：新闻体四块叠字（颜色池）

## 何时用本技能

用户已有**竖屏成片**（通常为 `1080×1920`），要在**整条时长内**叠一层**固定版式、可变文案**的营销字幕（**全片一张透明 PNG**，不是逐句时间轴）。

版式为**四块**，**颜色一律从脚本内置商务 / 活泼分槽颜色池抽样**（见下文），**描边随字色亮度自动选黑或白**——**不再使用**历史上的「白底主标题 + 固定橘/蓝」那一套固定配色。

四行分工：

1. **第一行**：居中，来自 `line1` 槽；着色字 + 描边（**无白底圆角框**）。  
2. **第二行**：居中，来自 `line2` 槽。  
3. **第三行**：居中，来自 `line3` 槽。  
4. **底部块**：左对齐（多行，常含「网友：」「学员：」），来自 `bottom` 槽。

这与 **`bake_overlay_subtitles.py` 按时间段换槽位**不同；本技能是**全片同一画面 PNG** 叠在视频上。

## 硬性依赖

- **`ffmpeg`** / **`ffprobe`**（含 `libx264`）。  
- **`python3`** + **Pillow**：`pip install -r requirements-bake.txt`。  
- **字体**：优先「新青年体」；未安装时脚本回退 Noto Sans CJK。可设环境变量 **`XINQING_FONT`**（字体文件绝对路径）或 **`FONT_DIR`**（用于中文正常显示，与「颜色池」无关）。

## 唯一入口脚本

相对仓库根目录：

`video-pipeline/scripts/burn_news_style_caption_overlay.py`

## 文案与成片：两文件、一条命令（推荐）

| 角色 | 说明 |
|------|------|
| **任务 JSON** | `in`、`out`、四段文案，可选 `workdir`、纵向百分比（`line1_y_pct` …）、`stroke_scale`、**`tone`**（`business` / `playful` / `random`）、**`random_seed`**。模板见 `video-pipeline/copy/caption-jobs/caption-job.example.json`；**细描边 + 底部位置上提**的定型示例见 `copy/caption-jobs/caption-002.json`。 |
| **脚本** | 读 JSON → 从颜色池抽样 → 生成 `overlay_news.png` → `ffmpeg` 叠到成片；有音轨则 **audio copy**。 |

**路径约定**：在 `video-pipeline` 目录下执行时，`in` / `out` / `workdir` 写**相对当前工作目录**的路径（与现有 `vertical-montage-dt-fit` 技能一致）。

## 推荐命令（--job）

```bash
cd "…/新闻体视频剪辑流水线/video-pipeline"

python3 scripts/burn_news_style_caption_overlay.py \
  --job copy/caption-jobs/你的任务.json
```

## 可选：纯 CLI（无 JSON）

```bash
cd "…/新闻体视频剪辑流水线/video-pipeline"

python3 scripts/burn_news_style_caption_overlay.py \
  --in out/成片输入.mp4 \
  --out out/成片输出.mp4 \
  --line1 "主标题" \
  --line2 "第二行" \
  --line3 "第三行" \
  --bottom "学员：……" \
  --line1-y-pct 0.075 \
  --line2-y-pct 0.125 \
  --line3-y-pct 0.17 \
  --bottom-center-y-pct 0.79 \
  --tone random
```

可加 `--random-seed 20260421` 复现同一套颜色。

同一字段 **CLI 优先于 job**（便于临时改一条试效果）。

## 间距/位置约定（百分比，不写死像素）

- 统一使用 **相对画面高度 H 的百分比** 控制纵向位置。
- 可在 job JSON 或 CLI 配置（范围 `0~1`，开区间）：
  - `line1_y_pct`：第一行首行中心 y，默认 `0.075`
  - `line2_y_pct`：第二行首行目标中心 y，默认 `0.125`
  - `line3_y_pct`：第三行首行目标中心 y，默认 `0.17`
  - `bottom_center_y_pct`：底部块**整体中心**的纵向位置，默认 `0.79`。**数值越小越靠上，越大越靠下**。若希望落在**画面下方 1/3**区域的大致中心，可取约 **`0.833`**；若**太贴底**，应**减小**该值（例如 `0.72`–`0.78` 一带）。
  - `stroke_scale`：描边相对默认粗细的缩放，默认 `1.0`；**小于 1 更细**（例如 **`0.72`**）。
- 第二/三行会先按目标百分比排版；若与上方行块挤压，脚本会下推以避免遮挡。

## 配色（一律颜色池）

- **无固定配色模式**：每次导出前从 **商务** 或 **活泼** 池中为 four 行各抽一色（分槽），描边自动：**深色字 → 白描边**，**浅色字 → 黑描边**（亮度阈值约 `140`）。
- **`tone`**：`business` | `playful` | `random`（随机先选商务或活泼再抽样；**默认 `random`**）。可用 CLI `--tone` 或写在 job JSON。
- **`random_seed`**：可选整数；指定后同一文案 + 同一参数可**复现同一套 RGB**。终端会打印本次 `tone` 与 `RGB=[…]`。

### 商务色池（脚本内置）

- `line1`：`#C47F2C` `#B85C38` `#8B5E3C` `#D4A017` `#C0392B`
- `line2`：`#2E6BC6` `#1F6F8B` `#1B7F7A` `#3A6EA5` `#2C6E85`
- `line3`：`#0F172A` `#111111` `#1F2937` `#0B3D2E`
- `bottom`：`#F5F5F7` `#EDEDED` `#F6F1E8` `#EAF2FF`
- fallback：`#D4A017` / `#2E6BC6` / `#111111` / `#F5F5F7`

### 活泼色池（脚本内置）

- `line1`：`#FFD400` `#FF8A00` `#FF5A5F` `#FF2D95` `#FFC107`
- `line2`：`#2D9CDB` `#00CEC9` `#6C5CE7` `#26C6DA` `#00B894`
- `line3`：`#0A0A0A` `#1B5E20` `#4A148C` `#004D40`
- `bottom`：`#FFFFFF` `#FFF8E1` `#F0FFF4` `#E8F7FF`
- fallback：`#FFD400` / `#2D9CDB` / `#0A0A0A` / `#FFFFFF`

### 抽样约束（脚本规则）

- 四行**分槽**抽样；四色 **HEX 互不相同**；任意两色 RGB 距离 **≥ 85**，不足则重试（最多 **40** 次），失败用对应 fallback。

### 推荐 `tone` 组合

- 每次气质也随机：`"tone": "random"`
- 只要商务池：`"tone": "business"`
- 只要活泼池：`"tone": "playful"`
- 颜色可复现：加 `"random_seed": 20260421`

## 可复用 job 模板（001-2：紧凑行距 + 颜色池）

将下面内容保存为 `video-pipeline/copy/caption-jobs/news-caption-compact.json`（或任意新文件名），换 `in`/`out` 与四段字即可：

```json
{
  "in": "out/001.mp4",
  "out": "out/001-2.mp4",
  "workdir": "out/_work/001-2",
  "line1": "打工人的 “保命技能”",
  "line2": "AI 短视频获客",
  "line3": "学会就是职场加分项",
  "bottom": "网友：现在不学，以后真的跟不上了。",
  "line1_y_pct": 0.09,
  "line2_y_pct": 0.147,
  "line3_y_pct": 0.201,
  "bottom_center_y_pct": 0.79,
  "tone": "random"
}
```

## 可复用 job 模板（002-caption：细描边 + 底部位置上提）

与 `video-pipeline/copy/caption-jobs/caption-002.json` 一致。经 `out/002-caption.mp4` 迭代：`bottom_center_y_pct` 取 **`0.725`**，避免底部行贴底或贴近播放器控件；`stroke_scale` **`0.72`**。

```json
{
  "in": "out/002.mp4",
  "out": "out/002-caption.mp4",
  "workdir": "out/_work/002-caption",
  "line1": "副业党必学的 AI 技能",
  "line2": "用 AI 批量做视频",
  "line3": "被动引流接单",
  "bottom": "网友：不用天天守着手机，客户自己来",
  "line1_y_pct": 0.09,
  "line2_y_pct": 0.147,
  "line3_y_pct": 0.201,
  "bottom_center_y_pct": 0.725,
  "stroke_scale": 0.72,
  "tone": "random"
}
```

仅微调底部高低：改 `bottom_center_y_pct`。只调位置、不换色：加 `"random_seed": <整数>`。

```bash
cd "…/新闻体视频剪辑流水线/video-pipeline"
python3 scripts/burn_news_style_caption_overlay.py --job copy/caption-jobs/caption-002.json
```

## 跑前自检（Agent 应执行）

- `test -f` 确认 **`in`** 存在；**`out`** 父目录可创建。  
- `command -v ffmpeg ffprobe python3`  
- `python3 -c "import PIL"`  
- 若用户要新青年体：`test -f` **`XINQING_FONT`** 或系统已安装该字体。

## 跑后自检

- 终端出现 **`配色（颜色池）:`** 与 **`已导出:`** 行及输出路径。  
- 可选：`ffprobe` 确认分辨率与源一致。

## 常见报错与处理

| 现象 | 处理 |
|------|------|
| `找不到输入` | `in` 错误或未先 `cd video-pipeline`；改用绝对路径。 |
| `需要 Pillow` | `pip install -r requirements-bake.txt` |
| 中文变方块 | 安装 Noto CJK 或设置 **`XINQING_FONT`** / **`FONT_DIR`** |

## 与用户沟通时的默认承诺

- **不改动口播**：有音轨则 **copy**。  
- **颜色**：始终来自内置池 + 约束抽样，**无「固定橘黄/墨蓝/白底」模式**；可用 `tone` / `random_seed` 控制气质与复现。  
- **字号策略**：默认是非等字号层级（第二行略大、第三行略小、底部更小），不会四行同字号。  
- **按字数自适应**：`line1` / `line2` / `line3` / `bottom` 能单行放下就不故意缩小；仅在放不下时才自动减小字号（`font_scale`）避免换行。  
- **新任务**建议复制模板 JSON 为新文件，避免覆盖 **`workdir`** 下中间 PNG。
