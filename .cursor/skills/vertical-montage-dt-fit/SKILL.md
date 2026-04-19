---
name: vertical-montage-dt-fit
description: >-
  Runs video-pipeline/scripts/render_fixed_fullscreen_overlay.py to concatenate ordered vertical
  clips, fit total duration D to voiceover T via setpts=PTS/(D/T) (no silence padding by default),
  use -noautorotate for concat and final encode, scale+pad to 1080x1920, strip Display Matrix on output.
  Use when the user asks for 竖屏拼接, D/T 口播对齐, 画面加速匹配音频, 口播不断, 新闻体视频剪辑流水线,
  matching B-roll to narration, or names that script or a test render like test1.mp4.
---

# 竖屏多段素材 + 口播：D/T 加速对齐成片

## 何时用本技能

用户要把**多段竖屏（或带旋转矩阵的）视频**按顺序**整段用完**，用**一条口播音频**定成片时长；画面整体变速 **`setpts=PTS/(D/T)`**（`D`=拼接总时长，`T`=口播有效时长），**不靠静音补时长**。可选全屏 PNG 文案（默认不要加）。

## 硬性依赖

- 系统已安装 **`ffmpeg`** / **`ffprobe`**（含 `libx264`）。
- **`python3`**。默认成片**不需要** Pillow；只有加 **`--overlay`** 绘制文案时才需要 `pip install -r requirements-bake.txt`（Pillow + 字体）。

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

## 推荐命令模板

将占位符换成真实路径（可多段 `--videos`）：

```bash
cd "…/新闻体视频剪辑流水线/video-pipeline"

python3 scripts/render_fixed_fullscreen_overlay.py \
  --videos assets/video/A.MOV assets/video/B.MOV \
  --audio assets/audio/voiceover.MP4 \
  --out out/成片名.mp4 \
  --workdir out/_work/成片名
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

## 常见报错与处理

| 现象 | 处理 |
|------|------|
| `缺少画面` / `缺少音频` | 路径错误或当前工作目录不是 `video-pipeline`；改为绝对路径或先 `cd`。 |
| `ffmpeg` / `ffprobe` not found | 安装 FFmpeg 并保证在 PATH。 |
| `--overlay` 时 Pillow 报错 | `pip install -r requirements-bake.txt`；字体可设 `XINQING_FONT` / `FONT_DIR`。 |

## 与用户沟通时的默认承诺

- **整段使用**用户给出的每一段素材顺序，不跳切中间。
- **口播不断**：在默认「省略 `--video-speed`」模式下不对口播做静音填充；画面用 `D/T` 一次对齐。
- **不在画面上加文案**，除非用户明确要求 `--overlay`。
