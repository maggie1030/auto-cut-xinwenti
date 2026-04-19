---
name: news-caption-overlay
description: >-
  Burns fixed 9:16 news-style on-screen copy (three centered lines + bottom left block) onto an
  existing vertical MP4 using video-pipeline/scripts/burn_news_style_caption_overlay.py (Pillow PNG
  + ffmpeg overlay). Use when the user asks for 新闻体叠字、四行标题、白底主标题、学员引语、烧录固定文案、
  burn_news_style_caption_overlay、caption job JSON、或成片上加营销字幕（非逐句时间轴字幕）。
---

# 竖屏成片：新闻体固定四块叠字

## 何时用本技能

用户已有**竖屏成片**（通常为 `1080×1920`），要在**整条时长内**叠一层固定版式文案：

1. **主标题**：白底圆角矩形 + 黑字，水平居中，靠上。  
2. **第二行**：橘黄字 + 白描边，居中。  
3. **第三行**：墨蓝字 + 白描边，居中。  
4. **底部块**：白字 + 黑描边，左对齐（多行，常含「学员：」）。

这与 **`bake_overlay_subtitles.py` 按时间段换槽位**不同；本技能是**全片同一画面 PNG 叠在视频上**。

## 硬性依赖

- **`ffmpeg`** / **`ffprobe`**（含 `libx264`）。  
- **`python3`** + **Pillow**：`pip install -r requirements-bake.txt`。  
- **字体**：优先「新青年体」；未安装时脚本回退 Noto Sans CJK。可设环境变量 **`XINQING_FONT`**（字体文件绝对路径）或 **`FONT_DIR`**。

## 唯一入口脚本

相对仓库根目录：

`video-pipeline/scripts/burn_news_style_caption_overlay.py`

## 文案与成片：两文件、一条命令（推荐）

| 角色 | 说明 |
|------|------|
| **任务 JSON** | 只存可变内容：`in`、`out`、四段文案，可选 `workdir`。模板见 `video-pipeline/copy/caption-jobs/caption-job.example.json`。 |
| **脚本** | 读 JSON → 生成 `overlay_news.png` → `ffmpeg` 叠到成片；有音轨则 **audio copy**。 |

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
  --bottom "学员：……"
```

同一字段 **CLI 优先于 job**（便于临时改一条试效果）。

## 跑前自检（Agent 应执行）

- `test -f`（或等价）确认 **`in`** 存在；**`out`** 父目录可创建即可。  
- `command -v ffmpeg ffprobe python3`  
- `python3 -c "import PIL"`  
- 若用户要新青年体：`test -f` **`XINQING_FONT`** 指向的文件，或确认系统字体目录已安装。

## 跑后自检

- 终端出现 **`已导出:`** 与输出路径。  
- 可选：`ffprobe -select_streams v:0 -show_entries stream=width,height -of json …` 确认分辨率与源一致。

## 常见报错与处理

| 现象 | 处理 |
|------|------|
| `找不到输入` | `in` 路径错误或未先 `cd video-pipeline`；改用绝对路径。 |
| `需要 Pillow` | `pip install -r requirements-bake.txt` |
| 中文变方块 | 安装 Noto CJK 或设置 **`XINQING_FONT`** / **`FONT_DIR`** |

## 与用户沟通时的默认承诺

- **不改动口播**：有音轨则 **copy**，不重编码音频。  
- **版式由脚本固定**：微调位置字号需改脚本内常量或后续迭代参数，不在本技能默认可调范围内。  
- **新任务**建议复制 `caption-job.example.json` 为新文件名，改 `in`/`out` 与四段字，避免互相覆盖 **`workdir`** 下的中间 PNG。
