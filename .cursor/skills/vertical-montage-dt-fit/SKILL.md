---
name: vertical-montage-dt-fit
description: >-
  Runs video-pipeline/scripts/render_fixed_fullscreen_overlay.py to concatenate ordered vertical
  clips, fit total duration D to voiceover T via setpts=PTS/(D/T) (no silence padding by default),
  then adds fixed transition styles and maxes input-audio loudness, while keeping -noautorotate flow,
  scale+pad to 1080x1920, and stripping Display Matrix on output.
  Use when the user asks for 竖屏拼接, D/T 口播对齐, 画面加速匹配音频, 口播不断, 新闻体视频剪辑流水线,
  matching B-roll to narration, or names that script or a test render like test1.mp4.
---

# 竖屏多段素材 + 口播：D/T 加速对齐成片

## 何时用本技能

用户要把**多段竖屏（或带旋转矩阵的）视频**按顺序**整段用完**，用**一条口播音频**定成片时长；画面整体变速 **`setpts=PTS/(D/T)`**（`D`=拼接总时长，`T`=口播有效时长），**不靠静音补时长**。成片默认要有转场；音频若来自 `assets/audio/`，默认做最大音量处理（带防爆限幅）。可选全屏 PNG 文案（默认不要加）。

## 硬性依赖

- 系统已安装 **`ffmpeg`** / **`ffprobe`**（含 `libx264`）。
- **`python3`**。默认成片**不需要** Pillow；只有加 **`--overlay`** 绘制文案时才需要 `pip install -r requirements-bake.txt`（Pillow + 字体）。一键脚本若执行**新闻体叠字烧录**，同样需要 Pillow（`burn_news_style_caption_overlay.py`）。

## 唯一入口脚本

路径（相对仓库根目录）：

`video-pipeline/scripts/render_fixed_fullscreen_overlay.py`

脚本已内建：ffprobe 读 rotation / Display Matrix → `-noautorotate` + `transpose` → `scale`+`pad` → `concat`（`-noautorotate`）→ 整条 `setpts` 对齐口播 → 可选 overlay → **`yuv4mpegpipe` 重走视频轨**去掉 Display Matrix、音轨 copy 再封装。

## 执行规范（避免出错）

1. **先 `cd` 到 `video-pipeline` 目录**，再运行 Python；这样 `--videos`、`--audio`、`--out` 可用相对路径（与历史用法一致）。
2. **`--videos` 顺序即成片镜头顺序**；路径必须存在。
3. **`--audio`**：口播文件（常为 `.mp4` 带音轨）；脚本取 **a:0** 时长算 `T`。
4. **`--out`**：建议 `out/<名字>.mp4`，父目录会自动创建。
5. **`--workdir`**：强烈建议每次任务单独目录，例如 `out/_work/<任务名>`，避免并发或复跑互相覆盖。
6. **默认不要加 `--overlay`**。只有用户**明确要**脚本里写死的那套全屏营销文案时再加；否则成片无画面字。
7. 默认 **`--video-speed` 省略**：自动 `D/T`。用户要求固定画面倍速时再传 `--video-speed`（此时口播链可能 `apad`/`atrim`，与「口播不断」冲突时需和用户确认）。
8. **`--audio-speed`**：默认 `1.0`；`T = 口播源时长 / audio-speed`。
9. **转场规则（默认开启）**：剪辑成片后必须补一条“带转场版”；只允许使用这组转场：**推进、叠化、拉远、模糊放大、横移模糊**。禁止使用其他转场风格。
10. **音量规则（默认开启）**：凡是输入音频来自 `video-pipeline/assets/audio/`，成片音频都要做“最大音量”处理，推荐 `loudnorm=I=-14:LRA=7:TP=-1.0`（最大化听感并限制峰值防爆音）。

## 推荐命令模板

将占位符换成真实路径（可多段 `--videos`）：

一键脚本（推荐：固定转场 + 最大音量；可选新闻体叠字烧录）：

```bash
cd "…/新闻体视频剪辑流水线/video-pipeline"

./scripts/render_fixed_transitions_maxvol.sh \
  --name 003 \
  --audio assets/audio/voiceover.MP4 \
  --videos assets/video/A.MOV assets/video/B.MOV assets/video/C.MOV
```

可选：显式指定叠字任务（否则若存在 `copy/caption-jobs/caption-<name>-final.json` 会自动烧录）：

```bash
./scripts/render_fixed_transitions_maxvol.sh \
  --name 003 \
  --audio assets/audio/voiceover.MP4 \
  --videos assets/video/A.MOV assets/video/B.MOV \
  --caption-job copy/caption-jobs/caption-003-final.json
```

产物（**`out/` 只保留最后一步一个文件**；前几步的中间文件在 `out/_work/<name>/`）：

- 有叠字任务时：仅 `out/<name>-final.mp4`
- 无叠字时：仅 `out/<name>-maxvol.mp4`

分步命令（需要自定义时）：

```bash
cd "…/新闻体视频剪辑流水线/video-pipeline"

python3 scripts/render_fixed_fullscreen_overlay.py \
  --videos assets/video/A.MOV assets/video/B.MOV \
  --audio assets/audio/voiceover.MP4 \
  --out out/成片名.mp4 \
  --workdir out/_work/成片名
```

再做“最大音量版”（当 `--audio` 来自 `assets/audio/` 时默认执行）：

```bash
ffmpeg -y \
  -i out/成片名.mp4 \
  -filter:a "loudnorm=I=-14:LRA=7:TP=-1.0" \
  -c:v copy -c:a aac -b:a 192k \
  out/成片名-maxvol.mp4
```

再做“固定转场版”（只用以下集合：推进/叠化/拉远/模糊放大/横移模糊）：

```bash
# 推荐 xfade 对应关系（仅这五种）
# 推进=slideleft；叠化=fade；拉远=squeezeh；模糊放大=pixelize；横移模糊=hblur
# 产物命名建议：out/成片名-transition-fixed.mp4
```

可选：**全屏 PNG 文案**（需 Pillow 与字体）：

```bash
python3 scripts/render_fixed_fullscreen_overlay.py \
  --videos … \
  --audio … \
  --out out/成片名.mp4 \
  --workdir out/_work/成片名 \
  --overlay
```

可选：**输出分辨率**（默认竖屏 `1080×1920`）：

`--w 1080 --h 1920`

## 跑前自检（Agent 应执行）

- `test -f` 或等价方式确认每个 `--videos`、`--audio` 存在。
- 在 `video-pipeline` 下执行：`command -v ffmpeg ffprobe python3`。
- 若使用 `--overlay`：`python3 -c "import PIL"` 或通过 `requirements-bake.txt` 安装。

## 跑后自检

- 日志含 `已导出:` 与 `已去除 Display Matrix`。
- 可选：`ffprobe -select_streams v:0 -show_entries stream=width,height,side_data_list -of json 成片.mp4` 确认无 **Display Matrix** 类旋转副作用、分辨率为目标竖屏。
- 若执行了最大音量：抽检输出音频是否正常、无明显爆音。
- 若执行了固定转场：确认只出现“推进/叠化/拉远/模糊放大/横移模糊”对应效果。

## 常见报错与处理

| 现象 | 处理 |
|------|------|
| `缺少画面` / `缺少音频` | 路径错误或当前工作目录不是 `video-pipeline`；改为绝对路径或先 `cd`。 |
| `ffmpeg` / `ffprobe` not found | 安装 FFmpeg 并保证在 PATH。 |
| `--overlay` 时 Pillow 报错 | `pip install -r requirements-bake.txt`；字体可设 `XINQING_FONT` / `FONT_DIR`。 |

## 与用户沟通时的默认承诺

- **整段使用**用户给出的每一段素材顺序，不跳切中间。
- **口播不断**：在默认「省略 `--video-speed`」模式下不对口播做静音填充；画面用 `D/T` 一次对齐。
- **转场固定集合**：只用“推进、叠化、拉远、模糊放大、横移模糊”，不用其他类型。
- **音频最大音量**：当音频来自 `assets/audio/` 时，默认交付最大音量版（限峰防爆）。
- **不在画面上加文案**，除非用户明确要求 `--overlay`。
