#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EP_REL="${1:-copy/examples/episode-001.json}"
EP_ABS="$ROOT/$EP_REL"

if [[ ! -f "$EP_ABS" ]]; then
  echo "找不到配置: $EP_ABS"
  exit 1
fi
command -v jq >/dev/null || { echo "需要 jq"; exit 1; }
command -v ffmpeg >/dev/null || { echo "需要 ffmpeg"; exit 1; }
command -v ffprobe >/dev/null || { echo "需要 ffprobe"; exit 1; }
command -v node >/dev/null || { echo "需要 node"; exit 1; }
command -v python3 >/dev/null || { echo "需要 python3（字幕 PNG 与校验链路）"; exit 1; }

node "$ROOT/scripts/validate-copy.mjs" "$EP_ABS"

ID="$(jq -r '.id // "episode"' "$EP_ABS")"
OUT_NAME="$(jq -r '.output.filename // ""' "$EP_ABS")"
if [[ -z "$OUT_NAME" || "$OUT_NAME" == "null" ]]; then
  OUT_NAME="${ID}.mp4"
fi

WORK="$ROOT/out/_work/$ID"
mkdir -p "$WORK" "$ROOT/out"

# macOS 默认 bash 3.2 无 mapfile，使用数组累加
VIDS=()
while IFS= read -r line; do
  [[ -n "$line" ]] && VIDS+=("$line")
done < <(jq -r '.assets.video[]' "$EP_ABS")

AUDIO_REL="$(jq -r '.assets.audio' "$EP_ABS")"

CONCAT_LIST="$WORK/concat.txt"
rm -f "$CONCAT_LIST"
for rel in "${VIDS[@]}"; do
  P="$ROOT/assets/video/$rel"
  if [[ ! -f "$P" ]]; then
    echo "缺少画面素材: $P（JSON 中 assets.video 为相对 assets/video/ 的路径）"
    exit 1
  fi
  ABS="$(python3 -c "import pathlib; print(pathlib.Path(r\"$P\").resolve())")"
  printf "file '%s'\n" "${ABS//\'/\'\\\'\'}" >> "$CONCAT_LIST"
done

AUDIO_ABS="$ROOT/assets/audio/$AUDIO_REL"
if [[ ! -f "$AUDIO_ABS" ]]; then
  echo "缺少音频素材: $AUDIO_ABS"
  exit 1
fi

CONCAT_MP4="$WORK/concat.mp4"
ffmpeg -y -f concat -safe 0 -i "$CONCAT_LIST" -c:v libx264 -pix_fmt yuv420p -c:a aac -movflags +faststart "$CONCAT_MP4"

FINAL="$ROOT/out/$OUT_NAME"
# 使用 PNG + overlay烧录字幕，兼容未编译 libass/libfreetype 的 ffmpeg（如部分 Homebrew 构建）
python3 "$ROOT/scripts/bake_overlay_subtitles.py" "$EP_ABS" "$CONCAT_MP4" "$AUDIO_ABS" "$FINAL" "$WORK"

echo "已导出: $FINAL"
