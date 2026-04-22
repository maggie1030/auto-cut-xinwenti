---
name: final-news-video
description: >-
  One-stop pipeline for final vertical marketing videos: concatenate ordered clips, auto fit visual
  duration to voiceover (D/T), normalize to max loudness, then burn four-line news-style caption
  overlay. Use when user only provides videos + audio + 4 lines of copy and wants one final export.
---

# 一站式新闻体成片（视频+音频+四行文案）

## 何时用本技能

当用户明确希望**一步出最终版**，并提供：

- 多段画面素材（按给定顺序）
- 一条口播/音频素材
- 四行新闻体文案（line1/line2/line3/bottom）

目标：不再分多次对话，直接交付带文案的最终成片。

## 本技能整合了什么

本技能把以下流程串成一条流水线：

1. `render_fixed_fullscreen_overlay.py`：多段竖屏拼接 + D/T 自动时长对齐 + 去 Display Matrix
2. `ffmpeg loudnorm`：最大音量处理（防爆限）
3. `burn_news_style_caption_overlay.py`：新闻体四行文案烧录（颜色池 + 自动描边）

## 唯一入口规范

工作目录固定为：

`video-pipeline/`

建议使用统一任务文件（本 skill 对应模板）：

`video-pipeline/copy/final-jobs/final-job.example.json`

实际执行时，请先复制为新文件，例如：

`video-pipeline/copy/final-jobs/final-003.json`

## 任务 JSON 字段（统一输入）

必填：

- `job_name`：任务名（用于输出命名与中间目录）
- `videos`：数组，按镜头顺序排列
- `audio`：口播音频路径
- `line1`、`line2`、`line3`、`bottom`：四行文案

可选（有默认值）：

- `tone`：`random` / `business` / `playful`（默认 `random`）
- `random_seed`：整数，固定配色复现
- `line1_y_pct`、`line2_y_pct`、`line3_y_pct`、`bottom_center_y_pct`、`stroke_scale`
- `keep_intermediate`：是否保留中间文件（默认 `true`）

## 固定输出约定

设 `job_name=003`，则输出：

- 基础拼接：`out/003.mp4`
- 最大音量：`out/003-maxvol.mp4`
- 最终带字：`out/003-final.mp4`
- 中间目录：`out/_work/003/`

交付时默认给用户 `out/<job_name>-final.mp4`。

## Agent 执行步骤（必须按顺序）

1. 读取用户给定素材与四行文案，写入 `copy/final-jobs/<job_name>.json`
2. 跑前自检：
   - `command -v ffmpeg ffprobe python3`
   - `python3 -c "import PIL"`
   - `test -f` 检查所有 `videos` 与 `audio`
3. 画面拼接 + D/T 对齐：
   - `python3 scripts/render_fixed_fullscreen_overlay.py --videos ... --audio ... --out out/<job_name>.mp4 --workdir out/_work/<job_name>`
4. 最大音量：
   - `ffmpeg -y -i out/<job_name>.mp4 -filter:a "loudnorm=I=-14:LRA=7:TP=-1.0" -c:v copy -c:a aac -b:a 192k out/<job_name>-maxvol.mp4`
5. 文案烧录：
   - 先生成 `copy/caption-jobs/caption-<job_name>-final.json`（`in` 指向 `out/<job_name>-maxvol.mp4`，`out` 指向 `out/<job_name>-final.mp4`，并写入四行文案及可选参数）
   - 执行 `python3 scripts/burn_news_style_caption_overlay.py --job copy/caption-jobs/caption-<job_name>-final.json`
6. 跑后验证：
   - `ffprobe` 检查最终文件分辨率、时长
   - 确认日志包含 `已导出:`

## 默认承诺

- 按用户给出的 `videos` 顺序整段使用，不跳切
- 默认口播不断，画面通过 D/T 自动对齐
- 音频默认给最大音量版（防爆限）
- 文案采用新闻体四行样式，颜色来自内置池（可通过 `tone` / `random_seed` 控制）
- 文案排版默认采用**非等字号层级**（第二行略大、第三行略小、底部更小），不会把四行做成同一字号
- 字号按文案长度自适应：**能单行放下就保持当前字号**；仅在放不下时才按需缩小（`font_scale` 向下调整）以避免换行
- 默认交付最终成片 `out/<job_name>-final.mp4`

## 常见异常处理

- 缺依赖（ffmpeg/ffprobe/python/Pillow）：先安装再继续
- 路径错误：先切到 `video-pipeline/` 再使用相对路径
- 中文字体异常：安装 Noto CJK 或设置 `XINQING_FONT` / `FONT_DIR`

## 与用户沟通的简化口令

当用户说：

- “给你视频+音频+文案，直接出最终版”
- “一条龙做完，不要分步骤”

默认启用本 skill，全流程一次执行并返回最终输出路径。
