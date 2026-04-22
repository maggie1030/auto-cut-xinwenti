#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 6 ]]; then
  echo "用法:"
  echo "  scripts/render_fixed_transitions_maxvol.sh --name 003 --audio assets/audio/voice.MP4 --videos assets/video/A.mp4 assets/video/B.MOV ..."
  echo ""
  echo "可选:"
  echo "  --caption-job copy/caption-jobs/caption-003-final.json   # 新闻体四行叠字烧录；省略时若存在 copy/caption-jobs/caption-<name>-final.json 则自动烧录"
  exit 1
fi

NAME=""
AUDIO=""
WORKDIR=""
CAPTION_JOB=""
declare -a VIDEOS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)
      NAME="${2:-}"
      shift 2
      ;;
    --audio)
      AUDIO="${2:-}"
      shift 2
      ;;
    --videos)
      shift
      while [[ $# -gt 0 && "$1" != --* ]]; do
        VIDEOS+=("$1")
        shift
      done
      ;;
    --workdir)
      WORKDIR="${2:-}"
      shift 2
      ;;
    --caption-job)
      CAPTION_JOB="${2:-}"
      shift 2
      ;;
    *)
      echo "未知参数: $1"
      exit 1
      ;;
  esac
done

if [[ -z "$NAME" || -z "$AUDIO" || ${#VIDEOS[@]} -lt 2 ]]; then
  echo "参数错误: 需提供 --name、--audio、且 --videos 至少 2 条"
  exit 1
fi

command -v ffmpeg >/dev/null
command -v ffprobe >/dev/null
command -v python3 >/dev/null

for v in "${VIDEOS[@]}"; do
  [[ -f "$v" ]] || { echo "缺少视频: $v"; exit 1; }
done
[[ -f "$AUDIO" ]] || { echo "缺少音频: $AUDIO"; exit 1; }

OUT_DIR="out"
mkdir -p "$OUT_DIR"

DEFAULT_WORKDIR="$OUT_DIR/_work/${NAME}"
RUN_WORKDIR="${WORKDIR:-$DEFAULT_WORKDIR}"
mkdir -p "$RUN_WORKDIR"

# 中间文件只在 workdir，不写入 out/；out/ 仅保留最后一步交付物
BASE_OUT="$RUN_WORKDIR/base.mp4"
TRANS_OUT="$RUN_WORKDIR/transition-fixed.mp4"
MAXVOL_OUT="$RUN_WORKDIR/maxvol.mp4"
DELIVER_FINAL="$OUT_DIR/${NAME}-final.mp4"
DELIVER_MAXVOL="$OUT_DIR/${NAME}-maxvol.mp4"

AUTO_CAPTION_JOB="copy/caption-jobs/caption-${NAME}-final.json"
if [[ -z "$CAPTION_JOB" && -f "$AUTO_CAPTION_JOB" ]]; then
  CAPTION_JOB="$AUTO_CAPTION_JOB"
  echo "已检测到叠字任务: ${CAPTION_JOB}（将烧录为 ${DELIVER_FINAL}）"
fi

echo "[1/4] 先做基础 D/T 对齐成片（中间件）: $BASE_OUT"
python3 scripts/render_fixed_fullscreen_overlay.py \
  --videos "${VIDEOS[@]}" \
  --audio "$AUDIO" \
  --out "$BASE_OUT" \
  --workdir "$RUN_WORKDIR/base"

echo "[2/4] 生成固定转场版（仅推进/叠化/拉远/模糊放大/横移模糊）: $TRANS_OUT"

# 用 python 生成并执行 ffmpeg 转场命令（避免 bash 字符串转义地狱）
python3 - "$NAME" "$AUDIO" "$TRANS_OUT" "$RUN_WORKDIR" "${VIDEOS[@]}" <<'PY'
import shlex
import subprocess
import sys
from pathlib import Path

name = sys.argv[1]
audio = Path(sys.argv[2])
trans_out = Path(sys.argv[3])
workdir = Path(sys.argv[4])
videos = [Path(p) for p in sys.argv[5:]]

if len(videos) < 2:
    raise SystemExit("至少需要 2 条视频才能做转场")

def dur(p: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=nk=1:nw=1",
            str(p),
        ],
        capture_output=True, text=True, check=True
    )
    return float(r.stdout.strip())

def audio_dur(p: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=duration",
            "-of", "default=nk=1:nw=1",
            str(p),
        ],
        capture_output=True, text=True
    )
    if r.returncode == 0 and r.stdout.strip() and r.stdout.strip() != "N/A":
        return float(r.stdout.strip())
    return dur(p)

durs = [dur(p) for p in videos]
voice = audio_dur(audio)
if voice <= 0.01:
    raise SystemExit("音频时长过短")

transition_names = [
    ("推进", "slideleft"),
    ("叠化", "fade"),
    ("拉远", "squeezeh"),
    ("模糊放大", "pixelize"),
    ("横移模糊", "hblur"),
]
td = 0.35

# 构建输入和标准化 filter
inputs = []
fparts = []
for i, p in enumerate(videos):
    inputs += ["-i", str(p)]
    fparts.append(
        f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p,fps=60[v{i}]"
    )

acc = durs[0]
last = "v0"
used = []
for i in range(1, len(videos)):
    zh, ff = transition_names[(i - 1) % len(transition_names)]
    used.append(zh)
    offset = acc - td
    out = f"x{i}"
    fparts.append(
        f"[{last}][v{i}]xfade=transition={ff}:duration={td:.2f}:offset={offset:.6f}[{out}]"
    )
    last = out
    acc = acc + durs[i] - td

vs = acc / voice
if vs <= 0.05:
    vs = 0.05
fparts.append(f"[{last}]setpts=PTS/{vs:.9f}[vout]")
filter_complex = ";".join(fparts)

cmd = [
    "ffmpeg", "-y",
    *inputs,
    "-i", str(audio),
    "-filter_complex", filter_complex,
    "-map", "[vout]",
    "-map", f"{len(videos)}:a:0",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "192k",
    "-movflags", "+faststart",
    "-shortest",
    str(trans_out),
]
subprocess.run(cmd, check=True)
print("固定转场已应用:", "、".join(used))
print(f"转场前时长D={acc:.3f}s，口播T={voice:.3f}s，画面倍速≈{vs:.4f}x")
PY

echo "[3/4] 音频最大音量（限峰防爆，中间件）: $MAXVOL_OUT"
ffmpeg -y \
  -i "$TRANS_OUT" \
  -filter:a "loudnorm=I=-14:LRA=7:TP=-1.0" \
  -c:v copy -c:a aac -b:a 192k \
  "$MAXVOL_OUT"

# 清理 out/ 里旧流程留下的中间文件名，避免与「只保留终版」混淆
rm -f "$OUT_DIR/${NAME}.mp4" "$OUT_DIR/${NAME}-transition-fixed.mp4"

if [[ -n "$CAPTION_JOB" ]]; then
  [[ -f "$CAPTION_JOB" ]] || { echo "找不到叠字任务文件: $CAPTION_JOB"; exit 1; }
  python3 -c "import PIL" 2>/dev/null || {
    echo "新闻体叠字需要 Pillow: pip install -r requirements-bake.txt"
    exit 1
  }
  echo "[4/4] 新闻体四行叠字烧录 → 仅交付: $DELIVER_FINAL"
  python3 scripts/burn_news_style_caption_overlay.py \
    --job "$CAPTION_JOB" \
    --in "$MAXVOL_OUT" \
    --out "$DELIVER_FINAL" \
    --workdir "$RUN_WORKDIR/caption"
  rm -f "$DELIVER_MAXVOL"
else
  echo "[4/4] 跳过叠字 → 仅交付: $DELIVER_MAXVOL"
  cp -f "$MAXVOL_OUT" "$DELIVER_MAXVOL"
  rm -f "$DELIVER_FINAL"
fi

echo "完成（out/ 仅保留上述一个交付文件；中间件在 ${RUN_WORKDIR}）"
